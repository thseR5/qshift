"""Tenant-scoped simulated intake, first quotation, and client-visible PDF."""

import os
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from qshift.agent.intake import extract_brief
from qshift.agent.itemized import CEILING, WARDROBE, propose_items
from qshift.agent.local_model import MODEL, propose_scope
from qshift.engine.pricing import format_inr, money_for_quantity, quote_total
from qshift.models import (
    Draft,
    Project,
    Quote,
    QuoteIntake,
    QuoteVersion,
    RateCard,
    RateEntry,
    SimulatedChat,
    SimulatedQuoteDelivery,
    User,
)
from qshift.services import audit, canonical_hash, require_project, uid

WARDROBE_SKU = WARDROBE
CONCEPT_PATH = "/static/wardrobe-concept-sample.png"
QUESTIONS = {
    "item": "What would you like quoted? This demo supports one wardrobe.",
    "room": "Which bedroom is the wardrobe for?",
    "finish": "Can you confirm white laminate for the wardrobe? This demo has that finish.",
    "width_ft": "How wide is the wardrobe in feet?",
    "height_ft": "How tall is the wardrobe in feet?",
    "unsupported_scope": "This demo supports one wardrobe. Start a new intake for that item alone.",
}
ITEM_QUESTIONS = {
    "items": "Which items should I quote? This sample supports a wardrobe and a gypsum ceiling.",
    "wardrobe_room": "Which room is the wardrobe for?",
    "wardrobe_finish": "Can you confirm white laminate for the wardrobe?",
    "wardrobe_width_ft": "How wide is the wardrobe in feet?",
    "wardrobe_height_ft": "How tall is the wardrobe in feet?",
    "ceiling_room": "Which room needs the gypsum ceiling?",
    "ceiling_area": "What is the gypsum ceiling area in square feet?",
    "unsupported_scope": "Some requested work needs designer review before I can price it.",
}
CANCEL_WORDS = {"cancel", "discard", "stop", "never mind", "nevermind"}


def start_sample(
    session: Session, user: User, scenario: str = "wardrobe", *, commit: bool = True
) -> dict:
    if user.firm_id != "firm-demo":
        raise LookupError("The sample is available in the fictional demo workspace only")
    card = session.scalar(
        select(RateCard).where(RateCard.id == "rate-card-demo-v1", RateCard.firm_id == user.firm_id)
    )
    if card is None:
        raise LookupError("Fictional sample rate card not found")
    rate = _sample_rate(session, user.firm_id, card.id, verified_only=False)
    if rate is None:
        rate = RateEntry(
            id=uid(),
            firm_id=user.firm_id,
            rate_card_id=card.id,
            sku=WARDROBE_SKU,
            name="Wardrobe, white laminate",
            category="Wardrobe",
            unit="sqft",
            rate_paise=125_000,
            gst_bps=0,
            verified=True,
        )
        session.add(rate)
        audit(session, user.firm_id, user.id, "RATE_VERIFIED", rate.id, "Fictional demo fixture")
    project = Project(
        id=uid(),
        firm_id=user.firm_id,
        name="Maple Apartment (fictional)",
        client_label="Fictional wardrobe client",
    )
    session.add(project)
    session.flush()
    messages = []
    if scenario == "itemized":
        messages.append(
            _message(
                "assistant",
                "Describe the wardrobe and gypsum ceiling you want quoted.",
                demo_scenario="itemized",
            )
        )
    intake = QuoteIntake(id=uid(), firm_id=user.firm_id, project_id=project.id, messages=messages)
    session.add(intake)
    audit(session, user.firm_id, user.id, "INITIAL_INTAKE_STARTED", project.id)
    session.flush()
    if commit:
        session.commit()
    return intake_view(session, user, project.id)


def start_project_intake(session: Session, user: User, project_id: str) -> None:
    project = require_project(session, user, project_id)
    already_quoted = session.scalar(
        select(Quote.id).where(
            Quote.firm_id == user.firm_id,
            Quote.project_id == project.id,
        )
    )
    if already_quoted:
        raise ValueError("This project already has a quotation.")
    existing = session.scalar(
        select(QuoteIntake.id).where(
            QuoteIntake.firm_id == user.firm_id,
            QuoteIntake.project_id == project.id,
        )
    )
    if existing:
        raise ValueError("This project already has an intake.")
    session.add(
        QuoteIntake(
            id=uid(),
            firm_id=user.firm_id,
            project_id=project.id,
            messages=[
                _message(
                    "assistant",
                    "Describe the wardrobe and gypsum ceiling you want quoted.",
                    demo_scenario="itemized",
                )
            ],
        )
    )
    audit(session, user.firm_id, user.id, "INITIAL_INTAKE_STARTED", project.id)


