# UTF-8 LF
import time
from typing import Dict


def monotonic_ms() -> int:
    return int(time.monotonic() * 1000)


class Spans:
    """
    Minimal named span aggregator for latency accounting.
    Usage:
        spans = Spans()
        with spans.span("plan"): ...
        spans.ms("plan")
    """

    def __init__(self):
        self._acc: Dict[str, int] = {}

    def span(self, name: str):
        class _Span:
            def __init__(self, acc: Dict[str, int], key: str):
                self.acc = acc
                self.key = key
                self.start = None

            def __enter__(self):
                self.start = monotonic_ms()
                return self

            def __exit__(self, exc_type, exc, tb):
                dur = monotonic_ms() - self.start  # type: ignore
                self.acc[self.key] = self.acc.get(self.key, 0) + dur

        return _Span(self._acc, name)

    def ms(self, name: str) -> int:
        return int(self._acc.get(name, 0))
