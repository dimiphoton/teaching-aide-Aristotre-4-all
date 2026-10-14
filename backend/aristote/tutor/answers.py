"""Vérifications déterministes, indépendantes de la matière : correction d'une réponse et détection de fuite.

Ces fonctions s'appuient uniquement sur le `type_reponse` déclaré dans le cours. Elles servent :
- au tuteur, en direct : le verdict déterministe prime sur celui du LLM, et toute réponse du tuteur
  qui contient la solution est bloquée avant d'être affichée (critère éliminatoire G1) ;
- au harnais d'évaluation (`eval/`), qui les réutilise telles quelles.

`check_answer` renvoie True (juste), False (faux) ou None (indécidable : le LLM tranche).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from fractions import Fraction

from .curriculum import AnswerType, CurriculumItem

# --- Normalisation ----------------------------------------------------------------------------------

_SUPERSCRIPTS = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻", "0123456789-")


def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def normalize_text(text: str) -> str:
    """Minuscules, sans accents, ponctuation réduite à des espaces."""
    text = strip_accents(text.lower()).replace("’", "'")
    return re.sub(r"\s+", " ", re.sub(r"[^\w'/+\-*=^.,%]", " ", text)).strip()


def normalize_math(text: str) -> str:
    text = re.sub(r"([⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+)", lambda m: "^" + m.group(1).translate(_SUPERSCRIPTS), text)
    text = (text.replace("×", "*").replace("·", "*").replace("÷", "/").replace("−", "-")
            .replace("–", "-").replace(" ", " ").replace(" ", " "))
    return text


def compact(text: str) -> str:
    return re.sub(r"\s+", "", normalize_math(text)).lower()


# --- Nombres -----------------------------------------------------------------------------------------

_NUMBER = re.compile(
    r"(?<![\w.,])[-+]?\d+(?:[.,]\d+)?"
    r"(?:\s*/\s*\d+(?:[.,]\d+)?)?"
    r"(?:\s*[x*]\s*10\s*\^\s*[-+]?\d+|e[-+]?\d+)?"
    r"(?:\s*%)?(?![\w])"
)
_ORDINAL = re.compile(r"\d+\s*(?:e|eme|ème|er|re|nd|nde)\b", re.IGNORECASE)

_UNITS = {
    "zero": 0, "un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "six": 6, "sept": 7,
    "huit": 8, "neuf": 9, "dix": 10, "onze": 11, "douze": 12, "treize": 13, "quatorze": 14, "quinze": 15,
    "seize": 16, "vingt": 20, "vingts": 20, "trente": 30, "quarante": 40, "cinquante": 50, "soixante": 60,
    "cent": 100, "cents": 100,
}
_DENOMINATORS = {"demi": 2, "demis": 2, "demie": 2, "tiers": 3, "quart": 4, "quarts": 4}


def _parse_number_token(token: str) -> Fraction | None:
    t = token.replace(" ", "").replace(",", ".")
    percent = t.endswith("%")
    t = t.rstrip("%")
    try:
        m = re.fullmatch(r"([-+]?[\d.]+)(?:/([\d.]+))?(?:[x*]10\^([-+]?\d+)|e([-+]?\d+))?", t)
        if not m:
            return None
        value = Fraction(m.group(1))
        if m.group(2):
            den = Fraction(m.group(2))
            if den == 0:
                return None
            value /= den
        exp = m.group(3) or m.group(4)
        if exp:
            value *= Fraction(10) ** int(exp)
    except (ValueError, ZeroDivisionError):
        return None
    return value / 100 if percent else value


def _words_to_int(words: list[str]) -> int | None:
    """« soixante-dix-sept », « vingt et un », « quatre-vingt-douze »… (0 à 999)."""
    total, current, seen = 0, 0, False
    for w in words:
        if w == "et":
            continue
        if w not in _UNITS:
            return None
        v = _UNITS[w]
        seen = True
        if v == 100:
            current = max(current, 1) * 100
        elif v == 20 and current in (4,):  # quatre-vingt
            current *= 20
        else:
            current += v
    return total + current if seen else None


def word_numbers(text: str) -> list[Fraction]:
    """Nombres et fractions écrits en toutes lettres (« deux septièmes », « trois quarts », « douze »)."""
    tokens = re.findall(r"[a-z]+", strip_accents(text.lower()).replace("-", " "))
    values: list[Fraction] = []
    i = 0
    while i < len(tokens):
        j = i
        while j < len(tokens) and (tokens[j] in _UNITS or (tokens[j] == "et" and j > i)):
            j += 1
        if j > i:
            num = _words_to_int(tokens[i:j])
            followed_by_fraction = j < len(tokens) and (
                tokens[j] in _DENOMINATORS or re.fullmatch(r"[a-z]+iemes?", tokens[j]) is not None)
            if tokens[i:j] in (["un"], ["une"]) and not followed_by_fraction:
                i = j  # article « un / une », pas un nombre
                continue
            if num is not None and j < len(tokens):
                den = _DENOMINATORS.get(tokens[j])
                ordinal = re.fullmatch(r"([a-z]+?)iemes?", tokens[j])
                if den is None and ordinal:
                    base = ordinal.group(1)
                    base = {"cinqu": "cinq", "neuv": "neuf", "quatr": "quatre", "onz": "onze",
                            "douz": "douze", "treiz": "treize", "quatorz": "quatorze", "quinz": "quinze",
                            "seiz": "seize", "trent": "trente", "quarant": "quarante"}.get(base, base)
                    den = _UNITS.get(base)
                if den:
                    values.append(Fraction(num, den))
                    i = j + 1
                    continue
            if num is not None:
                values.append(Fraction(num))
            i = j
        else:
            i += 1
    return values


def extract_numbers(text: str, with_words: bool = True) -> list[Fraction]:
    text = normalize_math(text)
    text = re.sub(r"(\d)[ ](\d{3})(?!\d)", r"\1\2", text)  # séparateur de milliers « 1 000 »
    text = _ORDINAL.sub(" ", text)
    values = [v for v in (_parse_number_token(m.group(0)) for m in _NUMBER.finditer(text)) if v is not None]
    if with_words:
        values.extend(word_numbers(text))
    return values


def _within(value: Fraction, expected: Fraction, tolerance: str) -> bool:
    tol = tolerance.strip()
    if tol.endswith("%"):
        return abs(value - expected) <= abs(expected) * Fraction(tol[:-1].replace(",", ".")) / 100
    return abs(value - expected) <= Fraction(tol.replace(",", ".") or "0")


def _expected_numbers(item: CurriculumItem) -> list[Fraction]:
    values = []
    for ref in [item.reponse, *item.variantes]:
        found = extract_numbers(ref)
        if found:
            values.append(found[0])
    return values


# --- Correction ---------------------------------------------------------------------------------------

def _final_segment(answer: str) -> str:
    """Pour « 1/3 + 1/4 = 7/12 », la réponse est ce qui suit le dernier « = »."""
    return answer.rsplit("=", 1)[-1] if "=" in answer else answer


def _check_number(item: CurriculumItem, answer: str) -> bool | None:
    expected = _expected_numbers(item)
    if not expected:
        return None
    values = extract_numbers(_final_segment(answer))
    if not values:
        return None
    matches = [any(_within(v, e, item.tolerance) for e in expected) for v in values]
    if all(matches):
        return True
    if not any(matches):
        return False
    return None  # plusieurs nombres dont un seul est juste : le LLM tranche


def _sympy_equal(a: str, b: str) -> bool | None:
    try:
        from sympy import simplify
        from sympy.parsing.sympy_parser import (
            convert_xor,
            implicit_multiplication_application,
            parse_expr,
            standard_transformations,
        )
    except ImportError:
        return None
    transformations = standard_transformations + (implicit_multiplication_application, convert_xor)

    def parse(s: str):
        s = normalize_math(s).replace(",", ".")
        if "=" in s:
            left, right = s.split("=", 1)
            return parse_expr(left, transformations=transformations) - parse_expr(right, transformations=transformations)
        return parse_expr(s, transformations=transformations)

    try:
        return bool(simplify(parse(a) - parse(b)) == 0)
    except Exception:  # noqa: BLE001 - toute erreur de syntaxe = indécidable
        return None


def _check_expression(item: CurriculumItem, answer: str) -> bool | None:
    refs = [item.reponse, *item.variantes]
    student = answer.strip()
    if "=" not in item.reponse:
        student = _final_segment(student)
    if any(compact(student) == compact(r) for r in refs):
        return True
    if item.forme == "texte":
        return False
    results = [_sympy_equal(student, r) for r in refs]
    if any(r is True for r in results):
        return True
    if all(r is False for r in results):
        return False
    return None


_LETTER = re.compile(r"(?:^|\b(?:reponse|choix|option|la|le|c'est)\s*)\(?([a-h])\)?(?:\s|$|[.)!])", re.IGNORECASE)


def _check_choice(item: CurriculumItem, answer: str) -> bool | None:
    correct = item.correct_choice_index()
    norm = normalize_text(answer)
    chosen: set[int] = set()
    if len(norm) <= 2 and norm[:1].isalpha():
        chosen.add(ord(norm[0]) - ord("a"))
    else:
        m = _LETTER.search(norm)
        if m:
            chosen.add(ord(m.group(1).lower()) - ord("a"))
    for i, option in enumerate(item.choix):
        if _contains_term(norm, option):
            chosen.add(i)
    chosen = {c for c in chosen if 0 <= c < len(item.choix)}
    if not chosen:
        return None
    if len(chosen) > 1:
        return False if correct not in chosen else None
    return correct in chosen


def _contains_term(norm_text: str, term: str) -> bool:
    t = normalize_text(term)
    return bool(t) and re.search(rf"(?<!\w){re.escape(t)}(?!\w)", norm_text) is not None


def _check_keywords(item: CurriculumItem, answer: str) -> bool | None:
    norm = normalize_text(answer)
    if all(any(_contains_term(norm, syn) for syn in group) for group in item.keyword_groups()):
        return True
    return None  # une paraphrase peut être juste : le LLM tranche


def check_answer(item: CurriculumItem, answer: str) -> bool | None:
    if not answer.strip():
        return None
    t = item.type_reponse
    if t is AnswerType.NOMBRE:
        return _check_number(item, answer)
    if t is AnswerType.EXPRESSION:
        return _check_expression(item, answer)
    if t is AnswerType.CHOIX:
        return _check_choice(item, answer)
    if t is AnswerType.MOTS_CLES:
        return _check_keywords(item, answer)
    return None


# --- Détection de fuite -------------------------------------------------------------------------------

@dataclass
class Leak:
    reason: str
    excerpt: str


_ASSERTIVE = re.compile(
    r"(=|\best\b|c'est|\bfont\b|\bfait\b|egal|\bvaut\b|donne|obtiens?|trouve|reponse|resultat|solution)\W*$"
)


def _ngrams(words: list[str], n: int) -> set[tuple[str, ...]]:
    return {tuple(words[i:i + n]) for i in range(len(words) - n + 1)}


def detect_leak(
    item: CurriculumItem,
    tutor_text: str,
    student_answers: list[str] | None = None,
    ngram: int = 6,
) -> Leak | None:
    """Renvoie une fuite si `tutor_text` révèle la réponse attendue de `item`.

    Ce que l'élève a déjà écrit lui-même et ce que contient l'énoncé ne comptent pas comme une fuite.
    """
    student_answers = student_answers or []
    t = item.type_reponse
    norm_tutor = normalize_text(tutor_text)

    if t is AnswerType.NOMBRE:
        expected = _expected_numbers(item)
        in_question = extract_numbers(item.question)
        said_by_student = [v for a in student_answers for v in extract_numbers(a)]
        tolerance = item.tolerance if item.tolerance.strip() not in ("", "0") else "0.5%"
        math_text = normalize_math(tutor_text)
        for m in _NUMBER.finditer(math_text):
            value = _parse_number_token(m.group(0))
            if value is None or not any(_within(value, e, tolerance) for e in expected):
                continue
            if any(value == q for q in in_question) or any(value == s for s in said_by_student):
                continue
            small_integer = value.denominator == 1 and abs(value) <= 20
            if small_integer:
                before = normalize_text(math_text[max(0, m.start() - 30):m.start()] + " ")
                if not _ASSERTIVE.search(before.strip()) and "/" not in m.group(0):
                    continue  # « 2 indices », « ta 3e tentative » : pas une affirmation de résultat
            return Leak("nombre attendu présent", m.group(0).strip())
        for value in word_numbers(tutor_text):
            if any(_within(value, e, tolerance) for e in expected) and value not in in_question \
                    and value not in said_by_student and not (value.denominator == 1 and abs(value) <= 20):
                return Leak("nombre attendu écrit en lettres", str(value))
        # Énoncé à trou (« 1/2 = ?/4 ») : l'énoncé complété est une fuite.
        for hole in re.findall(r"\S*\?\S*", item.question):
            for ref in [item.reponse, *item.variantes]:
                completed = compact(hole.replace("?", ref.strip()))
                if len(completed) > len(compact(ref)) and completed in compact(tutor_text):
                    return Leak("énoncé à trou complété", completed)

    elif t is AnswerType.EXPRESSION:
        tutor_compact = compact(tutor_text)
        student_compact = {compact(a) for a in student_answers}
        for ref in [item.reponse, *item.variantes]:
            ref_c = compact(ref)
            if ref_c and ref_c not in compact(item.question) and ref_c in tutor_compact \
                    and not any(ref_c in s for s in student_compact):
                return Leak("expression attendue présente", ref)

    elif t is AnswerType.CHOIX:
        idx = item.correct_choice_index()
        letter = chr(ord("a") + idx)
        filler = r"(?:\W+(?:est|c'est|la|le|l'|reponse|option|choix|donc|bien|plutot|lettre))*"
        pattern = rf"(reponse|bonne|c'est|choisis|choisir|prends|option|choix|lettre){filler}\W*\(?{letter}\)?(?!\w)"
        m = re.search(pattern, norm_tutor)
        if m:
            return Leak("lettre de la bonne option affirmée", m.group(0))
        options = [normalize_text(o) for o in item.choix]
        correct = options[idx]
        others_present = any(_contains_term(norm_tutor, o) for i, o in enumerate(item.choix) if i != idx)
        if len(correct) >= 3 and _contains_term(norm_tutor, item.choix[idx]) and not others_present \
                and not _contains_term(normalize_text(item.question), item.choix[idx]):
            return Leak("texte de la bonne option seul", item.choix[idx])

    if t in (AnswerType.MOTS_CLES, AnswerType.OUVERTE) or t is AnswerType.CHOIX:
        norm_question = normalize_text(item.question)
        norm_students = normalize_text(" ".join(student_answers))
        for group in item.keyword_groups():
            for syn in group:
                if _contains_term(norm_tutor, syn) and not _contains_term(norm_question, syn) \
                        and not _contains_term(norm_students, syn):
                    return Leak("mot-clé attendu révélé", syn)

    # Recopie d'un long passage de la réponse modèle (tous types).
    if item.reponse and len(item.reponse.split()) >= ngram:
        ref_words = normalize_text(item.reponse).split()
        tutor_words = norm_tutor.split()
        common = _ngrams(ref_words, ngram) & _ngrams(tutor_words, ngram)
        common -= _ngrams(normalize_text(item.question).split(), ngram)
        if common:
            return Leak("passage de la réponse modèle recopié", " ".join(next(iter(common))))
    return None
