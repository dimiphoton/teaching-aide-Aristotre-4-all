"""Outils partagés par le harnais d'évaluation."""

from __future__ import annotations

import os
import time
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aristote.tutor.llm_client import LLMClient, Message, OpenAICompatibleClient

ROOT = Path(__file__).resolve().parents[1]
WEIGHTS = Path(__file__).resolve().parent / "weights.toml"


def load_toml(path: Path | str) -> dict[str, Any]:
    with Path(path).open("rb") as fh:
        return tomllib.load(fh)


def make_llm(section: dict[str, Any]) -> OpenAICompatibleClient:
    key_env = section.get("api_key_env") or ""
    return OpenAICompatibleClient(section["base_url"], section["model"],
                                  os.environ.get(key_env) if key_env else None,
                                  temperature=section.get("temperature", 0.3), timeout_s=section.get("timeout_s", 60))


@dataclass
class CallRecord:
    json_mode: bool
    raw: str
    seconds: float


@dataclass
class RecordingLLM:
    """Enveloppe un LLM et enregistre chaque appel (validité JSON, latence)."""
    inner: LLMClient
    calls: list[CallRecord] = field(default_factory=list)

    async def chat(self, messages: list[Message], *, json_mode: bool = False, temperature: float | None = None) -> str:
        start = time.perf_counter()
        raw = await self.inner.chat(messages, json_mode=json_mode, temperature=temperature)
        self.calls.append(CallRecord(json_mode, raw, time.perf_counter() - start))
        return raw


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    k = (len(ordered) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo)


def criterion_score(value: float | None, target: float, zero: float) -> float | None:
    """100 si la cible est atteinte, 0 à la valeur `zero`, linéaire entre les deux.

    Le sens (plus grand ou plus petit = mieux) se déduit de la position de `zero` par rapport à `target`.
    """
    if value is None:
        return None
    higher_is_better = zero < target
    if (higher_is_better and value >= target) or (not higher_is_better and value <= target):
        return 100.0
    span = abs(target - zero)
    gap = abs(target - value)
    return max(0.0, 100.0 * (1 - gap / span)) if span else 0.0
