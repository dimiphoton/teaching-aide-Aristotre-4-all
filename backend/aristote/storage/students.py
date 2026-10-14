"""Profils pseudonymisés des élèves (`eleves/<pseudo>/profil.md`).

Le profil résume ce que le kiosque sait de l'élève et sert au tuteur pour adapter ses questions :
notions acquises, notions fragiles, misconceptions récurrentes. Il est mis à jour à la fin de chaque session.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .markdown_store import (
    ItemStatus,
    MarkdownStore,
    Session,
    atomic_write,
    dump_frontmatter,
    parse_frontmatter,
)


@dataclass
class StudentProfile:
    student: str
    kiosk: str
    button: int                                                   # 1 à 4
    acquired: list[str] = field(default_factory=list)              # notions validées sans verrou
    fragile: list[str] = field(default_factory=list)               # notions verrouillées, pas encore revalidées
    misconceptions: dict[str, int] = field(default_factory=dict)   # étiquette → nombre d'occurrences
    sessions: int = 0
    last_session: datetime | None = None

    def to_meta(self) -> dict:
        return {
            "type": "profil",
            "eleve": self.student,
            "kiosque": self.kiosk,
            "bouton": self.button,
            "sessions": self.sessions,
            "derniere_session": self.last_session.isoformat(timespec="seconds") if self.last_session else None,
            "notions_acquises": sorted(self.acquired),
            "notions_fragiles": sorted(self.fragile),
            "misconceptions": dict(sorted(self.misconceptions.items(), key=lambda kv: (-kv[1], kv[0]))),
        }

    @classmethod
    def from_meta(cls, meta: dict, *, student: str, kiosk: str, button: int) -> "StudentProfile":
        last = meta.get("derniere_session")
        return cls(
            student=student,
            kiosk=kiosk,
            button=button,
            acquired=list(meta.get("notions_acquises") or []),
            fragile=list(meta.get("notions_fragiles") or []),
            misconceptions={str(k): int(v) for k, v in (meta.get("misconceptions") or {}).items()},
            sessions=int(meta.get("sessions") or 0),
            last_session=datetime.fromisoformat(last) if isinstance(last, str) else last,
        )

    def apply_session(self, session: Session) -> None:
        """Intègre le bilan d'une session terminée."""
        for item in session.items:
            if item.status is ItemStatus.VALIDE:
                # Une notion fragile redevient acquise quand l'élève la valide ensuite sans verrou.
                if item.notion in self.fragile:
                    self.fragile.remove(item.notion)
                if item.notion not in self.acquired:
                    self.acquired.append(item.notion)
            elif item.status is ItemStatus.VERROUILLE:
                if item.notion in self.acquired:
                    self.acquired.remove(item.notion)
                if item.notion not in self.fragile:
                    self.fragile.append(item.notion)
            for attempt in item.attempts:
                if attempt.misconception:
                    self.misconceptions[attempt.misconception] = self.misconceptions.get(attempt.misconception, 0) + 1
        self.sessions += 1
        self.last_session = session.end or session.start


class ProfileRepository:
    def __init__(self, store: MarkdownStore, students: list[str]) -> None:
        self._store = store
        self._students = students

    def _path(self, student: str) -> Path:
        return self._store.student_dir(student) / "profil.md"

    def load(self, student: str) -> StudentProfile:
        button = self._students.index(student) + 1
        path = self._path(student)
        meta: dict = {}
        if path.exists():
            meta, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
        return StudentProfile.from_meta(meta, student=student, kiosk=self._store.kiosk_id, button=button)

    def save(self, profile: StudentProfile) -> Path:
        path = self._path(profile.student)
        lines = [f"# Profil {profile.student}", ""]
        if profile.fragile:
            lines += ["## Notions fragiles", *(f"- `{n}`" for n in sorted(profile.fragile)), ""]
        if profile.misconceptions:
            lines += ["## Misconceptions observées",
                      *(f"- `{tag}` × {count}" for tag, count in profile.to_meta()["misconceptions"].items()), ""]
        atomic_write(path, f"{dump_frontmatter(profile.to_meta())}\n" + "\n".join(lines) + "\n")
        return path
