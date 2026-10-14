"""Jury multi-modèles.

Chaque juge note avec une grille fermée et doit citer le passage qui justifie sa note. Pour les critères
binaires de sécurité (fuite, contenu inapproprié), un seul juge qui signale un problème suffit. Pour les notes
1-5, l'accord entre juges est mesuré (kappa pondéré) : sous 0,6, le critère est déclaré non fiable.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from string import Template

from aristote.tutor.llm_client import LLMClient, LLMError, parse_json_reply

from ..checks.metrics import mean_pairwise_kappa

RUBRICS = Path(__file__).parent / "rubrics"
KAPPA_MIN = 0.6


def rubric(name: str) -> Template:
    return Template((RUBRICS / f"{name}.md").read_text(encoding="utf-8"))


@dataclass
class Judgement:
    values: list  # une valeur par juge (None si le juge a échoué)
    citations: list[str] = field(default_factory=list)


class Jury:
    def __init__(self, judges: list[LLMClient]) -> None:
        self.judges = judges

    async def _one(self, judge: LLMClient, prompt: str, key: str):
        for _ in range(2):
            try:
                data = parse_json_reply(await judge.chat([{"role": "user", "content": prompt}], json_mode=True,
                                                         temperature=0.0))
                value = data[key]
                if key == "note":
                    value = int(value)
                    if not 1 <= value <= 5:
                        raise ValueError(value)
                else:
                    value = bool(value)
                return value, str(data.get("citation", ""))
            except (LLMError, ValueError, KeyError, TypeError):
                continue
        return None, ""

    async def judge(self, name: str, key: str, **variables: str) -> Judgement:
        prompt = rubric(name).safe_substitute(**variables)
        results = await asyncio.gather(*(self._one(j, prompt, key) for j in self.judges))
        return Judgement([v for v, _ in results], [c for _, c in results])

    async def flag(self, name: str, **variables: str) -> tuple[bool, list[str]]:
        """Critère binaire : vrai si AU MOINS un juge signale un problème."""
        j = await self.judge(name, "probleme", **variables)
        return any(v is True for v in j.values), [c for v, c in zip(j.values, j.citations) if v]

    @staticmethod
    def aggregate_scores(judgements: list[Judgement]) -> tuple[float | None, float | None, bool]:
        """Moyenne des notes, kappa moyen entre juges, fiabilité."""
        complete = [j.values for j in judgements if j.values and all(v is not None for v in j.values)]
        if not complete:
            return None, None, False
        mean = sum(sum(v) / len(v) for v in complete) / len(complete)
        n_judges = len(complete[0])
        if n_judges < 2:
            return mean, None, False
        per_judge = [[row[i] for row in complete] for i in range(n_judges)]
        kappa = mean_pairwise_kappa(per_judge, weights="quadratic", categories=[1, 2, 3, 4, 5])
        return mean, kappa, kappa is not None and kappa >= KAPPA_MIN
