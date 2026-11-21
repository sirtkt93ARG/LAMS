"""Límite de frecuencia en memoria (ventana deslizante). Protege respuestas, pistas y el canje de tokens LTI."""
from __future__ import annotations
import threading
import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, clock=time.monotonic):
        self._clock, self._hits, self._lock = clock, defaultdict(deque), threading.Lock()

    def allow(self, key: str, limit: int, window_s: float) -> bool:
        now = self._clock()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > window_s:
                q.popleft()
            if len(q) >= limit:
                return False
            q.append(now)
            return True
