"""Interfaces communes des périphériques.

Chaque périphérique a une implémentation réelle et une implémentation simulée : le logiciel se développe
et se teste sur n'importe quel PC (`ARISTOTE_MOCK=1`).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Protocol

import numpy as np


class ButtonKind(str, Enum):
    STUDENT = "student"
    STUDENT_LONG = "student_long"
    SCAN = "scan"


@dataclass(frozen=True)
class ButtonPress:
    kind: ButtonKind
    index: int | None = None  # 0..3 pour un bouton élève, None pour SCAN


ButtonCallback = Callable[[ButtonPress], None]


class ButtonPanel(Protocol):
    def start(self, callback: ButtonCallback) -> None: ...
    def close(self) -> None: ...


class LedPanel(Protocol):
    def set_active(self, index: int | None) -> None: ...
    def set_scan(self, on: bool) -> None: ...
    def close(self) -> None: ...


@dataclass
class CaptureResult:
    image: np.ndarray      # BGR (convention OpenCV), page redressée si détectée
    jpeg: bytes
    page_found: bool


class Camera(Protocol):
    def capture(self) -> CaptureResult: ...
    def preview_jpeg(self) -> bytes: ...
    def close(self) -> None: ...


class Microphone(Protocol):
    def start(self) -> None: ...
    def stop(self) -> bytes:
        """Arrête l'enregistrement et renvoie un WAV mono 16 bits."""
        ...

    @property
    def recording(self) -> bool: ...
    def close(self) -> None: ...