def _sample_rate(
    session: Session,
    firm_id: str,
    card_id: str,
    *,
    verified_only: bool = True,
    sku: str = WARDROBE,
) -> RateEntry | None:
    query = select(RateEntry).where(
        RateEntry.firm_id == firm_id,
        RateEntry.rate_card_id == card_id,
        RateEntry.sku == sku,
    )
    if verified_only:
        query = query.where(RateEntry.verified.is_(True), RateEntry.unit == "sqft")
    return session.scalar(query)


def _intake(session: Session, user: User, project_id: str) -> QuoteIntake:
    require_project(session, user, project_id)
    record = session.scalar(
        select(QuoteIntake).where(
            QuoteIntake.project_id == project_id, QuoteIntake.firm_id == user.firm_id
        )
    )
    if record is None:
        raise LookupError("Start a first-quote demo for this project")
    return record


def _draft(session: Session, intake: QuoteIntake) -> Draft | None:
    if intake.draft_id is None:
        return None
    return session.scalar(
        select(Draft).where(
            Draft.id == intake.draft_id,
            Draft.firm_id == intake.firm_id,
            Draft.project_id == intake.project_id,
        )
    )


def _message(role: str, text: str, **extra: str) -> dict:
    return {"id": uid(), "role": role, "text": text, **extra}


def add_client_message(
    session: Session,
    user: User,
    project_id: str,
    text: str,
    *,
    commit: bool = True,
    chat: SimulatedChat | None = None,
) -> dict:
    intake = _intake(session, user, project_id)
    bound = chat_for_project(session, user, project_id)
    if bound is not None and (chat is None or chat.id != bound.id):
        raise ValueError("Send messages for this chat through the simulated webhook.")
    clean_text = text.strip()
    if clean_text.casefold() in CANCEL_WORDS and intake.draft_id is not None:
        draft = session.get(Draft, intake.draft_id)
        if draft is not None and draft.firm_id == user.firm_id and draft.status in {
            "NEEDS_CLARIFICATION",
            "DRAFT_READY",
        }:
            draft.status = "CANCELLED"
            draft.ops = [{**op, "status": "CANCELLED"} for op in draft.ops]
            intake.draft_id = None
            intake.messages = [
                *intake.messages,
                _message("client", clean_text),
                _message("assistant", "Cancelled the open draft. The approved quote is unchanged."),
            ]
            audit(session, user.firm_id, user.id, "FIRST_QUOTE_CANCELLED", draft.id)
            session.flush()
            if commit:
                session.commit()
            return intake_view(session, user, project_id)
    if intake.draft_id is not None:
        raise ValueError("Intake is complete. Edit the quotation in designer review.")
    if not clean_text or len(intake.messages) >= 40:
        raise ValueError("Enter a fictional message or start a fresh demo when the chat is full.")
    messages = [*intake.messages, _message("client", clean_text)]
    use_model = os.getenv("QSHIFT_INTAKE_MODEL") == "ollama"
    if _scenario(intake) == "itemized":
        return _add_itemized_message(
            session,
            user,
            intake,
            messages,
            use_model,
            rate_card_id=bound.rate_card_id if bound else "rate-card-demo-v1",
            commit=commit,
        )
    brief, missing = propose_scope(messages) if use_model else extract_brief(messages)
    if missing:
        reply = _message("assistant", QUESTIONS[missing], field=missing)
    else:
        rate = _sample_rate(session, user.firm_id, "rate-card-demo-v1")
        if rate is None:
            reply = _message(
                "assistant", "A designer needs to verify a matching rate before pricing."
            )
        else:
            draft = _create_first_draft(
                session, user, project_id, rate.rate_card_id, [_priced_line(brief, rate)]
            )
            intake.draft_id = draft.id
            reply = _message(
                "assistant", "I have the details. Your designer will review the quote."
            )
    reply.update(extracted_brief=brief, missing=missing, model=MODEL if use_model else None)
    intake.messages = [*messages, reply]
    session.flush()
    if commit:
        session.commit()
    return intake_view(session, user, project_id)


