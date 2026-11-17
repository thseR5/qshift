"""Tenant-scoped workflow services used by the API, simulator, and demo."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import uuid
from datetime import UTC, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from qshift.agent.extraction import MockLLM
from qshift.approval.core import issue_token, token_digest, validate_token
from qshift.engine.pricing import (
    format_inr,
    gst_by_slab,
    line_total,
    money_for_quantity,
    quote_total,
)
from qshift.models import (
    Approval,
    AuditEvent,
    Draft,
    Firm,
    Project,
    Quote,
    QuoteIntake,
    QuoteVersion,
    RateCard,
    RateEntry,
    SimulatedChat,
    SimulatedQuoteDelivery,
    SimulatedReceipt,
    User,
    now_utc,
)

APPROVAL_SECRET = os.getenv("QSHIFT_APPROVAL_SECRET", "local-demo-only-change-me").encode()


def uid() -> str:
    return str(uuid.uuid4())


def hash_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def canonical_hash(lines: list[dict[str, Any]]) -> str:
    payload = json.dumps(lines, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hash_text(payload)


def audit(
    session: Session, firm_id: str, user_id: str, action: str, object_id: str, detail: str = ""
) -> None:
    session.add(
        AuditEvent(
            id=uid(),
            firm_id=firm_id,
            actor_id=user_id,
            action=action,
            object_id=object_id,
            detail=detail,
        )
    )


def user_from_demo_token(session: Session, bearer: str | None) -> User | None:
    if not bearer:
        return None
    digest = hash_text(bearer)
    return session.scalar(select(User).where(User.demo_token_hash == digest))


def seed_demo(session: Session, reset: bool = False) -> dict[str, Any]:
    """Create explicitly fictional demo tenant, catalogue, projects, and quotation."""
    firm_id = "firm-demo"
    existing = session.get(Firm, firm_id)
    if existing and not reset:
        return demo_summary(session)
    if existing and reset:
        for model in (
            SimulatedQuoteDelivery,
            SimulatedReceipt,
            SimulatedChat,
            Approval,
            AuditEvent,
            QuoteIntake,
            Draft,
            QuoteVersion,
            Quote,
            RateEntry,
            RateCard,
            Project,
            User,
            Firm,
        ):
            session.query(model).filter(
                getattr(model, "firm_id", getattr(model, "id", None)) == firm_id
            ).delete(synchronize_session=False)
        session.flush()
        session.expunge_all()
    session.add(Firm(id=firm_id, name="Demo Interiors", illustrative=True))
    session.flush()
    users = []
    for user_id, name, role, token in [
        ("user-owner", "Asha Owner", "OWNER", "demo-owner-token"),
        ("user-approver", "Dev Approver", "APPROVER", "demo-approver-token"),
        ("user-designer", "Ravi Designer", "DESIGNER", "demo-designer-token"),
    ]:
        user = User(
            id=user_id, firm_id=firm_id, name=name, role=role, demo_token_hash=hash_text(token)
        )
        session.add(user)
        users.append(user)
    rate_card_id = "rate-card-demo-v1"
    session.add(RateCard(id=rate_card_id, firm_id=firm_id, version=1))
    session.flush()
    entries = [
        ("COUNTER-GRANITE", "Granite countertop, standard", "Countertop", "sqft", 65000),
        ("COUNTER-QUARTZ-WHITE", "Quartz countertop, white", "Countertop", "sqft", 92000),
        ("COUNTER-QUARTZ-CALACATTA", "Quartz countertop, Calacatta", "Countertop", "sqft", 128000),
        ("FALSE-CEILING-GYPSUM", "Gypsum false ceiling", "Ceiling", "sqft", 8500),
        ("FALSE-CEILING-POP", "POP false ceiling", "Ceiling", "sqft", 7200),
    ]
    catalog = [(sku, name, cat, unit, rate) for sku, name, cat, unit, rate in entries]
    categories = ["Kitchen", "Wardrobe", "Painting", "Electrical", "Flooring", "Furniture"]
    for i in range(55):
        cat = categories[i % len(categories)]
        sku = f"DEMO-{i + 1:03}"
        catalog.append(
            (
                sku,
                f"Illustrative {cat.lower()} work {i + 1}",
                cat,
                ["sqft", "rft", "nos", "lumpsum"][i % 4],
                32000 if sku == "DEMO-013" else 12000 + i * 1750,
            )
        )
    for sku, name, category, unit, price in catalog:
        entry_id = uid()
        session.add(
            RateEntry(
                id=entry_id,
                firm_id=firm_id,
                rate_card_id=rate_card_id,
                sku=sku,
                name=name,
                category=category,
                unit=unit,
                rate_paise=price,
                gst_bps=0,
                verified=True,
            )
        )
        audit(
            session,
            firm_id,
            "user-owner",
            "RATE_VERIFIED",
            entry_id,
            f"Fictional seed catalogue {rate_card_id}",
        )
    projects = [
        Project(
            id="project-sharma",
            firm_id=firm_id,
            name="Sharma Residence",
            client_label="Illustrative client: Sharma family",
        ),
        Project(
            id="project-mehta",
            firm_id=firm_id,
            name="Mehta Apartment",
            client_label="Illustrative client: Mehta family",
        ),
        Project(
            id="project-iyer",
            firm_id=firm_id,
            name="Iyer Villa",
            client_label="Illustrative client: Iyer family",
        ),
    ]
    session.add_all(projects)
    session.flush()
    quote_id, version_id = "quote-sharma", "version-sharma-1"
    lines = [
        {
            "line_id": "line-kitchen-counter",
            "room": "Kitchen",
            "category": "Countertop",
            "description": "Granite countertop, standard",
            "sku": "COUNTER-GRANITE",
            "quantity": "40.000",
            "unit": "sqft",
            "rate_paise": 65000,
            "total_paise": 2600000,
            "gst_bps": 0,
        },
        {
            "line_id": "line-bedroom-ceiling",
            "room": "Bedroom",
            "category": "Ceiling",
            "description": "Gypsum false ceiling",
            "sku": "FALSE-CEILING-GYPSUM",
            "quantity": "120.000",
            "unit": "sqft",
            "rate_paise": 8500,
            "total_paise": 1020000,
            "gst_bps": 0,
        },
        {
            "line_id": "line-living-paint",
            "room": "Living Room",
            "category": "Painting",
            "description": "Interior painting, premium",
            "sku": "DEMO-013",
            "quantity": "600.000",
            "unit": "sqft",
            "rate_paise": 32000,
            "total_paise": 19200000,
            "gst_bps": 0,
        },
    ]
    # Fictional base scope is ₹2,28,200; scale and rates are illustrative demo values.
    total = quote_total(lines)
    session.add(
        Quote(
            id=quote_id,
            firm_id=firm_id,
            project_id="project-sharma",
            current_version=1,
            rate_card_id=rate_card_id,
        )
    )
    session.flush()
    session.add(
        QuoteVersion(
            id=version_id,
            firm_id=firm_id,
            quote_id=quote_id,
            number=1,
            base_version=None,
            rate_card_id=rate_card_id,
            content_sha256=canonical_hash(lines),
            lines=lines,
            total_paise=total,
            status="APPROVED",
            change_summary=[],
            created_by="user-owner",
        )
    )
    session.commit()
    return demo_summary(session)


def demo_summary(session: Session) -> dict[str, Any]:
    firm = session.get(Firm, "firm-demo")
    if firm is None:
        return {"seeded": False}
    projects = session.scalars(select(Project).where(Project.firm_id == firm.id)).all()
    return {
        "seeded": True,
        "firm": firm.name,
        "projects": [{"id": p.id, "name": p.name} for p in projects],
        "users": [
            {"id": "user-owner", "role": "OWNER", "token": "demo-owner-token"},
            {"id": "user-approver", "role": "APPROVER", "token": "demo-approver-token"},
            {"id": "user-designer", "role": "DESIGNER", "token": "demo-designer-token"},
        ],
        "warning": "Fictional demo-only accounts and data.",
    }


def require_project(session: Session, user: User, project_id: str) -> Project:
    project = session.scalar(
        select(Project).where(Project.id == project_id, Project.firm_id == user.firm_id)
    )
    if project is None:
        raise LookupError("Project not found")
    return project


def pin_project(
    session: Session, user: User, project_id: str, *, commit: bool = True
) -> dict[str, Any]:
    project = require_project(session, user, project_id)
    project.pinned_by = user.id
    audit(session, user.firm_id, user.id, "PROJECT_PINNED", project.id)
    if commit:
        session.commit()
    return {"id": project.id, "name": project.name}


def projects_for_user(session: Session, user: User) -> list[dict[str, str]]:
    return [
        {"id": p.id, "name": p.name}
        for p in session.scalars(select(Project).where(Project.firm_id == user.firm_id)).all()
    ]


def create_project(session: Session, user: User, name: str, client_label: str) -> dict[str, str]:
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Project name cannot be blank")
    project = Project(
        id=uid(),
        firm_id=user.firm_id,
        name=clean_name,
        client_label=client_label.strip() or "Fictional client",
        pinned_by=None,
    )
    session.add(project)
    audit(session, user.firm_id, user.id, "PROJECT_CREATED", project.id)
    session.commit()
    return {"id": project.id, "name": project.name}


def import_rate_card(session: Session, user: User, filename: str, content: bytes) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    if filename.lower().endswith(".csv"):
        rows = list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))
    elif filename.lower().endswith((".xlsx", ".xlsm")):
        ws = load_workbook(io.BytesIO(content), read_only=True, data_only=True).active
        iterator = ws.iter_rows(values_only=True)
        headers = [str(h).strip().lower() for h in next(iterator, ()) if h is not None]
        rows = [
            dict(zip(headers, row, strict=False))
            for row in iterator
            if any(v is not None for v in row)
        ]
    else:
        raise ValueError("Only CSV and XLSX imports are supported")
    errors: list[str] = []
    warnings: list[str] = []
    candidate_rates = sorted(
        int(str(row.get("rate_paise", "")).strip())
        for row in rows
        if str(row.get("rate_paise", "")).strip().isdigit()
        and int(str(row.get("rate_paise", "")).strip()) > 0
    )
    median_rate = candidate_rates[(len(candidate_rates) - 1) // 2] if candidate_rates else 0
    accepted = 0
    version = (
        int(
            session.scalar(
                select(RateCard.version)
                .where(RateCard.firm_id == user.firm_id)
                .order_by(RateCard.version.desc())
                .limit(1)
            )
            or 0
        )
        + 1
    )
    card = RateCard(id=uid(), firm_id=user.firm_id, version=version)
    session.add(card)
    session.flush()
    seen: set[str] = set()
    imported_entries: list[dict[str, str]] = []
    for index, raw in enumerate(rows, start=2):
        row = {str(k).strip().lower(): v for k, v in raw.items()}
        sku = str(row.get("sku", "")).strip()
        unit = str(row.get("unit", "")).strip().lower()
        price = str(row.get("rate_paise", "")).strip()
        try:
            rate = int(price)
            if not sku or unit not in {"sqft", "rft", "sqm", "nos", "lumpsum"} or rate <= 0:
                raise ValueError
            gst_bps = int(row.get("gst_bps", 0) or 0)
            if gst_bps < 0:
                raise ValueError
            if sku in seen:
                raise ValueError
        except ValueError:
            errors.append(
                f"Row {index}: duplicate SKU or missing/invalid SKU, unit, or positive rate_paise"
            )
            continue
        seen.add(sku)
        if median_rate and (rate > median_rate * 10 or rate * 10 < median_rate):
            warnings.append(
                f"Row {index}: rate is over 10x from the imported rate-card median; manual review required"
            )
        entry_id = uid()
        session.add(
            RateEntry(
                id=entry_id,
                firm_id=user.firm_id,
                rate_card_id=card.id,
                sku=sku,
                name=str(row.get("name", sku)),
                category=str(row.get("category", "Other")),
                unit=unit,
                rate_paise=rate,
                gst_bps=gst_bps,
                verified=False,
            )
        )
        imported_entries.append({"id": entry_id, "sku": sku, "name": str(row.get("name", sku))})
        accepted += 1
    session.commit()
    return {
        "rate_card_id": card.id,
        "version": version,
        "accepted": accepted,
        "unverified": accepted,
        "errors": errors,
        "warnings": warnings,
        "entries": imported_entries,
    }


def verify_rate(session: Session, user: User, entry_id: str) -> None:
    if user.role not in {"OWNER", "APPROVER"}:
        raise PermissionError("Only an OWNER or APPROVER can verify imported rates")
    entry = session.scalar(
        select(RateEntry).where(RateEntry.id == entry_id, RateEntry.firm_id == user.firm_id)
    )
    if entry is None:
        raise LookupError("Rate not found")
    entry.verified = True
    audit(session, user.firm_id, user.id, "RATE_VERIFIED", entry.id)
    session.commit()


def import_quotation(
    session: Session, user: User, project_id: str, filename: str, content: bytes
) -> dict[str, Any]:
    """Import a simple itemized CSV/XLSX quotation after matching verified SKUs."""
    require_project(session, user, project_id)
    existing_quote = session.scalar(
        select(Quote).where(Quote.firm_id == user.firm_id, Quote.project_id == project_id)
    )
    if existing_quote:
        raise ValueError(
            "This project already has a quotation; import into a new project to preserve history"
        )
    card = session.scalar(
        select(RateCard)
        .where(RateCard.firm_id == user.firm_id)
        .order_by(RateCard.version.desc())
        .limit(1)
    )
    if card is None:
        raise ValueError("Import a rate card before importing a quotation")
    rows: list[dict[str, Any]] = []
    if filename.lower().endswith(".csv"):
        rows = list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))
    elif filename.lower().endswith((".xlsx", ".xlsm")):
        ws = load_workbook(io.BytesIO(content), read_only=True, data_only=True).active
        iterator = ws.iter_rows(values_only=True)
        headers = [str(h).strip().lower() for h in next(iterator, ()) if h is not None]
        rows = [
            dict(zip(headers, row, strict=False))
            for row in iterator
            if any(v is not None for v in row)
        ]
    else:
        raise ValueError("Only CSV and XLSX imports are supported")
    errors: list[str] = []
    lines: list[dict[str, Any]] = []
    for row_num, raw in enumerate(rows, start=2):
        row = {str(k).strip().lower(): v for k, v in raw.items()}
        sku = str(row.get("sku", "")).strip()
        entry = session.scalar(
            select(RateEntry).where(
                RateEntry.firm_id == user.firm_id,
                RateEntry.rate_card_id == card.id,
                RateEntry.sku == sku,
                RateEntry.verified.is_(True),
            )
        )
        try:
            quantity = Decimal(str(row.get("quantity", "")))
            if (
                not entry
                or not row.get("room")
                or not quantity.is_finite()
                or quantity <= 0
                or quantity.as_tuple().exponent < -3
            ):
                raise ValueError
        except Exception:
            errors.append(f"Row {row_num}: missing room, quantity, or verified SKU {sku!r}")
            continue
        lines.append(
            {
                "line_id": uid(),
                "room": str(row["room"]),
                "category": entry.category,
                "description": entry.name,
                "sku": entry.sku,
                "quantity": format(quantity, ".3f"),
                "unit": entry.unit,
                "rate_paise": entry.rate_paise,
                "total_paise": int(
                    (quantity * entry.rate_paise).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
                ),
                "gst_bps": entry.gst_bps,
            }
        )
    if not lines:
        raise ValueError("No valid quotation rows to import")
    quote_id = uid()
    quote = Quote(
        id=quote_id,
        firm_id=user.firm_id,
        project_id=project_id,
        current_version=1,
        rate_card_id=card.id,
    )
    session.add(quote)
    session.flush()
    version = QuoteVersion(
        id=uid(),
        firm_id=user.firm_id,
        quote_id=quote_id,
        number=1,
        base_version=None,
        rate_card_id=card.id,
        content_sha256=canonical_hash(lines),
        lines=lines,
        total_paise=quote_total(lines),
        status="APPROVED",
        change_summary=[],
        created_by=user.id,
    )
    session.add(version)
    audit(session, user.firm_id, user.id, "QUOTATION_IMPORTED", quote_id, f"{len(lines)} line(s)")
    session.commit()
    return {
        "quote_id": quote_id,
        "version": 1,
        "valid_rows": len(lines),
        "errors": errors,
        "total_paise": version.total_paise,
        "total": format_inr(version.total_paise),
    }


def submit_change(
    session: Session, user: User, project_id: str, text: str, *, commit: bool = True
) -> dict[str, Any]:
    require_project(session, user, project_id)
    quote = session.scalar(
        select(Quote).where(Quote.project_id == project_id, Quote.firm_id == user.firm_id)
    )
    if quote is None or quote.current_version == 0:
        raise LookupError("Approve the first quotation before requesting revisions")
    existing = session.scalar(
        select(Draft).where(
            Draft.firm_id == user.firm_id,
            Draft.project_id == project_id,
            Draft.status.in_(["NEEDS_CLARIFICATION", "DRAFT_READY"]),
        )
    )
    if existing:
        raise ValueError("This project already has an open draft")
    llm = MockLLM()
    if llm.classify(text) != "submit_change_request":
        return {
            "intent": "out_of_scope",
            "reply": "I can pin a project, revise a quotation from your request, review or approve a draft, show version history, or summarize recorded project changes. Type help for options.",
        }
    base = session.scalar(
        select(QuoteVersion).where(
            QuoteVersion.firm_id == user.firm_id,
            QuoteVersion.quote_id == quote.id, QuoteVersion.number == quote.current_version
        )
    )
    assert base is not None
    ops = llm.extract(text)
    output_lines = [dict(line) for line in base.lines]
    for op in ops:
        if op["op"] == "REMOVE":
            idx = next(
                (
                    i
                    for i, line in enumerate(output_lines)
                    if line["room"].casefold() == str(op["room"]).casefold()
                    and "ceiling" in line["category"].casefold()
                ),
                None,
            )
            if idx is None:
                op["status"], op["missing_fields"] = "NEEDS_INFO", ["target"]
            else:
                removed = output_lines.pop(idx)
                op["resolved_line_id"] = removed["line_id"]
                op["removed_line"] = removed
        elif op["op"] == "REPLACE":
            matches = session.scalars(
                select(RateEntry).where(
                    RateEntry.firm_id == user.firm_id,
                    RateEntry.rate_card_id == quote.rate_card_id,
                    RateEntry.verified.is_(True),
                    RateEntry.name.ilike("%quartz%"),
                )
            ).all()
            op["options"] = [
                {"sku": e.sku, "name": e.name, "rate_paise": e.rate_paise, "unit": e.unit}
                for e in matches
            ]
            source_line = next(
                (
                    line
                    for line in base.lines
                    if line["room"] == op["room"] and line["category"] == "Countertop"
                ),
                None,
            )
            if source_line:
                op["resolved_line_id"] = source_line["line_id"]
            op["status"] = "NEEDS_INFO"
            op["missing_fields"] = ["catalogue_selection"]
    new_total = quote_total(output_lines)
    draft = Draft(
        id=uid(),
        firm_id=user.firm_id,
        project_id=project_id,
        quote_id=quote.id,
        base_version=base.number,
        rate_card_id=quote.rate_card_id,
        ops=ops,
        lines=output_lines,
        total_paise=new_total,
        content_sha256=canonical_hash(output_lines),
        status="NEEDS_CLARIFICATION"
        if any(op["status"] == "NEEDS_INFO" for op in ops)
        else "DRAFT_READY",
        created_by=user.id,
    )
    session.add(draft)
    audit(session, user.firm_id, user.id, "CHANGE_PROPOSED", draft.id)
    if commit:
        session.commit()
    return draft_view(draft, base.total_paise, base.lines)


def resolve_catalogue(
    session: Session, user: User, draft_id: str, sku: str, *, commit: bool = True
) -> dict[str, Any]:
    draft = session.scalar(
        select(Draft).where(Draft.id == draft_id, Draft.firm_id == user.firm_id).with_for_update()
    )
    if not draft:
        raise LookupError("Draft not found")
    if draft.status != "NEEDS_CLARIFICATION":
        raise ValueError("This draft is no longer waiting for a catalogue choice")
    ops = [dict(operation) for operation in draft.ops]
    op = next(
        (
            operation
            for operation in ops
            if operation["op"] == "REPLACE"
            and operation["status"] == "NEEDS_INFO"
            and any(option["sku"] == sku for option in operation.get("options", []))
        ),
        None,
    )
    if op is None:
        raise ValueError("Choose one of the catalogue options offered for this draft")
    entry = session.scalar(
        select(RateEntry).where(
            RateEntry.sku == sku,
            RateEntry.firm_id == user.firm_id,
            RateEntry.rate_card_id == draft.rate_card_id,
            RateEntry.verified.is_(True),
        )
    )
    if not entry:
        raise ValueError("Select a verified catalogue option")
    if entry.unit != "sqft":
        raise ValueError("Unit mismatch; designer confirmation is required")
    # Resolve from the original base line when the REMOVE operation already deleted it.
    base = session.scalar(
        select(QuoteVersion).where(
            QuoteVersion.firm_id == user.firm_id,
            QuoteVersion.quote_id == draft.quote_id,
            QuoteVersion.number == draft.base_version,
        )
    )
    old_line = next(
        (
            line
            for line in (base.lines if base else [])
            if line["room"] == op["room"] and line["category"] == "Countertop"
        ),
        None,
    )
    if old_line is None:
        raise ValueError("Could not resolve the original countertop line")
    draft.lines = [line for line in draft.lines if line["line_id"] != old_line["line_id"]]
    replacement = {
        **old_line,
        "description": entry.name,
        "sku": entry.sku,
        "rate_paise": entry.rate_paise,
        "total_paise": money_for_quantity(old_line["quantity"], entry.rate_paise),
        "gst_bps": entry.gst_bps,
    }
    draft.lines.append(replacement)
    op.update(
        {
            "sku": entry.sku,
            "selected_name": entry.name,
            "quantity": old_line["quantity"],
            "unit": entry.unit,
            "status": "VERIFIED",
            "missing_fields": [],
            "resolved_line_id": old_line["line_id"],
        }
    )
    draft.ops = ops
    draft.total_paise = quote_total(draft.lines)
    draft.content_sha256 = canonical_hash(draft.lines)
    draft.status = (
        "NEEDS_CLARIFICATION"
        if any(operation["status"] == "NEEDS_INFO" for operation in ops)
        else "DRAFT_READY"
    )
    audit(session, user.firm_id, user.id, "CATALOGUE_SELECTED", draft.id, entry.sku)
    if commit:
        session.commit()
    return draft_view(draft, base.total_paise if base else 0, base.lines if base else [])


def draft_view(
    draft: Draft, original_total: int, base_lines: list[dict[str, Any]]
) -> dict[str, Any]:
    before = {line["line_id"]: line for line in base_lines}
    after = {line["line_id"]: line for line in draft.lines}
    diff: list[dict[str, Any]] = []
    for line_id in sorted(before.keys() | after.keys()):
        old, new = before.get(line_id), after.get(line_id)
        if old is None and new is not None:
            kind, delta, line = "added", line_total(new), new
        elif new is None and old is not None:
            kind, delta, line = "removed", -line_total(old), old
        elif old is not None and new is not None and old != new:
            kind, delta, line = (
                "changed",
                line_total(new) - line_total(old),
                new,
            )
        else:
            kind, delta, line = "unchanged", 0, new or old
        assert line is not None
        diff.append(
            {
                "line_id": line_id,
                "kind": kind,
                "room": line["room"],
                "description": line["description"],
                "delta_paise": delta,
                "delta": format_inr(delta),
            }
        )
    return {
        "id": draft.id,
        "status": draft.status,
        "ops": draft.ops,
        "lines": draft.lines,
        "line_diffs": diff,
        "line_delta_basis": "before GST; GST is rounded once per rate slab",
        "original_gst_paise": sum(gst_by_slab(base_lines).values()),
        "revised_gst_paise": sum(gst_by_slab(draft.lines).values()),
        "original_total_paise": original_total,
        "revised_total_paise": draft.total_paise,
        "net_change_paise": draft.total_paise - original_total,
        "original_total": format_inr(original_total),
        "revised_total": format_inr(draft.total_paise),
        "net_change": format_inr(draft.total_paise - original_total),
        "content_sha256": draft.content_sha256,
    }


def issue_approval_token(
    session: Session, user: User, draft_id: str, expected_hash: str | None = None
) -> str:
    if user.role not in {"OWNER", "APPROVER"}:
        raise PermissionError("Only an OWNER or APPROVER can approve quotations")
    draft = session.scalar(select(Draft).where(Draft.id == draft_id, Draft.firm_id == user.firm_id))
    if not draft:
        raise LookupError("Draft not found")
    if draft.status != "DRAFT_READY":
        raise ValueError("Draft needs clarification before approval")
    if (draft.base_version == 0 or expected_hash is not None) and draft.content_sha256 != expected_hash:
        raise ValueError("The draft has changed. Review the current quotation before approving.")
    token, expiry = issue_token(draft.id, draft.content_sha256, user.id, APPROVAL_SECRET)
    approval = session.scalar(
        select(Approval).where(Approval.firm_id == user.firm_id, Approval.draft_id == draft.id)
    )
    if approval is None:
        approval = Approval(id=uid(), firm_id=user.firm_id, draft_id=draft.id)
        session.add(approval)
    approval.token_hash = token_digest(token)
    approval.approver_id = user.id
    approval.content_sha256 = draft.content_sha256
    approval.expires_at = expiry
    audit(session, user.firm_id, user.id, "APPROVAL_TOKEN_ISSUED", draft.id)
    session.commit()
    return token


def reject_draft(session: Session, user: User, draft_id: str) -> dict[str, str]:
    draft = session.scalar(select(Draft).where(Draft.id == draft_id, Draft.firm_id == user.firm_id))
    if draft is None:
        raise LookupError("Draft not found")
    if draft.base_version == 0:
        raise ValueError("Use first-quote intake to review this draft")
    if draft.status not in {"NEEDS_CLARIFICATION", "DRAFT_READY"}:
        raise ValueError("Only an open draft can be rejected")
    draft.status = "REJECTED"
    draft.ops = [{**op, "status": "REJECTED"} for op in draft.ops]
    audit(session, user.firm_id, user.id, "REVISION_REJECTED", draft.id)
    session.commit()
    return {"draft_id": draft.id, "status": draft.status}


def approve_draft(
    session: Session, user: User, token: str, *, write_pdf: bool = True
) -> dict[str, Any]:
    if user.role not in {"OWNER", "APPROVER"}:
        raise PermissionError("Only an OWNER or APPROVER can approve quotations")
    try:
        claims = validate_token(token, APPROVAL_SECRET)
    except ValueError as exc:
        raise PermissionError(str(exc)) from exc
    approval = session.scalar(
        select(Approval)
        .where(Approval.token_hash == token_digest(token), Approval.firm_id == user.firm_id)
        .with_for_update()
    )
    expiry = approval.expires_at if approval else now_utc()
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=UTC)
    if (
        not approval
        or expiry <= now_utc()
        or approval.approver_id != user.id
        or approval.used_at
        or claims["approver_id"] != user.id
        or claims["draft_id"] != approval.draft_id
        or claims["content_sha256"] != approval.content_sha256
    ):
        raise PermissionError(
            "Approval token is invalid, expired, replayed, or bound to another approver"
        )
    draft = session.scalar(
        select(Draft).where(Draft.id == approval.draft_id, Draft.firm_id == user.firm_id)
    )
    quote = (
        session.scalar(
            select(Quote)
            .where(Quote.id == draft.quote_id, Quote.firm_id == user.firm_id)
            .with_for_update()
        )
        if draft
        else None
    )
    if not draft or not quote:
        raise LookupError("Draft or quotation not found")
    if draft.content_sha256 != approval.content_sha256 or draft.content_sha256 != canonical_hash(
        draft.lines
    ):
        raise ValueError("Draft content changed after approval request")
    if draft.total_paise != quote_total(draft.lines):
        raise ValueError("Draft total does not match deterministic line and tax calculations")
    if quote.current_version != draft.base_version or quote.rate_card_id != draft.rate_card_id:
        raise ValueError("Quotation or rate card changed since this draft was prepared")
    for line in draft.lines:
        rate = session.scalar(
            select(RateEntry).where(
                RateEntry.firm_id == user.firm_id,
                RateEntry.rate_card_id == draft.rate_card_id,
                RateEntry.sku == line["sku"],
            )
        )
        if (
            rate is None
            or not rate.verified
            or rate.rate_paise != int(line["rate_paise"])
            or rate.unit != line["unit"]
            or rate.gst_bps != int(line.get("gst_bps", 0))
        ):
            raise ValueError("A quotation rate or unit changed or is no longer verified")
    claimed = session.execute(
        update(Draft)
        .where(
            Draft.id == draft.id,
            Draft.firm_id == user.firm_id,
            Draft.status == "DRAFT_READY",
            Draft.content_sha256 == approval.content_sha256,
        )
        .values(status="APPROVED")
    )
    if claimed.rowcount != 1:
        raise ValueError("Draft changed or is no longer ready for approval")
    number = quote.current_version + 1
    applied_ops = [{**op, "status": "APPLIED"} for op in draft.ops]
    version = QuoteVersion(
        id=uid(),
        firm_id=user.firm_id,
        quote_id=quote.id,
        number=number,
        base_version=quote.current_version or None,
        rate_card_id=quote.rate_card_id,
        content_sha256=draft.content_sha256,
        lines=draft.lines,
        total_paise=draft.total_paise,
        status="APPROVED",
        change_summary=applied_ops,
        created_by=user.id,
    )
    session.add(version)
    quote.current_version = number
    draft.ops = applied_ops
    approval.used_at = now_utc()
    action = "INITIAL_QUOTE_APPROVED" if number == 1 else "REVISION_APPROVED"
    audit(session, user.firm_id, user.id, action, version.id, draft.content_sha256)
    queued_pdf = queue_simulated_pdf(session, user, quote, version)
    session.commit()
    pdf_path = queued_pdf or f"/api/versions/{version.id}/pdf"
    if queued_pdf is None and write_pdf and number > 1:
        pdf_path = make_pdf(version, "Demo Interiors", "Sharma Residence")
    return {
        "version_id": version.id,
        "version": number,
        "total": format_inr(version.total_paise),
        "total_paise": version.total_paise,
        "pdf_path": pdf_path,
    }


def queue_simulated_pdf(
    session: Session, user: User, quote: Quote, version: QuoteVersion
) -> str | None:
    chat = session.scalar(
        select(SimulatedChat).where(
            SimulatedChat.firm_id == user.firm_id,
            SimulatedChat.project_id == quote.project_id,
        )
    )
    if chat is None:
        return None
    if chat.rate_card_id != version.rate_card_id:
        raise ValueError("The approved version must use the chat's verified rate card")
    project = require_project(session, user, chat.project_id)
    firm = session.scalar(
        select(Firm).where(Firm.id == user.firm_id, Firm.illustrative.is_(True))
    )
    if firm is None:
        raise ValueError("Simulated quote delivery requires a fictional firm")
    document = render_pdf(version, firm.name, project.name)
    session.add(
        SimulatedQuoteDelivery(
            firm_id=user.firm_id,
            chat_id=chat.id,
            version_id=version.id,
            quote_sha256=version.content_sha256,
            pdf_sha256=hashlib.sha256(document).hexdigest(),
            pdf_bytes=document,
        )
    )
    audit(session, user.firm_id, user.id, "SIMULATED_QUOTE_QUEUED", version.id, chat.id)
    return f"/api/simulated-whatsapp/chats/{chat.id}/quotes/{version.id}/pdf"


def versions(session: Session, user: User, project_id: str) -> list[dict[str, Any]]:
    project = require_project(session, user, project_id)
    quote = session.scalar(
        select(Quote).where(Quote.project_id == project.id, Quote.firm_id == user.firm_id)
    )
    if not quote:
        return []
    items = session.scalars(
        select(QuoteVersion)
        .where(QuoteVersion.quote_id == quote.id, QuoteVersion.firm_id == user.firm_id)
        .order_by(QuoteVersion.number)
    ).all()
    return [
        {
            "version": v.number,
            "status": v.status,
            "total": format_inr(v.total_paise),
            "total_paise": v.total_paise,
            "created_at": v.created_at.isoformat(),
            "pdf_path": f"/api/versions/{v.id}/pdf",
        }
        for v in items
    ]


def project_memory(session: Session, user: User, project_id: str) -> dict[str, Any]:
    project = require_project(session, user, project_id)
    since = now_utc() - timedelta(days=7)
    drafts = session.scalars(
        select(Draft).where(
            Draft.project_id == project.id,
            Draft.firm_id == user.firm_id,
            Draft.created_at >= since,
        )
    ).all()
    ops = [op for draft in drafts for op in draft.ops]
    return {
        "project": project.name,
        "period": "last 7 days (demo timestamps are synthetic)",
        "requested": len(ops),
        "included": sum(op.get("status") == "APPLIED" for op in ops),
        "pending": sum(op.get("status") in {"NEEDS_INFO", "VERIFIED"} for op in ops),
        "rejected": sum(op.get("status") == "REJECTED" for op in ops),
        "records": [
            {"operation": op["op"], "target": op.get("target_text"), "status": op.get("status")}
            for op in ops
        ],
    }


def make_pdf(version: QuoteVersion, firm_name: str, project_name: str) -> str:
    output_dir = Path(os.getenv("QSHIFT_OUTPUT_DIR", "demo-output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{project_name.lower().replace(' ', '-')}-quote-v{version.number}.pdf"
    path.write_bytes(render_pdf(version, firm_name, project_name))
    return str(path)


def render_pdf(
    version: QuoteVersion, firm_name: str, project_name: str, *, fictional_test: bool = False
) -> bytes:
    output = io.BytesIO()
    pdf = canvas.Canvas(output, pagesize=A4)
    width, height = A4
    # Use an installed Noto Sans font when available; built-in fallback keeps offline demo usable.
    bundled_font = Path(__file__).parent / "assets" / "NotoSans.ttf"
    font_path = next(
        (
            p
            for p in [
                str(bundled_font),
                "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
                "/Library/Fonts/NotoSans-Regular.ttf",
                str(Path.home() / "Library/Fonts/NotoSans-Regular.ttf"),
            ]
            if Path(p).exists()
        ),
        None,
    )
    if font_path:
        pdfmetrics.registerFont(TTFont("QshiftNoto", font_path))
        font = "QshiftNoto"
    else:
        font = "Helvetica"
    pdf.setTitle(f"{project_name} quotation v{version.number} — Qshift")
    pdf.setFont(font, 18)
    pdf.drawString(48, height - 52, "QSHIFT  |  Make Every Change Count")
    pdf.setFont(font, 12)
    pdf.drawString(48, height - 82, f"{firm_name} — {project_name}")
    pdf.drawString(48, height - 102, f"APPROVED QUOTATION · Version {version.number}")
    y = height - 140
    pdf.setFont(font, 9)
    pdf.drawString(48, y, "Room / Item")
    pdf.drawString(330, y, "Qty")
    pdf.drawString(390, y, "Unit rate")
    pdf.drawRightString(width - 48, y, "Amount")
    y -= 18
    for line in version.lines:
        if y < 90:
            pdf.showPage()
            y = height - 50
            pdf.setFont(font, 9)
        label = f"{line['room']} — {line['description']}"
        pdf.drawString(48, y, label[:55])
        pdf.drawString(330, y, f"{line['quantity']} {line['unit']}")
        pdf.drawString(390, y, format_inr(int(line["rate_paise"])))
        pdf.drawRightString(width - 48, y, format_inr(int(line["total_paise"])))
        y -= 16
    y -= 16
    pdf.setFont(font, 9)
    subtotal = sum(int(line["total_paise"]) for line in version.lines)
    pdf.drawRightString(width - 48, y, f"Subtotal: {format_inr(subtotal)}")
    y -= 14
    for slab, tax in sorted(gst_by_slab(version.lines).items()):
        if tax:
            rate_label = f"{Decimal(slab) / Decimal(100):.2f}%"
            pdf.drawRightString(width - 48, y, f"GST {rate_label}: {format_inr(tax)}")
            y -= 14
    pdf.setFont(font, 12)
    pdf.drawRightString(width - 48, y, f"Total: {format_inr(version.total_paise)}")
    pdf.setFont(font, 8)
    if fictional_test:
        pdf.drawString(48, 61, "FICTIONAL WHATSAPP PILOT ONLY - NOT A BILLABLE QUOTE")
    pdf.drawString(
        48,
        45,
        "Quotation only, not a tax invoice. Subject to site verification. Rounding: half up to the nearest paise.",
    )
    pdf.save()
    return output.getvalue()
