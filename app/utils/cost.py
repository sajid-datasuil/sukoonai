# UTF-8 LF
from collections import OrderedDict
from math import ceil


def simple_token_count(text: str) -> int:
    """
    Very rough token proxy: ~4 characters per token.
    Good enough for Week-1 counters and budgeting hooks.
    """
    if not text:
        return 0
    return int(ceil(len(text) / 4))


class TTSCacher:
    """
    Tiny in-memory LRU to simulate TTS cache hits.
    """
    def __init__(self, capacity: int = 256):
        self.capacity = capacity
        self._lru: OrderedDict[str, None] = OrderedDict()

    def get(self, key: str) -> bool:
        hit = key in self._lru
        if hit:
            self._lru.move_to_end(key)
        else:
            self._lru[key] = None
            if len(self._lru) > self.capacity:
                self._lru.popitem(last=False)
        return hit


def estimate_cost_per_minute_usd(tts_seconds: float) -> float:
    """
    Placeholder for $/min estimator (Principle #18). Week-1: return 0.0.
    """
    _ = tts_seconds
    return 0.0
