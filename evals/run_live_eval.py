"""Run the versioned revision set against the configured local Ollama model."""

from __future__ import annotations

import json
import os
import statistics
import time
from collections import defaultdict
from pathlib import Path

from qshift.agent.extraction import LocalModelUnavailable, OllamaChangeLLM


def _pair(operation: dict) -> tuple[str, str | None, str]:
    return operation["op"], operation.get("room"), operation.get("target_text", "").casefold()


def main() -> int:
    cases = json.loads(Path("qshift/fixtures/revision_eval_v1.json").read_text())
    start = int(os.getenv("QSHIFT_EVAL_START", "0"))
    limit = os.getenv("QSHIFT_EVAL_LIMIT")
    cases = cases[start : start + int(limit) if limit else None]
    model = OllamaChangeLLM()
    output_path = Path(os.getenv("QSHIFT_LIVE_EVAL_OUTPUT", "work/revision_eval_live.jsonl"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("")
    totals = defaultdict(lambda: [0, 0, 0, 0, 0, 0, 0.0])
    examples: list[dict] = []
    invalid_outputs = 0
    latencies: list[float] = []
    matched_targets = 0
    wrong_targets = 0
    missing_changes = 0
    expected_total = 0
    full_context = {
        "quotation_lines": [
            {"line_id": "kitchen-counter", "room": "Kitchen", "category": "Countertop", "description": "Granite countertop", "sku": "COUNTER-GRANITE", "quantity": "40", "unit": "sqft"},
            {"line_id": "guest-ceiling", "room": "Guest Bedroom", "category": "Ceiling", "description": "Gypsum false ceiling", "sku": "FALSE-CEILING-GYPSUM", "quantity": "120", "unit": "sqft"},
            {"line_id": "wardrobe", "room": "Guest Bedroom", "category": "Wardrobe", "description": "White laminate wardrobe", "sku": "WARDROBE-WHITE-LAMINATE", "quantity": "42", "unit": "sqft"},
        ],
        "verified_catalogue": [],
    }
    context = full_context if os.getenv("QSHIFT_EVAL_CONTEXT_MODE", "full") == "full" else {}
    for case in cases:
        started = time.perf_counter()
        try:
            result = model.extract(case["text"], context)
        except LocalModelUnavailable as exc:
            record = {
                "id": case["id"],
                "language": case["language"],
                "input": case["text"],
                "expected_ops": case["expected_ops"],
                "raw_output": model.last_raw,
                "raw_output_text": model.last_raw_text,
                "response_meta": model.last_meta,
                "normalized_output": None,
                "validation_error": str(exc),
                "latency_ms": round((time.perf_counter() - started) * 1000, 1),
                "model": model.model,
            }
            with output_path.open("a") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            print(f"case {case['id']} ERROR: {exc}", flush=True)
            invalid_outputs += 1
            examples.append({"id": case["id"], "expected": case["expected_ops"], "actual": None, "error": str(exc)})
            continue
        elapsed = (time.perf_counter() - started) * 1000
        latencies.append(elapsed)
        with output_path.open("a") as handle:
            handle.write(
                json.dumps(
                    {
                        "id": case["id"],
                        "language": case["language"],
                        "input": case["text"],
                        "expected_ops": case["expected_ops"],
                        "raw_output": model.last_raw,
                        "raw_output_text": model.last_raw_text,
                        "response_meta": model.last_meta,
                        "normalized_output": result.model_dump(mode="json"),
                        "validation_error": None,
                        "latency_ms": round(elapsed, 1),
                        "model": model.model,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
        print(f"case {case['id']} ok ({elapsed:.0f} ms)", flush=True)
        expected = {_pair(item) for item in case["expected_ops"]}
        actual = {_pair(item.model_dump(mode="json")) for item in result.operations}
        tp, fp, fn = len(expected & actual), len(actual - expected), len(expected - actual)
        matched_targets += tp
        wrong_targets += fp
        missing_changes += fn
        expected_total += len(expected)
        clarification = any(item.missing_fields for item in result.operations)
        row = totals[case["language"]]
        row[0] += tp
        row[1] += fp
        row[2] += fn
        row[3] += int(case["requires_clarification"] and clarification)
        row[4] += int(not case["requires_clarification"] and clarification)
        row[5] += int(case["requires_clarification"] and not clarification)
        row[6] += elapsed
        if len(examples) < 10 or (expected != actual and len(examples) < 20):
            examples.append({"id": case["id"], "expected": sorted(expected), "actual": sorted(actual), "ms": round(elapsed, 1)})
    print(f"Live Ollama revision evaluation: {len(cases)} cases; model={model.model}")
    print(f"Invalid/schema outputs: {invalid_outputs}; raw records: {output_path}")
    target_denominator = matched_targets + wrong_targets
    operation_precision = matched_targets / target_denominator if target_denominator else 0
    operation_recall = matched_targets / expected_total if expected_total else 0
    operation_f1 = (
        2 * operation_precision * operation_recall / (operation_precision + operation_recall)
        if operation_precision + operation_recall
        else 0
    )
    clarification_tp = sum(row[3] for row in totals.values())
    clarification_fp = sum(row[4] for row in totals.values())
    clarification_fn = sum(row[5] for row in totals.values())
    clarification_precision = clarification_tp / (clarification_tp + clarification_fp) if clarification_tp + clarification_fp else 0
    clarification_recall = clarification_tp / (clarification_tp + clarification_fn) if clarification_tp + clarification_fn else 0
    print(
        "operation_precision="
        f"{operation_precision:.3f} operation_recall={operation_recall:.3f} operation_f1={operation_f1:.3f} "
        "target_correct_rate="
        f"{matched_targets / expected_total if expected_total else 0:.3f} "
        "wrong_target_rate="
        f"{wrong_targets / target_denominator if target_denominator else 0:.3f} "
        "missing_change_rate="
        f"{missing_changes / expected_total if expected_total else 0:.3f} "
        f"clarification_precision={clarification_precision:.3f} clarification_recall={clarification_recall:.3f} "
        f"median_ms={statistics.median(latencies) if latencies else 0:.1f} "
        f"p95_ms={statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 2 else (latencies[0] if latencies else 0):.1f}"
    )
    for language, (tp, fp, fn, clar_tp, clar_fp, clar_fn, latency) in sorted(totals.items()):
        precision = tp / (tp + fp) if tp + fp else 0
        recall = tp / (tp + fn) if tp + fn else 0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0
        clar_precision = clar_tp / (clar_tp + clar_fp) if clar_tp + clar_fp else 0
        clar_recall = clar_tp / (clar_tp + clar_fn) if clar_tp + clar_fn else 0
        language_count = sum(1 for item in cases if item["language"] == language)
        print(f"{language:18s} P={precision:.3f} R={recall:.3f} F1={f1:.3f} clarification P={clar_precision:.3f} R={clar_recall:.3f} avg_ms={latency / language_count if language_count else 0:.1f}")
    print("Examples:")
    for example in examples[:10]:
        print(json.dumps(example, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
