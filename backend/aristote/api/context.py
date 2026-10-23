"""Assemblage des services du kiosque (une instance par application)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from ..config import Config
from ..events import EventBus
from ..hardware import Hardware, build_hardware
from ..ocr import OcrEngine, build_ocr
from ..ocr.base import MockOcr
from ..services.captures import CaptureStore
from ..services.printing import PrinterService
from ..services.session_manager import SessionManager
from ..storage import MarkdownStore, ProfileRepository
from ..storage.eval_corpus import EvalCorpus
from ..stt import SttEngine, build_stt
from ..stt.whisper_engine import MockStt
from ..tutor.agent import TutorAgent
from ..tutor.curriculum import Curriculum, load_curriculum
from ..tutor.demo_llm import demo_llm
from ..tutor.llm_client import LLMClient, client_from_config

log = logging.getLogger(__name__)

DEMO_CURRICULUM = Path(__file__).parents[1] / "tutor" / "curriculum" / "demo.yaml"


@dataclass
class KioskContext:
    config: Config
    bus: EventBus
    hardware: Hardware
    store: MarkdownStore
    profiles: ProfileRepository
    manager: SessionManager
    curriculum: Curriculum
    llm: LLMClient
    agent: TutorAgent
    printer: PrinterService
    ocr: OcrEngine
    stt: SttEngine
    corpus: EvalCorpus
    captures: CaptureStore = field(default_factory=CaptureStore)
    llm_mode: str = "api"

    @property
    def scans_dir(self) -> Path:
        return self.config.storage.eval_corpus_dir.parent / "scans"


def _safe_engine(name, factory, fallback):
    try:
        return factory()
    except Exception:  # noqa: BLE001 - le kiosque démarre même si un moteur manque ; le diagnostic le montre
        log.exception("moteur %s indisponible, repli sur la simulation", name)
        return fallback


def build_context(config: Config, *, llm: LLMClient | None = None, hardware: Hardware | None = None,
                  ocr: OcrEngine | None = None, stt: SttEngine | None = None) -> KioskContext:
    bus = EventBus()
    hardware = hardware or build_hardware(config)
    store = MarkdownStore(config.kiosk_vault_dir, config.kiosk.id)
    profiles = ProfileRepository(store, config.kiosk.students)
    manager = SessionManager(kiosk_id=config.kiosk.id, students=config.kiosk.students, store=store,
                             profiles=profiles, leds=hardware.leds, bus=bus,
                             idle_timeout_s=config.session.idle_timeout_s)
    curriculum = load_curriculum(config.tutor.curriculum or DEMO_CURRICULUM)
    llm_mode = "injecté" if llm else "api"
    if llm is None:
        if config.tutor.offline_demo or config.hardware.mode == "mock":
            llm, llm_mode = demo_llm(), "démonstration"
        else:
            llm = client_from_config(config.llm)
    printer = PrinterService(hardware.printer)
    agent = TutorAgent(llm, curriculum, print_ticket=printer.print_ticket if printer.available else None)
    return KioskContext(
        config=config, bus=bus, hardware=hardware, store=store, profiles=profiles, manager=manager,
        curriculum=curriculum, llm=llm, agent=agent, printer=printer,
        ocr=ocr or _safe_engine("OCR", lambda: build_ocr(config.ocr), MockOcr("")),
        stt=stt or _safe_engine("dictée", lambda: build_stt(config.stt), MockStt("")),
        corpus=EvalCorpus(config.storage.eval_corpus_dir, config.kiosk.id, config.storage.eval_retention_days),
        llm_mode=llm_mode,
    )
