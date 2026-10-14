"""Parcours complet par l'API, matériel et LLM simulés."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aristote.api.context import build_context
from aristote.config import mock_config
from aristote.main import create_app
from aristote.ocr.base import MockOcr
from aristote.stt.whisper_engine import MockStt
from aristote.tutor.llm_client import ScriptedLLM


def responder(messages, json_mode):
    if json_mode and "ticket de caisse" in messages[0]["content"]:
        return json.dumps({"titre": "Révision", "consigne": "Complète.", "questions": ["1/3 = ?/6"]})
    if json_mode:
        return json.dumps({"nature": "reponse", "verdict": "faux",
                           "misconception": "additionne-numerateurs-et-denominateurs",
                           "explication": "Additionne terme à terme.", "elements_justes": ""})
    return "Que représente le 7 dans ta réponse ?"


@pytest.fixture
def client(tmp_path):
    config = mock_config()
    config.storage.vault_dir = tmp_path / "vault"
    config.storage.eval_corpus_dir = tmp_path / "eval"
    config.storage.eval_capture = True
    config.frontend.dist_dir = tmp_path / "dist"
    context = build_context(config, llm=ScriptedLLM(responder), ocr=MockOcr("1/3 + 1/4 = 2/7"),
                            stt=MockStt("deux septièmes"))
    with TestClient(create_app(config, context)) as test_client:
        test_client.ctx = context
        test_client.tmp = tmp_path
        yield test_client


def test_full_student_flow(client):
    assert client.post("/api/tutor/next").status_code == 409  # personne n'est sélectionné

    with client.websocket_connect("/ws") as ws:
        state = client.post("/api/keys", json={"key": "F14"}).json()
        assert client.get("/api/state").json()["active"]["pseudo"] == "E02"
        assert ws.receive_json()["type"] == "student.changed"

    # Sans profil, l'élève commence par la notion sans prérequis.
    item = client.post("/api/tutor/next").json()["item"]
    assert item["notion"] == "fractions-equivalentes"
    # On force l'item d'addition pour le scénario.
    session = client.ctx.manager.current
    session.items.clear()
    profile = client.ctx.profiles.load("E02")
    profile.acquired.append("fractions-equivalentes")
    client.ctx.profiles.save(profile)
    item = client.post("/api/tutor/next").json()["item"]
    assert item["question"] == "Calcule 1/3 + 1/4."

    scan = client.post("/api/scan").json()
    assert scan["page_found"] and scan["image"].startswith("data:image/jpeg")
    t1 = client.post("/api/tutor/answer", json={"text": "2/7", "capture_id": scan["capture_id"]}).json()
    assert t1["action"] == "relancer" and t1["errors"] == 1

    client.post("/api/dictation/start")
    dictation = client.post("/api/dictation/stop").json()
    t2 = client.post("/api/tutor/answer", json={"text": dictation["text"], "capture_id": dictation["capture_id"]}).json()
    assert t2["action"] == "indice"

    t3 = client.post("/api/tutor/answer", json={"text": "2/7"}).json()
    assert t3["action"] == "verrouiller" and t3["ticket_printed"] and "7/12" not in t3["reply"]
    assert "1/3 = ?/6" in client.ctx.hardware.printer.printed[-1]

    # Le corpus d'évaluation a reçu le scan et la dictée, hors du coffre synchronisé.
    corpus = client.tmp / "eval"
    assert len(list(corpus.rglob("*.jpg"))) == 1 and len(list(corpus.rglob("*.wav"))) == 1
    assert not list((client.tmp / "vault").rglob("*.jpg"))

    client.post("/api/session/end")
    session_file = next((client.tmp / "vault/K01/eleves/E02/sessions").glob("*.md")).read_text()
    assert "a_revoir_prof: true" in session_file and "scan, confiance 0.99" in session_file


def test_admin_requires_pin(client):
    assert client.get("/api/admin/diag").status_code == 403
    diag = client.get("/api/admin/diag", headers={"X-Admin-Pin": "0000"}).json()
    assert diag["printer"] and diag["llm"]["ok"]


def test_frontend_fallback(client):
    assert client.get("/api/nope").status_code == 404
    assert client.get("/").status_code == 503
    dist = client.tmp / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html>ok</html>")
    assert client.get("/tutor").text == "<html>ok</html>"
    assert client.get("/../../etc/passwd").status_code in (200, 404)  # jamais hors de dist
