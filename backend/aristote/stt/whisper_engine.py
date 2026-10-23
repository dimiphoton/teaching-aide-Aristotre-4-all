from __future__ import annotations

import asyncio
import io
import math
import wave
from dataclasses import dataclass
from typing import Protocol

import numpy as np


@dataclass
class SttResult:
    text: str
    confidence: float | None
    engine: str


class SttEngine(Protocol):
    name: str

    async def transcribe(self, wav: bytes) -> SttResult: ...


def wav_to_float32(wav: bytes) -> np.ndarray:
    with wave.open(io.BytesIO(wav)) as w:
        if w.getsampwidth() != 2 or w.getnchannels() != 1:
            raise ValueError("WAV mono 16 bits attendu")
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    return pcm.astype(np.float32) / 32768.0


class WhisperStt:
    """faster-whisper en local. Modèle `base` en int8 : environ le temps réel sur Raspberry Pi 5.

    Le modèle est téléchargé une seule fois à l'installation (deploy/install.sh), puis utilisé hors ligne.
    """

    name = "whisper"

    def __init__(self, model: str = "base", language: str = "fr", compute_type: str = "int8") -> None:
        from faster_whisper import WhisperModel

        self._model = WhisperModel(model, device="cpu", compute_type=compute_type)
        self._language = language

    def _run(self, wav: bytes) -> SttResult:
        audio = wav_to_float32(wav)
        if audio.size == 0:
            return SttResult("", 0.0, self.name)
        segments, _ = self._model.transcribe(audio, language=self._language, beam_size=5, vad_filter=True,
                                             condition_on_previous_text=False)
        segments = list(segments)
        text = " ".join(s.text.strip() for s in segments).strip()
        confidence = math.exp(sum(s.avg_logprob for s in segments) / len(segments)) if segments else 0.0
        return SttResult(text, round(confidence, 3), self.name)

    async def transcribe(self, wav: bytes) -> SttResult:
        return await asyncio.to_thread(self._run, wav)


class MockStt:
    name = "mock"

    def __init__(self, text: str = "sept douzièmes") -> None:
        self.text = text

    async def transcribe(self, wav: bytes) -> SttResult:
        return SttResult(self.text, 0.9, self.name)
