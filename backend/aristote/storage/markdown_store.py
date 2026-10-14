"""Stockage des sessions en Markdown (en-tête YAML lisible par Dataview).

Arborescence produite dans le dossier synchronisé du kiosque :

    <vault>/<kiosque>/
    ├── kiosque.md
    └── eleves/<pseudo>/
        ├── profil.md
        └── sessions/AAAA-MM-JJ_HHMM_<pseudo>.md

Règles :
- écriture atomique (fichier temporaire + rename) : une coupure de courant laisse l'ancienne version
  ou la nouvelle, jamais un fichier tronqué ;
- la session est réécrite après chaque tentative : au pire, on perd la tentative en cours ;
- le texte des élèves est neutralisé pour ne pas créer de tags, liens ou champs Dataview dans le coffre
  du professeur.
"""

from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


# --- Écriture atomique et en-têtes ----------------------------------------------------------------

def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    dir_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(dir_fd)  # rend le rename durable
    finally:
        os.close(dir_fd)


def dump_frontmatter(meta: dict[str, Any]) -> str:
    body = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False, default_flow_style=None, width=120)
    return f"---\n{body}---\n"


_FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n?", re.DOTALL)


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    match = _FRONTMATTER.match(text)
    if not match:
        return {}, text
    meta = yaml.safe_load(match.group(1)) or {}
    return meta, text[match.end():]


_MD_SPECIAL = re.compile(r"([\\`*_\[\]#|<>~=$^])")


