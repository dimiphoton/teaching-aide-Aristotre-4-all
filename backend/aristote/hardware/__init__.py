"""Construction des périphériques à partir de la configuration.

Les bibliothèques propres au Raspberry Pi (gpiozero, picamera2, sounddevice) ne sont importées que si
le périphérique réel correspondant est demandé : le backend démarre sur n'importe quel PC en mode simulation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from ..config import Config
from .base import ButtonKind, ButtonPanel, ButtonPress, Camera, LedPanel, Microphone
from .buttons import GpioButtonPanel, VirtualButtonPanel
from .camera import MockCamera, OpenCVCamera, Picamera2Camera
from .leds import GpioLedPanel, MockLedPanel
from .microphone import MockMicrophone, SoundDeviceMicrophone
from .printer_csn_a2 import CsnA2Printer, PreviewPrinter, SerialTransport

log = logging.getLogger(__name__)

__all__ = ["Hardware", "build_hardware", "ButtonKind", "ButtonPress"]


@dataclass
class Hardware:
    buttons: ButtonPanel
    leds: LedPanel
    camera: Camera | None
    printer: Any  # CsnA2Printer | PreviewPrinter | None
    microphone: Microphone | None

    def close(self) -> None:
        for device in (self.buttons, self.leds, self.camera, self.printer, self.microphone):
            if device is None:
                continue
            try:
                device.close()
            except Exception:  # noqa: BLE001 - on ferme tout ce qui peut l'être
                log.exception("fermeture de %r", device)


def _safe(name: str, factory):
    """Un périphérique absent ne doit pas empêcher le kiosque de démarrer (le diagnostic le signale)."""
    try:
        return factory()
    except Exception:  # noqa: BLE001
        log.exception("périphérique indisponible : %s", name)
        return None


def build_hardware(config: Config) -> Hardware:
    hw = config.hardware
    n = len(config.kiosk.students)
    mock = hw.mode == "mock"

    if mock or hw.buttons.backend == "keyboard":
        buttons: ButtonPanel = VirtualButtonPanel(n)
    else:
        buttons = GpioButtonPanel(hw.buttons.student_pins[:n], hw.buttons.scan_pin,
                                  hw.buttons.long_press_s, hw.buttons.bounce_s)

    if mock or not hw.leds.enabled:
        leds: LedPanel = MockLedPanel(n)
    else:
        leds = GpioLedPanel(hw.leds.student_pins[:n], hw.leds.scan_pin)

    cam = hw.camera
    if mock or cam.backend == "mock":
        camera = MockCamera(cam.deskew)
    elif cam.backend == "picamera2":
        camera = _safe("caméra", lambda: Picamera2Camera(cam.width, cam.height, cam.deskew))
    else:
        camera = _safe("caméra", lambda: OpenCVCamera(cam.opencv_device, cam.width, cam.height, cam.deskew))

    pr = hw.printer
    if mock:
        printer = PreviewPrinter()
    elif not pr.enabled:
        printer = None
    else:
        printer = _safe("imprimante", lambda: CsnA2Printer(
            SerialTransport(pr.port, pr.baudrate),
            baudrate=pr.baudrate, heat_dots=pr.heat_dots, heat_time=pr.heat_time,
            heat_interval=pr.heat_interval, density=pr.density, break_time=pr.break_time,
            dot_print_time_s=pr.dot_print_time_s, dot_feed_time_s=pr.dot_feed_time_s,
        ))

    mic = hw.microphone
    if mock or mic.backend == "mock":
        microphone = MockMicrophone(mic.samplerate)
    else:
        microphone = _safe("micro", lambda: SoundDeviceMicrophone(mic.samplerate, mic.device, mic.max_seconds))

    return Hardware(buttons=buttons, leds=leds, camera=camera, printer=printer, microphone=microphone)
