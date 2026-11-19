import threading
import time


class TtlCache:
    """Cache en memoria con TTL para listas GET (evita round-trips lentos a Supabase)."""

    def __init__(self, ttl_sec=20):
        self.ttl_sec = max(1, int(ttl_sec))
        self._lock = threading.Lock()
        self._items = {}

    def get(self, key):
        now = time.monotonic()
        with self._lock:
            item = self._items.get(key)
            if item is None:
                return None
            stamped_at, value = item
            if now - stamped_at > self.ttl_sec:
                del self._items[key]
                return None
            return value

    def set(self, key, value):
        with self._lock:
            self._items[key] = (time.monotonic(), value)

    def invalidate(self, prefix=None):
        with self._lock:
            if prefix is None:
                self._items.clear()
                return
            for key in [k for k in self._items if str(k).startswith(prefix)]:
                del self._items[key]
