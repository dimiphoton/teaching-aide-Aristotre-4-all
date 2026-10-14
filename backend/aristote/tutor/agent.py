"""Agent tuteur : choisit les questions, évalue les réponses, applique la règle des 3 erreurs, formule.

Répartition des rôles :
- le CODE décide (vérification déterministe, compteur, verrou, choix de l'item, garde anti-fuite) ;
- le LLM évalue ce que le code ne sait pas trancher et rédige les messages.

Chaque message du tuteur passe par `detect_leak` avant d'être montré à l'élève. S'il révèle la réponse,
il est régénéré une fois, puis remplacé par un message sûr. Si le LLM est injoignable, des messages de
repli déterministes permettent de continuer.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from string import Template
from typing import Callable, Literal

from pydantic import BaseModel, ValidationError, field_validator

from ..hardware.printer_csn_a2 import Ticket, exercise_ticket
from ..storage import Attempt, InputMode, Item, ItemStatus, Session, StudentProfile, Verdict
from .answers import check_answer, detect_leak
from .curriculum import AnswerType, Curriculum, CurriculumItem, Notion
from .llm_client import LLMClient, LLMError, parse_json_reply
from .misconceptions import normalize_tag
from .state import MAX_ERRORS, Action, apply_action, next_action

log = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_prompt(name: str) -> Template:
    return Template((PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8"))


class Evaluation(BaseModel):
    nature: Literal["reponse", "demande_aide", "hors_sujet", "illisible"] = "reponse"
    verdict: Literal["juste", "partiel", "faux"] = "faux"
    misconception: str | None = None
    explication: str = ""
    elements_justes: str = ""

    @field_validator("misconception", mode="before")
    @classmethod
    def _empty_is_none(cls, v):
        return v or None


class RemediationExercise(BaseModel):
    titre: str
    consigne: str
    questions: list[str]


@dataclass
class TutorTurn:
    reply: str
    action: Action
    verdict: Verdict | None
    nature: str | None
    misconception: str | None
    errors: int
    max_errors: int
    item_status: ItemStatus
    ticket_printed: bool = False
    leak_blocked: bool = False

    def to_dict(self) -> dict:
        return {
            "reply": self.reply, "action": self.action.value,
            "verdict": self.verdict.value if self.verdict else None, "nature": self.nature,
            "misconception": self.misconception, "errors": self.errors, "max_errors": self.max_errors,
            "item_status": self.item_status.value, "ticket_printed": self.ticket_printed,
            "leak_blocked": self.leak_blocked,
        }


# Messages de repli : utilisés si le LLM est injoignable ou si sa réponse fuit deux fois.
FALLBACK = {
    Action.VALIDER: "Bravo, tu as trouvé ! Passons à la suite.",
    Action.RELANCER: "Regardons ta réponse ensemble. Peux-tu m'expliquer, étape par étape, comment tu l'as obtenue ?",
    Action.INDICE: "Reprends l'énoncé : qu'est-ce qu'on te demande exactement ? Essaie de vérifier ta réponse avec un exemple plus simple.",
    Action.VERROUILLER: "On va s'arrêter là pour cet exercice : ce n'est pas grave, c'est comme ça qu'on apprend. "
                        "On va d'abord travailler une notion plus simple, et un petit exercice s'imprime pour toi.",
    Action.REFORMULER: "Je n'ai pas bien compris ta réponse. Peux-tu la réécrire ou l'expliquer autrement ?",
}
DONE_LOCKED = "On a terminé cet exercice pour aujourd'hui, ton professeur le reprendra avec toi. Passons à la suite !"
DONE_VALID = "Tu as déjà réussi cet exercice ! Passons au suivant."

ACTION_INSTRUCTIONS = {
    Action.VALIDER: "L'élève a trouvé. Félicite-le en citant précisément ce qu'il a bien fait, en une ou deux phrases. "
                    "N'ajoute pas de nouvelle question.",
    Action.RELANCER: "C'est sa première erreur sur cet exercice. Ne donne aucun indice sur la solution. Pose UNE question "
                     "ouverte qui l'amène à relire ou vérifier lui-même son raisonnement (par exemple avec un cas simple).",
    Action.INDICE: "C'est sa deuxième erreur. Donne UN indice ciblé sur l'erreur de raisonnement probable, formulé comme "
                   "une question. Ne fais pas le calcul ni le raisonnement à sa place.",
    Action.VERROUILLER: "C'est sa troisième erreur : l'exercice s'arrête ici et tu NE DONNES PAS la réponse. Rassure-le "
                        "(se tromper fait partie de l'apprentissage), dis-lui qu'on va d'abord travailler « ${prerequis} » "
                        "et qu'un petit exercice va s'imprimer pour lui.",
}
REFORMULATE_INSTRUCTIONS = {
    "demande_aide": "L'élève demande de l'aide ou dit qu'il ne comprend pas. Ne donne pas la réponse : aide-le à reformuler "
                    "la question avec ses mots, ou à repérer ce qu'on lui demande et ce qu'il sait déjà.",
    "hors_sujet": "L'élève parle d'autre chose. Ramène-le gentiment et brièvement à la question.",
    "illisible": "Sa réponse n'a pas pu être lue correctement. Demande-lui de la réécrire plus lisiblement ou de la taper.",
    "reponse": "Sa réponse n'a pas pu être analysée. Demande-lui de la reformuler.",
}
INPUT_NOTES = {
    InputMode.SAISIE: "",
    InputMode.SCAN: "Cette réponse manuscrite a été lue par OCR puis relue par l'élève : tolère les erreurs de lecture évidentes.",
    InputMode.DICTEE: "Cette réponse orale a été transcrite automatiquement puis relue par l'élève : les nombres peuvent être "
                      "écrits en lettres et la ponctuation est approximative.",
}


def present_question(item: CurriculumItem) -> str:
    if item.type_reponse is AnswerType.CHOIX:
        options = "\n".join(f"{chr(ord('A') + i)}) {option}" for i, option in enumerate(item.choix))
        return f"{item.question}\n{options}"
    return item.question


class TutorAgent:
    def __init__(
        self,
        llm: LLMClient,
        curriculum: Curriculum,
        *,
        print_ticket: Callable[[Ticket], None] | None = None,
        now: Callable[[], datetime] = lambda: datetime.now().astimezone(),
    ) -> None:
        self.llm = llm
        self.curriculum = curriculum
        self._print_ticket = print_ticket
        self._now = now
        self._system = load_prompt("system_tutor")
        self._evaluate = load_prompt("evaluate_answer")
        self._turn = load_prompt("turn_instructions")
        self._exercise = load_prompt("generate_exercise")

    # --- Choix de la question -----------------------------------------------------------------------

    def choose_item(self, session: Session, profile: StudentProfile) -> tuple[Notion, CurriculumItem] | None:
        """Choix déterministe : prérequis en attente, puis notions fragiles, puis nouvelles notions
        dont les prérequis sont acquis, puis révision."""
        seen = {i.item_id for i in session.items}
        locked_notions = {i.notion for i in session.items if i.status is ItemStatus.VERROUILLE}
        acquired = set(profile.acquired)

        def pick(notion: Notion) -> CurriculumItem | None:
            candidates = [it for it in notion.items if it.id not in seen]
            if not candidates:
                return None
            # Après un verrou sur cette notion, on repart de l'item le plus facile.
            return sorted(candidates, key=lambda it: it.difficulte)[0] if notion.id in locked_notions \
                else candidates[0]

        order: list[Notion] = []
        if session.pending_prerequisite:
            order.append(self.curriculum.notion(session.pending_prerequisite))
        ready = [n for n in self.curriculum.notions if set(n.prerequis) <= acquired]
        order += [n for n in ready if n.id in profile.fragile and n.id not in locked_notions]
        order += [n for n in ready if n.id not in acquired and n.id not in profile.fragile
                  and n.id not in locked_notions]
        order += [n for n in self.curriculum.notions if n.id in acquired]
        order += self.curriculum.notions  # dernier recours : tout item non vu
        for notion in order:
            item = pick(notion)
            if item is not None:
                if notion.id == session.pending_prerequisite:
                    session.pending_prerequisite = None
                return notion, item
        return None

    def start_item(self, session: Session, profile: StudentProfile) -> tuple[Item, str] | None:
        """Ouvre l'item suivant dans la session et renvoie (item, texte de la question)."""
        if session.current_item is not None:
            notion, citem = self.curriculum.find_item(session.current_item.item_id)
            return session.current_item, present_question(citem)
        choice = self.choose_item(session, profile)
        if choice is None:
            return None
        notion, citem = choice
        if session.subject is None:
            session.subject = self.curriculum.matiere
        item = Item(index=len(session.items) + 1, notion=notion.id, question=present_question(citem),
                    item_id=citem.id)
        session.items.append(item)
        return item, item.question

    # --- Réponse de l'élève ---------------------------------------------------------------------------

    async def answer(self, session: Session, text: str, mode: InputMode = InputMode.SAISIE, *,
                     confidence: float | None = None, raw_text: str | None = None) -> TutorTurn:
        item = session.items[-1] if session.items else None
        if item is None:
            raise ValueError("aucun exercice en cours")
        if item.status is not ItemStatus.EN_COURS:
            reply = DONE_LOCKED if item.status is ItemStatus.VERROUILLE else DONE_VALID
            return TutorTurn(reply, Action.DEJA_TERMINE, None, None, None, item.errors, MAX_ERRORS, item.status)

        notion, citem = self.curriculum.find_item(item.item_id)
        catalog_ids = [m.id for m in notion.misconceptions]
        evaluation = await self._evaluate_answer(notion, citem, item, text, mode)
        deterministic = check_answer(citem, text)

        nature = evaluation.nature if evaluation else "reponse"
        if deterministic is True:
            verdict, nature = Verdict.JUSTE, "reponse"
        elif evaluation is None and deterministic is None:
            verdict = Verdict.INCOMPRIS
        elif nature != "reponse":
            verdict = Verdict.INCOMPRIS
        elif deterministic is False:
            verdict = Verdict.PARTIEL if evaluation and evaluation.verdict == "partiel" else Verdict.FAUX
        else:
            verdict = Verdict(evaluation.verdict)

        misconception = None
        if verdict in (Verdict.FAUX, Verdict.PARTIEL) and evaluation:
            misconception = normalize_tag(evaluation.misconception, catalog_ids)

        attempt = Attempt(number=len(item.attempts) + 1, mode=mode, answer=text, verdict=verdict, ts=self._now(),
                          misconception=misconception, confidence=confidence, raw_text=raw_text)
        item.attempts.append(attempt)
        action = next_action(item, verdict)
        apply_action(item, action)

        prerequisite_notion = None
        if action is Action.VERROUILLER:
            item.diagnostic = evaluation.explication if evaluation and evaluation.explication else None
            prerequisite_notion = self._prerequisite_for(notion, session)
            item.prerequisite = prerequisite_notion.id if prerequisite_notion else None
            session.pending_prerequisite = item.prerequisite

        reply, leak_blocked = await self._compose_reply(
            notion, citem, item, action, nature, text, evaluation, misconception, prerequisite_notion)
        attempt.tutor_reply = reply

        printed = False
        if action is Action.VERROUILLER:
            printed = await self._print_remediation(session, notion, citem, item, misconception, prerequisite_notion)

        return TutorTurn(reply, action, verdict, nature, misconception, item.errors, MAX_ERRORS, item.status,
                         ticket_printed=printed, leak_blocked=leak_blocked)

    # --- Étapes internes --------------------------------------------------------------------------------

    def _common_vars(self) -> dict[str, str]:
        c = self.curriculum
        return {"niveau": c.niveau or "non précisé", "matiere": c.matiere, "langue": "français" if c.langue == "fr" else c.langue}

    async def _evaluate_answer(self, notion: Notion, citem: CurriculumItem, item: Item, text: str,
                               mode: InputMode) -> Evaluation | None:
        history = "\n".join(
            f"{a.number}. « {a.answer} » → {a.verdict.value}" + (f" ({a.misconception})" if a.misconception else "")
            for a in item.attempts) or "(aucune)"
        catalog = "\n".join(f"- {m.id} : {m.description}" for m in notion.misconceptions) or "(catalogue vide)"
        prompt = self._evaluate.safe_substitute(
            **self._common_vars(), notion=notion.titre, question=present_question(citem),
            type_reponse=citem.type_reponse.value, reponse=citem.reponse or "(voir critères)",
            variantes=", ".join(citem.variantes) or "(aucune)",
            criteres="; ".join(citem.criteres) or "(aucun)", catalogue=catalog, historique=history,
            mode=mode.value, reponse_eleve=text.replace(">>>", "> > >"), note_lecture=INPUT_NOTES[mode])
        messages = [{"role": "system", "content": prompt},
                    {"role": "user", "content": "Produis l'objet JSON d'évaluation."}]
        for attempt in range(2):
            try:
                raw = await self.llm.chat(messages, json_mode=True, temperature=0.0)
                return Evaluation.model_validate(parse_json_reply(raw))
            except (ValueError, ValidationError) as exc:
                log.warning("évaluation JSON invalide (%s)", exc)
                messages = messages + [{"role": "assistant", "content": raw},
                                       {"role": "user", "content": "Réponds uniquement avec l'objet JSON demandé, "
                                                                   "avec exactement les clés indiquées."}]
            except LLMError as exc:
                log.error("LLM injoignable pour l'évaluation : %s", exc)
                return None
        return None

    def _prerequisite_for(self, notion: Notion, session: Session) -> Notion | None:
        if not notion.prerequis:
            return None
        return self.curriculum.notion(notion.prerequis[0])

    async def _compose_reply(self, notion: Notion, citem: CurriculumItem, item: Item, action: Action, nature: str,
                             text: str, evaluation: Evaluation | None, misconception: str | None,
                             prerequisite: Notion | None) -> tuple[str, bool]:
        if action is Action.REFORMULER:
            instruction = REFORMULATE_INSTRUCTIONS.get(nature, REFORMULATE_INSTRUCTIONS["reponse"])
        else:
            instruction = Template(ACTION_INSTRUCTIONS[action]).safe_substitute(
                prerequis=prerequisite.titre if prerequisite else "les bases de cette notion")
        misconception_text = "aucune identifiée"
        if misconception:
            described = {m.id: m.description for m in notion.misconceptions}
            misconception_text = described.get(misconception, evaluation.explication if evaluation else misconception)
        system = self._system.safe_substitute(**self._common_vars(), consignes_cours=self.curriculum.consignes_tuteur)
        turn = self._turn.safe_substitute(
            notion=notion.titre, question=present_question(citem), reponse_eleve=text,
            elements_justes=(evaluation.elements_justes if evaluation and evaluation.elements_justes else "rien de précis"),
            misconception=misconception_text,
            indices=" / ".join(citem.indices) if action is Action.INDICE and citem.indices else "(aucun)",
            consigne_action=instruction)

        messages: list[dict] = [{"role": "system", "content": system},
                                {"role": "assistant", "content": present_question(citem)}]
        for previous in item.attempts[:-1]:
            messages.append({"role": "user", "content": previous.answer})
            if previous.tutor_reply:
                messages.append({"role": "assistant", "content": previous.tutor_reply})
        messages.append({"role": "user", "content": f"[Message de l'élève]\n{text}\n\n"
                                                    f"[Consignes pour toi, invisibles pour l'élève]\n{turn}"})

        student_answers = [a.answer for a in item.attempts]
        if action is Action.VALIDER:
            check = lambda reply: None  # l'élève a trouvé : citer sa réponse n'est plus une fuite
        else:
            check = lambda reply: detect_leak(citem, reply, student_answers)

        for attempt in range(2):
            try:
                reply = (await self.llm.chat(messages)).strip()
            except LLMError:
                return FALLBACK[action], False
            leak = check(reply)
            if reply and leak is None:
                return reply, attempt > 0
            log.warning("réponse du tuteur bloquée (%s)", leak.reason if leak else "vide")
            messages = messages + [{"role": "assistant", "content": reply},
                                   {"role": "user", "content": "[Consigne invisible pour l'élève] Ce message révèle "
                                    "tout ou partie de la solution. Réécris-le sans aucun élément de la réponse attendue."}]
        return FALLBACK[action], True

    async def _print_remediation(self, session: Session, notion: Notion, citem: CurriculumItem, item: Item,
                                 misconception: str | None, prerequisite: Notion | None) -> bool:
        exercise = await self._generate_exercise(notion, citem, misconception, prerequisite)
        if exercise is None:
            exercise = self._fallback_exercise(citem, prerequisite or notion)
        item.remediation = f"{exercise.titre} — " + " / ".join(exercise.questions)
        if self._print_ticket is None:
            return False
        ticket = exercise_ticket(student=session.student, kiosk=session.kiosk, title=exercise.titre,
                                 instructions=exercise.consigne, questions=exercise.questions, now=self._now())
        try:
            await asyncio.to_thread(self._print_ticket, ticket)
        except Exception:  # noqa: BLE001 - une imprimante en panne ne doit pas bloquer la séance
            log.exception("impression du ticket de remédiation impossible")
            return False
        item.printed = True
        return True

    @staticmethod
    def _fallback_exercise(citem: CurriculumItem, source: Notion) -> RemediationExercise:
        """Ticket de repli construit avec les questions du professeur, filtrées par la garde anti-fuite.

        Même une question du cours peut révéler la réponse de l'item bloqué (ex. « 1/2 = ?/4 » quand
        la réponse bloquée est 1/2) : tout passe par `detect_leak`.
        """
        questions = [q for q in (present_question(it) for it in sorted(source.items, key=lambda it: it.difficulte)
                                 if it.id != citem.id) if detect_leak(citem, q) is None][:2]
        if not questions:
            questions = ["Relis ta leçon, puis écris avec tes mots ce que tu as compris."]
        title = f"Révision : {source.titre}"[:40]
        if detect_leak(citem, title):
            title = "Révision"
        return RemediationExercise(titre=title, consigne="Fais ces exercices, puis montre-les à ton professeur.",
                                   questions=questions)

    async def _generate_exercise(self, notion: Notion, citem: CurriculumItem, misconception: str | None,
                                 prerequisite: Notion | None) -> RemediationExercise | None:
        prompt = self._exercise.safe_substitute(
            **self._common_vars(), notion=notion.titre,
            prerequis=prerequisite.titre if prerequisite else notion.titre,
            misconception=misconception or "non identifiée", question=present_question(citem))
        try:
            raw = await self.llm.chat([{"role": "system", "content": prompt},
                                       {"role": "user", "content": "Produis l'objet JSON."}], json_mode=True)
            exercise = RemediationExercise.model_validate(parse_json_reply(raw))
        except (LLMError, ValueError, ValidationError) as exc:
            log.warning("génération d'exercice impossible (%s) : repli sur les items du cours", exc)
            return None
        # Garde anti-fuite : aucune question du ticket ne doit révéler la réponse de l'item bloqué.
        exercise.questions = [q for q in exercise.questions[:4] if q.strip() and detect_leak(citem, q) is None]
        if not exercise.questions or detect_leak(citem, exercise.titre + " " + exercise.consigne):
            return None
        return exercise
