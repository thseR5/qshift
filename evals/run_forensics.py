"""Audit a completed live-evaluation JSONL without rerunning the model.

This produces a forensic decomposition of the V6.3 run. It does not alter the historical
scorer or count deterministic service decisions as model successes.
"""

from __future__ import annotations

import json
import os
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from evals.forensics import (
    aggregate,
    expected_intent_family,
    intent_family,
    normalize_room,
    score_case,
    tokens,
)

CONTEXT_LINES = [
    {"line_id": "kitchen-counter", "room": "Kitchen", "category": "Countertop", "description": "Granite countertop", "sku": "COUNTER-GRANITE"},
    {"line_id": "guest-ceiling", "room": "Guest Bedroom", "category": "Ceiling", "description": "Gypsum false ceiling", "sku": "FALSE-CEILING-GYPSUM"},
    {"line_id": "wardrobe", "room": "Guest Bedroom", "category": "Wardrobe", "description": "White laminate wardrobe", "sku": "WARDROBE-WHITE-LAMINATE"},
]


def _operations(record: dict[str, Any]) -> list[dict[str, Any]]:
    output = record.get("raw_output") or {}
    return list(output.get("operations") or []) if isinstance(output, dict) else []


def _historical_pair(operation: dict[str, Any]) -> tuple[Any, Any, str]:
    return (
        operation.get("op"),
        operation.get("room"),
        str(operation.get("target_text", "")).casefold(),
    )


def _historical_metrics(expected: list[dict[str, Any]], predicted: list[dict[str, Any]]) -> tuple[int, int, int]:
    expected_set = {_historical_pair(item) for item in expected}
    predicted_set = {_historical_pair(item) for item in predicted}
    return (
        len(expected_set & predicted_set),
        len(predicted_set - expected_set),
        len(expected_set - predicted_set),
    )


def _context_candidates(operation: dict[str, Any]) -> list[dict[str, Any]]:
    requested = tokens(operation.get("target_text"))
    room = normalize_room(operation.get("room"))
    ranked: list[tuple[dict[str, Any], int]] = []
    for line in CONTEXT_LINES:
        line_tokens = tokens(" ".join(str(line[key]) for key in ("category", "description", "sku")))
        score = len(requested & line_tokens)
        if room and room == normalize_room(line["room"]):
            score += 4
        if operation.get("target_line_id") == line["line_id"]:
            score += 100
        if score:
            ranked.append((line, score))
    if not ranked:
        return []
    highest = max(score for _, score in ranked)
    return [line for line, score in ranked if score == highest]


def _gate_prediction(operations: list[dict[str, Any]]) -> str:
    if not operations:
        return "REJECTED/OUT_OF_SCOPE"
    if any(operation.get("missing_fields") for operation in operations):
        return "HELD_FOR_CLARIFICATION"
    for operation in operations:
        kind = operation.get("op")
        if kind in {"ADD", "REPLACE"}:
            return "HELD_FOR_VERIFIED_CATALOGUE"
        if kind in {"REMOVE", "MODIFY", "CORRECT_PREVIOUS_CHANGE"}:
            candidates = _context_candidates(operation)
            if len(candidates) != 1:
                return "HELD_FOR_TARGET_REVIEW"
    return "CANDIDATE_ONLY; ENDPOINT_NOT_INVOKED"


def _classification(
    expected: list[dict[str, Any]],
    predicted: list[dict[str, Any]],
    validation_error: str | None,
    score: Any,
) -> str:
    if validation_error:
        return "SCHEMA_OR_RUNTIME_FAILURE"
    if not expected and not predicted:
        return "CORRECT_NOOP"
    if not expected and predicted:
        return "UNEXPECTED_OPERATION"
    if score.operation_type_tp == 0:
        return "OPERATION_TYPE_ERROR"
    if score.target_tp < score.operation_type_tp:
        return "TARGET_ERROR"
    if score.room_tp < score.operation_type_tp:
        return "ROOM_ERROR"
    if score.expected_clarification != score.predicted_clarification:
        return "CLARIFICATION_DECISION_ERROR"
    if not score.fully_correct:
        return "MULTI_OPERATION_OR_INTENT_ERROR"
    return "CORRECT_EXTRACTION"


