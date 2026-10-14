from __future__ import annotations

import asyncio

import numpy as np

from ..hardware.camera import enhance_for_ocr
from .base import OcrResult


class TesseractOcr:
    """Tesseract en local (paquets apt tesseract-ocr et tesseract-ocr-fra, module pytesseract).

    Fiable sur du texte imprimé ou très soigné ; médiocre sur l'écriture manuscrite d'enfant.
    """

    name = "tesseract"

    def __init__(self, lang: str = "fra") -> None:
        import pytesseract

        self._tess = pytesseract
        self._lang = lang

    def _run(self, image: np.ndarray) -> OcrResult:
        gray = enhance_for_ocr(image)
        data = self._tess.image_to_data(gray, lang=self._lang, config="--psm 6",
                                        output_type=self._tess.Output.DICT)
        lines: dict[tuple[int, int, int], list[str]] = {}
        confidences = []
        for i, word in enumerate(data["text"]):
            conf = float(data["conf"][i])
            if word.strip() and conf >= 0:
                key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
                lines.setdefault(key, []).append(word)
                confidences.append(conf / 100)
        text = "\n".join(" ".join(words) for _, words in sorted(lines.items()))
        confidence = sum(confidences) / len(confidences) if confidences else 0.0
        return OcrResult(text, round(confidence, 3), self.name)

    async def recognize(self, image: np.ndarray) -> OcrResult:
        return await asyncio.to_thread(self._run, image)