def sanitize(text: str) -> str:
    """Neutralise un texte libre d'élève (ou issu de l'OCR / du LLM) avant de l'écrire dans le coffre.

    Échappe la syntaxe Markdown/Obsidian (#tag, [[lien]], tableaux, HTML, LaTeX, surlignage) et casse les
    champs en ligne Dataview (`clé:: valeur`) qui pollueraient les requêtes du professeur.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    text = _MD_SPECIAL.sub(r"\\\1", text)
    text = text.replace("::", ": :")
    return text


def quote(text: str) -> str:
    """Texte multiligne rendu comme citation Markdown."""
    return "\n".join(f"> {line}" if line else ">" for line in sanitize(text).split("\n"))


# --- Modèle de données ----------------------------------------------------------------------------

class InputMode(str, Enum):
    SAISIE = "saisie"
    SCAN = "scan"
    DICTEE = "dictee"


class Verdict(str, Enum):
    JUSTE = "juste"
    PARTIEL = "partiel"
    FAUX = "faux"
    INCOMPRIS = "incompris"  # réponse illisible ou hors sujet : ne compte pas comme une erreur


class ItemStatus(str, Enum):
    EN_COURS = "en_cours"
    VALIDE = "valide"
    VERROUILLE = "verrouille"
    ABANDONNE = "abandonne"


class SessionStatus(str, Enum):
    EN_COURS = "en_cours"
    TERMINEE = "terminee"


@dataclass
class Attempt:
    number: int
    mode: InputMode
    answer: str
    verdict: Verdict
    ts: datetime
    misconception: str | None = None
    confidence: float | None = None  # confiance OCR / dictée
    raw_text: str | None = None      # texte brut du moteur, si l'élève l'a corrigé
    tutor_reply: str | None = None


@dataclass
class Item:
    index: int
    notion: str
    question: str
    status: ItemStatus = ItemStatus.EN_COURS
    attempts: list[Attempt] = field(default_factory=list)
    diagnostic: str | None = None
    remediation: str | None = None
    prerequisite: str | None = None
    printed: bool = False

    @property
    def errors(self) -> int:
        return sum(1 for a in self.attempts if a.verdict in (Verdict.FAUX, Verdict.PARTIEL))


@dataclass
class Session:
    student: str
    kiosk: str
    start: datetime
    subject: str | None = None
    end: datetime | None = None
    status: SessionStatus = SessionStatus.EN_COURS
    close_reason: str | None = None
    items: list[Item] = field(default_factory=list)
    path: Path | None = None

    @property
    def notions(self) -> list[str]:
        return list(dict.fromkeys(item.notion for item in self.items))

    @property
    def misconceptions(self) -> list[str]:
        tags = (a.misconception for item in self.items for a in item.attempts if a.misconception)
        return list(dict.fromkeys(tags))

    @property
    def needs_teacher(self) -> bool:
        return any(item.status is ItemStatus.VERROUILLE for item in self.items)


# --- Rendu ----------------------------------------------------------------------------------------

_STATUS_LABEL = {
    ItemStatus.EN_COURS: "EN COURS",
    ItemStatus.VALIDE: "VALIDÉ",
    ItemStatus.VERROUILLE: "VERROUILLÉ",
    ItemStatus.ABANDONNE: "ABANDONNÉ",
}

_MODE_LABEL = {InputMode.SAISIE: "saisie", InputMode.SCAN: "scan", InputMode.DICTEE: "dictée"}


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat(timespec="seconds") if dt else None


def session_frontmatter(session: Session) -> dict[str, Any]:
    items = session.items
    return {
        "type": "session",
        "eleve": session.student,
        "kiosque": session.kiosk,
        "statut": session.status.value,
        "debut": _iso(session.start),
        "fin": _iso(session.end),
        "duree_min": round((session.end - session.start).total_seconds() / 60, 1) if session.end else None,
        "matiere": session.subject,
        "notions": session.notions,
        "items_total": len(items),
        "items_valides": sum(i.status is ItemStatus.VALIDE for i in items),
        "items_verrouilles": sum(i.status is ItemStatus.VERROUILLE for i in items),
        "tentatives": sum(len(i.attempts) for i in items),
        "erreurs": sum(i.errors for i in items),
        "misconceptions": session.misconceptions,
        "a_revoir_prof": session.needs_teacher,
        "fin_motif": session.close_reason,
    }


def render_attempt(attempt: Attempt) -> str:
    details = [_MODE_LABEL[attempt.mode]]
    if attempt.confidence is not None:
        details.append(f"confiance {attempt.confidence:.2f}")
    details.append(f"{attempt.ts:%H:%M:%S}")
    head = f"- **Tentative {attempt.number}** ({', '.join(details)}) → {attempt.verdict.value}"
    if attempt.misconception:
        head += f" · misconception `{attempt.misconception}`"
    lines = [head, *(f"  {line}" for line in quote(attempt.answer).split("\n"))]
    if attempt.raw_text is not None and attempt.raw_text != attempt.answer:
        lines.append(f"  - Texte reconnu avant correction : {sanitize(attempt.raw_text)}")
    if attempt.tutor_reply:
        lines.append(f"  - Tuteur : {sanitize(attempt.tutor_reply)}")
    return "\n".join(lines)


def render_item(item: Item) -> str:
    out = [
        f"## Item {item.index} — {item.notion} — {_STATUS_LABEL[item.status]} ({item.errors}/3)",
        "",
        f"**Question** : {sanitize(item.question)}",
        "",
    ]
    out.extend(render_attempt(a) for a in item.attempts)
    extras = []
    if item.diagnostic:
        extras.append(f"- **Diagnostic** : {sanitize(item.diagnostic)}")
    if item.prerequisite:
        extras.append(f"- **Prérequis proposé** : `{item.prerequisite}`")
    if item.remediation:
        suffix = " (ticket imprimé)" if item.printed else ""
        extras.append(f"- **Remédiation**{suffix} : {sanitize(item.remediation)}")
    if extras:
        out.extend(["", *extras])
    return "\n".join(out)


def render_session(session: Session) -> str:
    title = f"# Session {session.student} — {session.start:%d/%m/%Y %H:%M}"
    body = "\n\n".join(render_item(item) for item in session.items) or "_Aucun item._"
    return f"{dump_frontmatter(session_frontmatter(session))}\n{title}\n\n{body}\n"


# --- Magasin --------------------------------------------------------------------------------------

class MarkdownStore:
    def __init__(self, kiosk_dir: Path, kiosk_id: str) -> None:
        self.root = kiosk_dir
        self.kiosk_id = kiosk_id

    def student_dir(self, student: str) -> Path:
        return self.root / "eleves" / student

    def _new_session_path(self, session: Session) -> Path:
        folder = self.student_dir(session.student) / "sessions"
        stem = f"{session.start:%Y-%m-%d_%H%M}_{session.student}"
        path = folder / f"{stem}.md"
        n = 2
        while path.exists():
            path = folder / f"{stem}_{n}.md"
            n += 1
        return path

    def save_session(self, session: Session) -> Path:
        if session.path is None:
            session.path = self._new_session_path(session)
        atomic_write(session.path, render_session(session))
        return session.path

    def write_kiosk_status(self, meta: dict[str, Any], body: str = "") -> Path:
        path = self.root / "kiosque.md"
        meta = {"type": "kiosque", "kiosque": self.kiosk_id, **meta}
        atomic_write(path, f"{dump_frontmatter(meta)}\n# Kiosque {self.kiosk_id}\n\n{body}\n")
        return path
