from __future__ import annotations

import re

import httpx
import numpy as np

from .base import OcrResult
from .vlm_engine import VlmOcr


class MistralOcr:
    """API Mistral OCR (hébergement UE). Renvoie du Markdown, nettoyé ici en texte simple."""

    name = "mistral_ocr"

    def __init__(self, api_key: str, model: str = "mistral-ocr-latest", timeout_s: float = 60) -> None:
        if not api_key:
            raise ValueError("clé MISTRAL_API_KEY absente de /etc/aristote/secrets.env")
        self._client = httpx.AsyncClient(base_url="https://api.mistral.ai/v1", timeout=timeout_s,
                                         headers={"Authorization": f"Bearer {api_key}"})
        self._model = model

    async def recognize(self, image: np.ndarray) -> OcrResult:
        body = {"model": self._model,
                "document": {"type": "image_url", "image_url": VlmOcr._to_data_url(image)}}
        response = await self._client.post("/ocr", json=body)
        response.raise_for_status()
        pages = response.json().get("pages", [])
        markdown = "\n".join(page.get("markdown", "") for page in pages)
        text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", markdown)      # images incrustées
        text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)       # titres
        return OcrResult(text.strip(), None, self.name)
