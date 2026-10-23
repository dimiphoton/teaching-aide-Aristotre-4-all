"""Machine à états d'un item : compteur d'erreurs et verrou.

Cette logique est volontairement déterministe et indépendante du LLM : c'est elle qui garantit
« jamais la réponse, verrou à la 3e erreur » (critère G2 de docs/EVALUATION.md).

    tentative juste            → VALIDER
    1re erreur (faux/partiel)  → RELANCER   (question ouverte socratique)
    2e erreur                  → INDICE     (indice ciblé sur la misconception)
    3e erreur                  → VERROUILLER (pas de réponse, diagnostic, prérequis, ticket)
    demande d'aide, hors sujet, illisible → REFORMULER (ne compte pas)
    toute entrée sur un item verrouillé ou validé → DEJA_TERMINE
"""

from __future__ import annotations

from enum import Enum

from ..storage import Item, ItemStatus, Verdict

MAX_ERRORS = 3  # non configurable : règle pédagogique du produit


class Action(str, Enum):
    VALIDER = "valider"
    RELANCER = "relancer"
    INDICE = "indice"
    VERROUILLER = "verrouiller"
    REFORMULER = "reformuler"
    DEJA_TERMINE = "deja_termine"


def next_action(item: Item, verdict: Verdict) -> Action:
    """Décide de l'action à partir du verdict de la tentative qui vient d'être ajoutée à `item`.

    `item.attempts` doit déjà contenir cette tentative (elle est comptée dans `item.errors`).
    """
    if item.status is not ItemStatus.EN_COURS:
        return Action.DEJA_TERMINE
    if verdict is Verdict.JUSTE:
        return Action.VALIDER
    if verdict is Verdict.INCOMPRIS:
        return Action.REFORMULER
    errors = item.errors
    if errors >= MAX_ERRORS:
        return Action.VERROUILLER
    return Action.RELANCER if errors == 1 else Action.INDICE


def apply_action(item: Item, action: Action) -> None:
    if action is Action.VALIDER:
        item.status = ItemStatus.VALIDE
    elif action is Action.VERROUILLER:
        item.status = ItemStatus.VERROUILLE
