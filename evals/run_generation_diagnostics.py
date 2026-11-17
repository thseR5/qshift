"""Run bounded, non-tuning generation comparisons on the installed local model."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from qshift.agent.extraction import OllamaChangeLLM
from qshift.agent.local_model import LocalModelUnavailable

CASES = [
    ("en-01", "Increase the guest bedroom wardrobe from 6 by 7 feet to 8 by 7 feet."),
    ("en-02", "Replace the kitchen granite countertop with white quartz and remove the false ceiling in the guest bedroom."),
    ("telugu-01", "Kitchen lo granite badulu quartz pettandi, guest bedroom false ceiling teeseyandi."),
    ("correction-01", "Correction: I meant the living room ceiling, not the guest bedroom ceiling."),
    ("ambiguous-01", "Change the countertop to quartz."),
    ("unrelated-01", "What is the weather in Hyderabad today?"),
]

FULL_CONTEXT = {
    "quotation_lines": [
        {"line_id": "kitchen-counter", "room": "Kitchen", "category": "Countertop", "description": "Granite countertop", "sku": "COUNTER-GRANITE", "quantity": "40", "unit": "sqft"},
        {"line_id": "guest-ceiling", "room": "Guest Bedroom", "category": "Ceiling", "description": "Gypsum false ceiling", "sku": "FALSE-CEILING-GYPSUM", "quantity": "120", "unit": "sqft"},
        {"line_id": "wardrobe", "room": "Guest Bedroom", "category": "Wardrobe", "description": "White laminate wardrobe", "sku": "WARDROBE-WHITE-LAMINATE", "quantity": "42", "unit": "sqft"},
    ],
    "verified_catalogue": [],
}


def run_variant(name: str, num_predict: int, context: dict[str, Any]) -> list[dict[str, Any]]:
    os.environ["QSHIFT_CHANGE_NUM_PREDICT"] = str(num_predict)
    model = OllamaChangeLLM()
    rows = []
    for case_id, text in CASES:
        started = time.perf_counter()
        try:
            result = model.extract(text, context)
            error = None
            normalized = result.model_dump(mode="json")
        except LocalModelUnavailable as exc:
            error = str(exc)
            normalized = None
        rows.append(
            {
                "variant": name,
                "case_id": case_id,
                "num_predict": num_predict,
                "context_lines": len(context.get("quotation_lines", [])),
                "raw_output": model.last_raw,
                "raw_output_text": model.last_raw_text,
                "normalized_output": normalized,
                "response_meta": model.last_meta,
                "error": error,
                "latency_ms": round((time.perf_counter() - started) * 1000, 1),
            }
        )
    return rows


def main() -> int:
    rows = []
    rows.extend(run_variant("full_context_350", 350, FULL_CONTEXT))
    rows.extend(run_variant("full_context_1200", 1200, FULL_CONTEXT))
    rows.extend(run_variant("no_quotation_context_350", 350, {"quotation_lines": [], "verified_catalogue": []}))
    output = Path(os.getenv("QSHIFT_DIAGNOSTIC_OUTPUT", "work/generation_diagnostics_v64.json"))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
    print(f"Saved {len(rows)} diagnostic records to {output}")
    for row in rows:
        operations = (row.get("normalized_output") or {}).get("operations", [])
        print(
            row["variant"], row["case_id"],
            f"ops={len(operations)} latency_ms={row['latency_ms']}",
            f"done_reason={(row.get('response_meta') or {}).get('done_reason')}",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
