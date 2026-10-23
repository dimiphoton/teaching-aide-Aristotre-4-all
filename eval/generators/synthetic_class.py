"""Classe synthétique de 30 élèves avec des misconceptions et des lacunes de prérequis PLANTÉES.

Elle sert à évaluer les prompts du professeur : on connaît la vérité (qui a quelle difficulté, quels groupes),
on mesure ce que les prompts retrouvent. Les fichiers produits ont exactement le format réel des kiosques.

    python -m eval.generators.synthetic_class -o /tmp/classe   # → /tmp/classe/Aristote/Kiosques/K01…K08 + verite.json
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from aristote.storage import Attempt, InputMode, Item, ItemStatus, MarkdownStore, Session, SessionStatus, Verdict
from aristote.storage.students import ProfileRepository
from aristote.tutor.agent import present_question
from aristote.tutor.curriculum import Curriculum, course_summary, load_curriculum

from ..common import ROOT
from ..simulated_student import scripted_right, scripted_wrong

N_STUDENTS = 30
PER_KIOSK = 4


def plan_groups(curriculum: Curriculum, rng: random.Random) -> list[dict]:
    """Groupes de besoin : une misconception par notion (jusqu'à 3), une lacune de prérequis, un groupe en réussite."""
    groups = []
    for notion in curriculum.notions:
        if notion.misconceptions and len(groups) < 3:
            groups.append({"nom": f"misconception:{notion.misconceptions[0].id}", "notion": notion.id,
                           "misconception": notion.misconceptions[0].id, "prerequis_manquant": None})
    dependent = next((n for n in curriculum.notions if n.prerequis), None)
    if dependent:
        prereq = curriculum.notion(dependent.prerequis[0])
        groups.append({"nom": f"prerequis:{prereq.id}", "notion": dependent.id,
                       "misconception": prereq.misconceptions[0].id if prereq.misconceptions else None,
                       "prerequis_manquant": prereq.id})
    groups.append({"nom": "reussite", "notion": None, "misconception": None, "prerequis_manquant": None})
    return groups


def build(curriculum: Curriculum, out: Path, seed: int = 7, noise: float = 0.15) -> dict:
    rng = random.Random(seed)
    groups = plan_groups(curriculum, rng)
    students = [f"E{i:02d}" for i in range(1, N_STUDENTS + 1)]
    assignment = {s: groups[i % len(groups)]["nom"] for i, s in enumerate(rng.sample(students, len(students)))}
    by_name = {g["nom"]: g for g in groups}
    now = datetime(2026, 10, 14, 16, 0, tzinfo=timezone(timedelta(hours=2)))
    truth = {"groupes": {}, "misconceptions": sorted({g["misconception"] for g in groups if g["misconception"]}),
             "prerequis_manquants": {}}

    for k in range(0, N_STUDENTS, PER_KIOSK):
        kiosk = f"K{k // PER_KIOSK + 1:02d}"
        kiosk_students = students[k:k + PER_KIOSK]
        store = MarkdownStore(out / "Aristote" / "Kiosques" / kiosk, kiosk)
        store.write_note("cours.md", *course_summary(curriculum))
        profiles = ProfileRepository(store, kiosk_students)
        for student in kiosk_students:
            group = by_name[assignment[student]]
            truth["groupes"].setdefault(group["nom"], []).append(student)
            if group["prerequis_manquant"]:
                truth["prerequis_manquants"][student] = [group["prerequis_manquant"]]
            profile = profiles.load(student)
            for day in range(3):
                start = now - timedelta(days=9 - 3 * day, minutes=rng.randint(0, 300))
                session = Session(student, kiosk, start, subject=curriculum.matiere)
                t = start
                for notion in curriculum.notions:
                    for citem in notion.items[:1]:
                        item = Item(len(session.items) + 1, notion.id, present_question(citem), item_id=citem.id)
                        struggles = notion.id == group["notion"] or notion.id == group["prerequis_manquant"]
                        if struggles:
                            tag = group["misconception"] if notion.id != group["notion"] or not group["prerequis_manquant"] \
                                else None
                            for n in range(1, 4):
                                t += timedelta(minutes=2)
                                noisy = rng.random() < noise
                                item.attempts.append(Attempt(n, rng.choice(list(InputMode)), scripted_wrong(citem),
                                                             Verdict.FAUX, t, misconception=None if noisy else tag))
                            item.status = ItemStatus.VERROUILLE
                            item.prerequisite = notion.prerequis[0] if notion.prerequis else None
                            item.diagnostic = "Raisonnement erroné récurrent."
                        else:
                            if rng.random() < noise:  # étourderie isolée
                                t += timedelta(minutes=1)
                                item.attempts.append(Attempt(1, InputMode.SAISIE, scripted_wrong(citem), Verdict.FAUX, t))
                            t += timedelta(minutes=1)
                            item.attempts.append(Attempt(len(item.attempts) + 1, InputMode.SAISIE, scripted_right(citem),
                                                         Verdict.JUSTE, t))
                            item.status = ItemStatus.VALIDE
                        session.items.append(item)
                session.end, session.status, session.close_reason = t + timedelta(minutes=1), SessionStatus.TERMINEE, "appui_long"
                store.save_session(session)
                profile.apply_session(session)
            profiles.save(profile)
    (out / "verite.json").write_text(json.dumps(truth, ensure_ascii=False, indent=2), encoding="utf-8")
    return truth


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cours", type=Path, default=ROOT / "backend/aristote/tutor/curriculum/demo.yaml")
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args(argv)
    truth = build(load_curriculum(args.cours), args.output, args.seed)
    print(json.dumps(truth, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
