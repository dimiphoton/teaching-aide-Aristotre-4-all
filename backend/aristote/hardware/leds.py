"""LED des boutons (commandées via un ULN2803A : GPIO à 1 = LED allumée)."""

from __future__ import annotations


class GpioLedPanel:
    def __init__(self, student_pins: list[int], scan_pin: int) -> None:
        from gpiozero import LED  # import tardif : absent hors Raspberry Pi

        self._students = [LED(pin) for pin in student_pins]
        self._scan = LED(scan_pin)

    def set_active(self, index: int | None) -> None:
        for i, led in enumerate(self._students):
            led.on() if i == index else led.off()

    def set_scan(self, on: bool) -> None:
        self._scan.on() if on else self._scan.off()

    def blink_all(self, times: int = 3) -> None:
        """Signal de démarrage / d'erreur visible sans écran."""
        for led in [*self._students, self._scan]:
            led.blink(on_time=0.2, off_time=0.2, n=times)

    def close(self) -> None:
        for led in [*self._students, self._scan]:
            led.close()


class MockLedPanel:
    def __init__(self, n_students: int) -> None:
        self.states = [False] * n_students
        self.scan = False

    def set_active(self, index: int | None) -> None:
        self.states = [i == index for i in range(len(self.states))]

    def set_scan(self, on: bool) -> None:
        self.scan = on

    def blink_all(self, times: int = 3) -> None:
        pass

    def close(self) -> None:
        pass
