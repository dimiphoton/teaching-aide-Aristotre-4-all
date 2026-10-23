"""Boutons physiques : 4 boutons élèves + 1 bouton SCAN.

- `GpioButtonPanel` : Raspberry Pi (gpiozero, boutons entre la broche et la masse, pull-up interne).
- `VirtualButtonPanel` : mini-PC (boutons câblés sur un clavier USB HID, touches relayées par l'interface
  web) et simulation. Les appuis sont injectés par `inject()`.

Un appui court sur un bouton élève sélectionne l'élève ; un appui long (≥ long_press_s) termine sa session.
"""

from __future__ import annotations

import time
from typing import Callable

from .base import ButtonCallback, ButtonKind, ButtonPress


class PressDecoder:
    """Transforme les fronts appui/relâchement d'un bouton élève en appui court ou long."""

    def __init__(self, index: int, long_press_s: float, clock: Callable[[], float] = time.monotonic) -> None:
        self.index = index
        self.long_press_s = long_press_s
        self._clock = clock
        self._pressed_at: float | None = None

    def down(self) -> None:
        self._pressed_at = self._clock()

    def up(self) -> ButtonPress | None:
        if self._pressed_at is None:
            return None  # relâchement sans appui connu (démarrage bouton enfoncé)
        duration = self._clock() - self._pressed_at
        self._pressed_at = None
        kind = ButtonKind.STUDENT_LONG if duration >= self.long_press_s else ButtonKind.STUDENT
        return ButtonPress(kind, self.index)


class GpioButtonPanel:
    def __init__(self, student_pins: list[int], scan_pin: int, long_press_s: float, bounce_s: float) -> None:
        from gpiozero import Button  # import tardif : absent hors Raspberry Pi

        self._decoders = [PressDecoder(i, long_press_s) for i in range(len(student_pins))]
        self._student = [Button(pin, pull_up=True, bounce_time=bounce_s) for pin in student_pins]
        self._scan = Button(scan_pin, pull_up=True, bounce_time=bounce_s)
        self._buttons = [*self._student, self._scan]

    def start(self, callback: ButtonCallback) -> None:
        for button, decoder in zip(self._student, self._decoders):
            button.when_pressed = decoder.down
            button.when_released = lambda d=decoder: self._emit(callback, d.up())
        self._scan.when_pressed = lambda: callback(ButtonPress(ButtonKind.SCAN))

    @staticmethod
    def _emit(callback: ButtonCallback, press: ButtonPress | None) -> None:
        if press is not None:
            callback(press)

    def close(self) -> None:
        for button in self._buttons:
            button.close()


class VirtualButtonPanel:
    """Boutons injectés par logiciel (clavier HID relayé par l'interface, ou simulation)."""

    # Touches suggérées pour un encodeur clavier (RP2040, encodeur arcade USB) : F13 à F17.
    KEYMAP = {"F13": 0, "F14": 1, "F15": 2, "F16": 3, "F17": "scan"}

    def __init__(self, n_students: int) -> None:
        self._n = n_students
        self._callback: ButtonCallback | None = None

    def start(self, callback: ButtonCallback) -> None:
        self._callback = callback

    def inject(self, press: ButtonPress) -> None:
        if self._callback is None:
            return
        if press.kind is not ButtonKind.SCAN and not (press.index is not None and 0 <= press.index < self._n):
            raise ValueError(f"bouton élève inexistant : {press.index}")
        self._callback(press)

    def inject_key(self, key: str, long: bool = False) -> bool:
        """Injecte un appui à partir d'un nom de touche ; renvoie False si la touche n'est pas affectée."""
        target = self.KEYMAP.get(key)
        if target is None:
            return False
        if target == "scan":
            self.inject(ButtonPress(ButtonKind.SCAN))
        elif isinstance(target, int) and target < self._n:
            self.inject(ButtonPress(ButtonKind.STUDENT_LONG if long else ButtonKind.STUDENT, target))
        else:
            return False
        return True

    def close(self) -> None:
        self._callback = None
