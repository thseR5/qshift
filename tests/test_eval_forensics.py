from typing import Any

from evals.forensics import (
    aggregate,
    align_operations,
    normalize_room,
    score_case,
    target_match,
)


def op(kind: str, room: str | None, target: str, **extra: object) -> dict[str, Any]:
    return {"op": kind, "room": room, "target_text": target, **extra}


def test_alias_and_containment_matching_are_explicit() -> None:
    assert normalize_room("Guest Room") == "guest bedroom"
    assert target_match("wardrobe", "guest bedroom wardrobe")
    assert not target_match("wardrobe", "kitchen countertop")


def test_alignment_does_not_duplicate_a_prediction() -> None:
    expected = [op("REMOVE", "Bedroom", "ceiling"), op("REPLACE", "Kitchen", "granite")]
    predicted = [op("REMOVE", None, "false ceiling")]
    assert len(align_operations(expected, predicted)) == 1
    result = score_case(expected, predicted, expected_clarification=True)
    assert result.operation_type_tp == 1
    assert result.type_fn == 1
    assert result.predicted_count == 1


def test_component_metrics_separate_type_target_room_and_clarification() -> None:
    result = score_case(
        [op("MODIFY", "Guest Bedroom", "wardrobe")],
        [op("ADD", None, "guest bedroom wardrobe", missing_fields=["quantity"])],
        expected_intent="CHANGE",
        predicted_intent="ADD",
        expected_clarification=False,
    )
    assert result.operation_type_tp == 0
    assert result.target_tp == 0
    assert result.room_tp == 0
    assert result.intent_correct
    assert result.predicted_clarification


def test_aggregate_reports_precision_recall_without_hidden_aliases() -> None:
    rows = [
        score_case([op("REMOVE", "Bedroom", "ceiling")], [op("REMOVE", "Bedroom", "ceiling")]),
        score_case([op("ADD", "Balcony", "screen")], []),
    ]
    result = aggregate(rows)
    assert result["cases"] == 2
    assert result["expected_operations"] == 2
    assert result["predicted_operations"] == 1
    assert result["operation_type_precision"] == 1.0
    assert result["operation_type_recall"] == 0.5
