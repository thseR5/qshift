"""Transparent decomposition metrics for the revision extraction benchmark.

The V6.3 scorer remains historical evidence.  This module intentionally keeps strict
matching separate from component metrics so a room/target alias cannot hide an operation
type mistake, and so missing gold fields are reported as unmeasurable rather than guessed.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

ROOM_ALIASES = {
    "guest room": "guest bedroom",
    "guest-bedroom": "guest bedroom",
    "guest bed room": "guest bedroom",
    "bed room": "bedroom",
    "master bed room": "master bedroom",
}


def normalize_text(value: Any) -> str:
    """Normalize punctuation and whitespace without semantic translation."""

    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    text = text.replace("-", " ")
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return " ".join(text.split())


def normalize_room(value: Any) -> str:
    text = normalize_text(value)
    return ROOM_ALIASES.get(text, text)


def tokens(value: Any) -> set[str]:
    return {token for token in normalize_text(value).split() if len(token) > 1}


def target_match(expected: Any, predicted: Any) -> bool:
    """Accept exact or containment matches, but never unrelated nouns."""

    expected_tokens = tokens(expected)
    predicted_tokens = tokens(predicted)
    if not expected_tokens or not predicted_tokens:
        return not expected_tokens and not predicted_tokens
    return expected_tokens <= predicted_tokens or predicted_tokens <= expected_tokens


def _op_similarity(expected: dict[str, Any], predicted: dict[str, Any]) -> int:
    score = 0
    if expected.get("op") == predicted.get("op"):
        score += 100
    if target_match(expected.get("target_text"), predicted.get("target_text")):
        score += 30
    if normalize_room(expected.get("room")) == normalize_room(predicted.get("room")):
        score += 20
    if expected.get("replacement_text") and target_match(
        expected.get("replacement_text"), predicted.get("replacement_text")
    ):
        score += 10
    return score


def align_operations(
    expected: list[dict[str, Any]], predicted: list[dict[str, Any]]
) -> list[tuple[int, int, int]]:
    """Find a deterministic maximum-weight one-to-one alignment.

    The benchmark has at most a few operations per message, so exhaustive alignment keeps
    the rule auditable and avoids greedy duplicate behaviour.
    """

    best: tuple[int, list[tuple[int, int, int]]] = (0, [])

    def visit(
        expected_index: int,
        used: set[int],
        score: int,
        pairs: list[tuple[int, int, int]],
    ) -> None:
        nonlocal best
        if expected_index == len(expected):
            if score > best[0]:
                best = (score, list(pairs))
            return
        visit(expected_index + 1, used, score, pairs)
        for predicted_index, operation in enumerate(predicted):
            if predicted_index in used:
                continue
            similarity = _op_similarity(expected[expected_index], operation)
            if similarity < 100:
                continue
            used.add(predicted_index)
            pairs.append((expected_index, predicted_index, similarity))
            visit(expected_index + 1, used, score + similarity, pairs)
            pairs.pop()
            used.remove(predicted_index)

    visit(0, set(), 0, [])
    return best[1]


def intent_family(intent: str | None, operations: list[dict[str, Any]]) -> str:
    """Map model-specific intents to benchmark-level intent families."""

    value = normalize_text(intent)
    if value in {"unrelated message", "help"}:
        return "UNRELATED"
    if value in {"project status", "get project changes", "get version history"}:
        return "STATUS"
    if value in {"cancel"}:
        return "CANCEL"
    if value in {"correct previous change"}:
        return "CORRECTION"
    if any(operation.get("op") == "CORRECT_PREVIOUS_CHANGE" for operation in operations):
        return "CORRECTION"
    if any(operation.get("op") in {"ADD", "REMOVE", "REPLACE", "MODIFY"} for operation in operations):
        return "CHANGE"
    if not operations:
        return "UNRELATED"
    return value.upper().replace(" ", "_")


def expected_intent_family(expected: list[dict[str, Any]]) -> str:
    if not expected:
        return "UNRELATED"
    if any(operation.get("op") == "CORRECT_PREVIOUS_CHANGE" for operation in expected):
        return "CORRECTION"
    if any(operation.get("op") == "CANCEL" for operation in expected):
        return "CANCEL"
    if any(operation.get("op") == "PROJECT_STATUS" for operation in expected):
        return "STATUS"
    return "CHANGE"


@dataclass(frozen=True)
class ForensicScore:
    expected_count: int
    predicted_count: int
    strict_tp: int
    operation_type_tp: int
    target_tp: int
    room_tp: int
    aligned_pairs: int
    type_fp: int
    type_fn: int
    target_fp: int
    target_fn: int
    room_fp: int
    room_fn: int
    intent_correct: bool
    expected_clarification: bool
    predicted_clarification: bool
    fully_correct: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "expected_count": self.expected_count,
            "predicted_count": self.predicted_count,
            "strict_tp": self.strict_tp,
            "operation_type_tp": self.operation_type_tp,
            "target_tp": self.target_tp,
            "room_tp": self.room_tp,
            "aligned_pairs": self.aligned_pairs,
            "type_fp": self.type_fp,
            "type_fn": self.type_fn,
            "target_fp": self.target_fp,
            "target_fn": self.target_fn,
            "room_fp": self.room_fp,
            "room_fn": self.room_fn,
            "intent_correct": self.intent_correct,
            "expected_clarification": self.expected_clarification,
            "predicted_clarification": self.predicted_clarification,
            "fully_correct": self.fully_correct,
        }


def score_case(
    expected: list[dict[str, Any]],
    predicted: list[dict[str, Any]],
    *,
    expected_intent: str | None = None,
    predicted_intent: str | None = None,
    expected_clarification: bool = False,
    predicted_clarification: bool | None = None,
) -> ForensicScore:
    pairs = align_operations(expected, predicted)
    expected_by_type = Counter(operation.get("op") for operation in expected)
    predicted_by_type = Counter(operation.get("op") for operation in predicted)
    operation_type_tp = sum(
        min(expected_by_type[operation_type], predicted_by_type[operation_type])
        for operation_type in expected_by_type
    )
    target_tp = sum(
        target_match(expected[expected_index].get("target_text"), predicted[predicted_index].get("target_text"))
        for expected_index, predicted_index, _ in pairs
    )
    room_tp = sum(
        normalize_room(expected[expected_index].get("room"))
        == normalize_room(predicted[predicted_index].get("room"))
        for expected_index, predicted_index, _ in pairs
    )
    strict_expected = {
        (
            operation.get("op"),
            operation.get("room"),
            normalize_text(operation.get("target_text")),
        )
        for operation in expected
    }
    strict_predicted = {
        (
            operation.get("op"),
            operation.get("room"),
            normalize_text(operation.get("target_text")),
        )
        for operation in predicted
    }
    strict_tp = len(strict_expected & strict_predicted)
    if predicted_clarification is None:
        predicted_clarification = any(
            operation.get("missing_fields") for operation in predicted
        )
    fully_correct = (
        len(expected) == len(predicted)
        and operation_type_tp == len(expected)
        and target_tp == len(expected)
        and room_tp == len(expected)
        and (
            expected_intent is None
            or intent_family(predicted_intent, predicted)
            == expected_intent
        )
    )
    return ForensicScore(
        expected_count=len(expected),
        predicted_count=len(predicted),
        strict_tp=strict_tp,
        operation_type_tp=operation_type_tp,
        target_tp=target_tp,
        room_tp=room_tp,
        aligned_pairs=len(pairs),
        type_fp=max(0, len(predicted) - operation_type_tp),
        type_fn=max(0, len(expected) - operation_type_tp),
        target_fp=max(0, len(predicted) - target_tp),
        target_fn=max(0, len(expected) - target_tp),
        room_fp=max(0, len(predicted) - room_tp),
        room_fn=max(0, len(expected) - room_tp),
        intent_correct=(
            expected_intent is None
            or intent_family(predicted_intent, predicted) == expected_intent
        ),
        expected_clarification=expected_clarification,
        predicted_clarification=predicted_clarification,
        fully_correct=fully_correct,
    )


def aggregate(scores: Iterable[ForensicScore]) -> dict[str, Any]:
    rows = list(scores)
    expected = sum(row.expected_count for row in rows)
    predicted = sum(row.predicted_count for row in rows)
    strict_tp = sum(row.strict_tp for row in rows)
    type_tp = sum(row.operation_type_tp for row in rows)
    target_tp = sum(row.target_tp for row in rows)
    room_tp = sum(row.room_tp for row in rows)
    expected_clarification = sum(row.expected_clarification for row in rows)
    predicted_clarification = sum(row.predicted_clarification for row in rows)
    clar_tp = sum(
        row.expected_clarification and row.predicted_clarification for row in rows
    )
    def f1(precision: float, recall: float) -> float:
        return 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    strict_precision = strict_tp / predicted if predicted else 0.0
    strict_recall = strict_tp / expected if expected else 0.0
    type_precision = type_tp / predicted if predicted else 0.0
    type_recall = type_tp / expected if expected else 0.0
    target_precision = target_tp / predicted if predicted else 0.0
    target_recall = target_tp / expected if expected else 0.0
    room_precision = room_tp / predicted if predicted else 0.0
    room_recall = room_tp / expected if expected else 0.0
    return {
        "cases": len(rows),
        "expected_operations": expected,
        "predicted_operations": predicted,
        "strict_precision": strict_precision,
        "strict_recall": strict_recall,
        "strict_f1": f1(strict_precision, strict_recall),
        "operation_type_precision": type_precision,
        "operation_type_recall": type_recall,
        "operation_type_f1": f1(type_precision, type_recall),
        "target_precision": target_precision,
        "target_recall": target_recall,
        "target_f1": f1(target_precision, target_recall),
        "room_precision": room_precision,
        "room_recall": room_recall,
        "room_f1": f1(room_precision, room_recall),
        "fully_correct_rate": sum(row.fully_correct for row in rows) / len(rows) if rows else 0.0,
        "intent_accuracy": sum(row.intent_correct for row in rows) / len(rows) if rows else 0.0,
        "clarification_accuracy": sum(
            row.expected_clarification == row.predicted_clarification for row in rows
        )
        / len(rows)
        if rows
        else 0.0,
        "clarification_precision": clar_tp / predicted_clarification if predicted_clarification else 0.0,
        "clarification_recall": clar_tp / expected_clarification if expected_clarification else 0.0,
    }
