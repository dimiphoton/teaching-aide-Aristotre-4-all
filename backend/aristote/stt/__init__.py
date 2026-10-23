"""Transcription des réponses orales, en local."""

from __future__ import annotations

from .whisper_engine import MockStt, SttEngine, SttResult, WhisperStt

__all__ = ["MockStt", "SttEngine", "SttResult", "WhisperStt", "build_stt"]


def build_stt(cfg) -> SttEngine:
    if cfg.engine == "whisper":
        return WhisperStt(cfg.model, language=cfg.language, compute_type=cfg.compute_type)
    return MockStt()
