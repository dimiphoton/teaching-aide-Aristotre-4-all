"""Corpus d'évaluation collecté par le kiosque (option `eval_capture`, désactivée par défaut).

Quand l'élève relit et valide le texte reconnu, on obtient une paire (média, vérité de référence) :
- `scan` : image JPEG + texte brut du moteur OCR + texte validé ;
- `dictee` : audio WAV + transcription brute + texte validé.

Ce dossier n'est JAMAIS dans le coffre synchronisé. Les fichiers sont supprimés après
`eval_retention_days` jours. L'export est une action explicite (`aristote eval-export`).
"""

from __future__ import annotations

import json
import tarfile
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from .markdown_store import atomic_write


class EvalCorpus:
    def __init__(self, root: Path, kiosk_id: str, retention_days: int = 90) -> None:
        self.root = root
        self.kiosk_id = kiosk_id
        self.retention = timedelta(days=retention_days)

    def save(self, kind: str, media: bytes, *, raw_text: str, validated_text: str, engine: str,
             student: str, item_id: str | None, confidence: float | None) -> Path:
        if kind not in ("scan", "dictee"):
            raise ValueError(kind)
        now = datetime.now().astimezone()
        folder = self.root / kind / f"{now:%Y-%m-%d}"
        folder.mkdir(parents=True, exist_ok=True)
        stem = uuid.uuid4().hex[:12]
        media_path = folder / f"{stem}.{'jpg' if kind == 'scan' else 'wav'}"
        media_path.write_bytes(media)
        meta = {
            "kiosque": self.kiosk_id, "eleve": student, "item": item_id, "date": now.isoformat(timespec="seconds"),
            "moteur": engine, "confiance": confidence, "texte_brut": raw_text, "texte_valide": validated_text,
            "media": media_path.name,
        }
        atomic_write(folder / f"{stem}.json", json.dumps(meta, ensure_ascii=False, indent=2))
        return media_path

    def purge(self, now: float | None = None) -> int:
        """Supprime les fichiers plus anciens que la durée de conservation ; renvoie le nombre supprimé."""
        limit = (now or time.time()) - self.retention.total_seconds()
        removed = 0
        if not self.root.exists():
            return 0
        for path in self.root.rglob("*"):
            if path.is_file() and path.stat().st_mtime < limit:
                path.unlink()
                removed += 1
        for folder in sorted((p for p in self.root.rglob("*") if p.is_dir()), reverse=True):
            if not any(folder.iterdir()):
                folder.rmdir()
        return removed

    def export(self, destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tarfile.open(destination, "w:gz") as tar:
            if self.root.exists():
                tar.add(self.root, arcname=f"eval_corpus_{self.kiosk_id}")
        return destination
