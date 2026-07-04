"""
rate_limit.py
─────────────
Rate limiting simple en memoria, por ventana deslizante.

Suficiente para un MVP de un solo proceso. Si el servicio corre con
más de un worker/proceso (gunicorn -w N, múltiples réplicas, etc.) cada
uno tendría su propio contador y el límite efectivo se multiplica por N.
Para eso hace falta un store compartido (Redis, por ejemplo) — ver
README, sección Roadmap.
"""

import time
from collections import defaultdict, deque
from threading import Lock


class RateLimiter:
    def __init__(self):
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str, limit: int, window_seconds: int = 60) -> bool:
        """True si la solicitud identificada por `key` entra dentro del
        límite `limit` solicitudes por `window_seconds`."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > window_seconds:
                hits.popleft()
            if len(hits) >= limit:
                return False
            hits.append(now)
            return True


# Instancia compartida por toda la app.
rate_limiter = RateLimiter()
