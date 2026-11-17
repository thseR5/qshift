"""Signed WhatsApp receiver for one enrolled staff member and fictional data."""

import argparse
import os
import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from qshift.agent.chat import respond_to_message
from qshift.agent.local_model import LocalModelUnavailable
from qshift.db import engine
from qshift.intake import add_client_message, start_sample
from qshift.models import Draft, Firm, User, now_utc
from qshift.services import approve_draft, hash_text, issue_approval_token, seed_demo
from qshift.whatsapp_store import Conversation, Receipt, lock_conversation
from qshift.whatsapp_webhook import IncomingText, WebhookCredentials, webhook_routes

PILOT_FIRM = "firm-demo"
PILOT_DESIGNER = "user-designer"
OPT_OUT_COMMANDS = {"stop", "unsubscribe", "opt out"}


def read_credentials() -> WebhookCredentials:
    if os.getenv("QSHIFT_WHATSAPP_RECEIVE_ENABLED") != "true":
        raise RuntimeError("Set QSHIFT_WHATSAPP_RECEIVE_ENABLED=true to start the receive pilot")

    def numeric_id(name: str) -> str:
        value = os.getenv(name, "")
        if re.fullmatch(r"[0-9]{5,32}", value) is None:
            raise RuntimeError(f"{name} must be a numeric ID without spaces or a plus sign")
        return value

    app_secret = os.getenv("QSHIFT_WHATSAPP_APP_SECRET", "").encode()
    verify_token = os.getenv("QSHIFT_WHATSAPP_VERIFY_TOKEN", "").encode()
    if len(app_secret) < 16 or len(verify_token) < 24 or app_secret == verify_token:
        raise RuntimeError("Set a Meta app secret and a separate random webhook verification token")
    return WebhookCredentials(
        account_id=numeric_id("QSHIFT_WHATSAPP_ACCOUNT_ID"),
        phone_number_id=numeric_id("QSHIFT_WHATSAPP_PHONE_NUMBER_ID"),
        sender_id=numeric_id("QSHIFT_WHATSAPP_STAFF_SENDER_ID"),
        app_secret=app_secret,
        verify_token=verify_token,
    )


def enrollment_key(credentials: WebhookCredentials) -> str:
    scope = f"{credentials.account_id}:{credentials.phone_number_id}:{credentials.sender_id}"
    return hash_text(scope)


def require_fictional_designer(session: Session) -> User:
    user = session.scalar(
        select(User)
        .join(Firm, Firm.id == User.firm_id)
        .where(
            User.id == PILOT_DESIGNER,
            User.firm_id == PILOT_FIRM,
            User.role == "DESIGNER",
            Firm.illustrative.is_(True),
        )
    )
    if user is None:
        raise RuntimeError("The receive pilot requires the seeded fictional designer and firm")
    return user


def capture_reply(session: Session, user: User, conversation: Conversation, message: str) -> str:
    try:
        with session.begin_nested():
            result = respond_to_message(
                session,
                user,
                message,
                conversation.project_id,
                conversation.draft_id,
                commit=False,
            )
    except (LookupError, ValueError) as exc:
        return str(exc)

    selected = result.get("project_id")
    if selected and selected != conversation.project_id:
        conversation.project_id = selected
        conversation.draft_id = None
    if "draft" in result:
        conversation.draft_id = result["draft"]["id"]
    if result.get("reply", "").startswith("Cancelled the open draft"):
        conversation.draft_id = None
    return result["reply"]


def record_staff_consent(
    database: Engine, credentials: WebhookCredentials, reference: str, *, first_quote: bool = False
) -> None:
    if re.fullmatch(r"[A-Za-z0-9_-]{1,64}", reference) is None:
        raise ValueError("Use a short, non-identifying consent reference, such as CONSENT-001")
    insert = {"sqlite": sqlite_insert, "postgresql": postgresql_insert}.get(database.dialect.name)
    if insert is None:
        raise ValueError("The receive pilot supports SQLite and PostgreSQL")
    identity = (PILOT_FIRM, enrollment_key(credentials))
    with Session(database) as session, session.begin():
        session.execute(
            insert(Conversation)
            .values(firm_id=identity[0], enrollment_key=identity[1])
            .on_conflict_do_nothing(index_elements=["firm_id", "enrollment_key"])
        )
        user = require_fictional_designer(session)
        conversation = lock_conversation(session, identity)
        assert conversation is not None
        if conversation.delivery_opted_out or conversation.consent_recorded_at is not None:
            raise ValueError("This pilot enrollment is already recorded or opted out")
        conversation.consent_reference = reference
        conversation.consent_recorded_at = now_utc()
        if first_quote:
            conversation.project_id = start_sample(session, user, commit=False)["project_id"]
            conversation.document_state = "pending"


