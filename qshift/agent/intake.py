"""Offline extraction for the fictional single-wardrobe intake."""

import re
from decimal import Decimal

ROOM = re.compile(
    r"\b(?:second bedroom|master bedroom|guest bedroom|primary bedroom|bedroom\s+[1-9]|bedroom)\b"
)
FEET = r"(?:ft\.?|feet|foot|')"
NUMBER = r"([0-9]{1,2}(?:\.[0-9]{1,2})?)"
DIMENSIONS = {
    "width_ft": re.compile(
        rf"\b(?:{NUMBER}\s*{FEET}\s+wide\b|width\s*(?:is|:|=)?\s*{NUMBER}\s*{FEET})"
    ),
    "height_ft": re.compile(
        rf"\b(?:{NUMBER}\s*{FEET}\s+(?:high|tall)\b|height\s*(?:is|:|=)?\s*{NUMBER}\s*{FEET})"
    ),
}
BARE_MEASUREMENT = re.compile(rf"^{NUMBER}\s*{FEET}[.! ]*$")
EXTRA_SCOPE = re.compile(
    r"\b(?:kitchen|ceiling|countertop|flooring|lighting|painting|tv unit|another wardrobe|"
    r"two wardrobes|2 wardrobes|wardrobes|and\s+(?:a|another)\b)\b"
)
UNCERTAIN = re.compile(r"\b(?:not|no|maybe|might|or|instead of|could be)\b|\?")


def extract_brief(messages: list[dict]) -> tuple[dict, str | None]:
    """Collect supported facts with message IDs and ask for the next missing fact."""
    brief: dict[str, dict[str, str]] = {}
    pending: str | None = None
    for message in messages:
        if message["role"] == "assistant":
            pending = message.get("field")
            continue
        text = message["text"].casefold().strip()
        if EXTRA_SCOPE.search(text):
            return brief, "unsupported_scope"
        if UNCERTAIN.search(text):
            if any(pattern.search(text) for pattern in DIMENSIONS.values()):
                for field, pattern in DIMENSIONS.items():
                    if pattern.search(text):
                        brief.pop(field, None)
            continue

        facts = {}
        if match := ROOM.search(text):
            facts["room"] = match.group().title()
        if re.search(r"\bwardrobe\b", text):
            facts["item"] = "Wardrobe"
        if re.search(r"\bwhite laminate\b", text):
            facts["finish"] = "White laminate"
        elif re.search(r"\b(?:laminate|veneer|acrylic|painted)\b", text):
            brief.pop("finish", None)

        for field, pattern in DIMENSIONS.items():
            matches = list(pattern.finditer(text))
            if matches:
                values = {Decimal(match.group(1) or match.group(2)) for match in matches}
                if len(values) == 1 and 0 < (value := values.pop()) <= 20:
                    facts[field] = str(value)
                else:
                    brief.pop(field, None)
        if pending in DIMENSIONS and not any(field in facts for field in DIMENSIONS):
            if match := BARE_MEASUREMENT.fullmatch(text):
                value = Decimal(match.group(1))
                if 0 < value <= 20:
                    facts[pending] = str(value)

        for field, value in facts.items():
            brief[field] = {"value": value, "source": message["id"]}

    for field in ("item", "room", "finish", "width_ft", "height_ft"):
        if field not in brief:
            return brief, field
    return brief, None
