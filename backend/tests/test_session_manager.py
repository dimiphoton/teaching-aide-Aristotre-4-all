from datetime import datetime, timezone

from aristote.events import SESSION_CLOSED, STUDENT_CHANGED, EventBus
from aristote.hardware.base import ButtonKind, ButtonPress
from aristote.hardware.buttons import PressDecoder, VirtualButtonPanel
from aristote.hardware.leds import MockLedPanel
from aristote.services.session_manager import SessionManager
from aristote.storage import Attempt, InputMode, Item, MarkdownStore, ProfileRepository, Verdict

STUDENTS = ["E01", "E02", "E03", "E04"]


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def make_manager(tmp_path, clock=None, bus=None):
    store = MarkdownStore(tmp_path, "K01")
    leds = MockLedPanel(4)
    manager = SessionManager(kiosk_id="K01", students=STUDENTS, store=store,
                             profiles=ProfileRepository(store, STUDENTS), leds=leds, bus=bus,
                             idle_timeout_s=600, now=lambda: datetime(2026, 10, 14, 9, 0, tzinfo=timezone.utc),
                             monotonic=clock or FakeClock())
    return manager, leds


def add_item(manager):
    item = Item(1, "notion", "question")
    item.attempts.append(Attempt(1, InputMode.SAISIE, "r", Verdict.JUSTE, manager._now()))
    manager.current.items.append(item)


def test_press_decoder_short_and_long():
    clock = FakeClock()
    decoder = PressDecoder(2, long_press_s=3.0, clock=clock)
    assert decoder.up() is None  # relâchement sans appui
    decoder.down(); clock.t = 1.0
    assert decoder.up() == ButtonPress(ButtonKind.STUDENT, 2)
    decoder.down(); clock.t = 4.5
    assert decoder.up() == ButtonPress(ButtonKind.STUDENT_LONG, 2)


def test_switching_students_closes_previous_session(tmp_path):
    manager, leds = make_manager(tmp_path)
    manager.handle_press(ButtonPress(ButtonKind.STUDENT, 0))
    assert manager.current.student == "E01" and leds.states == [True, False, False, False]
    add_item(manager)

    manager.handle_press(ButtonPress(ButtonKind.STUDENT, 2))
    assert manager.current.student == "E03" and leds.states == [False, False, True, False]
    files = list((tmp_path / "eleves/E01/sessions").glob("*.md"))
    assert len(files) == 1 and "changement_eleve" in files[0].read_text()
    assert (tmp_path / "eleves/E01/profil.md").exists()


def test_same_button_keeps_session_and_empty_session_writes_nothing(tmp_path):
    manager, leds = make_manager(tmp_path)
    first = manager.select(1)
    assert manager.select(1) is first
    manager.handle_press(ButtonPress(ButtonKind.STUDENT_LONG, 1))
    assert manager.current is None and leds.states == [False] * 4
    assert not (tmp_path / "eleves").exists()


def test_long_press_on_other_button_only_selects(tmp_path):
    manager, _ = make_manager(tmp_path)
    manager.select(0)
    manager.handle_press(ButtonPress(ButtonKind.STUDENT_LONG, 3))
    assert manager.current.student == "E04"


def test_idle_timeout(tmp_path):
    clock = FakeClock()
    manager, _ = make_manager(tmp_path, clock=clock)
    manager.select(0)
    add_item(manager)
    clock.t = 599
    assert manager.check_idle() is False
    manager.touch(); clock.t = 1100
    assert manager.check_idle() is False
    clock.t = 1199
    assert manager.check_idle() is True
    assert manager.current is None
    assert "inactivite" in next((tmp_path / "eleves/E01/sessions").glob("*.md")).read_text()


async def test_events_reach_subscribers(tmp_path):
    import asyncio

    bus = EventBus()
    bus.bind_loop(asyncio.get_running_loop())
    queue = bus.subscribe()
    manager, _ = make_manager(tmp_path, bus=bus)
    panel = VirtualButtonPanel(4)
    panel.start(manager.handle_press)
    assert panel.inject_key("F14")
    add_item(manager)
    assert panel.inject_key("F14", long=True)
    assert panel.inject_key("F1") is False
    types = [queue.get_nowait().type for _ in range(queue.qsize())]
    assert types == [STUDENT_CHANGED, SESSION_CLOSED, STUDENT_CHANGED]
