from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import hashlib
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CacheIdentity:
    cache_key: str
    model_name: str
    prompt_hash: str
    request_hash: str


def hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_cache_identity(
    *, model_name: str, prompt_text: str, request_contents: Any
) -> CacheIdentity:
    normalized_model = model_name.strip() or "unknown-model"
    prompt_hash = hash_text(prompt_text)
    request_payload = _normalize_for_hash(request_contents)
    request_hash = hash_text(
        json.dumps(request_payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    )
    cache_key = f"qa_agent:{normalized_model}:{prompt_hash}:{request_hash}"
    return CacheIdentity(
        cache_key=cache_key,
        model_name=normalized_model,
        prompt_hash=prompt_hash,
        request_hash=request_hash,
    )


def _normalize_for_hash(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, bytes):
        return {"__bytes__": value.hex()}
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {
            str(key): _normalize_for_hash(val)
            for key, val in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_normalize_for_hash(item) for item in value]
    if isinstance(value, set):
        normalized_items = [_normalize_for_hash(item) for item in value]
        return sorted(normalized_items, key=lambda item: json.dumps(item, ensure_ascii=True, sort_keys=True))

    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return _normalize_for_hash(
            model_dump(mode="python", by_alias=True, exclude_none=False)
        )

    dict_value = getattr(value, "__dict__", None)
    if isinstance(dict_value, dict) and dict_value:
        return _normalize_for_hash(dict_value)

    return repr(value)