"""Captures en attente de validation par l'élève (scan ou dictée).

Entre la reconnaissance et la validation, l'image ou l'audio reste en mémoire seulement. À la validation,
il est soit oublié (par défaut), soit versé au corpus d'évaluation (`eval_capture`), soit archivé
localement (`keep_scans`).
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field


@dataclass
class PendingCapture:
    kind: str                 # "scan" | "dictee"
    media: bytes
    raw_text: str
    confidence: float | None
    engine: str
    student: str
    created: float = field(default_factory=time.monotonic)


class CaptureStore:
    def __init__(self, ttl_s: float = 900, max_items: int = 8) -> None:
        self._items: dict[str, PendingCapture] = {}
        self._ttl = ttl_s
        self._max = max_items

    def add(self, capture: PendingCapture) -> str:
        self._expire()
        while len(self._items) >= self._max:
            self._items.pop(next(iter(self._items)))
        capture_id = uuid.uuid4().hex
        self._items[capture_id] = capture
        return capture_id

    def pop(self, capture_id: str) -> PendingCapture | None:
        self._expire()
        return self._items.pop(capture_id, None)

    def clear(self) -> None:
        self._items.clear()

    def _expire(self) -> None:
        now = time.monotonic()
        for key in [k for k, c in self._items.items() if now - c.created > self._ttl]:
            del self._items[key]
