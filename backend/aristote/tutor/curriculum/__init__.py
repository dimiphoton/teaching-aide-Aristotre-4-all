"""Chargement des cours."""

from __future__ import annotations

from pathlib import Path

import yaml

from .schema import AnswerType, Curriculum, CurriculumItem, Misconception, Notion

__all__ = ["AnswerType", "Curriculum", "CurriculumItem", "Misconception", "Notion", "load_curriculum"]


def load_curriculum(path: Path | str) -> Curriculum:
    with Path(path).open(encoding="utf-8") as fh:
        return Curriculum.model_validate(yaml.safe_load(fh))
