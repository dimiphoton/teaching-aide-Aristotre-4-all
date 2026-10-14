"""LLM de démonstration, sans réseau (`[tutor] offline_demo = true` ou `ARISTOTE_MOCK=1`).

Il permet d'essayer l'interface et le matériel sans clé d'API. La correction repose alors uniquement
sur les vérifications déterministes : les questions ouvertes ne peuvent pas être validées.
"""

from __future__ import annotations

import json

from .llm_client import Message, ScriptedLLM

REPLIES = [
    ("première erreur", "Regardons ta réponse ensemble : peux-tu m'expliquer comment tu l'as obtenue ?"),
    ("deuxième erreur", "Reprends l'énoncé mot par mot : qu'est-ce qu'on te demande exactement ?"),
    ("troisième erreur", "On s'arrête là pour cet exercice, ce n'est pas grave. Un petit exercice de révision s'imprime pour toi."),
    ("a trouvé", "Bravo, c'est bien ça ! Tu peux passer à la suite."),
    ("demande de l'aide", "Dis-moi avec tes mots ce que la question te demande."),
    ("autre chose", "Revenons à la question, tu vas y arriver !"),
]


def _respond(messages: list[Message], json_mode: bool) -> str:
    system = str(messages[0]["content"])
    if json_mode and "ticket de caisse" in system:
        return "{}"  # invalide : l'agent se replie sur les items du cours
    if json_mode:
        return json.dumps({"nature": "reponse", "verdict": "faux", "misconception": None,
                           "explication": "Mode démonstration : pas d'analyse.", "elements_justes": ""})
    last = str(messages[-1]["content"])
    for marker, reply in REPLIES:
        if marker in last:
            return reply
    return "Peux-tu reformuler ta réponse ?"


def demo_llm() -> ScriptedLLM:
    return ScriptedLLM(_respond)
