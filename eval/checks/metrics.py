"""Métriques : CER, WER, réponse finale exacte, accord entre juges (kappa), indice de Rand ajusté."""

from __future__ import annotations

import re
from collections import Counter
from itertools import combinations
from math import comb

from aristote.tutor.answers import extract_numbers, normalize_text


def levenshtein(a: list | str, b: list | str) -> int:
    previous = list(range(len(b) + 1))
    for i, x in enumerate(a, start=1):
        current = [i]
        for j, y in enumerate(b, start=1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (x != y)))
        previous = current
    return previous[-1]


def cer(hypothesis: str, reference: str) -> float:
    """Taux d'erreur par caractère (espaces normalisés, casse conservée)."""
    ref, hyp = " ".join(reference.split()), " ".join(hypothesis.split())
    return levenshtein(hyp, ref) / max(1, len(ref))


def wer(hypothesis: str, reference: str) -> float:
    words = lambda text: re.findall(r"[\w'/^*+=-]+", normalize_text(text))
    ref, hyp = words(reference), words(hypothesis)
    return levenshtein(hyp, ref) / max(1, len(ref))


def final_answer_match(hypothesis: str, reference: str) -> bool:
    """La partie évaluée est-elle lue correctement ? Nombres de la dernière ligne si présents, sinon texte normalisé."""
    ref_tail = reference.strip().splitlines()[-1] if reference.strip() else ""
    hyp_tail = hypothesis.strip().splitlines()[-1] if hypothesis.strip() else ""
    ref_tail, hyp_tail = ref_tail.rsplit("=", 1)[-1], hyp_tail.rsplit("=", 1)[-1]
    ref_numbers = extract_numbers(ref_tail)
    if ref_numbers:
        return extract_numbers(hyp_tail) == ref_numbers
    return normalize_text(ref_tail) == normalize_text(hyp_tail)


def cohen_kappa(a: list, b: list, weights: str | None = None, categories: list | None = None) -> float | None:
    """Kappa de Cohen (pondération quadratique possible pour des notes ordinales)."""
    if len(a) != len(b) or not a:
        return None
    cats = categories or sorted(set(a) | set(b))
    index = {c: i for i, c in enumerate(cats)}
    k = len(cats)
    if k == 1:
        return 1.0
    n = len(a)
    observed = [[0.0] * k for _ in range(k)]
    for x, y in zip(a, b):
        observed[index[x]][index[y]] += 1 / n
    pa, pb = Counter(a), Counter(b)
    expected = [[pa[cats[i]] / n * pb[cats[j]] / n for j in range(k)] for i in range(k)]

    def w(i: int, j: int) -> float:
        if weights == "quadratic":
            return ((i - j) / (k - 1)) ** 2
        return 0.0 if i == j else 1.0

    num = sum(w(i, j) * observed[i][j] for i in range(k) for j in range(k))
    den = sum(w(i, j) * expected[i][j] for i in range(k) for j in range(k))
    return 1.0 if den == 0 else 1 - num / den


def mean_pairwise_kappa(ratings: list[list], weights: str | None = None, categories: list | None = None) -> float | None:
    """`ratings[j]` = notes du juge j sur les mêmes éléments."""
    values = [cohen_kappa(x, y, weights, categories) for x, y in combinations(ratings, 2)]
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def adjusted_rand_index(labels_true: list, labels_pred: list) -> float:
    contingency = Counter(zip(labels_true, labels_pred))
    sum_comb = sum(comb(v, 2) for v in contingency.values())
    a = sum(comb(v, 2) for v in Counter(labels_true).values())
    b = sum(comb(v, 2) for v in Counter(labels_pred).values())
    total = comb(len(labels_true), 2)
    if total == 0:
        return 1.0
    expected = a * b / total
    maximum = (a + b) / 2
    return 1.0 if maximum == expected else (sum_comb - expected) / (maximum - expected)
