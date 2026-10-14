from datetime import datetime

from aristote.storage import Attempt, InputMode, Item, ItemStatus, Verdict
from aristote.tutor.state import MAX_ERRORS, Action, apply_action, next_action


def play(verdicts):
    item = Item(1, "n", "q")
    actions = []
    for v in verdicts:
        item.attempts.append(Attempt(len(item.attempts) + 1, InputMode.SAISIE, "x", v, datetime.now()))
        action = next_action(item, v)
        apply_action(item, action)
        actions.append(action)
    return item, actions


def test_lock_exactly_at_third_error():
    assert MAX_ERRORS == 3
    item, actions = play([Verdict.FAUX, Verdict.PARTIEL, Verdict.FAUX])
    assert actions == [Action.RELANCER, Action.INDICE, Action.VERROUILLER]
    assert item.status is ItemStatus.VERROUILLE


def test_help_requests_do_not_count():
    item, actions = play([Verdict.FAUX, Verdict.INCOMPRIS, Verdict.INCOMPRIS, Verdict.FAUX, Verdict.FAUX])
    assert actions == [Action.RELANCER, Action.REFORMULER, Action.REFORMULER, Action.INDICE, Action.VERROUILLER]


def test_correct_answer_validates_and_item_stays_closed():
    item, actions = play([Verdict.FAUX, Verdict.JUSTE, Verdict.FAUX])
    assert actions == [Action.RELANCER, Action.VALIDER, Action.DEJA_TERMINE]
    assert item.status is ItemStatus.VALIDE


def test_locked_item_never_reopens():
    item, actions = play([Verdict.FAUX] * 3 + [Verdict.JUSTE])
    assert actions[-1] is Action.DEJA_TERMINE and item.status is ItemStatus.VERROUILLE
