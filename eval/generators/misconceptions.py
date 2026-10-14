"""Complète les catalogues de misconceptions vides d'un cours (par LLM) et écrit un nouveau fichier de cours.

    python -m eval.generators.misconceptions --cours mon-cours.yaml --config eval/configs/exemple.toml -o mon-cours.complet.yaml

Le professeur relit et corrige le résultat avant de l'utiliser sur les kiosques.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

import yaml

from aristote.tutor.curriculum import Misconception, load_curriculum
from aristote.tutor.llm_client import parse_json_reply
from aristote.tutor.misconceptions import slugify

from ..common import load_toml, make_llm

PROMPT = """Tu es didacticien en {matiere}, niveau {niveau}. Pour la notion « {titre} », liste les 2 à 4
erreurs de raisonnement (misconceptions) les plus fréquentes chez les élèves, documentées en didactique.
Exemples de questions de cette notion : {questions}
Produis uniquement un objet JSON :
{{"misconceptions": [{{"id": "identifiant-court-en-minuscules", "description": "L'élève pense que…"}}]}}"""


async def complete(path: Path, config: dict) -> dict:
    curriculum = load_curriculum(path)
    llm = make_llm(config["tuteur"])
    for notion in curriculum.notions:
        if notion.misconceptions:
            continue
        raw = await llm.chat([{"role": "user", "content": PROMPT.format(
            matiere=curriculum.matiere, niveau=curriculum.niveau, titre=notion.titre,
            questions=" / ".join(i.question for i in notion.items[:3]))}], json_mode=True, temperature=0.2)
        for m in parse_json_reply(raw).get("misconceptions", []):
            notion.misconceptions.append(Misconception(id=slugify(m["id"]), description=m["description"]))
    return curriculum.model_dump(mode="json", exclude_defaults=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cours", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("-o", "--output", type=Path, required=True)
    args = parser.parse_args(argv)
    data = asyncio.run(complete(args.cours, load_toml(args.config)))
    args.output.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"Cours complété : {args.output} (à relire avant usage)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
