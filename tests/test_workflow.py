from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from qshift.agent.extraction import ChangeExtraction, ChangeOp
from qshift.agent.local_model import LocalModelUnavailable
from qshift.models import Firm, Project, QuoteVersion, RateEntry, User
from qshift.services import (
    approve_draft,
    cancel_draft,
    issue_approval_token,
    pin_project,
    project_memory,
    reject_draft,
    resolve_catalogue,
    seed_demo,
    submit_change,
    versions,
)


def users(session):
    return (
        session.scalar(select(User).where(User.id == "user-designer")),
        session.scalar(select(User).where(User.id == "user-approver")),
    )


def test_full_workflow_approval_pdf_and_immutable_version(session, tmp_path, monkeypatch):
    monkeypatch.setenv("QSHIFT_OUTPUT_DIR", str(tmp_path))
    seed_demo(session)
    designer, approver = users(session)
    assert designer and approver
    pin_project(session, designer, "project-sharma")
    draft = submit_change(
        session,
        designer,
        "project-sharma",
        "Kitchen lo granite badulu quartz pettandi, bedroom false ceiling remove cheyyandi.",
    )
    assert draft["status"] == "NEEDS_CLARIFICATION"
    draft = resolve_catalogue(session, designer, draft["id"], "COUNTER-QUARTZ-CALACATTA")
    assert draft["status"] == "DRAFT_READY"
    assert draft["net_change"] == "₹15,000"
    assert {d["kind"] for d in draft["line_diffs"]} >= {"changed", "removed"}
    token = issue_approval_token(session, approver, draft["id"])
    result = approve_draft(session, approver, token)
    assert result["version"] == 2
    assert Path(result["pdf_path"]).read_bytes().startswith(b"%PDF")
    history = versions(session, designer, "project-sharma")
    assert [v["version"] for v in history] == [1, 2]
    assert (
        session.scalar(select(QuoteVersion).where(QuoteVersion.number == 1)).total_paise
        == 22_820_000
    )
    assert project_memory(session, designer, "project-sharma")["included"] == 2
    with pytest.raises(PermissionError):
        approve_draft(session, approver, token)


def test_designer_cannot_issue_approval(session):
    seed_demo(session)
    designer, _ = users(session)
    assert designer
    draft = submit_change(
        session, designer, "project-sharma", "Please remove the bedroom false ceiling"
    )
    # No ambiguity means draft is ready, but the role still may not approve.
    with pytest.raises(PermissionError):
        issue_approval_token(session, designer, draft["id"])


def test_designer_can_reject_and_history_marks_scope_rejected(session):
    seed_demo(session)
    designer, _ = users(session)
    assert designer
    draft = submit_change(
        session, designer, "project-sharma", "Please remove the bedroom false ceiling"
    )
    result = reject_draft(session, designer, draft["id"])
    assert result["status"] == "REJECTED"
    memory = project_memory(session, designer, "project-sharma")
    assert memory["rejected"] == 1
    with pytest.raises(ValueError, match="open draft"):
        reject_draft(session, designer, draft["id"])


def test_open_draft_can_be_cancelled_without_changing_approved_version(session):
    seed_demo(session)
    designer, _ = users(session)
    assert designer
    draft = submit_change(
        session, designer, "project-sharma", "Please remove the bedroom false ceiling"
    )
    result = cancel_draft(session, designer, "project-sharma", draft["id"])
    assert result["status"] == "CANCELLED"
    quote = session.scalar(select(QuoteVersion).where(QuoteVersion.number == 1))
    assert quote and quote.total_paise == 22_820_000


def test_rate_snapshot_is_rechecked_at_approval(session):
    seed_demo(session)
    designer, approver = users(session)
    assert designer and approver
    draft = submit_change(
        session, designer, "project-sharma", "Please remove the bedroom false ceiling"
    )
    token = issue_approval_token(session, approver, draft["id"])
    rate = session.scalar(select(RateEntry).where(RateEntry.sku == "DEMO-013"))
    assert rate
    rate.rate_paise += 1
    session.commit()
    with pytest.raises(ValueError, match="rate or unit changed"):
        approve_draft(session, approver, token)


def test_cross_tenant_project_access_is_denied(session):
    seed_demo(session)
    user, _ = users(session)
    assert user
    session.add(Firm(id="firm-other", name="Other fictional firm"))
    session.flush()
    session.add(
        Project(
            id="project-other", firm_id="firm-other", name="Other project", client_label="fictional"
        )
    )
    session.commit()
    with pytest.raises(LookupError):
        pin_project(session, user, "project-other")
    with pytest.raises(LookupError):
        versions(session, user, "project-other")


