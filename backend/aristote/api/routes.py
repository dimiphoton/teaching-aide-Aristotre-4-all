"""Routes HTTP et WebSocket consommées par l'interface du kiosque."""

from __future__ import annotations

import asyncio
import base64
import hmac
import logging
from datetime import datetime

import cv2
from fastapi import APIRouter, Depends, Header, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from pydantic import BaseModel, Field

from ..hardware.base import ButtonKind, ButtonPress
from ..hardware.camera import encode_jpeg
from ..hardware.printer_csn_a2 import exercise_ticket
from ..services.captures import PendingCapture
from ..storage import InputMode, Session
from ..tutor.state import MAX_ERRORS
from .context import KioskContext

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api")
ws_router = APIRouter()


def ctx(request: Request) -> KioskContext:
    return request.app.state.ctx


def active_session(c: KioskContext = Depends(ctx)) -> Session:
    if c.manager.current is None:
        raise HTTPException(409, "Aucun élève sélectionné : appuie sur ton bouton.")
    return c.manager.current


def admin(x_admin_pin: str = Header(default=""), c: KioskContext = Depends(ctx)) -> None:
    if not hmac.compare_digest(x_admin_pin, c.config.admin.pin):
        raise HTTPException(403, "Code PIN incorrect")


# --- État et élèves ---------------------------------------------------------------------------------

def item_payload(c: KioskContext) -> dict | None:
    session = c.manager.current
    if session is None or not session.items:
        return None
    item = session.items[-1]
    return {"index": item.index, "notion": item.notion, "notion_title": c.curriculum.notion(item.notion).titre,
            "question": item.question, "status": item.status.value, "errors": item.errors,
            "max_errors": MAX_ERRORS}


@router.get("/state")
def state(c: KioskContext = Depends(ctx)) -> dict:
    m = c.manager
    return {
        "kiosk": c.config.kiosk.id,
        "students": [{"index": i, "pseudo": s} for i, s in enumerate(c.config.kiosk.students)],
        "active": {"index": m.current_index, "pseudo": m.current.student} if m.current else None,
        "item": item_payload(c),
        "course": {"id": c.curriculum.id, "title": c.curriculum.titre, "subject": c.curriculum.matiere},
        "capabilities": {"camera": c.hardware.camera is not None, "microphone": c.hardware.microphone is not None,
                         "printer": c.printer.available,
                         "keyboard_buttons": c.config.hardware.buttons.backend == "keyboard"
                         or c.config.hardware.mode == "mock"},
        "mode": c.llm_mode,
    }


@router.post("/students/{index}/select")
def select_student(index: int, c: KioskContext = Depends(ctx)) -> dict:
    if not 0 <= index < len(c.config.kiosk.students):
        raise HTTPException(404, "Élève inconnu")
    c.captures.clear()
    c.manager.select(index)
    return state(c)


@router.post("/session/end")
def end_session(c: KioskContext = Depends(ctx)) -> dict:
    c.captures.clear()
    c.manager.end_current("fin_ecran")
    return state(c)


class KeyIn(BaseModel):
    key: str
    long: bool = False


@router.post("/keys")
def key_press(body: KeyIn, c: KioskContext = Depends(ctx)) -> dict:
    """Relais des boutons câblés sur un clavier USB (mini-PC) : l'interface transmet F13 à F17."""
    panel = c.hardware.buttons
    if not hasattr(panel, "inject_key"):
        raise HTTPException(400, "Les boutons sont câblés en GPIO sur ce kiosque")
    return {"handled": panel.inject_key(body.key, long=body.long)}


# --- Tuteur -----------------------------------------------------------------------------------------

@router.post("/tutor/next")
def next_question(session: Session = Depends(active_session), c: KioskContext = Depends(ctx)) -> dict:
    c.manager.touch()
    profile = c.profiles.load(session.student)
    started = c.agent.start_item(session, profile)
    if started is None:
        return {"done": True, "item": None}
    c.manager.save_current()
    return {"done": False, "item": item_payload(c)}


