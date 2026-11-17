from pathlib import Path

import pytest
from sqlalchemy import select

from qshift.models import Firm, Project, QuoteVersion, RateEntry, User
from qshift.services import (
    approve_draft,
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