def suppress_ready_replies(session: Session, identity: tuple[str, str]) -> None:
    session.execute(
        update(Receipt)
        .where(
            Receipt.firm_id == identity[0],
            Receipt.enrollment_key == identity[1],
            Receipt.delivery_state.in_(["queued", "ready"]),
        )
        .values(delivery_state="suppressed", inbound_text=None)
    )


def pilot_reply(session: Session, user: User, conversation: Conversation, message: str) -> str:
    if conversation.document_state is None:
        return capture_reply(session, user, conversation, message)
    if conversation.draft_id:
        return "Your fictional quote is with the designer for review."
    assert conversation.project_id is not None
    try:
        with session.begin_nested():
            result = add_client_message(
                session, user, conversation.project_id, message, commit=False
            )
    except ValueError:
        return "The designer needs to review this fictional request."
    if result["draft"]:
        conversation.draft_id = result["draft"]["id"]
    return result["messages"][-1]["text"]


def process_next_incoming(database: Engine, credentials: WebhookCredentials) -> bool:
    identity = (PILOT_FIRM, enrollment_key(credentials))
    pending = (
        select(Receipt)
        .where(
            Receipt.firm_id == identity[0],
            Receipt.enrollment_key == identity[1],
            Receipt.delivery_state == "queued",
        )
        .order_by(Receipt.source_sent_at, Receipt.created_at, Receipt.message_hash)
        .limit(1)
    )
    with Session(database) as session:
        if session.scalar(pending) is None:
            return False
    with Session(database) as session, session.begin():
        conversation = lock_conversation(session, identity)
        if conversation is None:
            return False
        if not conversation.has_active_consent(now_utc()):
            suppress_ready_replies(session, identity)
            return True
        receipt = session.scalar(pending)
        if receipt is None:
            return False
        user = require_fictional_designer(session)
        assert receipt.inbound_text is not None
        receipt.reply = pilot_reply(session, user, conversation, receipt.inbound_text)
        receipt.inbound_text = None
        receipt.delivery_state = "ready" if receipt.reply else "captured"
        return True


