"""Format des cours (`curriculum.yaml`), valable pour toutes les matières.

Un cours est une liste de notions reliées par des prérequis. Chaque notion porte des items (questions)
et un catalogue de misconceptions connues. Le `type_reponse` de chaque item permet de vérifier la réponse
et de détecter une fuite sans connaître la matière.
"""

from __future__ import annotations

import re
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator

SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class AnswerType(str, Enum):
    NOMBRE = "nombre"
    EXPRESSION = "expression"
    CHOIX = "choix"
    MOTS_CLES = "mots_cles"
    OUVERTE = "ouverte"


class Misconception(BaseModel):
    id: str
    description: str

    @field_validator("id")
    @classmethod
    def _slug(cls, v: str) -> str:
        if not SLUG.match(v):
            raise ValueError(f"identifiant de misconception invalide (minuscules, chiffres, tirets) : {v!r}")
        return v


class CurriculumItem(BaseModel):
    id: str
    question: str
    type_reponse: AnswerType
    # Réponse de référence (nombre, expression, lettre ou texte de l'option, texte modèle pour mots_cles/ouverte).
    reponse: str = ""
    variantes: list[str] = Field(default_factory=list)       # autres réponses acceptées
    tolerance: str = "0"                                      # nombre : écart absolu ("0.01") ou relatif ("1%")
    forme: str = "symbolique"                                 # expression : "symbolique" (SymPy) ou "texte"
    choix: list[str] = Field(default_factory=list)            # choix : options dans l'ordre A, B, C…
    mots_cles: list[str] = Field(default_factory=list)        # mots_cles : synonymes séparés par « | »
    criteres: list[str] = Field(default_factory=list)         # ouverte : grille de réussite
    indices: list[str] = Field(default_factory=list)          # indices rédigés par le professeur (facultatif)
    difficulte: int = Field(1, ge=1, le=3)

    @model_validator(mode="after")
    def _consistent(self) -> "CurriculumItem":
        t = self.type_reponse
        if t in (AnswerType.NOMBRE, AnswerType.EXPRESSION) and not self.reponse:
            raise ValueError(f"item {self.id} : 'reponse' obligatoire pour le type {t.value}")
        if t is AnswerType.CHOIX:
            if len(self.choix) < 2 or not self.reponse:
                raise ValueError(f"item {self.id} : au moins 2 'choix' et une 'reponse' (lettre ou texte)")
            if self.correct_choice_index() is None:
                raise ValueError(f"item {self.id} : la réponse ne correspond à aucun choix")
        if t is AnswerType.MOTS_CLES and not self.mots_cles:
            raise ValueError(f"item {self.id} : 'mots_cles' obligatoire pour le type mots_cles")
        if t is AnswerType.OUVERTE and not self.criteres:
            raise ValueError(f"item {self.id} : 'criteres' obligatoire pour une question ouverte")
        return self

    def correct_choice_index(self) -> int | None:
        ref = self.reponse.strip()
        if len(ref) == 1 and ref.upper().isalpha():
            idx = ord(ref.upper()) - ord("A")
            return idx if 0 <= idx < len(self.choix) else None
        for i, option in enumerate(self.choix):
            if option.strip().lower() == ref.lower():
                return i
        return None

    def keyword_groups(self) -> list[list[str]]:
        return [[s.strip() for s in group.split("|") if s.strip()] for group in self.mots_cles]


class Notion(BaseModel):
    id: str
    titre: str
    prerequis: list[str] = Field(default_factory=list)
    misconceptions: list[Misconception] = Field(default_factory=list)
    items: list[CurriculumItem] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def _slug(cls, v: str) -> str:
        if not SLUG.match(v):
            raise ValueError(f"identifiant de notion invalide : {v!r}")
        return v


class Curriculum(BaseModel):
    id: str
    titre: str
    matiere: str
    niveau: str = ""                     # ex. « 5e », « CE2 », « seconde » : règle le niveau de langue
    langue: str = "fr"
    consignes_tuteur: str = ""           # consignes propres au cours, ajoutées au prompt système
    notions: list[Notion]

    @model_validator(mode="after")
    def _graph(self) -> "Curriculum":
        ids = [n.id for n in self.notions]
        if len(set(ids)) != len(ids):
            raise ValueError("identifiants de notions en double")
        item_ids = [i.id for n in self.notions for i in n.items]
        if len(set(item_ids)) != len(item_ids):
            raise ValueError("identifiants d'items en double")
        known = set(ids)
        for n in self.notions:
            missing = set(n.prerequis) - known
            if missing:
                raise ValueError(f"notion {n.id} : prérequis inconnus {sorted(missing)}")
        # Détection de cycle (parcours en profondeur)
        state: dict[str, int] = {}
        graph = {n.id: n.prerequis for n in self.notions}

        def visit(node: str) -> None:
            if state.get(node) == 1:
                raise ValueError(f"cycle de prérequis autour de {node}")
            if state.get(node) == 2:
                return
            state[node] = 1
            for dep in graph[node]:
                visit(dep)
            state[node] = 2

        for node in graph:
            visit(node)
        return self

    def notion(self, notion_id: str) -> Notion:
        for n in self.notions:
            if n.id == notion_id:
                return n
        raise KeyError(notion_id)

    def find_item(self, item_id: str) -> tuple[Notion, CurriculumItem]:
        for n in self.notions:
            for item in n.items:
                if item.id == item_id:
                    return n, item
        raise KeyError(item_id)
