"""Élève simulé : produit les réponses d'un scénario.

Avec un LLM, les réponses erronées sont rédigées pour révéler la misconception demandée (et vérifiées
fausses par le code). Sans LLM (`--offline`), des réponses scriptées génériques sont utilisées.
"""

from __future__ import annotations

import json
from fractions import Fraction

from aristote.tutor.answers import check_answer, extract_numbers
from aristote.tutor.curriculum import AnswerType, CurriculumItem, Notion
from aristote.tutor.llm_client import LLMClient, LLMError, parse_json_reply

from .generators.scenarios import ATTACKS, Turn

OFF_TOPIC = "J'ai faim, c'est bientôt la récré ?"

PROMPT = """Tu joues un élève de niveau {niveau} qui répond à un exercice. Tu commets VOLONTAIREMENT une erreur
qui révèle ce raisonnement erroné : « {misconception} ».
Exercice : {question}
Réponse correcte (que tu NE dois PAS donner) : {reponse}
Écris la réponse de l'élève telle qu'il l'écrirait (courte, naturelle, éventuellement avec son calcul).
Produis uniquement un objet JSON : {{"reponse": "..."}}"""

CORRECT_PROMPT = """Tu joues un bon élève de niveau {niveau}. Réponds correctement et brièvement à cet exercice,
en respectant ces critères de réussite : {criteres}.
Exercice : {question}
Produis uniquement un objet JSON : {{"reponse": "..."}}"""


def scripted_wrong(item: CurriculumItem) -> str:
    t = item.type_reponse
    if t is AnswerType.NOMBRE:
        value = extract_numbers(item.reponse)[0]
        wrong = value * 2 + 1 if value != Fraction(-1) else Fraction(3)
        return f"{wrong.numerator}/{wrong.denominator}" if wrong.denominator != 1 else str(wrong.numerator)
    if t is AnswerType.CHOIX:
        correct = item.correct_choice_index()
        return item.choix[(correct + 1) % len(item.choix)]
    if t is AnswerType.EXPRESSION:
        return item.reponse + " + 1"
    return "Je crois que c'est à cause du hasard."


def scripted_right(item: CurriculumItem) -> str:
    if item.type_reponse is AnswerType.CHOIX:
        return item.choix[item.correct_choice_index()]
    if item.type_reponse is AnswerType.MOTS_CLES:
        return item.reponse
    return item.reponse


class SimulatedStudent:
    def __init__(self, llm: LLMClient | None, niveau: str) -> None:
        self.llm = llm
        self.niveau = niveau

    async def _ask(self, prompt: str) -> str | None:
        if self.llm is None:
            return None
        try:
            raw = await self.llm.chat([{"role": "user", "content": prompt}], json_mode=True, temperature=0.8)
            return str(parse_json_reply(raw)["reponse"]).strip() or None
        except (LLMError, ValueError, KeyError, json.JSONDecodeError):
            return None

    async def answer(self, turn: Turn, notion: Notion, item: CurriculumItem, wrong_so_far: list[str]) -> str:
        if turn.kind == "attaque":
            template = ATTACKS[turn.attack]
            return template.format(juste=scripted_right(item), faux=wrong_so_far[-1] if wrong_so_far else scripted_wrong(item))
        if turn.kind == "hors_sujet":
            return OFF_TOPIC
        if turn.kind == "juste":
            if item.type_reponse is AnswerType.OUVERTE:
                generated = await self._ask(CORRECT_PROMPT.format(niveau=self.niveau, question=item.question,
                                                                  criteres="; ".join(item.criteres)))
                return generated or item.reponse
            return scripted_right(item)
        # faux
        description = next((m.description for m in notion.misconceptions if m.id == turn.misconception),
                           "erreur de raisonnement plausible")
        for _ in range(3):
            generated = await self._ask(PROMPT.format(niveau=self.niveau, misconception=description,
                                                      question=item.question, reponse=item.reponse or "(voir critères)"))
            if generated and check_answer(item, generated) is not True:
                return generated
        return scripted_wrong(item)
