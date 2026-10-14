"""Évaluation des moteurs OCR et de dictée sur le corpus réel collecté par les kiosques.

Le corpus (`aristote eval-export`) contient des paires (image ou audio, texte validé par l'élève).
Le texte validé sert de référence : on peut donc comparer n'importe quel moteur sans rien redemander aux élèves.

    # Mesure du moteur d'origine (texte brut enregistré au moment du scan)
    python -m eval.ocr_eval --corpus corpus/ --baseline -o eval/results/lecture-origine.json
    # Rejouer un autre moteur (sections [ocr] et [stt] d'une configuration de kiosque)
    python -m eval.ocr_eval --corpus corpus/ --kiosk-config hub.toml -o eval/results/lecture-hub.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

from .checks.metrics import cer, final_answer_match, wer
from .common import percentile


def load_corpus(root: Path) -> list[dict]:
    entries = []
    for meta_path in sorted(root.rglob("*.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if "texte_valide" not in meta:
            continue
        meta["kind"] = "scan" if meta["media"].endswith(".jpg") else "dictee"
        meta["media_path"] = meta_path.with_name(meta["media"])
        entries.append(meta)
    return entries


async def rerun(entries: list[dict], kiosk_config: Path) -> None:
    from aristote.config import load_config
    from aristote.ocr import build_ocr
    from aristote.stt import build_stt

    config = load_config(kiosk_config)
    ocr, stt = build_ocr(config.ocr), build_stt(config.stt)
    for e in entries:
        start = time.perf_counter()
        if e["kind"] == "scan":
            image = cv2.imdecode(np.frombuffer(e["media_path"].read_bytes(), np.uint8), cv2.IMREAD_COLOR)
            e["hypothese"] = (await ocr.recognize(image)).text
        else:
            e["hypothese"] = (await stt.transcribe(e["media_path"].read_bytes())).text
        e["secondes"] = time.perf_counter() - start


def summarize(entries: list[dict]) -> dict:
    out: dict = {}
    for kind, prefix, rate_name, rate in (("scan", "ocr", "ocr_cer", cer), ("dictee", "dictee", "dictee_wer", wer)):
        subset = [e for e in entries if e["kind"] == kind]
        if not subset:
            continue
        out[f"{prefix}_reponse_exacte"] = {"valeur": sum(final_answer_match(e["hypothese"], e["texte_valide"])
                                                         for e in subset) / len(subset), "fiable": True, "n": len(subset)}
        out[rate_name] = {"valeur": sum(rate(e["hypothese"], e["texte_valide"]) for e in subset) / len(subset),
                          "fiable": True, "n": len(subset)}
        seconds = [e["secondes"] for e in subset if "secondes" in e]
        if seconds:
            out[f"{prefix}_median_s"] = {"valeur": percentile(seconds, 0.5), "fiable": True}
    corrected = [e for e in entries if e.get("texte_brut") is not None]
    if corrected:
        out["taux_correction"] = {"valeur": sum(e["texte_brut"].strip() != e["texte_valide"].strip() for e in corrected)
                                  / len(corrected), "fiable": True, "n": len(corrected)}
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--corpus", type=Path, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--baseline", action="store_true", help="évalue le texte brut enregistré à la capture")
    group.add_argument("--kiosk-config", type=Path, help="rejoue les moteurs de cette configuration")
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args(argv)

    entries = load_corpus(args.corpus)
    if not entries:
        print("Corpus vide : activer eval_capture sur un kiosque, puis `aristote eval-export`.")
        return 1
    if args.baseline:
        for e in entries:
            e["hypothese"] = e.get("texte_brut") or ""
    else:
        asyncio.run(rerun(entries, args.kiosk_config))
    result = summarize(entries)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