def _scenario(intake: QuoteIntake) -> str:
    return intake.messages[0].get("demo_scenario", "wardrobe") if intake.messages else "wardrobe"


def _add_itemized_message(
    session: Session,
    user: User,
    intake: QuoteIntake,
    messages: list[dict],
    use_model: bool,
    *,
    rate_card_id: str,
    commit: bool,
) -> dict:
    if not use_model:
        raise ValueError("Start QShift with the local AI model to run the itemized sample.")
    items, missing = propose_items(messages)
    lines = []
    if not missing:
        for item in items:
            rate = _sample_rate(session, user.firm_id, rate_card_id, sku=item["sku"])
            if rate is None:
                missing = "verified_rate"
                break
            lines.append(_priced_line(item["facts"], rate))
    if missing == "verified_rate":
        reply = _message("assistant", "A designer needs to verify a matching rate before pricing.")
    elif missing:
        reply = _message("assistant", ITEM_QUESTIONS[missing], field=missing)
    else:
        draft = _create_first_draft(session, user, intake.project_id, rate_card_id, lines)
        intake.draft_id = draft.id
        reply = _message("assistant", "Your itemized quote is ready for designer review.")
    reply.update(extracted_brief={}, items=items, missing=missing, model=MODEL)
    intake.messages = [*messages, reply]
    session.flush()
    if commit:
        session.commit()
    return intake_view(session, user, intake.project_id)


def _priced_line(brief: dict, rate: RateEntry) -> dict:
    quantity = (
        Decimal(brief["area"]["value"])
        if rate.sku == CEILING
        else Decimal(brief["width_ft"]["value"]) * Decimal(brief["height_ft"]["value"])
    )
    return {
        "line_id": uid(),
        "room": brief["room"]["value"],
        "category": rate.category,
        "description": rate.name,
        "sku": rate.sku,
        "quantity": format(quantity, "f"),
        "unit": rate.unit,
        "rate_paise": rate.rate_paise,
        "total_paise": money_for_quantity(quantity, rate.rate_paise),
        "gst_bps": rate.gst_bps,
    }


def _create_first_draft(
    session: Session, user: User, project_id: str, rate_card_id: str, lines: list[dict]
) -> Draft:
    quote = Quote(
        id=uid(),
        firm_id=user.firm_id,
        project_id=project_id,
        current_version=0,
        rate_card_id=rate_card_id,
    )
    session.add(quote)
    session.flush()
    draft = Draft(
        id=uid(),
        firm_id=user.firm_id,
        project_id=project_id,
        quote_id=quote.id,
        base_version=0,
        rate_card_id=rate_card_id,
        ops=[
            {"op": "ADD", "target_text": line["description"], "status": "VERIFIED"}
            for line in lines
        ],
        lines=lines,
        total_paise=quote_total(lines),
        content_sha256=canonical_hash(lines),
        status="DRAFT_READY",
        created_by=user.id,
    )
    session.add(draft)
    session.flush()
    audit(session, user.firm_id, user.id, "INITIAL_QUOTE_DRAFTED", draft.id)
    return draft


def edit_quantity(
    session: Session,
    user: User,
    project_id: str,
    quantity: Decimal,
    expected_hash: str,
    line_id: str | None = None,
) -> dict:
    draft = _draft(session, _intake(session, user, project_id))
    if draft is None or draft.status != "DRAFT_READY":
        raise ValueError("Only a quote awaiting review can be edited")
    if line_id is None and len(draft.lines) == 1:
        line_id = draft.lines[0]["line_id"]
    index = next((i for i, row in enumerate(draft.lines) if row["line_id"] == line_id), None)
    if index is None:
        raise ValueError("Select a line from the current draft before editing.")
    line = dict(draft.lines[index])
    # Each edit changes the approval hash, even when a reviewer restores a prior quantity.
    line["line_id"] = uid()
    line["quantity"] = format(quantity, "f")
    line["total_paise"] = money_for_quantity(quantity, line["rate_paise"])
    lines = [*draft.lines]
    lines[index] = line
    result = session.execute(
        update(Draft)
        .where(
            Draft.id == draft.id,
            Draft.firm_id == user.firm_id,
            Draft.status == "DRAFT_READY",
            Draft.content_sha256 == expected_hash,
        )
        .values(lines=lines, content_sha256=canonical_hash(lines), total_paise=quote_total(lines))
    )
    if result.rowcount != 1:
        raise ValueError("The draft changed. Reload it before making an edit.")
    audit(session, user.firm_id, user.id, "INITIAL_QUOTE_QUANTITY_EDITED", draft.id)
    session.commit()
    return intake_view(session, user, project_id)


