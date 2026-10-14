"""Moteurs OCR enfichables pour les réponses manuscrites.

| Moteur        | Où tourne-t-il ?                         | Manuscrit | Confidentialité |
|---------------|------------------------------------------|-----------|-----------------|
| `tesseract`   | sur le kiosque                           | faible    | 100 % local     |
| `vlm`         | hub de classe (Ollama) ou API Mistral     | bon       | local ou UE     |
| `mistral_ocr` | API Mistral OCR                          | bon       | UE              |
| `mock`        | tests                                    | —         | —               |
"""

from __future__ import annotations

import os

from .base import MockOcr, OcrEngine, OcrResult

__all__ = ["OcrEngine", "OcrResult", "build_ocr"]


def build_ocr(cfg) -> OcrEngine:
    if cfg.engine == "tesseract":
        from .tesseract_engine import TesseractOcr
        return TesseractOcr(cfg.tesseract_lang)
    if cfg.engine == "vlm":
        from .vlm_engine import VlmOcr
        return VlmOcr(cfg.base_url, cfg.model, os.environ.get(cfg.api_key_env) if cfg.api_key_env else None,
                      timeout_s=cfg.timeout_s)
    if cfg.engine == "mistral_ocr":
        from .mistral_engine import MistralOcr
        return MistralOcr(os.environ.get(cfg.api_key_env or "MISTRAL_API_KEY", ""), model=cfg.model,
                          timeout_s=cfg.timeout_s)
    return MockOcr()
