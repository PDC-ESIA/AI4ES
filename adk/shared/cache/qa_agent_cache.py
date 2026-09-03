from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
import os
import threading
from typing import Any

from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

from .cache_key import CacheIdentity, build_cache_identity
from .sql_cache import PostgresCache, create_cache_backend

logger = logging.getLogger(__name__)


class _SingleFlightCoordinator:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._inflight: dict[str, threading.Condition] = {}

    def try_become_leader(self, cache_key: str) -> bool:
        with self._lock:
            if cache_key in self._inflight:
                return False
            self._inflight[cache_key] = threading.Condition(self._lock)
            return True

    def wait_for_completion(self, cache_key: str, timeout_seconds: float) -> bool:
        with self._lock:
            condition = self._inflight.get(cache_key)
            if condition is None:
                return True
            condition.wait(timeout_seconds)
            return cache_key not in self._inflight

    def complete(self, cache_key: str) -> None:
        with self._lock:
            condition = self._inflight.pop(cache_key, None)
            if condition is not None:
                condition.notify_all()


class QaAgentResponseCache:
    def __init__(
        self,
        *,
        prompt_text: str,
        database_url: str | None,
        ttl_seconds: int = 86400,
        wait_timeout_seconds: float = 300.0,
        poll_interval_seconds: float = 0.1,
        clock: callable | None = None,
    ) -> None:
        self.prompt_text = prompt_text
        self.database_url = (database_url or "").strip()
        self.ttl_seconds = ttl_seconds
        self.wait_timeout_seconds = wait_timeout_seconds
        self.poll_interval_seconds = poll_interval_seconds
        self.clock = clock or datetime.utcnow
        self._coordinator = _SingleFlightCoordinator()
        self._backend = create_cache_backend(self.database_url) if self.database_url else None
        # ADK cria uma instância nova de CallbackContext a cada hook (before/after/
        # on_error), então o estado pendente não pode viver como atributo do
        # contexto: guardamos aqui, correlacionado pelo EventActions compartilhado
        # entre os hooks de uma mesma chamada de modelo.
        self._pending: dict[int, dict[str, Any]] = {}

    @staticmethod
    def _pending_key(callback_context: Any) -> int:
        return id(callback_context.actions)

    @classmethod
    def from_env(cls, *, prompt_text: str) -> "QaAgentResponseCache":
        ttl_seconds = int(os.environ.get("QA_AGENT_CACHE_TTL_SECONDS", "86400"))
        wait_timeout_seconds = float(
            os.environ.get("QA_AGENT_CACHE_WAIT_TIMEOUT_SECONDS", "300")
        )
        poll_interval_seconds = float(
            os.environ.get("QA_AGENT_CACHE_POLL_INTERVAL_SECONDS", "0.1")
        )
        return cls(
            prompt_text=prompt_text,
            database_url=os.environ.get("DATABASE_URL"),
            ttl_seconds=ttl_seconds,
            wait_timeout_seconds=wait_timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )

    async def before_model_callback(
        self, callback_context: Any, llm_request: LlmRequest
    ) -> LlmResponse | None:
        if self._backend is None:
            return None

        if self._pending.get(self._pending_key(callback_context)):
            return None

        identity = self._build_identity(llm_request)

        try:
            while True:
                cached_value = await asyncio.to_thread(self._backend.get, identity.cache_key, self.clock())
                if cached_value is not None:
                    return _response_from_text(cached_value)

                is_leader = await asyncio.to_thread(
                    self._coordinator.try_become_leader,
                    identity.cache_key,
                )
                if is_leader:
                    break

                finished = await asyncio.to_thread(
                    self._coordinator.wait_for_completion,
                    identity.cache_key,
                    self.wait_timeout_seconds,
                )
                if not finished:
                    logger.warning(
                        "QA cache timed out waiting for in-flight key %s; continuing without cache.",
                        identity.cache_key,
                    )
                    return None

            lock_handle = await self._safe_acquire_lock(identity.cache_key)
            if self._backend is None:
                self._coordinator.complete(identity.cache_key)
                return None

            cached_value = await asyncio.to_thread(self._backend.get, identity.cache_key, self.clock())
            if cached_value is not None:
                await self._safe_release_lock(lock_handle)
                self._coordinator.complete(identity.cache_key)
                return _response_from_text(cached_value)

            self._pending[self._pending_key(callback_context)] = {
                "cache_key": identity.cache_key,
                "lock_handle": lock_handle,
            }
            return None
        except Exception as exc:
            self._coordinator.complete(identity.cache_key)
            logger.warning(
                "QA cache disabled for this request after backend failure: %s",
                exc,
            )
            return None

    async def after_model_callback(
        self, callback_context: Any, llm_response: LlmResponse
    ) -> LlmResponse | None:
        pending = self._pending.get(self._pending_key(callback_context))
        if not pending:
            return None

        if llm_response.partial:
            return None

        if llm_response.error_code or llm_response.error_message:
            await self._finalize_pending(callback_context, store_value=None)
            return None

        if llm_response.get_function_calls() or llm_response.get_function_responses():
            return None

        final_text = _extract_text(llm_response)
        if final_text:
            await self._finalize_pending(callback_context, store_value=final_text)
        else:
            await self._finalize_pending(callback_context, store_value=None)
        return None

    async def on_model_error_callback(
        self,
        callback_context: Any,
        llm_request: LlmRequest,
        error: Exception,
    ) -> LlmResponse | None:
        pending = self._pending.get(self._pending_key(callback_context))
        if pending:
            logger.warning("QA cache releasing in-flight entry after model error: %s", error)
            await self._finalize_pending(callback_context, store_value=None)
        return None

    def _build_identity(self, llm_request: LlmRequest) -> CacheIdentity:
        model_name = llm_request.model or "unknown-model"
        return build_cache_identity(
            model_name=model_name,
            prompt_text=self.prompt_text,
            request_contents=llm_request.contents,
        )

    async def _finalize_pending(self, callback_context: Any, store_value: str | None) -> None:
        pending = self._pending.pop(self._pending_key(callback_context), None)
        if not pending:
            return

        cache_key = pending["cache_key"]
        lock_handle = pending.get("lock_handle")
        try:
            if store_value and self._backend is not None:
                expires_at = self.clock() + timedelta(seconds=self.ttl_seconds)
                if isinstance(self._backend, PostgresCache):
                    await asyncio.to_thread(
                        self._backend.set_with_lock,
                        lock_handle,
                        cache_key,
                        store_value,
                        expires_at,
                    )
                else:
                    await asyncio.to_thread(
                        self._backend.set,
                        cache_key,
                        store_value,
                        expires_at,
                    )
        except Exception as exc:
            logger.warning("QA cache failed to persist response for %s: %s", cache_key, exc)
        finally:
            await self._safe_release_lock(lock_handle)
            self._coordinator.complete(cache_key)

    async def _safe_acquire_lock(self, cache_key: str) -> object | None:
        if self._backend is None:
            return None
        try:
            return await asyncio.to_thread(
                self._backend.acquire_lock,
                cache_key,
                wait_timeout_seconds=self.wait_timeout_seconds,
                poll_interval_seconds=self.poll_interval_seconds,
            )
        except Exception as exc:
            logger.warning("QA cache could not acquire lock for %s: %s", cache_key, exc)
            return None

    async def _safe_release_lock(self, lock_handle: object | None) -> None:
        if self._backend is None or lock_handle is None:
            return
        try:
            await asyncio.to_thread(self._backend.release_lock, lock_handle)
        except Exception as exc:
            logger.warning("QA cache could not release advisory lock cleanly: %s", exc)


def create_qa_agent_response_cache(*, prompt_text: str) -> QaAgentResponseCache:
    return QaAgentResponseCache.from_env(prompt_text=prompt_text)


def _extract_text(llm_response: LlmResponse) -> str:
    if llm_response.content is None or not llm_response.content.parts:
        return ""
    chunks = []
    for part in llm_response.content.parts:
        text = getattr(part, "text", None)
        if text and not getattr(part, "thought", False):
            chunks.append(text)
    return "".join(chunks).strip()


def _response_from_text(text: str) -> LlmResponse:
    return LlmResponse(
        content=types.Content(role="model", parts=[types.Part.from_text(text=text)])
    )