from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
import sqlite3
import threading
import time
from typing import Protocol
from urllib.parse import parse_qs, urlparse, unquote

import psycopg2

logger = logging.getLogger(__name__)

_CACHE_TABLE_NAME = "qa_agent_response_cache"


class CacheBackend(Protocol):
    def get(self, cache_key: str, now: datetime) -> str | None:
        ...

    def set(self, cache_key: str, value: str, expires_at: datetime | None) -> None:
        ...

    def acquire_lock(
        self,
        cache_key: str,
        *,
        wait_timeout_seconds: float,
        poll_interval_seconds: float,
    ) -> object | None:
        ...

    def release_lock(self, lock_handle: object | None) -> None:
        ...


@dataclass(frozen=True)
class PostgresLockHandle:
    connection: object
    lock_id: int


class SqliteCache:
    def __init__(self, database_url: str, table_name: str = _CACHE_TABLE_NAME):
        self.database_url = database_url
        self.table_name = table_name
        self._connection: sqlite3.Connection | None = None
        self._connection_lock = threading.RLock()
        self._initialized = False

    def get(self, cache_key: str, now: datetime) -> str | None:
        connection = self._get_connection()
        with self._connection_lock:
            self._ensure_table(connection)
            cursor = connection.execute(
                f"SELECT value, expires_at FROM {self.table_name} WHERE cache_key = ?",
                (cache_key,),
            )
            row = cursor.fetchone()
            if row is None:
                return None

            value, expires_at_raw = row
            expires_at = _parse_sqlite_timestamp(expires_at_raw)
            if expires_at is not None and expires_at <= now:
                connection.execute(
                    f"DELETE FROM {self.table_name} WHERE cache_key = ?",
                    (cache_key,),
                )
                connection.commit()
                return None
            return value

    def set(self, cache_key: str, value: str, expires_at: datetime | None) -> None:
        connection = self._get_connection()
        with self._connection_lock:
            self._ensure_table(connection)
            connection.execute(
                (
                    f"INSERT INTO {self.table_name} (cache_key, value, expires_at) "
                    "VALUES (?, ?, ?) "
                    "ON CONFLICT(cache_key) DO UPDATE SET "
                    "value = excluded.value, expires_at = excluded.expires_at"
                ),
                (cache_key, value, _format_sqlite_timestamp(expires_at)),
            )
            connection.commit()

    def acquire_lock(
        self,
        cache_key: str,
        *,
        wait_timeout_seconds: float,
        poll_interval_seconds: float,
    ) -> object | None:
        return None

    def release_lock(self, lock_handle: object | None) -> None:
        return None

    def _get_connection(self) -> sqlite3.Connection:
        with self._connection_lock:
            if self._connection is None:
                location, use_uri = _parse_sqlite_location(self.database_url)
                self._connection = sqlite3.connect(
                    location,
                    check_same_thread=False,
                    uri=use_uri,
                )
            return self._connection

    def _ensure_table(self, connection: sqlite3.Connection) -> None:
        if self._initialized:
            return
        connection.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                cache_key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                expires_at TIMESTAMP NULL
            )
            """
        )
        connection.commit()
        self._initialized = True


class PostgresCache:
    def __init__(self, database_url: str, table_name: str = _CACHE_TABLE_NAME):
        self.database_url = database_url
        self.table_name = table_name
        self._ensure_table_lock = threading.Lock()
        self._initialized = False

    def get(self, cache_key: str, now: datetime) -> str | None:
        self._ensure_table()
        connection = self._connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    (
                        f"SELECT value, expires_at FROM {self.table_name} "
                        "WHERE cache_key = %s"
                    ),
                    (cache_key,),
                )
                row = cursor.fetchone()
                if row is None:
                    return None
                value, expires_at = row
                if expires_at is not None and expires_at <= now:
                    cursor.execute(
                        f"DELETE FROM {self.table_name} WHERE cache_key = %s",
                        (cache_key,),
                    )
                    return None
                return value
        finally:
            connection.close()

    def set(self, cache_key: str, value: str, expires_at: datetime | None) -> None:
        self._ensure_table()
        connection = self._connect()
        try:
            self._set_with_connection(connection, cache_key, value, expires_at)
        finally:
            connection.close()

    def acquire_lock(
        self,
        cache_key: str,
        *,
        wait_timeout_seconds: float,
        poll_interval_seconds: float,
    ) -> PostgresLockHandle:
        self._ensure_table()
        connection = self._connect()
        lock_id = _lock_id_for_key(cache_key)
        deadline = time.monotonic() + wait_timeout_seconds
        try:
            with connection.cursor() as cursor:
                while True:
                    cursor.execute("SELECT pg_try_advisory_lock(%s)", (lock_id,))
                    acquired = cursor.fetchone()[0]
                    if acquired:
                        return PostgresLockHandle(connection=connection, lock_id=lock_id)
                    if time.monotonic() >= deadline:
                        raise TimeoutError(
                            f"Timeout while waiting for cache advisory lock: {cache_key}"
                        )
                    time.sleep(poll_interval_seconds)
        except Exception:
            connection.close()
            raise

    def release_lock(self, lock_handle: object | None) -> None:
        if not isinstance(lock_handle, PostgresLockHandle):
            return
        try:
            with lock_handle.connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_unlock(%s)", (lock_handle.lock_id,))
        finally:
            lock_handle.connection.close()

    def set_with_lock(
        self,
        lock_handle: object | None,
        cache_key: str,
        value: str,
        expires_at: datetime | None,
    ) -> None:
        if isinstance(lock_handle, PostgresLockHandle):
            self._set_with_connection(lock_handle.connection, cache_key, value, expires_at)
            return
        self.set(cache_key, value, expires_at)

    def _set_with_connection(
        self,
        connection: object,
        cache_key: str,
        value: str,
        expires_at: datetime | None,
    ) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                (
                    f"INSERT INTO {self.table_name} (cache_key, value, expires_at) "
                    "VALUES (%s, %s, %s) "
                    "ON CONFLICT (cache_key) DO UPDATE SET "
                    "value = EXCLUDED.value, expires_at = EXCLUDED.expires_at"
                ),
                (cache_key, value, expires_at),
            )

    def _ensure_table(self) -> None:
        if self._initialized:
            return
        with self._ensure_table_lock:
            if self._initialized:
                return
            connection = self._connect()
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        f"""
                        CREATE TABLE IF NOT EXISTS {self.table_name} (
                            cache_key TEXT PRIMARY KEY,
                            value TEXT NOT NULL,
                            expires_at TIMESTAMP NULL
                        )
                        """
                    )
            finally:
                connection.close()
            self._initialized = True

    def _connect(self):
        connection = psycopg2.connect(self.database_url)
        connection.autocommit = True
        return connection


def create_cache_backend(database_url: str) -> CacheBackend:
    parsed = urlparse(database_url)
    if parsed.scheme.startswith("postgres"):
        return PostgresCache(database_url)
    if parsed.scheme.startswith("sqlite"):
        return SqliteCache(database_url)
    raise ValueError(f"Unsupported DATABASE_URL scheme for QA cache: {parsed.scheme}")


def _parse_sqlite_location(database_url: str) -> tuple[str, bool]:
    parsed = urlparse(database_url)
    path = unquote(parsed.path or "")
    query = parsed.query
    location = path.lstrip("/")

    if parsed.netloc:
        location = f"//{parsed.netloc}{path}"

    if location in {"", ":memory:"}:
        return ":memory:", False

    if location.startswith("file:"):
        suffix = f"?{query}" if query else ""
        return f"{location}{suffix}", True

    return location, False


def _parse_sqlite_timestamp(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    raise TypeError(f"Unsupported sqlite timestamp type: {type(value)!r}")


def _format_sqlite_timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat(timespec="microseconds")


def _lock_id_for_key(cache_key: str) -> int:
    digest = __import__("hashlib").sha256(cache_key.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=True)