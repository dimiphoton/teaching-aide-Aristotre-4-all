"""Bus d'événements interne.

Les rappels matériels (gpiozero) arrivent depuis des threads ; le bus les ramène dans la boucle asyncio
pour que toute la logique métier tourne dans un seul thread. Chaque abonné (WebSocket, gestionnaire de
session…) reçoit sa propre file.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Event:
    type: str
    payload: dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "payload": self.payload, "ts": self.ts}


class EventBus:
    def __init__(self, maxsize: int = 256) -> None:
        self._subscribers: set[asyncio.Queue[Event]] = set()
        self._maxsize = maxsize
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """À appeler au démarrage de l'application, depuis la boucle asyncio."""
        self._loop = loop

    def subscribe(self) -> asyncio.Queue[Event]:
        queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=self._maxsize)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[Event]) -> None:
        self._subscribers.discard(queue)

    def publish(self, event: Event) -> None:
        """Publie depuis la boucle asyncio. Un abonné saturé perd ses événements les plus anciens."""
        for queue in list(self._subscribers):
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            queue.put_nowait(event)

    def publish_threadsafe(self, event: Event) -> None:
        """Publie depuis n'importe quel thread (rappels gpiozero, sounddevice…)."""
        if self._loop is None or self._loop.is_closed():
            raise RuntimeError("EventBus.bind_loop() n'a pas été appelé")
        self._loop.call_soon_threadsafe(self.publish, event)


# Types d'événements
BUTTON_STUDENT = "button.student"          # payload: {"index": int}
BUTTON_STUDENT_LONG = "button.student_long"  # payload: {"index": int}
BUTTON_SCAN = "button.scan"
STUDENT_CHANGED = "student.changed"        # payload: {"index": int | None, "student": str | None}
SESSION_CLOSED = "session.closed"          # payload: {"student": str, "path": str, "reason": str}
PRINTER_STATUS = "printer.status"          # payload: {"ok": bool, "paper": bool | None}
