"""Trava de escrita para SQLite em cenarios com concorrencia entre processos.

Usa um `FileLock` por arquivo de banco e um `RLock` por processo para evitar
colisoes entre threads do mesmo processo e entre processos diferentes.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from hashlib import sha1
from pathlib import Path
from typing import Iterator

from filelock import FileLock, Timeout

_THREAD_LOCKS: dict[str, threading.RLock] = {}
_LOCKS_GUARD = threading.Lock()


def _lock_key(db_path: str | Path) -> str:
    return str(Path(db_path).resolve()).lower()


def _lock_file_path(db_path: str | Path) -> Path:
    path = Path(db_path)
    digest = sha1(_lock_key(path).encode("utf-8")).hexdigest()
    base_dir = path.parent if path.parent.exists() else Path(".")
    return base_dir / f".{path.stem}.{digest}.sqlite.lock"


def _get_thread_lock(key: str) -> threading.RLock:
    with _LOCKS_GUARD:
        lock = _THREAD_LOCKS.get(key)
        if lock is None:
            lock = threading.RLock()
            _THREAD_LOCKS[key] = lock
        return lock


@contextmanager
def sqlite_write_lock(db_path: str | Path, *, timeout: float = 30.0) -> Iterator[None]:
    """Serializa escritas no banco SQLite por arquivo."""
    key = _lock_key(db_path)
    thread_lock = _get_thread_lock(key)
    lock_path = _lock_file_path(db_path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    file_lock = FileLock(str(lock_path))

    with thread_lock:
        try:
            with file_lock.acquire(timeout=timeout):
                yield
        except Timeout as exc:
            raise TimeoutError(f"Timeout aguardando lock de escrita em {db_path}") from exc
