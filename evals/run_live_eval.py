"""Run the versioned revision set against the configured local Ollama model."""

from __future__ import annotations

import json
import time
from collections import defaultdict
from pathlib import Path

from qshift.agent.extraction import LocalModelUnavailable, OllamaChangeLLM


def _pair(operation: dict) -> tuple[str, str | None, str]:
    return operation["op"], operation.get("room"), operation.get("target_text", "").casefold()


def main() -> int:
    cases = json.loads(Path("qshift/fixtures/revision_eval_v1.json").read_text())
    model = OllamaChangeLLM()
    totals = defaultdict(lambda: [0, 0, 0, 0, 0, 0, 0.0])
    examples: list[dict] = []
    context = {
        "quotation_lines": [
            {"line_id": "kitchen-counter", "room": "Kitchen", "category": "Countertop", "description": "Granite countertop", "sku": "COUNTER-GRANITE", "quantity": "40", "unit": "sqft"},
            {"line_id": "guest-ceiling", "room": "Guest Bedroom", "category": "Ceiling", "description": "Gypsum false ceiling", "sku": "FALSE-CEILING-GYPSUM", "quantity": "120", "unit": "sqft"},
            {"line_id": "wardrobe", "room": "Guest Bedroom", "category": "Wardrobe", "description": "White laminate wardrobe", "sku": "WARDROBE-WHITE-LAMINATE", "quantity": "42", "unit": "sqft"},
        ],
        "verified_catalogue": [],
    }
    for case in cases:
        started = time.perf_counter()
        try:
            result = model.extract(case["text"], context)
        except LocalModelUnavailable as exc:
            print(f"LIVE EVAL BLOCKED: {exc}")
            print("No model was downloaded and no paid provider was contacted.")
            return 0
        elapsed = (time.perf_counter() - started) * 1000
        expected = {_pair(item) for item in case["expected_ops"]}
        actual = {_pair(item.model_dump(mode="json")) for item in result.operations}
        tp, fp, fn = len(expected & actual), len(actual - expected), len(expected - actual)
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
    for language, (tp, fp, fn, clar_tp, clar_fp, clar_fn, latency) in sorted(totals.items()):
        precision = tp / (tp + fp) if tp + fp else 0
        recall = tp / (tp + fn) if tp + fn else 0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0
        clar_precision = clar_tp / (clar_tp + clar_fp) if clar_tp + clar_fp else 0
        clar_recall = clar_tp / (clar_tp + clar_fn) if clar_tp + clar_fn else 0
        print(f"{language:18s} P={precision:.3f} R={recall:.3f} F1={f1:.3f} clarification P={clar_precision:.3f} R={clar_recall:.3f} avg_ms={latency / len(cases):.1f}")
    print("Examples:")
    for example in examples[:10]:
        print(json.dumps(example, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
