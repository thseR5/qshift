"""Evaluate the offline fixture parser on synthetic cases; not real-world accuracy."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from qshift.agent.extraction import MockLLM


def main() -> None:
    cases = json.loads(Path("qshift/fixtures/extraction_cases.json").read_text())
    llm = MockLLM()
    totals: dict[str, list[int]] = defaultdict(lambda: [0] * 8)
    for case in cases:
        actual = llm.extract(case["text"])
        language = case["language"]
        expected_ops = {item["op"] for item in case["expected_ops"]}
        actual_ops = {item["op"] for item in actual if item["op"] != "CLARIFY"}
        true_positive = len(expected_ops & actual_ops)
        totals[language][0] += true_positive
        totals[language][1] += len(actual_ops - expected_ops)
        totals[language][2] += len(expected_ops - actual_ops)
        expected_pairs = {
            (item["op"], item["room"], item["target_text"]) for item in case["expected_ops"]
        }
        actual_pairs = {
            (item["op"], item.get("room"), item.get("target_text"))
            for item in actual
            if item["op"] != "CLARIFY"
        }
        totals[language][6] += len(expected_pairs & actual_pairs)
        totals[language][7] += len(expected_pairs)
        expected_clarification = bool(case["requires_clarification"])
        actual_clarification = any(item["status"] == "NEEDS_INFO" for item in actual)
        totals[language][3] += int(expected_clarification and actual_clarification)
        totals[language][4] += int(not expected_clarification and actual_clarification)
        totals[language][5] += int(expected_clarification and not actual_clarification)
    print(f"Offline MockLLM synthetic fixture evaluation: {len(cases)} cases")
    print("These scores measure fixture behavior only, not real language understanding.")
    for lang, (tp, fp, fn, clar_tp, clar_fp, clar_fn, line_correct, line_total) in sorted(
        totals.items()
    ):
        precision = tp / (tp + fp) if tp + fp else 0
        recall = tp / (tp + fn) if tp + fn else 0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0
        line_accuracy = line_correct / line_total if line_total else 0
        clarification_precision = clar_tp / (clar_tp + clar_fp) if clar_tp + clar_fp else 0
        clarification_recall = clar_tp / (clar_tp + clar_fn) if clar_tp + clar_fn else 0
        print(
            f"{lang:18s} op P={precision:.3f} R={recall:.3f} F1={f1:.3f}; "
            f"line/target exact={line_accuracy:.3f}; "
            f"clarification P={clarification_precision:.3f} R={clarification_recall:.3f}"
        )


if __name__ == "__main__":
    main()
