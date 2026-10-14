from datetime import datetime, timedelta, timezone

import yaml

from aristote.storage import (
    Attempt,
    InputMode,
    Item,
    ItemStatus,
    MarkdownStore,
    ProfileRepository,
    Session,
    SessionStatus,
    Verdict,
)
from aristote.storage.markdown_store import parse_frontmatter, sanitize

T0 = datetime(2026, 10, 14, 10, 32, 5, tzinfo=timezone(timedelta(hours=2)))


def make_session() -> Session:
    locked = Item(1, "addition-fractions", "Combien font 1/3 + 1/4 ?", status=ItemStatus.VERROUILLE,
                  diagnostic="Traite numérateurs et dénominateurs comme des entiers indépendants.",
                  prerequisite="fractions-equivalentes", remediation="Partager une pizza en 12.", printed=True)
    for n, (mode, answer) in enumerate([(InputMode.SAISIE, "2/7"), (InputMode.SCAN, "2/12"),
                                        (InputMode.DICTEE, "deux septièmes")], start=1):
        locked.attempts.append(Attempt(n, mode, answer, Verdict.FAUX, T0 + timedelta(minutes=n),
                                       misconception="additionne-numerateurs-et-denominateurs",
                                       confidence=0.91 if mode is InputMode.SCAN else None))
    ok = Item(2, "fractions-equivalentes", "Complète : 1/2 = ?/4", status=ItemStatus.VALIDE,
              attempts=[Attempt(1, InputMode.SAISIE, "2", Verdict.JUSTE, T0 + timedelta(minutes=6))])
    return Session("E07", "K03", T0, subject="mathematiques", items=[locked, ok],
                   end=T0 + timedelta(minutes=19), status=SessionStatus.TERMINEE, close_reason="appui_long")


def test_session_file_layout_and_frontmatter(tmp_path):
    store = MarkdownStore(tmp_path / "K03", "K03")
    path = store.save_session(make_session())
    assert path == tmp_path / "K03/eleves/E07/sessions/2026-10-14_1032_E07.md"

    meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
    assert meta["eleve"] == "E07" and meta["kiosque"] == "K03"
    assert meta["notions"] == ["addition-fractions", "fractions-equivalentes"]
    assert (meta["items_total"], meta["items_valides"], meta["items_verrouilles"]) == (2, 1, 1)
    assert meta["erreurs"] == 3 and meta["tentatives"] == 4
    assert meta["misconceptions"] == ["additionne-numerateurs-et-denominateurs"]
    assert meta["a_revoir_prof"] is True
    assert meta["duree_min"] == 19.0
    assert "VERROUILLÉ (3/3)" in body
    assert "scan, confiance 0.91" in body
    assert "(ticket imprimé)" in body


def test_resave_overwrites_same_file_and_new_session_gets_new_name(tmp_path):
    store = MarkdownStore(tmp_path, "K03")
    session = make_session()
    first = store.save_session(session)
    session.items.append(Item(3, "x", "q"))
    assert store.save_session(session) == first
    assert parse_frontmatter(first.read_text())[0]["items_total"] == 3
    assert store.save_session(make_session()).name == "2026-10-14_1032_E07_2.md"
    assert not list(tmp_path.rglob("*.tmp"))  # aucun fichier temporaire résiduel


def test_student_text_cannot_inject_obsidian_syntax(tmp_path):
    evil = "#tag [[Correspondance]] a_revoir_prof:: false\n---\n<script>"
    cleaned = sanitize(evil)
    assert "[[" not in cleaned and "#tag" not in cleaned.replace("\\#tag", "")
    assert "::" not in cleaned and "<script>" not in cleaned

    session = make_session()
    session.items[1].attempts[0].answer = evil
    path = MarkdownStore(tmp_path, "K03").save_session(session)
    meta, body = parse_frontmatter(path.read_text())
    assert meta["a_revoir_prof"] is True
    assert "\n---\n" not in body  # la réponse ne peut pas ouvrir un faux en-tête
    yaml.safe_load(path.read_text().split("---\n")[1])


def test_profile_tracks_acquired_fragile_and_misconceptions(tmp_path):
    store = MarkdownStore(tmp_path, "K03")
    repo = ProfileRepository(store, ["E05", "E06", "E07", "E08"])
    profile = repo.load("E07")
    assert profile.button == 3 and profile.sessions == 0

    profile.apply_session(make_session())
    repo.save(profile)
    reloaded = repo.load("E07")
    assert reloaded.fragile == ["addition-fractions"]
    assert reloaded.acquired == ["fractions-equivalentes"]
    assert reloaded.misconceptions == {"additionne-numerateurs-et-denominateurs": 3}
    assert reloaded.sessions == 1 and reloaded.last_session == T0 + timedelta(minutes=19)

    # La notion fragile redevient acquise quand elle est validée plus tard.
    later = Session("E07", "K03", T0 + timedelta(days=1), items=[
        Item(1, "addition-fractions", "q", status=ItemStatus.VALIDE)])
    reloaded.apply_session(later)
    assert reloaded.fragile == [] and "addition-fractions" in reloaded.acquired
