"""Accès sérialisé à l'imprimante (un seul ticket à la fois, depuis des threads)."""

from __future__ import annotations

import logging
import threading

from ..hardware.printer_csn_a2 import Ticket

log = logging.getLogger(__name__)


class PrinterService:
    def __init__(self, printer) -> None:
        self._printer = printer
        self._lock = threading.Lock()

    @property
    def available(self) -> bool:
        return self._printer is not None

    def print_ticket(self, ticket: Ticket) -> None:
        if self._printer is None:
            raise RuntimeError("imprimante indisponible")
        with self._lock:
            self._printer.print_ticket(ticket)

    def has_paper(self) -> bool | None:
        if self._printer is None:
            return None
        with self._lock:
            try:
                return self._printer.has_paper()
            except Exception:  # noqa: BLE001
                log.exception("lecture du capteur papier")
                return None