def test_provider_proposal_modifies_quantity_without_pricing_authority(session, monkeypatch):
    seed_demo(session)
    designer, _ = users(session)
    assert designer

    class Provider:
        def extract(self, _text, _context):
            return ChangeExtraction(
                intent="MODIFY",
                operations=[
                    ChangeOp(
                        op="MODIFY",
                        room="Kitchen",
                        target_text="countertop",
                        quantity="50",
                        unit="sqft",
                        source_span="make the countertop 50 sqft",
                        confidence=0.8,
                        status="PROPOSED",
                    )
                ],
            )

    monkeypatch.setattr("qshift.services.get_change_extractor", lambda: Provider())
    draft = submit_change(session, designer, "project-sharma", "make the countertop 50 sqft")
    assert draft["status"] == "DRAFT_READY"
    kitchen = next(line for line in draft["lines"] if line["room"] == "Kitchen")
    assert kitchen["quantity"] == "50.000"
    assert kitchen["rate_paise"] == 65000


def test_provider_hallucinated_target_is_held_for_source_review(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_demo(session)
    designer = session.scalar(select(User).where(User.id == "user-designer"))
    assert designer

    class Provider:
        def extract(self, _text: str, _context: dict[str, object]) -> ChangeExtraction:
            return ChangeExtraction(
                intent="REMOVE",
                operations=[
                    ChangeOp(
                        op="REMOVE",
                        target_text="guest-ceiling",
                        confidence=0.99,
                        status="PROPOSED",
                    )
                ],
            )

    monkeypatch.setattr("qshift.services.get_change_extractor", lambda: Provider())
    draft = submit_change(session, designer, "project-sharma", "remove the kitchen countertop")
    assert draft["status"] == "NEEDS_CLARIFICATION"
    assert draft["ops"][0]["missing_fields"] == ["source_evidence"]


def test_open_draft_correction_changes_only_target_line(session, monkeypatch):
    seed_demo(session)
    designer, _ = users(session)
    assert designer

    class Provider:
        def __init__(self):
            self.calls = 0

        def extract(self, _text, _context):
            self.calls += 1
            if self.calls == 1:
                return ChangeExtraction(
                    intent="MODIFY",
                    operations=[
                        ChangeOp(
                            op="MODIFY",
                            room="Kitchen",
                            target_text="countertop",
                            quantity="50",
                            unit="sqft",
                            source_span="make the countertop 50 sqft",
                            confidence=0.8,
                            status="PROPOSED",
                        )
                    ],
                )
            return ChangeExtraction(
                intent="CORRECT_PREVIOUS_CHANGE",
                operations=[
                    ChangeOp(
                        op="CORRECT_PREVIOUS_CHANGE",
                        room="Kitchen",
                        target_text="countertop",
                        quantity="45",
                        unit="sqft",
                        target_line_id="line-kitchen-counter",
                        source_span="correction, make it 45 sqft",
                        confidence=0.8,
                        status="PROPOSED",
                    )
                ],
            )

    provider = Provider()
    monkeypatch.setattr("qshift.services.get_change_extractor", lambda: provider)
    first = submit_change(session, designer, "project-sharma", "make the countertop 50 sqft")
    from qshift.services import amend_open_draft

    corrected = amend_open_draft(session, designer, first["id"], "correction, make it 45 sqft")
    assert corrected and corrected["status"] == "DRAFT_READY"
    kitchen = next(line for line in corrected["lines"] if line["room"] == "Kitchen")
    ceiling = next(line for line in corrected["lines"] if line["room"] == "Bedroom")
    assert kitchen["quantity"] == "45.000"
    assert ceiling["quantity"] == "120.000"


def test_model_failure_creates_manual_review_without_mutating_quote(session, monkeypatch):
    seed_demo(session)
    designer, _ = users(session)
    assert designer

    class BrokenProvider:
        def extract(self, _text, _context):
            raise LocalModelUnavailable("synthetic model outage")

    monkeypatch.setattr("qshift.services.get_change_extractor", lambda: BrokenProvider())
    draft = submit_change(session, designer, "project-sharma", "replace the countertop")
    assert draft["status"] == "NEEDS_CLARIFICATION"
    assert "synthetic model outage" in draft["manual_review"]
    assert draft["original_total_paise"] == draft["revised_total_paise"]
