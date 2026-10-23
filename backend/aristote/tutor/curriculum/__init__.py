"""Chargement des cours."""

from __future__ import annotations

from pathlib import Path

import yaml

from .schema import AnswerType, Curriculum, CurriculumItem, Misconception, Notion

__all__ = ["AnswerType", "Curriculum", "CurriculumItem", "Misconception", "Notion", "load_curriculum"]


def load_curriculum(path: Path | str) -> Curriculum:
    with Path(path).open(encoding="utf-8") as fh:
        return Curriculum.model_validate(yaml.safe_load(fh))


def course_summary(curriculum: Curriculum) -> tuple[dict, str]:
    """En-tête et corps de `cours.md`, synchronisé vers Obsidian : structure du cours sans les réponses.

    Le professeur et ses prompts d'analyse y trouvent les notions, les prérequis et le catalogue de
    misconceptions. Les réponses attendues ne sont pas copiées (le coffre peut être partagé).
    """
    meta = {
        "type": "cours", "cours": curriculum.id, "titre": curriculum.titre, "matiere": curriculum.matiere,
        "niveau": curriculum.niveau, "notions": [n.id for n in curriculum.notions],
    }
    lines = [f"# Cours : {curriculum.titre}", ""]
    for notion in curriculum.notions:
        prereq = ", ".join(f"`{p}`" for p in notion.prerequis) or "aucun"
        lines += [f"## `{notion.id}` — {notion.titre}", "", f"- Prérequis : {prereq}",
                  f"- Questions : {len(notion.items)}"]
        if notion.misconceptions:
            lines.append("- Misconceptions répertoriées :")
            lines += [f"  - `{m.id}` : {m.description}" for m in notion.misconceptions]
        lines.append("")
    return meta, "\n".join(lines)