def create_receive_app(
    credentials: WebhookCredentials,
    database: Engine,
    *,
    health_endpoint: bool = True,
    durable_inbox: bool = False,
) -> FastAPI:
    identity = (PILOT_FIRM, enrollment_key(credentials))

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        with Session(database) as session:
            require_fictional_designer(session)
            session.get(Conversation, identity)
            session.scalar(
                select(Receipt.inbound_text)
                .where(Receipt.firm_id == identity[0], Receipt.enrollment_key == identity[1])
                .limit(1)
            )
        yield

    def handle_messages(messages: list[IncomingText]) -> None:
        with Session(database) as session, session.begin():
            conversation = lock_conversation(session, identity)
            if conversation is None or conversation.delivery_opted_out:
                return
            start = conversation.consent_start()
            if start is None:
                return
            user = require_fictional_designer(session)

            for message in messages:
                if message.body.casefold() in OPT_OUT_COMMANDS:
                    conversation.delivery_opted_out = True
                    suppress_ready_replies(session, identity)
                    return
                now = now_utc()
                if not conversation.has_active_consent(now):
                    continue
                if (
                    message.sent_at is None
                    or not start.replace(microsecond=0) <= message.sent_at <= now
                ):
                    continue
                digest = hash_text(message.message_id)
                if session.get(Receipt, (*identity, digest)) is not None:
                    continue
                try:
                    reply = (
                        ""
                        if durable_inbox
                        else pilot_reply(session, user, conversation, message.body)
                    )
                except LocalModelUnavailable:
                    raise HTTPException(503, "Local extraction unavailable") from None
                state = "ready" if reply else "captured"
                if durable_inbox:
                    state = "queued"
                session.add(
                    Receipt(
                        firm_id=identity[0],
                        enrollment_key=identity[1],
                        message_hash=digest,
                        reply=reply,
                        source_sent_at=message.sent_at,
                        delivery_state=state,
                        inbound_text=message.body if durable_inbox else None,
                    )
                )
                session.flush()

    app = FastAPI(
        title="QShift WhatsApp receive pilot",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    def health() -> dict[str, str]:
        try:
            with database.connect() as connection:
                connection.execute(select(1))
        except SQLAlchemyError:
            raise HTTPException(503, "Pilot database unavailable") from None
        return {"status": "ok"}

    if health_endpoint:
        app.add_api_route("/healthz", health, include_in_schema=False)
    app.include_router(webhook_routes(credentials, handle_messages))
    return app


def require_database_setting() -> None:
    if not os.getenv("DATABASE_URL"):
        raise RuntimeError("Set DATABASE_URL to a dedicated, migrated pilot database")


def create_app() -> FastAPI:
    """Uvicorn factory. Disabled unless the operator explicitly enables it."""
    require_database_setting()
    return create_receive_app(
        read_credentials(),
        engine,
        health_endpoint=os.getenv("QSHIFT_PILOT_CALLBACK_ONLY") != "true",
        durable_inbox=os.getenv("QSHIFT_WHATSAPP_DURABLE_INBOX") == "true",
    )


def first_quote_draft(
    session: Session, credentials: WebhookCredentials, *, active: bool = False
) -> Draft | None:
    conversation = session.get(Conversation, (PILOT_FIRM, enrollment_key(credentials)))
    if (
        conversation is None
        or conversation.document_state is None
        or (active and not conversation.has_active_consent(now_utc()))
    ):
        return None
    return session.scalar(
        select(Draft).where(
            Draft.firm_id == PILOT_FIRM,
            Draft.id == conversation.draft_id,
            Draft.project_id == conversation.project_id,
        )
    )


def approve_first_quote(
    session: Session, credentials: WebhookCredentials, content_hash: str
) -> dict:
    draft = first_quote_draft(session, credentials, active=True)
    if draft is None:
        raise ValueError("No draft for this active pilot enrollment.")
    approver = session.scalar(
        select(User)
        .join(Firm, Firm.id == User.firm_id)
        .where(
            User.firm_id == PILOT_FIRM,
            User.id == "user-approver",
            User.role == "APPROVER",
            Firm.illustrative.is_(True),
        )
    )
    if approver is None:
        raise ValueError("The fictional pilot approver does not exist.")
    token = issue_approval_token(session, approver, draft.id, content_hash)
    return approve_draft(session, approver, token, write_pdf=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage the private QShift receive pilot database")
    parser.add_argument("command", choices=["seed", "consent", "replies", "review", "approve"])
    parser.add_argument("--reference", help="Non-identifying reference to the staff opt-in record")
    parser.add_argument("--first-quote", action="store_true")
    parser.add_argument("--hash", help="Exact content hash displayed in review")
    args = parser.parse_args()
    if args.command == "consent" and not args.reference:
        parser.error("consent requires --reference")
    if args.command == "approve" and not re.fullmatch(r"[a-f0-9]{64}", args.hash or ""):
        parser.error("approve requires the exact --hash shown in review")
    require_database_setting()
    if args.command == "consent":
        try:
            record_staff_consent(
                engine, read_credentials(), args.reference, first_quote=args.first_quote
            )
        except ValueError as exc:
            parser.error(str(exc))
        print("Staff consent recorded for this 24-hour pilot.")
        return
    with Session(engine) as session:
        if args.command == "seed":
            seed_demo(session)
            print("Fictional pilot firm is ready.")
            return
        if args.command == "review":
            from qshift.engine.pricing import format_inr

            draft = first_quote_draft(session, read_credentials())
            if draft is None:
                print("Waiting for the tester to complete the fictional brief.")
                return
            print(f"FICTIONAL PILOT · {draft.status}")
            for line in draft.lines:
                print(
                    f"{line['room']} | {line['description']} | {line['quantity']} {line['unit']} "
                    f"× {format_inr(line['rate_paise'])} = {format_inr(line['total_paise'])}"
                )
            print(f"Total: {format_inr(draft.total_paise)}")
            print(f"Content hash: {draft.content_sha256}")
            return
        if args.command == "approve":
            try:
                quote = approve_first_quote(session, read_credentials(), args.hash)
            except (LookupError, PermissionError, ValueError) as exc:
                parser.error(str(exc))
            print(f"Approved fictional quotation v{quote['version']}: {quote['total']}")
            return
        key = enrollment_key(read_credentials())
        replies = session.scalars(
            select(Receipt.reply)
            .where(Receipt.firm_id == PILOT_FIRM, Receipt.enrollment_key == key)
            .order_by(Receipt.created_at.desc())
            .limit(10)
        ).all()
        for reply in reversed(replies):
            print(f"Captured locally: {reply}")
        if not replies:
            print("No captured replies for this enrollment.")


if __name__ == "__main__":
    main()
