"""Normalisation des étiquettes de misconceptions renvoyées par le LLM.

Les étiquettes du catalogue du cours sont stables (le professeur les agrège dans Obsidian). Une
étiquette proposée par le LLM est rapprochée du catalogue si elle en est très proche ; sinon elle est
conservée avec le préfixe `nouvelle:` pour que le professeur la repère et l'ajoute éventuellement au cours.
"""

from __future__ import annotations

import difflib
import re

from .answers import strip_accents

NEW_PREFIX = "nouvelle:"


def slugify(text: str, max_len: int = 60) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", strip_accents(text.lower())).strip("-")
    return slug[:max_len].rstrip("-")


def normalize_tag(raw: str | None, catalog_ids: list[str]) -> str | None:
    if not raw or not str(raw).strip() or str(raw).strip().lower() in ("null", "none", "aucune"):
        return None
    raw = str(raw).strip()
    proposed_new = raw.lower().startswith(NEW_PREFIX)
    slug = slugify(raw[len(NEW_PREFIX):] if proposed_new else raw)
    if not slug:
        return None
    if slug in catalog_ids:
        return slug
    close = difflib.get_close_matches(slug, catalog_ids, n=1, cutoff=0.85)
    if close:
        return close[0]
    return f"{NEW_PREFIX}{slug}"
