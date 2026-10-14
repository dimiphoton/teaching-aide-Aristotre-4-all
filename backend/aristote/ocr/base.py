from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

# Consigne commune aux moteurs fondés sur un modèle de langage.
TRANSCRIBE_PROMPT = (
    "Transcris exactement le texte manuscrit de cette copie d'élève. Ne corrige rien : garde les fautes, "
    "les ratures lisibles et la mise en ligne. Écris les fractions avec « / », les puissances avec « ^ », "
    "les multiplications avec « x ». N'ajoute aucun commentaire. Si rien n'est lisible, réponds exactement : [illisible]"
)


@dataclass
class OcrResult:
    text: str
    confidence: float | None
    engine: str


class OcrEngine(Protocol):
    name: str

    async def recognize(self, image: np.ndarray) -> OcrResult: ...


class MockOcr:
    name = "mock"

    def __init__(self, text: str = "1/3 + 1/4 = 2/7") -> None:
        self.text = text

    async def recognize(self, image: np.ndarray) -> OcrResult:
        return OcrResult(self.text, 0.99, self.name)
