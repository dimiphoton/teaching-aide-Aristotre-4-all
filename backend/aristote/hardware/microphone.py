"""Enregistrement des réponses orales (WAV mono 16 bits, 16 kHz par défaut, format attendu par Whisper)."""

from __future__ import annotations

import io
import threading
import wave

import numpy as np


def to_wav(samples: np.ndarray, samplerate: int) -> bytes:
    """Encode des échantillons int16 mono en WAV."""
    pcm = np.asarray(samples, dtype=np.int16).reshape(-1)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(samplerate)
        wav.writeframes(pcm.tobytes())
    return buf.getvalue()


class SoundDeviceMicrophone:
    def __init__(self, samplerate: int = 16000, device: str = "", max_seconds: int = 60) -> None:
        import sounddevice as sd  # dépendance optionnelle (extra "audio")

        self._sd = sd
        self._samplerate = samplerate
        self._device = device or None
        self._max_frames = samplerate * max_seconds
        self._frames: list[np.ndarray] = []
        self._count = 0
        self._lock = threading.Lock()
        self._stream = None

    @property
    def recording(self) -> bool:
        return self._stream is not None

    def _callback(self, indata, frames, time_info, status) -> None:  # thread audio
        with self._lock:
            if self._count >= self._max_frames:
                return  # durée maximale atteinte : on ignore la suite
            chunk = indata[:, 0].copy()[: self._max_frames - self._count]
            self._frames.append(chunk)
            self._count += len(chunk)

    def start(self) -> None:
        if self._stream is not None:
            return
        with self._lock:
            self._frames, self._count = [], 0
        self._stream = self._sd.InputStream(
            samplerate=self._samplerate, channels=1, dtype="int16",
            device=self._device, callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> bytes:
        if self._stream is None:
            return to_wav(np.zeros(0, dtype=np.int16), self._samplerate)
        self._stream.stop()
        self._stream.close()
        self._stream = None
        with self._lock:
            samples = np.concatenate(self._frames) if self._frames else np.zeros(0, dtype=np.int16)
        return to_wav(samples, self._samplerate)

    def close(self) -> None:
        if self._stream is not None:
            self.stop()


class MockMicrophone:
    """Micro simulé : renvoie un enregistrement fourni, ou 1 s de silence."""

    def __init__(self, samplerate: int = 16000, wav: bytes | None = None) -> None:
        self._samplerate = samplerate
        self._wav = wav
        self._recording = False

    @property
    def recording(self) -> bool:
        return self._recording

    def start(self) -> None:
        self._recording = True

    def stop(self) -> bytes:
        self._recording = False
        return self._wav or to_wav(np.zeros(self._samplerate, dtype=np.int16), self._samplerate)

    def close(self) -> None:
        self._recording = False
