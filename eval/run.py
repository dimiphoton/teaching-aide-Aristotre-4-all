"""Évaluation complète d'une configuration (modèle, prompts, cours) → résultats JSON.

    python -m eval.run --config eval/configs/exemple.toml
    python -m eval.run --offline            # sans réseau : LLM de démonstration, élève scripté, pas de jury

Les résultats sont écrits dans eval/results/<date>_<nom>/ (results.json + transcripts.jsonl).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from aristote.hardware.printer_csn_a2 import PreviewPrinter
from aristote.storage import Item, Session, Verdict
from aristote.tutor.agent import TutorAgent, present_question
from aristote.tutor.answers import detect_leak
from aristote.tutor.curriculum import load_curriculum
from aristote.tutor.demo_llm import demo_llm
from aristote.tutor.state import Action

from .common import ROOT, RecordingLLM, load_toml, make_llm, percentile
from .generators.scenarios import Scenario, generate
from .judges.jury import Jury
from .report import compute_scores
from .simulated_student import SimulatedStudent

EXPECTED = {"juste": {"juste"}, "faux": {"faux", "partiel"}, "attaque": {"incompris"}, "hors_sujet": {"incompris"}}


async def play(scenario: Scenario, repetition: int, llm, student: SimulatedStudent, curriculum) -> dict:
    # Une imprimante simulée par scénario : les tickets ne se mélangent pas entre scénarios parallèles.
    printer = PreviewPrinter()
    agent = TutorAgent(llm, curriculum, print_ticket=printer.print_ticket)
    notion, citem = curriculum.find_item(scenario.item_id)
    session = Session("EVAL", "EVAL", datetime.now().astimezone())
    session.items.append(Item(index=1, notion=notion.id, question=present_question(citem), item_id=citem.id))
    turns, said, wrong = [], [], []
    for turn in scenario.turns:
        text = await student.answer(turn, notion, citem, wrong)
        said.append(text)
        if turn.kind == "faux":
            wrong.append(text)
        printed_before = len(printer.printed)
        start = time.perf_counter()
        result = await agent.answer(session, text)
        seconds = time.perf_counter() - start
        tickets = printer.printed[printed_before:]
        turns.append({
            "kind": turn.kind, "planted": turn.misconception, "attack": turn.attack, "student": text,
            "reply": result.reply, "action": result.action.value,
            "verdict": result.verdict.value if result.verdict else None, "errors": result.errors,
            "misconception": result.misconception, "leak_blocked": result.leak_blocked,
            "seconds": round(seconds, 3), "tickets": tickets,
            "student_so_far": list(said),
        })
    return {"scenario": scenario.id, "repetition": repetition, "item_id": citem.id, "notion": notion.id,
            "profile": scenario.profile, "adversarial": scenario.adversarial, "turns": turns}


def check_gates_deterministic(transcript: dict, curriculum) -> tuple[list[dict], list[str]]:
    """G1 (détecteur déterministe) et G2 (compteur) pour un scénario."""
    _, citem = curriculum.find_item(transcript["item_id"])
    leaks, g2 = [], []
    counted = 0
    for t in transcript["turns"]:
        if t["action"] != Action.VALIDER.value:
            leak = detect_leak(citem, t["reply"], t["student_so_far"])
            if leak:
                leaks.append({"scenario": transcript["scenario"], "message": t["reply"], "reason": leak.reason})
        for ticket in t["tickets"]:
            leak = detect_leak(citem, ticket, t["student_so_far"])
            if leak:
                leaks.append({"scenario": transcript["scenario"], "message": "[ticket] " + ticket, "reason": leak.reason})
        if t["action"] == Action.DEJA_TERMINE.value:
            continue
        if t["verdict"] in ("faux", "partiel"):
            counted += 1
        if t["errors"] != counted:
            g2.append(f"{transcript['scenario']}: compteur {t['errors']} au lieu de {counted}")
        if (t["action"] == Action.VERROUILLER.value) != (counted == 3 and t["verdict"] in ("faux", "partiel")):
            g2.append(f"{transcript['scenario']}: action {t['action']} avec {counted} erreur(s)")
    return leaks, g2


def run_unit_tests() -> bool:
    """G4 (pas de perte de données) et G5 (confidentialité) sont couverts par les tests du backend."""
    tests = ["tests/test_markdown_store.py", "tests/test_session_manager.py", "tests/test_api.py"]
    result = subprocess.run([sys.executable, "-m", "pytest", "-q", *tests], cwd=ROOT / "backend",
                            capture_output=True, text=True)
    return result.returncode == 0


async def evaluate(config: dict, offline: bool, skip_tests: bool) -> dict:
    curriculum = load_curriculum(ROOT / config.get("cours", "backend/aristote/tutor/curriculum/demo.yaml"))
    repetitions = 1 if offline else int(config.get("repetitions", 1))
    tutor_llm = RecordingLLM(demo_llm() if offline else make_llm(config["tuteur"]))
    student = SimulatedStudent(None if offline else make_llm(config["eleve_simule"]), curriculum.niveau)
    jury = Jury([] if offline else [make_llm(j) for j in config.get("juges", [])])
    scenarios = generate(curriculum)
    semaphore = asyncio.Semaphore(4)

    async def bounded(s: Scenario, r: int) -> dict:
        async with semaphore:
            return await play(s, r, tutor_llm, student, curriculum)

    transcripts = await asyncio.gather(*(bounded(s, r) for s in scenarios for r in range(repetitions)))

    # --- Critères éliminatoires ---------------------------------------------------------------------------
    leaks, g2_errors = [], []
    for tr in transcripts:
        l, g = check_gates_deterministic(tr, curriculum)
        leaks += l
        g2_errors += g
    g3_flags: list[dict] = []
    g3_evaluated = bool(jury.judges)
    if jury.judges:
        for tr in transcripts:
            _, citem = curriculum.find_item(tr["item_id"])
            for t in tr["turns"]:
                if t["action"] != Action.VALIDER.value:
                    flagged, cites = await jury.flag("fuite", question=citem.question, reponse=citem.reponse,
                                                     eleve=" / ".join(t["student_so_far"]), message=t["reply"])
                    if flagged:
                        leaks.append({"scenario": tr["scenario"], "message": t["reply"], "reason": "jury : " + "; ".join(cites)})
                if tr["adversarial"] or t["kind"] in ("attaque", "hors_sujet"):
                    flagged, cites = await jury.flag("securite", eleve=t["student"], message=t["reply"])
                    if flagged:
                        g3_flags.append({"scenario": tr["scenario"], "message": t["reply"], "citations": cites})
    tests_ok = None if skip_tests else run_unit_tests()

    gates = {
        "G1": {"ok": not leaks, "details": leaks[:50]},
        "G2": {"ok": not g2_errors, "details": g2_errors[:50]},
        "G3": {"ok": (not g3_flags) if g3_evaluated else None, "details": g3_flags[:50]},
        "G4": {"ok": tests_ok, "details": "tests du backend (écriture atomique, sessions)"},
        "G5": {"ok": tests_ok, "details": "tests du backend (neutralisation, corpus hors coffre)"},
    }

    # --- Critères notés ---------------------------------------------------------------------------------------
    all_turns = [t for tr in transcripts for t in tr["turns"] if t["action"] != Action.DEJA_TERMINE.value]
    verdict_ok = [t["verdict"] in EXPECTED[t["kind"]] for t in all_turns]
    planted = [t for t in all_turns if t["kind"] == "faux" and t["planted"]]
    json_calls = [c for c in tutor_llm.calls if c.json_mode]

    def parses(raw: str) -> bool:
        try:
            from aristote.tutor.llm_client import parse_json_reply
            parse_json_reply(raw)
            return True
        except ValueError:
            return False

    latencies = [t["seconds"] for t in all_turns]
    tutor = {
        "verdict_exact": {"valeur": sum(verdict_ok) / len(verdict_ok) if verdict_ok else None, "fiable": True},
        "misconception_rappel": {"valeur": (sum(t["misconception"] == t["planted"] for t in planted) / len(planted))
                                 if planted else None, "fiable": True},
        "json_valide": {"valeur": sum(parses(c.raw) for c in json_calls) / len(json_calls) if json_calls else None,
                        "fiable": True},
    }
    for criterion, action, rubric_name in (("socratique", Action.RELANCER, "socratique"),
                                           ("indice_pertinent", Action.INDICE, "indice")):
        judgements = []
        if jury.judges:
            for tr in transcripts:
                _, citem = curriculum.find_item(tr["item_id"])
                for t in tr["turns"]:
                    if t["action"] == action.value:
                        judgements.append(await jury.judge(rubric_name, "note", question=citem.question,
                                                           eleve=t["student"], message=t["reply"],
                                                           misconception=t["misconception"] or "non identifiée"))
        mean, kappa, reliable = Jury.aggregate_scores(judgements)
        tutor[criterion] = {"valeur": mean, "kappa": kappa, "fiable": reliable and len(jury.judges) >= 2}

    delays = {"tuteur_median_s": {"valeur": percentile(latencies, 0.5), "fiable": True},
              "tuteur_p95_s": {"valeur": percentile(latencies, 0.95), "fiable": True}}
    measures = config.get("mesures", {})
    reading: dict = {}
    if measures.get("lecture"):
        reading = json.loads((ROOT / measures["lecture"]).read_text())
    if measures.get("delais"):
        delays.update(json.loads((ROOT / measures["delais"]).read_text()))
    cost = {"euros_par_eleve_an": {"valeur": measures.get("cout_euros_par_eleve_an") or None, "fiable": True}}

    results = {
        "nom": config.get("nom", "sans nom"), "date": datetime.now().isoformat(timespec="seconds"),
        "hors_ligne": offline, "cours": curriculum.id, "scenarios": len(scenarios), "repetitions": repetitions,
        "juges": len(jury.judges), "confidentialite": config.get("confidentialite", "api_ue"),
        "eliminatoires": gates,
        "criteres": {"tuteur": tutor, "lecture": reading, "delais": delays, "cout": cost},
    }
    results["score"] = compute_scores(results)
    return results, transcripts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", type=Path, default=Path(__file__).parent / "configs" / "exemple.toml")
    parser.add_argument("--offline", action="store_true", help="sans réseau (vérifie la chaîne et G1/G2)")
    parser.add_argument("--skip-tests", action="store_true", help="ne pas relancer les tests du backend (G4/G5)")
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "results")
    args = parser.parse_args(argv)

    config = load_toml(args.config)
    if args.offline:
        config["nom"] = config.get("nom", "") + " (hors ligne)"
    results, transcripts = asyncio.run(evaluate(config, args.offline, args.skip_tests))
    slug = re.sub(r"[^a-z0-9]+", "-", results["nom"].lower()).strip("-")
    out = args.out / f"{datetime.now():%Y%m%d-%H%M%S}_{slug}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    with (out / "transcripts.jsonl").open("w", encoding="utf-8") as fh:
        for tr in transcripts:
            fh.write(json.dumps(tr, ensure_ascii=False) + "\n")

    gates = results["eliminatoires"]
    print(f"Résultats : {out}")
    for name, gate in gates.items():
        status = {True: "OK", False: "ÉCHEC", None: "non évalué"}[gate["ok"]]
        print(f"  {name} : {status}")
    print(f"  Score : {results['score']['global']}")
    return 0 if all(g["ok"] is not False for g in gates.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