def intake_view(session: Session, user: User, project_id: str) -> dict:
    intake = _intake(session, user, project_id)
    chat = chat_for_project(session, user, project_id)
    extraction = next((m for m in reversed(intake.messages) if "extracted_brief" in m), None)
    if extraction is None:
        brief, missing = extract_brief(intake.messages)
    else:
        brief, missing = extraction["extracted_brief"], extraction["missing"]
    draft = _draft(session, intake)
    messages = [
        {key: message[key] for key in ("id", "role", "text")}
        for message in intake.messages
        if "concept_version_id" not in message
    ]
    review = None
    if draft is not None:
        review = {
            "id": draft.id,
            "hash": draft.content_sha256,
            "status": draft.status,
            "line": draft.lines[0],
            "lines": draft.lines,
            "total": format_inr(draft.total_paise),
        }
        if any(line["sku"] == WARDROBE for line in draft.lines):
            review["concept_preview"] = CONCEPT_PATH
        version = _approved_version(session, draft)
        delivery = (
            session.get(SimulatedQuoteDelivery, (user.firm_id, chat.id, version.id))
            if version is not None and chat is not None
            else None
        )
        if version is not None and (chat is None or delivery is not None):
            review["version_id"] = version.id
            concept = next(
                (m for m in intake.messages if m.get("concept_version_id") == version.id), None
            )
            review["concept_attached"] = concept is not None
            messages.append(
                {
                    "id": version.id,
                    "role": "assistant",
                    "text": f"SIMULATED DELIVERY · Approved quotation v1 · {review['total']}",
                    "pdf_path": (
                        f"/api/simulated-whatsapp/chats/{chat.id}/quotes/{version.id}/pdf"
                        if chat
                        else f"/api/versions/{version.id}/pdf"
                    ),
                }
            )
            if concept is not None:
                messages.append({**concept, "concept_preview": CONCEPT_PATH})
    return {
        "project_id": project_id,
        "messages": messages,
        "brief": brief,
        "missing": missing,
        "draft": review,
        "extraction": extraction["model"] if extraction else None,
        "scenario": _scenario(intake),
        "items": extraction.get("items", []) if extraction else [],
        "chat_id": chat.id if chat else None,
    }


def chat_for_project(session: Session, user: User, project_id: str) -> SimulatedChat | None:
    return session.scalar(
        select(SimulatedChat).where(
            SimulatedChat.firm_id == user.firm_id, SimulatedChat.project_id == project_id
        )
    )


def _approved_version(session: Session, draft: Draft) -> QuoteVersion | None:
    if draft.status != "APPROVED":
        return None
    return session.scalar(
        select(QuoteVersion).where(
            QuoteVersion.firm_id == draft.firm_id,
            QuoteVersion.quote_id == draft.quote_id,
            QuoteVersion.number == 1,
            QuoteVersion.status == "APPROVED",
            QuoteVersion.content_sha256 == draft.content_sha256,
        )
    )


def attach_concept(session: Session, user: User, project_id: str, version_id: str) -> dict:
    intake = _intake(session, user, project_id)
    if user.role not in {"OWNER", "APPROVER"}:
        raise PermissionError("Only an authorized approver can attach the client concept")
    draft = _draft(session, intake)
    version = _approved_version(session, draft) if draft is not None else None
    if version is None or version.id != version_id:
        raise ValueError("Select the approved first quote before attaching its concept preview")
    if not any(line["sku"] == WARDROBE for line in version.lines):
        raise ValueError("The sample preview is available for wardrobe quotes.")
    if not any(message.get("concept_version_id") == version.id for message in intake.messages):
        concept = _message(
            "assistant", "AI concept preview · illustrative sample", concept_version_id=version.id
        )
        intake.messages = [*intake.messages, concept]
        audit(session, user.firm_id, user.id, "SIMULATED_CONCEPT_ATTACHED", version.id)
        session.commit()
    return intake_view(session, user, project_id)
