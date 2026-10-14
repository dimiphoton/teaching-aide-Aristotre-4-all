"""Gestion des sessions élèves : bascule par bouton, fin par appui long ou inactivité, sauvegarde.

Toute la logique tourne dans la boucle asyncio (les appuis matériels y sont ramenés par l'EventBus) :
pas de verrou nécessaire ici.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Callable

from ..events import (
    BUTTON_SCAN,
    SESSION_CLOSED,
    STUDENT_CHANGED,
    Event,
    EventBus,
)
from ..hardware.base import ButtonKind, ButtonPress, LedPanel
from ..storage import MarkdownStore, ProfileRepository, Session, SessionStatus

log = logging.getLogger(__name__)


def local_now() -> datetime:
    return datetime.now().astimezone()


class SessionManager:
    def __init__(
        self,
        *,
        kiosk_id: str,
        students: list[str],
        store: MarkdownStore,
        profiles: ProfileRepository,
        leds: LedPanel,
        bus: EventBus | None = None,
        idle_timeout_s: float = 600,
        now: Callable[[], datetime] = local_now,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.kiosk_id = kiosk_id
        self.students = students
        self.store = store
        self.profiles = profiles
        self.leds = leds
        self.bus = bus
        self.idle_timeout_s = idle_timeout_s
        self._now = now
        self._monotonic = monotonic
        self.current: Session | None = None
        self.current_index: int | None = None
        self._last_activity = monotonic()

    # --- Entrées ----------------------------------------------------------------------------------

    def handle_press(self, press: ButtonPress) -> None:
        if press.kind is ButtonKind.SCAN:
            self.touch()
            self._publish(Event(BUTTON_SCAN))
        elif press.kind is ButtonKind.STUDENT:
            self.select(press.index)
        elif press.kind is ButtonKind.STUDENT_LONG:
            if press.index == self.current_index:
                self.end_current("appui_long")
            else:
                self.select(press.index)  # appui long sur un autre bouton : simple sélection

    def touch(self) -> None:
        """Signale une activité de l'élève (repousse la fin automatique)."""
        self._last_activity = self._monotonic()

    # --- Cycle de vie -----------------------------------------------------------------------------

    def select(self, index: int | None) -> Session | None:
        if index is None or not 0 <= index < len(self.students):
            raise ValueError(f"bouton élève invalide : {index}")
        self.touch()
        if index == self.current_index and self.current is not None:
            return self.current  # même élève : on continue sa session
        self.end_current("changement_eleve")
        student = self.students[index]
        self.current = Session(student=student, kiosk=self.kiosk_id, start=self._now())
        self.current_index = index
        self.leds.set_active(index)
        self._publish(Event(STUDENT_CHANGED, {"index": index, "student": student}))
        log.info("session ouverte : %s", student)
        return self.current

    def end_current(self, reason: str) -> Path | None:
        session = self.current
        if session is None:
            return None
        self.current, self.current_index = None, None
        self.leds.set_active(None)
        path = None
        if session.items:  # une session vide (élève qui a juste appuyé) ne produit pas de fichier
            session.end = self._now()
            session.status = SessionStatus.TERMINEE
            session.close_reason = reason
            path = self.store.save_session(session)
            profile = self.profiles.load(session.student)
            profile.apply_session(session)
            self.profiles.save(profile)
            self._publish(Event(SESSION_CLOSED, {"student": session.student, "path": str(path), "reason": reason}))
        self._publish(Event(STUDENT_CHANGED, {"index": None, "student": None}))
        log.info("session fermée : %s (%s)", session.student, reason)
        return path

    def check_idle(self) -> bool:
        """À appeler périodiquement ; ferme la session après `idle_timeout_s` sans activité."""
        if self.current is not None and self._monotonic() - self._last_activity >= self.idle_timeout_s:
            self.end_current("inactivite")
            return True
        return False

    def save_current(self) -> Path | None:
        """Sauvegarde intermédiaire (après chaque tentative)."""
        if self.current is None or not self.current.items:
            return None
        return self.store.save_session(self.current)

    def shutdown(self) -> None:
        self.end_current("arret_kiosque")

    def _publish(self, event: Event) -> None:
        if self.bus is not None:
            self.bus.publish(event)
