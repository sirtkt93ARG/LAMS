"""Limitador de frecuencia compartido entre procesos mediante la base de datos."""
from __future__ import annotations
import hashlib
import threading
import time


class RateLimiter:
    """Ventana fija atómica en Store; los workers comparten los mismos contadores."""

    def __init__(self, store, clock=time.time):
        self._store = store
        self._clock = clock
        self._operations = 0
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int, window_s: float) -> bool:
        if limit < 1 or window_s <= 0:
            return False
        now = self._clock()
        window_start = int(now // window_s * window_s)
        key_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()
        hits = self._store.increment_rate_limit(key_hash, window_start)
        # Limpieza oportunista: evita conservar indefinidamente claves que ya no se usan.
        with self._lock:
            self._operations += 1
            cleanup = self._operations % 256 == 0
        if cleanup:
            self._store.purge_rate_limits(window_start - 86400)
        return hits <= limit
