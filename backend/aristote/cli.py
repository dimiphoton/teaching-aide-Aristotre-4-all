"""Outils en ligne de commande pour le montage et le diagnostic d'un kiosque.

    aristote config                 # affiche la configuration validée
    aristote diag printer           # imprime un ticket de test (accents, symboles, image)
    aristote diag camera -o scan.jpg
    aristote diag buttons           # affiche les appuis pendant 30 s, LED de l'élève actif
    aristote diag mic -s 5 -o test.wav
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import threading
import time
import wave
from pathlib import Path

import numpy as np

from .config import load_config
from .hardware import build_hardware
from .hardware.base import ButtonKind, ButtonPress
from .hardware.printer_csn_a2 import Bitmap, Feed, Separator, Text, Ticket


def _test_ticket() -> Ticket:
    # Damier 64×64 : vérifie l'impression d'image (figures, QR codes futurs).
    yy, xx = np.mgrid[0:64, 0:64]
    checker = ((xx // 8 + yy // 8) % 2).astype(bool)
    return Ticket().add(
        Text("TEST ARISTOTE", size="L", bold=True, align="center"),
        Separator("="),
        Text("Accents : é è ê ë à â ç ù û ô î ï"),
        Text("Majuscules : É Ç À È (translittérées)"),
        Text("Maths : ½ ¼ x² ± ÷ ≤ ≥ √ 90° π ∞ 3×4"),
        Text("Gras", bold=True),
        Text("Moyen", size="M"),
        Text("Souligné", underline=True),
        Text("Inversé", inverse=True),
        Text("Aligné à droite", align="right"),
        Bitmap(checker),
        Separator(),
        Feed(3),
    )


def diag_printer(config) -> int:
    hw = build_hardware(config)
    if hw.printer is None:
        print("Imprimante indisponible : vérifier le câblage, l'alimentation 9 V et le port", config.hardware.printer.port)
        return 1
    paper = hw.printer.has_paper()
    print("Capteur papier :", {True: "papier présent", False: "PAS DE PAPIER", None: "pas de réponse (fil TX ?)"}[paper])
    hw.printer.print_ticket(_test_ticket())
    if hasattr(hw.printer, "printed"):
        print(hw.printer.printed[-1])
    hw.close()
    print("Ticket envoyé. Texte illisible → essayer baudrate = 9600 dans la configuration.")
    return 0


def diag_camera(config, output: Path) -> int:
    hw = build_hardware(config)
    if hw.camera is None:
        print("Caméra indisponible : vérifier la nappe (sens des contacts) et `rpicam-hello --list-cameras`.")
        return 1
    started = time.monotonic()
    result = hw.camera.capture()
    output.write_bytes(result.jpeg)
    h, w = result.image.shape[:2]
    print(f"Capture {w}×{h} en {time.monotonic() - started:.1f} s → {output}")
    print("Page détectée et redressée." if result.page_found else
          "Page NON détectée : contraste feuille/bureau insuffisant ou feuille hors champ.")
    hw.close()
    return 0


def diag_buttons(config, seconds: float) -> int:
    hw = build_hardware(config)
    done = threading.Event()

    def on_press(press: ButtonPress) -> None:
        if press.kind is ButtonKind.SCAN:
            print("SCAN")
            hw.leds.set_scan(True)
            threading.Timer(0.5, hw.leds.set_scan, args=(False,)).start()
        else:
            label = "appui long" if press.kind is ButtonKind.STUDENT_LONG else "appui"
            print(f"Élève {press.index + 1} ({config.kiosk.students[press.index]}) : {label}")
            hw.leds.set_active(None if press.kind is ButtonKind.STUDENT_LONG else press.index)

    hw.buttons.start(on_press)
    print(f"Appuyez sur les boutons pendant {seconds:.0f} s (Ctrl+C pour arrêter)…")
    try:
        done.wait(seconds)
    except KeyboardInterrupt:
        pass
    hw.close()
    return 0


def diag_mic(config, seconds: float, output: Path) -> int:
    hw = build_hardware(config)
    if hw.microphone is None:
        print("Micro indisponible : vérifier `arecord -l`.")
        return 1
    print(f"Enregistrement {seconds:.0f} s : parlez…")
    hw.microphone.start()
    time.sleep(seconds)
    wav = hw.microphone.stop()
    output.write_bytes(wav)
    with wave.open(io.BytesIO(wav)) as w:
        samples = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64)
    rms = float(np.sqrt(np.mean(samples ** 2))) if samples.size else 0.0
    dbfs = 20 * np.log10(rms / 32768) if rms > 0 else float("-inf")
    print(f"→ {output} · niveau moyen {dbfs:.1f} dBFS")
    if dbfs < -45:
        print("Niveau très faible : rapprocher le micro ou augmenter le gain (`alsamixer`).")
    hw.close()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aristote")
    parser.add_argument("--config", type=Path, default=None)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("config", help="affiche la configuration validée")
    diag = sub.add_parser("diag", help="diagnostic matériel").add_subparsers(dest="device", required=True)
    diag.add_parser("printer")
    cam = diag.add_parser("camera")
    cam.add_argument("-o", "--output", type=Path, default=Path("scan-test.jpg"))
    btn = diag.add_parser("buttons")
    btn.add_argument("-s", "--seconds", type=float, default=30)
    mic = diag.add_parser("mic")
    mic.add_argument("-s", "--seconds", type=float, default=5)
    mic.add_argument("-o", "--output", type=Path, default=Path("micro-test.wav"))
    args = parser.parse_args(argv)

    config = load_config(args.config)
    if args.command == "config":
        print(json.dumps(config.model_dump(mode="json"), indent=2, ensure_ascii=False))
        return 0
    if args.device == "printer":
        return diag_printer(config)
    if args.device == "camera":
        return diag_camera(config, args.output)
    if args.device == "buttons":
        return diag_buttons(config, args.seconds)
    if args.device == "mic":
        return diag_mic(config, args.seconds, args.output)
    return 2


if __name__ == "__main__":
    sys.exit(main())
