from __future__ import annotations

import base64

import cv2
import httpx
import numpy as np

from ..hardware.camera import encode_jpeg
from .base import TRANSCRIBE_PROMPT, OcrResult

MAX_SIDE = 1600  # au-delà, le gain de lisibilité est nul et la latence augmente


class VlmOcr:
    """Modèle de vision via l'API compatible OpenAI.

    - Hub de classe : Ollama, `base_url = "http://hub.local:11434/v1"`, `model = "qwen2.5vl:7b"`.
    - Mistral : `base_url = "https://api.mistral.ai/v1"`, `model = "pixtral-12b-latest"`.
    """

    name = "vlm"

    def __init__(self, base_url: str, model: str, api_key: str | None = None, timeout_s: float = 60) -> None:
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._client = httpx.AsyncClient(base_url=base_url.rstrip("/"), headers=headers, timeout=timeout_s)
        self._model = model

    @staticmethod
    def _to_data_url(image: np.ndarray) -> str:
        h, w = image.shape[:2]
        scale = MAX_SIDE / max(h, w)
        if scale < 1:
            image = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        return "data:image/jpeg;base64," + base64.b64encode(encode_jpeg(image, 85)).decode()

    async def recognize(self, image: np.ndarray) -> OcrResult:
        body = {
            "model": self._model,
            "temperature": 0,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": TRANSCRIBE_PROMPT},
                {"type": "image_url", "image_url": {"url": self._to_data_url(image)}},
            ]}],
        }
        response = await self._client.post("/chat/completions", json=body)
        response.raise_for_status()
        text = (response.json()["choices"][0]["message"]["content"] or "").strip()
        if text == "[illisible]":
            return OcrResult("", 0.0, self.name)
        return OcrResult(text, None, self.name)
