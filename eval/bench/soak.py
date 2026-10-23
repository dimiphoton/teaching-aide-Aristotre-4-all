"""Endurance : sessions d'élèves simulées en continu pendant N heures (cible : 72 h, 0 plantage, < 75 °C).

    python -m eval.bench.soak --url http://127.0.0.1:8000 --hours 72 -o eval/results/endurance.json

À lancer sur le kiosque (lecture de la température du processeur dans /sys).
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

import httpx

THERMAL = Path("/sys/class/thermal/thermal_zone0/temp")
ANSWERS = ["2/7", "7/12", "je ne sais pas", "3x + 6", "D", "la Bastille", "went", "12"]


def cpu_temp() -> float | None:
    try:
        return int(THERMAL.read_text()) / 1000
    except (OSError, ValueError):
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--hours", type=float, default=72)
    parser.add_argument("--pause", type=float, default=2.0, help="secondes entre deux actions")
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args(argv)

    client = httpx.Client(base_url=args.url, timeout=60)
    end = time.monotonic() + args.hours * 3600
    stats = {"actions": 0, "erreurs": 0, "temp_max": None, "derniere_erreur": None}
    rng = random.Random(42)
    while time.monotonic() < end:
        try:
            client.post(f"/api/students/{rng.randrange(4)}/select").raise_for_status()
            client.post("/api/tutor/next").raise_for_status()
            for _ in range(rng.randint(1, 4)):
                client.post("/api/tutor/answer", json={"text": rng.choice(ANSWERS)})
                stats["actions"] += 1
                time.sleep(args.pause)
            if rng.random() < 0.3:
                client.post("/api/session/end")
        except httpx.HTTPError as exc:
            stats["erreurs"] += 1
            stats["derniere_erreur"] = f"{time.strftime('%H:%M:%S')} {exc}"
            time.sleep(5)
        temp = cpu_temp()
        if temp is not None:
            stats["temp_max"] = max(stats["temp_max"] or 0, temp)
    stats["ok"] = stats["erreurs"] == 0 and (stats["temp_max"] or 0) < 75
    text = json.dumps(stats, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text)
    return 0 if stats["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