def _load() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    fixture = json.loads(Path("qshift/fixtures/revision_eval_v1.json").read_text())
    path = Path(os.getenv("QSHIFT_FORENSIC_INPUT", "work/revision_eval_live_v63.jsonl"))
    records = {json.loads(line)["id"]: json.loads(line) for line in path.read_text().splitlines() if line.strip()}
    return fixture, records


def main() -> int:
    cases, records = _load()
    scores = []
    by_language: dict[str, list[Any]] = defaultdict(list)
    rows: list[dict[str, Any]] = []
    strict_tp = strict_fp = strict_fn = 0
    latencies: list[float] = []
    coverage = 0
    for case in cases:
        record = records.get(case["id"], {})
        predicted = _operations(record)
        expected = case["expected_ops"]
        predicted_intent = (record.get("raw_output") or {}).get("intent")
        predicted_clarification = bool(
            (record.get("raw_output") or {}).get("clarification")
            or any(operation.get("missing_fields") for operation in predicted)
        )
        score = score_case(
            expected,
            predicted,
            expected_intent=expected_intent_family(expected),
            predicted_intent=predicted_intent,
            expected_clarification=bool(case["requires_clarification"]),
            predicted_clarification=predicted_clarification,
        )
        scores.append(score)
        by_language[case["language"]].append(score)
        tp, fp, fn = _historical_metrics(expected, predicted)
        strict_tp += tp
        strict_fp += fp
        strict_fn += fn
        if record.get("latency_ms") is not None:
            latencies.append(float(record["latency_ms"]))
        expected_context = any(
            len(_context_candidates(operation)) == 1 for operation in expected
        )
        coverage += int(expected_context)
        rows.append(
            {
                "id": case["id"],
                "language": case["language"],
                "expected": expected,
                "predicted": predicted,
                "classification": _classification(
                    expected, predicted, record.get("validation_error"), score
                ),
                "gate_prediction": _gate_prediction(predicted),
                "intent_expected": expected_intent_family(expected),
                "intent_predicted": intent_family(predicted_intent, predicted),
                "fully_correct": score.fully_correct,
                "context_has_unique_gold_target": expected_context,
            }
        )
    overall = aggregate(scores)
    overall.update(
        {
            "historical_exact_precision": strict_tp / (strict_tp + strict_fp) if strict_tp + strict_fp else 0.0,
            "historical_exact_recall": strict_tp / (strict_tp + strict_fn) if strict_tp + strict_fn else 0.0,
            "historical_exact_tp": strict_tp,
            "historical_exact_fp": strict_fp,
            "historical_exact_fn": strict_fn,
            "invalid_or_missing_records": sum(
                int(bool(record.get("validation_error"))) for record in records.values()
            ),
            "gold_cases_with_unique_context_target": coverage,
            "gold_cases_without_unique_context_target": len(cases) - coverage,
            "latency_median_ms": statistics.median(latencies) if latencies else None,
            "latency_p95_ms": statistics.quantiles(latencies, n=20)[18] if len(latencies) > 1 else (latencies[0] if latencies else None),
        }
    )
    output = Path(os.getenv("QSHIFT_FORENSIC_OUTPUT", "work/revision_eval_forensics_v64.json"))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"metrics": overall, "rows": rows}, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(overall, ensure_ascii=False, indent=2))
    print(f"Forensic records: {output}")
    for language, language_scores in sorted(by_language.items()):
        print(language, json.dumps(aggregate(language_scores), ensure_ascii=False))
    print("Error classifications", Counter(row["classification"] for row in rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
