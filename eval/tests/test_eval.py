import asyncio
import json
from pathlib import Path

import pytest

from aristote.tutor.curriculum import load_curriculum
from aristote.tutor.llm_client import ScriptedLLM
from eval.checks.metrics import adjusted_rand_index, cer, cohen_kappa, final_answer_match, wer
from eval.common import ROOT, criterion_score
from eval.generators.scenarios import ATTACKS, generate
from eval.generators.synthetic_class import build
from eval.report import compute_scores, render
from eval.run import evaluate
from eval.teacher_eval import data_note, evaluate as evaluate_teacher

DEMO = load_curriculum(ROOT / "backend/aristote/tutor/curriculum/demo.yaml")


def test_text_metrics():
    assert cer("1/3 + 1/4 = 2/7", "1/3 + 1/4 = 2/7") == 0
    assert cer("1/3 + 1/4 = 2/1", "1/3 + 1/4 = 2/7") == pytest.approx(1 / 15)
    assert wer("la prise de la bastille", "La prise de la Bastille.") == 0
    assert final_answer_match("1/3+1/4 = 7/12", "1/3 + 1/4 = 7/12")
    assert not final_answer_match("1/3+1/4 = 1/12", "1/3 + 1/4 = 7/12")


def test_agreement_and_clustering_metrics():
    assert cohen_kappa([1, 2, 3], [1, 2, 3]) == 1
    assert cohen_kappa([4, 4, 5, 5], [4, 5, 4, 5], weights="quadratic", categories=[1, 2, 3, 4, 5]) < 0.6
    assert adjusted_rand_index([0, 0, 1, 1], ["a", "a", "b", "b"]) == 1
    assert adjusted_rand_index([0, 0, 1, 1], ["a", "b", "a", "b"]) < 0


def test_criterion_score_direction():
    assert criterion_score(0.97, 0.95, 0.75) == 100
    assert criterion_score(0.85, 0.95, 0.75) == pytest.approx(50)
    assert criterion_score(2.0, 3.0, 8.0) == 100
    assert criterion_score(5.5, 3.0, 8.0) == pytest.approx(50)
    assert criterion_score(20, 3.0, 8.0) == 0


def test_scenarios_cover_every_item_and_attack():
    scenarios = generate(DEMO)
    items = {i.id for n in DEMO.notions for i in n.items}
    assert {s.item_id for s in scenarios} == items
    attacks = {t.attack for s in scenarios for t in s.turns if t.kind == "attaque"}
    assert attacks == set(ATTACKS)


def test_offline_evaluation_passes_gates():
    results, transcripts = asyncio.run(evaluate({"nom": "test"}, offline=True, skip_tests=True))
    assert results["eliminatoires"]["G1"]["ok"], results["eliminatoires"]["G1"]["details"][:3]
    assert results["eliminatoires"]["G2"]["ok"], results["eliminatoires"]["G2"]["details"][:3]
    assert results["eliminatoires"]["G3"]["ok"] is None  # pas de jury hors ligne
    assert results["criteres"]["tuteur"]["verdict_exact"]["valeur"] > 0.8
    assert "G1" in render(results, results)


def test_failed_gate_rejects_the_version():
    results = {"criteres": {"tuteur": {"verdict_exact": {"valeur": 1.0, "fiable": True}}},
               "confidentialite": "kiosque",
               "eliminatoires": {"G1": {"ok": False, "details": []}}}
    score = compute_scores(results)
    assert score["rejete"] and score["global"] is None


def test_synthetic_class_and_teacher_metrics(tmp_path):
    truth = build(DEMO, tmp_path)
    assert sum(len(v) for v in truth["groupes"].values()) == 30
    note = data_note(tmp_path)
    assert "### Session E01" in note and "Structure du cours" in note
    assert "7/12" not in note.split("## Sessions")[0]  # la structure du cours ne contient pas les réponses

    perfect_groups = [{"nom": g, "eleves": m} for g, m in truth["groupes"].items() if g != "reussite"]

    def tutor(messages, json_mode):
        return "analyse"

    def judge(messages, json_mode):
        text = messages[0]["content"]
        if "misconceptions retenues" in text:
            return json.dumps({"misconceptions": truth["misconceptions"]})
        if "groupes d'élèves" in text:
            return json.dumps({"groupes": perfect_groups})
        return json.dumps({"prerequis_manquants": truth["prerequis_manquants"]})

    catalog = [m.id for n in DEMO.notions for m in n.misconceptions]
    result = asyncio.run(evaluate_teacher(ScriptedLLM(tutor), ScriptedLLM(judge), truth, note, catalog))
    assert result["misconceptions_rappel"]["valeur"] == 1
    assert result["groupes_ari"]["valeur"] == 1
    assert result["faux_prerequis"]["valeur"] == 0
