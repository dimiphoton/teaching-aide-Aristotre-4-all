"""Évaluation des 3 prompts du professeur sur la classe synthétique (docs/EVALUATION.md § 3.6).

    python -m eval.teacher_eval --config eval/configs/exemple.toml -o eval/results/prof.json

1. Génère la classe synthétique (misconceptions et lacunes plantées, vérité connue).
2. Construit la note de données exactement comme le modèle Templater du professeur.
3. Lance chaque prompt (teacher/obsidian/prompts) avec le modèle évalué.
4. Un juge extrait les conclusions en JSON ; on mesure rappel des misconceptions, ARI des groupes,
   faux prérequis manquants.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import tempfile
from pathlib import Path

from aristote.storage.markdown_store import parse_frontmatter
from aristote.tutor.curriculum import load_curriculum
from aristote.tutor.llm_client import LLMClient, parse_json_reply

from .checks.metrics import adjusted_rand_index
from .common import ROOT, load_toml, make_llm
from .generators.synthetic_class import build

PROMPTS = ROOT / "teacher" / "obsidian" / "prompts"
KEEP = re.compile(r"^(## Item |\*\*Question\*\*|- \*\*Tentative|  > |- \*\*Diagnostic|- \*\*Prérequis|- \*\*Remédiation)")

EXTRACT = {
    "01-misconceptions-par-notion": (
        "Extrais de cette analyse la liste des identifiants de misconceptions retenues comme réelles difficultés "
        "de la classe. Catalogue connu : {catalogue}. Associe chaque misconception citée à l'identifiant du "
        "catalogue le plus proche. JSON : {{\"misconceptions\": [\"id\", ...]}}"),
    "02-clusters-eleves-en-difficulte": (
        "Extrais de cette analyse les groupes d'élèves proposés. JSON : "
        "{{\"groupes\": [{{\"nom\": \"...\", \"eleves\": [\"E01\", ...]}}]}}"),
    "03-verification-prerequis": (
        "Extrais de cette analyse, pour chaque élève diagnostiqué en « lacune de prérequis », la liste des "
        "identifiants de notions prérequises non maîtrisées. JSON : {{\"prerequis_manquants\": {{\"E01\": [\"notion\"]}}}}"),
}


def data_note(vault: Path) -> str:
    """Équivalent Python de teacher/obsidian/templates/Preparer-donnees-analyse.md."""
    root = vault / "Aristote" / "Kiosques"
    parts = ["# Données Aristote (pseudonymisées)", "", "## Structure du cours", ""]
    course = next(root.rglob("cours.md"), None)
    if course:
        body = parse_frontmatter(course.read_text(encoding="utf-8"))[1]
        parts.append(re.sub(r"^# .*\n", "", body, flags=re.M).replace("\n## ", "\n### "))
    parts += ["## Sessions", ""]
    sessions = []
    for path in root.rglob("sessions/*.md"):
        meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
        sessions.append((str(meta["debut"]), meta, body))
    for _, meta, body in sorted(sessions, key=lambda s: s[0]):
        parts.append(f"### Session {meta['eleve']} · {meta['kiosque']} · {meta['debut']} · {meta.get('duree_min')} min")
        parts += [line.replace("## ", "#### ", 1) if line.startswith("## ") else line
                  for line in body.splitlines() if KEEP.match(line)]
        parts.append("")
    return "\n".join(parts)


def prompt_text(name: str, content: str) -> str:
    _, body = parse_frontmatter((PROMPTS / f"{name}.md").read_text(encoding="utf-8"))
    return body.replace("{{content}}", content)


async def evaluate(tutor: LLMClient, judge: LLMClient, truth: dict, note: str, catalog: list[str]) -> dict:
    outputs, extracted = {}, {}
    for name, instruction in EXTRACT.items():
        outputs[name] = await tutor.chat([{"role": "user", "content": prompt_text(name, note)}], temperature=0.2)
        raw = await judge.chat([{"role": "user", "content": instruction.format(catalogue=", ".join(catalog))
                                 + "\n\nANALYSE :\n" + outputs[name]}], json_mode=True, temperature=0.0)
        extracted[name] = parse_json_reply(raw)

    planted = set(truth["misconceptions"])
    found = set(extracted["01-misconceptions-par-notion"].get("misconceptions", []))
    recall = len(planted & found) / len(planted) if planted else None

    students = sorted({s for members in truth["groupes"].values() for s in members})
    true_label = {s: g for g, members in truth["groupes"].items() for s in members}
    predicted = {}
    for i, group in enumerate(extracted["02-clusters-eleves-en-difficulte"].get("groupes", [])):
        for s in group.get("eleves", []):
            predicted.setdefault(s, f"g{i}")
    # Le groupe « réussite » n'est pas un groupe de besoin : ses élèves non classés sont comptés ensemble.
    ari = adjusted_rand_index([true_label[s] for s in students], [predicted.get(s, "aucun") for s in students])

    predicted_prereq = extracted["03-verification-prerequis"].get("prerequis_manquants", {})
    false_prereq = sum(1 for s, notions in predicted_prereq.items() for n in notions
                       if n not in truth["prerequis_manquants"].get(s, []))
    return {
        "misconceptions_rappel": {"valeur": recall, "cible": 0.80},
        "groupes_ari": {"valeur": round(ari, 3), "cible": 0.6},
        "faux_prerequis": {"valeur": false_prereq, "cible": "≤ 1"},
        "extraits": extracted,
        "sorties": outputs,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--cours", type=Path, default=ROOT / "backend/aristote/tutor/curriculum/demo.yaml")
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args(argv)
    config = load_toml(args.config)
    curriculum = load_curriculum(args.cours)
    with tempfile.TemporaryDirectory() as tmp:
        truth = build(curriculum, Path(tmp))
        note = data_note(Path(tmp))
    catalog = [m.id for n in curriculum.notions for m in n.misconceptions]
    tutor = make_llm(config.get("prof", config["tuteur"]))
    judge = make_llm(config["juges"][0])
    result = asyncio.run(evaluate(tutor, judge, truth, note, catalog))
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in ("sorties", "extraits")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
