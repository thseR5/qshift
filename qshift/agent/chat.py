"""Text conversation flow shared by the simulator and future channel adapters."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from qshift.agent.local_model import LocalModelUnavailable
from qshift.engine.pricing import format_inr
from qshift.models import Draft, QuoteVersion, User
from qshift.services import (
    amend_open_draft,
    approve_draft,
    cancel_draft,
    draft_view,
    issue_approval_token,
    pin_project,
    project_memory,
    projects_for_user,
    reject_draft,
    require_project,
    resolve_catalogue,
    resolve_catalogue_text,
    submit_change,
    versions,
)

HELP = (
    "Send projects to see your projects, then use <project ID> to select one. "
    "Describe a quotation change in your own words. "
    "Send status for the open draft, choose <SKU> to answer a catalogue question, "
    "review for the before/after approval summary, history for approved quotations, "
    "changes for recent requests, or cancel to discard an open draft. "
    "A plain yes never approves a quotation."
)
OPEN_DRAFT_STATUSES = ("NEEDS_CLARIFICATION", "DRAFT_READY")


def draft_reply(draft: dict[str, Any]) -> dict[str, Any]:
    lines = []
    if draft["status"] == "DRAFT_READY":
        lines.append(
            f"Draft ready for review. Proposed total {draft['revised_total']} "
            f"(change {draft['net_change']}). Send review to see the before/after summary."
        )
        lines.append("Only an enrolled OWNER or APPROVER can authorize it with the one-time token.")
    else:
        lines.append("I need more information before this revision can be priced for approval.")
        for operation in draft["ops"]:
            if operation["status"] != "NEEDS_INFO":
                continue
            options = operation.get("options", [])
            if options:
                lines.append("Reply with choose <SKU> using one of these verified options:")
                for option in options:
                    amount = format_inr(option["rate_paise"])
                    lines.append(f"{option['sku']} — {option['name']} · {amount}/{option['unit']}")
            else:
                target = operation["target_text"]
                lines.append(f"Ask the designer to clarify the quoted line or scope for {target}.")
    result: dict[str, Any] = {"reply": "\n".join(lines), "draft": draft}
    if draft["status"] == "DRAFT_READY":
        result["interactive"] = {
            "type": "button",
            "buttons": ["review", "cancel"],
            "fallback": "Send review to inspect the exact before/after quotation.",
        }
    return result


def respond_to_message(
    session: Session,
    user: User,
    message: str,
    project_id: str | None = None,
    draft_id: str | None = None,
    *,
    commit: bool = True,
) -> dict[str, Any]:
    """Handle a message from a user already authenticated by the calling channel."""
    message = message.strip()
    tokens = message.split(maxsplit=1)
    if not tokens:
        return {"reply": HELP}
    command = tokens[0].casefold()
    argument = tokens[1] if len(tokens) == 2 else ""

    if not argument and command in {"help", "hi", "hello"}:
        return {"reply": HELP}
    if command == "document":
        suffix = argument.casefold().rsplit(".", 1)[-1] if "." in argument else ""
        if suffix not in {"csv", "xlsx"}:
            return {"reply": "Send a CSV or XLSX document. Other file types are not accepted."}
        return {
            "reply": (
                f"Received {argument[:160]} in the SIMULATED WhatsApp adapter. "
                "The file is untrusted; confirm the project and column mapping before any "
                "rate or quotation import. No Meta media bytes are downloaded in this pilot."
            ),
            "document_received": argument[:160],
            "interactive": {
                "type": "list",
                "title": "Import target",
                "items": ["rate card", "quotation"],
                "fallback": "Reply with rate card or quotation after reviewing the mapping.",
            },
        }
    if not argument and command == "projects":
        projects = projects_for_user(session, user)
        lines = [f"{project['name']} · {project['id']}" for project in projects]
        reply = "\n".join(["Reply with use <project ID>.", *lines])
        return {
            "reply": reply if projects else "No projects are available in your firm.",
            "interactive": {
                "type": "list",
                "title": "Choose a project",
                "items": [{"id": project["id"], "title": project["name"]} for project in projects],
                "fallback": "Reply with use <project ID>.",
            },
        }
    if command == "use":
        if not argument:
            return {"reply": "Reply with use <project ID>. Send projects to find the ID."}
        project = pin_project(session, user, argument, commit=commit)
        return {
            "reply": f"Selected {project['name']}. Describe the quotation change.",
            "project_id": project["id"],
        }
    if command in {"approve", "reject"}:
        if user.role not in {"OWNER", "APPROVER"}:
            return {
                "reply": (
                    "Only an enrolled owner or approver can authorize a quotation revision. "
                    "The authenticated Qshift review screen is not available to this identity."
                )
            }
        if not argument:
            return {
                "reply": (
                    "Send review first. Approval requires its one-time token; a plain 'yes' "
                    "is not accepted. The authenticated Qshift review screen is replaced by "
                    "this WhatsApp review command."
                )
            }
        if draft_id is None:
            return {"reply": "There is no open revision to authorize."}
        if command == "reject":
            result = reject_draft(session, user, draft_id, commit=commit)
            return {"reply": "Revision rejected. The approved quotation is unchanged.", "rejected_draft_id": result["draft_id"]}
        try:
            result = approve_draft(session, user, argument, write_pdf=False, commit=commit)
        except (LookupError, PermissionError, ValueError) as exc:
            return {"reply": f"Approval failed safely: {exc}"}
        return {
            "reply": (
                f"Approved quotation revision v{result['version']} for {result['total']}. "
                "The exact PDF is queued for delivery in this simulated WhatsApp channel."
            ),
            "approved_version_id": result["version_id"],
            "pdf_path": result["pdf_path"],
        }
    if project_id is None:
        return {"reply": "Select a project first. Send projects to find its ID."}

    project = require_project(session, user, project_id)
    if not argument and command in {"cancel", "discard", "stop"}:
        try:
            cancel_draft(session, user, project.id, draft_id, commit=commit)
        except LookupError:
            return {"reply": f"There is no open draft to cancel for {project.name}."}
        return {"reply": f"Cancelled the open draft for {project.name}. The approved quote is unchanged."}
    if not argument and command == "history":
        revisions = versions(session, user, project.id)
        lines = [f"v{row['version']} · {row['total']}" for row in revisions[-5:]]
        return {
            "reply": "\n".join([f"{project.name} quotation history", *lines])
            if lines
            else "No quotation yet."
        }
    if not argument and command == "changes":
        memory = project_memory(session, user, project.id)
        return {
            "reply": (
                f"{project.name}, last 7 days. {memory['requested']} requested, "
                f"{memory['included']} included, {memory['pending']} pending, "
                f"{memory['rejected']} rejected, {memory['cancelled']} cancelled."
            )
        }
    if command == "choose":
        if not argument or draft_id is None:
            return {"reply": "Send status to open the draft, then reply with choose <SKU>."}
        draft = session.scalar(
            select(Draft).where(
                Draft.id == draft_id, Draft.firm_id == user.firm_id, Draft.project_id == project.id
            )
        )
        if draft is None:
            raise LookupError("Draft not found for the selected project")
        return draft_reply(resolve_catalogue(session, user, draft.id, argument, commit=commit))
    if not argument and command == "status":
        draft = session.scalar(
            select(Draft).where(
                Draft.project_id == project.id,
                Draft.firm_id == user.firm_id,
                Draft.status.in_(OPEN_DRAFT_STATUSES),
            )
        )
        if draft is None:
            return {"reply": f"There is no open draft for {project.name}."}
        if draft.base_version == 0:
            return {"reply": "Review the draft in the First Quote simulator."}
        base = session.scalar(
            select(QuoteVersion).where(
                QuoteVersion.firm_id == user.firm_id,
                QuoteVersion.quote_id == draft.quote_id,
                QuoteVersion.number == draft.base_version,
            )
        )
        if base is None:
            raise LookupError("Base quotation version not found")
        return draft_reply(draft_view(draft, base.total_paise, base.lines))
    if not argument and command == "review":
        if user.role not in {"OWNER", "APPROVER"}:
            return {"reply": "This draft is waiting for an enrolled owner or approver."}
        draft = session.scalar(
            select(Draft).where(
                Draft.project_id == project.id,
                Draft.firm_id == user.firm_id,
                Draft.status == "DRAFT_READY",
            )
        )
        if draft is None:
            return {"reply": f"There is no ready revision for {project.name}."}
        if draft.base_version == 0:
            return {"reply": "The first quotation must be reviewed through the fictional intake flow."}
        base = session.scalar(
            select(QuoteVersion).where(
                QuoteVersion.firm_id == user.firm_id,
                QuoteVersion.quote_id == draft.quote_id,
                QuoteVersion.number == draft.base_version,
            )
        )
        if base is None:
            raise LookupError("Base quotation version not found")
        view = draft_view(draft, base.total_paise, base.lines)
        token = issue_approval_token(
            session, user, draft.id, draft.content_sha256, commit=commit
        )
        changes = [
            f"{item['kind']}: {item['room']} / {item['description']} ({item['delta']})"
            for item in view["line_diffs"]
            if item["kind"] != "unchanged"
        ]
        return {
            "reply": "\n".join(
                [
                    f"{project.name} revision review",
                    f"Before: {view['original_total']} · After: {view['revised_total']} · Change: {view['net_change']}",
                    *changes,
                    f"Approve exact revision with: approve {token}",
                    "Reject with: reject <anything>",
                ]
            ),
            "draft_id": draft.id,
            "review_token_issued": True,
            "interactive": {
                "type": "button",
                "buttons": ["approve <one-time token>", "reject"],
                "fallback": f"Approve exact revision with: approve {token}",
            },
        }
    open_query = select(Draft).where(
        Draft.firm_id == user.firm_id,
        Draft.project_id == project.id,
        Draft.status.in_(OPEN_DRAFT_STATUSES),
    )
    if draft_id is not None:
        open_query = open_query.where(Draft.id == draft_id)
    open_draft = session.scalar(open_query)
    if open_draft is not None:
        resolved = resolve_catalogue_text(session, user, open_draft.id, message, commit=commit)
        if resolved is not None:
            base = session.scalar(
                select(QuoteVersion).where(
                    QuoteVersion.firm_id == user.firm_id,
                    QuoteVersion.quote_id == open_draft.quote_id,
                    QuoteVersion.number == open_draft.base_version,
                )
            )
            return draft_reply(draft_view(open_draft, base.total_paise if base else 0, base.lines if base else []))
        try:
            amended = amend_open_draft(session, user, open_draft.id, message, commit=commit)
        except LocalModelUnavailable:
            amended = None
        if amended is not None:
            return draft_reply(amended)
        return {
            "reply": "The open draft still needs a specific verified catalogue choice. Reply with the SKU or exact catalogue name shown above, or use cancel.",
            "draft_id": open_draft.id,
        }
    result = submit_change(session, user, project.id, message, commit=commit)
    if result.get("intent") == "out_of_scope":
        return {"reply": HELP}
    return draft_reply(result)