class AnswerIn(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    mode: InputMode = InputMode.SAISIE
    capture_id: str | None = None


@router.post("/tutor/answer")
async def answer(body: AnswerIn, session: Session = Depends(active_session), c: KioskContext = Depends(ctx)) -> dict:
    c.manager.touch()
    if not session.items:
        raise HTTPException(409, "Aucune question en cours")
    mode, raw_text, confidence = body.mode, None, None
    capture = c.captures.pop(body.capture_id) if body.capture_id else None
    if capture is not None:
        mode = InputMode.SCAN if capture.kind == "scan" else InputMode.DICTEE
        raw_text, confidence = capture.raw_text, capture.confidence
        await asyncio.to_thread(_archive_capture, c, capture, body.text, session.items[-1].item_id)
    turn = await c.agent.answer(session, body.text.strip(), mode, confidence=confidence, raw_text=raw_text)
    c.manager.save_current()
    return {**turn.to_dict(), "item": item_payload(c)}


def _archive_capture(c: KioskContext, capture: PendingCapture, validated: str, item_id: str | None) -> None:
    storage = c.config.storage
    if storage.eval_capture:
        c.corpus.save(capture.kind, capture.media, raw_text=capture.raw_text, validated_text=validated,
                      engine=capture.engine, student=capture.student, item_id=item_id,
                      confidence=capture.confidence)
    if storage.keep_scans and capture.kind == "scan":
        folder = c.scans_dir / capture.student
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{datetime.now():%Y-%m-%d_%H%M%S}.jpg").write_bytes(capture.media)


@router.post("/tutor/print")
async def print_question(session: Session = Depends(active_session), c: KioskContext = Depends(ctx)) -> dict:
    """Imprime la question en cours sur un ticket, pour une réponse manuscrite à scanner."""
    if not c.printer.available:
        raise HTTPException(503, "Imprimante indisponible")
    if not session.items:
        raise HTTPException(409, "Aucune question en cours")
    item = session.items[-1]
    ticket = exercise_ticket(student=session.student, kiosk=session.kiosk,
                             title=c.curriculum.notion(item.notion).titre,
                             instructions="Réponds sous la question, puis scanne ton ticket.",
                             questions=[item.question], answer_lines=4,
                             footer="Pose le ticket sous la caméra et appuie sur SCAN.")
    await asyncio.to_thread(c.printer.print_ticket, ticket)
    return {"printed": True}


# --- Scan et dictée ---------------------------------------------------------------------------------

@router.get("/camera/preview.jpg")
async def camera_preview(c: KioskContext = Depends(ctx)) -> Response:
    if c.hardware.camera is None:
        raise HTTPException(503, "Caméra indisponible")
    jpeg = await asyncio.to_thread(c.hardware.camera.preview_jpeg)
    return Response(jpeg, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@router.post("/scan")
async def scan(session: Session = Depends(active_session), c: KioskContext = Depends(ctx)) -> dict:
    if c.hardware.camera is None:
        raise HTTPException(503, "Caméra indisponible")
    c.manager.touch()
    c.hardware.leds.set_scan(True)
    try:
        capture = await asyncio.to_thread(c.hardware.camera.capture)
        try:
            result = await c.ocr.recognize(capture.image)
        except Exception as exc:  # noqa: BLE001
            log.exception("OCR")
            raise HTTPException(502, "Lecture impossible pour le moment : tape ta réponse.") from exc
    finally:
        c.hardware.leds.set_scan(False)
    small = cv2.resize(capture.image, (480, int(capture.image.shape[0] * 480 / capture.image.shape[1])))
    capture_id = c.captures.add(PendingCapture("scan", capture.jpeg, result.text, result.confidence,
                                               result.engine, session.student))
    return {"capture_id": capture_id, "text": result.text, "confidence": result.confidence,
            "page_found": capture.page_found,
            "image": "data:image/jpeg;base64," + base64.b64encode(encode_jpeg(small, 70)).decode()}


@router.post("/dictation/start")
def dictation_start(session: Session = Depends(active_session), c: KioskContext = Depends(ctx)) -> dict:
    if c.hardware.microphone is None:
        raise HTTPException(503, "Micro indisponible")
    c.manager.touch()
    c.hardware.microphone.start()
    return {"recording": True}


@router.post("/dictation/stop")
async def dictation_stop(session: Session = Depends(active_session), c: KioskContext = Depends(ctx)) -> dict:
    if c.hardware.microphone is None:
        raise HTTPException(503, "Micro indisponible")
    c.manager.touch()
    wav = c.hardware.microphone.stop()
    result = await c.stt.transcribe(wav)
    capture_id = c.captures.add(PendingCapture("dictee", wav, result.text, result.confidence, result.engine,
                                               session.student))
    return {"capture_id": capture_id, "text": result.text, "confidence": result.confidence}


# --- Administration ---------------------------------------------------------------------------------

@router.get("/admin/diag", dependencies=[Depends(admin)])
async def diagnostics(c: KioskContext = Depends(ctx)) -> dict:
    paper = await asyncio.to_thread(c.printer.has_paper)
    llm_ok, llm_error = True, None
    try:
        await asyncio.wait_for(c.llm.chat([{"role": "user", "content": "Réponds OK."}]), timeout=15)
    except Exception as exc:  # noqa: BLE001
        llm_ok, llm_error = False, str(exc)
    return {
        "kiosk": c.config.kiosk.id, "hardware_mode": c.config.hardware.mode,
        "camera": c.hardware.camera is not None, "microphone": c.hardware.microphone is not None,
        "printer": c.printer.available, "paper": paper,
        "llm": {"ok": llm_ok, "error": llm_error, "mode": c.llm_mode, "model": c.config.llm.model},
        "ocr": c.ocr.name, "stt": c.stt.name, "course": c.curriculum.id,
        "vault": str(c.store.root), "eval_capture": c.config.storage.eval_capture,
    }


@router.post("/admin/print-test", dependencies=[Depends(admin)])
async def print_test(c: KioskContext = Depends(ctx)) -> dict:
    if not c.printer.available:
        raise HTTPException(503, "Imprimante indisponible")
    from ..cli import _test_ticket

    await asyncio.to_thread(c.printer.print_ticket, _test_ticket())
    return {"printed": True}


# --- WebSocket --------------------------------------------------------------------------------------

@ws_router.websocket("/ws")
async def events(websocket: WebSocket) -> None:
    c: KioskContext = websocket.app.state.ctx
    await websocket.accept()
    queue = c.bus.subscribe()
    try:
        while True:
            event = await queue.get()
            await websocket.send_json(event.to_dict())
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        c.bus.unsubscribe(queue)
