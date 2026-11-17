"""Offline structured mock extraction; never computes or chooses prices."""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field

INTENTS = {
    "pin_project",
    "list_projects",
    "upload_rate_card",
    "upload_quotation",
    "submit_change_request",
    "answer_clarification",
    "review_draft",
    "approve_or_reject",
    "get_project_changes",
    "get_version_history",
    "help",
}


class ChangeOp(BaseModel):
    """Validated proposal envelope; it has no approval or pricing authority."""

    op: Literal["ADD", "REMOVE", "REPLACE", "MODIFY", "CLARIFY", "CANCEL"]
    room: str | None = None
    target_text: str
    source_span: str | None = None
    sku: str | None = None
    replacement_text: str | None = None
    quantity: str | None = None
    unit: str | None = None
    confidence: float = Field(ge=0, le=1)
    status: Literal["PROPOSED", "NEEDS_INFO", "VERIFIED", "REJECTED", "CANCELLED", "APPLIED"]
    missing_fields: list[str] = Field(default_factory=list)
    resolved_line_id: str | None = None
    options: list[dict[str, Any]] = Field(default_factory=list)
    removed_line: dict[str, Any] | None = None
    selected_name: str | None = None


class MockLLM:
    """Recorded-pattern implementation for reproducible offline runs."""

    @staticmethod
    def _canonical(text: str) -> str:
        value = text.casefold()
        for source, target in (
            ("grannit", "granite"),
            ("gra night", "granite"),
            ("quarts", "quartz"),
            ("kitchin", "kitchen"),
            ("bed room", "bedroom"),
            ("fals seeling", "false ceiling"),
            ("false ceil", "false ceiling"),
            ("tiseseyandi", "teeseyandi"),
        ):
            value = value.replace(source, target)
        return value

    def classify(self, text: str) -> str:
        low = self._canonical(text)
        if any(w in low for w in ("what changes", "changes this week", "change history")):
            return "get_project_changes"
        if any(w in low for w in ("versions", "version history", "history of quote")):
            return "get_version_history"
        if any(w in low for w in ("approve", "reject")):
            return "approve_or_reject"
        if "project" in low and any(w in low for w in ("pin", "select", "choose")):
            return "pin_project"
        if any(w in low for w in ("help", "what can you do")):
            return "help"
        if any(w in low for w in ("quartz", "granite", "false ceiling", "ceiling", "countertop")):
            return "submit_change_request"
        return "out_of_scope"

    def extract(self, text: str) -> list[dict[str, Any]]:
        low = self._canonical(text)
        ops: list[dict[str, Any]] = []
        has_ceiling = "ceiling" in low or "ceil" in low
        remove_marker = any(
            word in low
            for word in ("remove", "hatao", "hataiye", "हटाइए", "हटाएं", "తీసేయండి", "teeseyandi")
        )
        if has_ceiling and remove_marker:
            ops.append(
                {
                    "op": "REMOVE",
                    "room": "Bedroom",
                    "target_text": "false ceiling",
                    "source_span": text,
                    "sku": None,
                    "quantity": None,
                    "unit": None,
                    "confidence": "0.91",
                    "status": "VERIFIED",
                    "missing_fields": [],
                }
            )
        if "quartz" in low and any(
            w in low
            for w in ("granite", "countertop", "kitchen", "ग्रेनाइट", "क्वार्ट्ज", "గ్రానైట్", "క్వార్ట్జ్")
        ):
            ops.append(
                {
                    "op": "REPLACE",
                    "room": "Kitchen",
                    "target_text": "countertop",
                    "source_span": text,
                    "sku": "COUNTER-GRANITE",
                    "replacement_text": "quartz",
                    "quantity": None,
                    "unit": None,
                    "confidence": "0.88",
                    "status": "NEEDS_INFO",
                    "missing_fields": ["catalogue_selection"],
                }
            )
        if not ops:
            ops.append(
                {
                    "op": "CLARIFY",
                    "room": None,
                    "target_text": text[:160],
                    "source_span": text,
                    "sku": None,
                    "quantity": None,
                    "unit": None,
                    "confidence": "0.40",
                    "status": "NEEDS_INFO",
                    "missing_fields": ["target", "scope"],
                }
            )
        return [ChangeOp.model_validate(op).model_dump(mode="json") for op in ops]


class MockTranscriber:
    def transcribe(self, fixture_name: str) -> dict[str, str]:
        fixtures = {
            "telugu_quartz_change": "Kitchen lo granite badulu quartz pettandi, bedroom false ceiling remove cheyyandi.",
            "hindi_upgrade": "Kitchen ka granite hata kar quartz lagaiye",
            "english_remove": "Please remove the bedroom false ceiling",
        }
        if fixture_name not in fixtures:
            raise ValueError("Unknown mock transcript fixture")
        return {
            "text": fixtures[fixture_name],
            "confidence": "0.96",
            "requires_confirmation": "true",
        }


def normalize_units(text: str) -> str:
    replacements = [
        (r"square\s*feet|sq\.?\s*ft\.?|sqft", "sqft"),
        (r"running\s*feet|rft", "rft"),
        (r"nos?\.?", "nos"),
    ]
    normalized = text
    for pattern, unit in replacements:
        normalized = re.sub(pattern, unit, normalized, flags=re.IGNORECASE)
    return normalized
