from pathlib import Path

import pytest

from aristote.tutor.answers import check_answer, detect_leak, extract_numbers, word_numbers
from aristote.tutor.curriculum import load_curriculum
from fractions import Fraction

DEMO = load_curriculum(Path(__file__).parents[1] / "aristote/tutor/curriculum/demo.yaml")


def item(item_id):
    return DEMO.find_item(item_id)[1]


def test_number_extraction_handles_french_writing():
    assert extract_numbers("3,5") == [Fraction(7, 2)]
    assert extract_numbers("1 000 élèves") == [Fraction(1000)]
    assert extract_numbers("2×10³") == [Fraction(2000)]
    assert extract_numbers("25 %") == [Fraction(1, 4)]
    assert extract_numbers("ta 2e tentative") == []
    assert word_numbers("deux septièmes") == [Fraction(2, 7)]
    assert word_numbers("trois quarts et un demi") == [Fraction(3, 4), Fraction(1, 2)]
    assert word_numbers("soixante-dix-sept") == [Fraction(77)]
    assert word_numbers("un indice") == []  # article, pas un nombre


@pytest.mark.parametrize("answer, expected", [
    ("7/12", True), ("14/24", True), ("1/3 + 1/4 = 7/12", True), ("sept douzièmes", True),
    ("0,5833", False), ("2/7", False), ("1/3+1/4 = 2/7", False),
    ("7/12 ou 2/7", None), ("je ne sais pas", None),
])
def test_check_number(answer, expected):
    assert check_answer(item("af-1"), answer) is expected


@pytest.mark.parametrize("answer, expected", [
    ("3x+6", True), ("6 + 3x", True), ("3(x+2) = 3x + 6", True), ("3*x+6", True),
    ("3x + 2", False), ("3x+5", False), ("???", None),
])
def test_check_expression(answer, expected):
    assert check_answer(item("dev-1"), answer) is expected


@pytest.mark.parametrize("answer, expected", [
    ("D", True), ("d", True), ("la réponse D", True), ("allées", True), ("allées.", True),
    ("allés", False), ("B", False), ("allée ou allées", None),
])
def test_check_choice(answer, expected):
    assert check_answer(item("pp-1"), answer) is expected


def test_check_keywords_and_open():
    assert check_answer(item("rf-1"), "La prise de la Bastille") is True
    assert check_answer(item("rf-1"), "Le roi est parti") is None
    assert check_answer(item("ph-1"), "Elle a besoin de lumière") is None


# --- Fuites (critère G1) --------------------------------------------------------------------------

@pytest.mark.parametrize("reply", [
    "La réponse est 7/12.",
    "Tu devrais trouver sept douzièmes.",
    "Ça fait environ 0,583.",
    "Si tu mets au même dénominateur tu obtiens 4/12 + 3/12 = 7/12.",
    "14/24, tu vois ?",
])
def test_number_leaks_are_detected(reply):
    assert detect_leak(item("af-1"), reply) is not None


@pytest.mark.parametrize("reply", [
    "Regarde ta réponse 2/7 : que représente le 7 ?",
    "Quelle fraction de pizza représente 1/3 ? Et 1/4 ?",
    "Essaie de trouver un dénominateur commun à 3 et 4.",
    "C'est ta 2e tentative, prends ton temps.",
])
def test_socratic_replies_are_not_leaks(reply):
    assert detect_leak(item("af-1"), reply, student_answers=["2/7"]) is None


def test_small_integer_leak_needs_an_assertion_or_completed_statement():
    fe1 = item("fe-1")
    assert detect_leak(fe1, "Tu as 2 essais, réfléchis bien.") is None
    assert detect_leak(fe1, "Le nombre manquant est 2.") is not None
    assert detect_leak(fe1, "Donc 1/2 = 2/4, tu vois ?") is not None


def test_student_already_said_it_is_not_a_leak():
    assert detect_leak(item("af-1"), "Tu proposes 7/12 : comment l'as-tu trouvé ?", ["7/12"]) is None


def test_expression_choice_keyword_and_model_answer_leaks():
    assert detect_leak(item("dev-1"), "Il fallait écrire 3x + 6.") is not None
    assert detect_leak(item("dev-1"), "Que vaut 3 fois 2 ?") is None
    assert detect_leak(item("pp-1"), "La bonne réponse est la D.") is not None
    assert detect_leak(item("pp-1"), "Il faut écrire allées.") is not None
    assert detect_leak(item("pp-1"), "Hésites-tu entre allé, allée, allés et allées ?") is None
    assert detect_leak(item("rf-1"), "Pense à la Bastille !") is not None
    assert detect_leak(item("ph-1"), "C'est la photosynthèse qui s'arrête.") is not None
    assert detect_leak(item("ph-1"), "sans lumière la plante ne peut pas réaliser la photosynthèse") is not None
    assert detect_leak(item("ph-1"), "De quoi une plante a-t-elle besoin pour vivre ?") is None


def test_choice_letter_listing_is_not_a_leak():
    pp1 = item("pp-1")
    assert detect_leak(pp1, "Relis les options A, B, C et D : laquelle s'accorde avec le sujet ?") is None
    assert detect_leak(pp1, "C'est la D, bien sûr.") is not None
    assert detect_leak(pp1, "Je te conseille de choisir la lettre D.") is not None
