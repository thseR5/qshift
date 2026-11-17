"""Preview or deliver queued staff pilot replies. Live delivery is opt-in."""

import argparse
import http.client
import json
import logging
import os
import re
import secrets
import sqlite3
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from qshift.agent.local_model import LocalModelUnavailable
from qshift.db import engine
from qshift.models import Draft, Quote, QuoteVersion, now_utc
from qshift.services import canonical_hash, render_pdf
from qshift.whatsapp_pilot import (
    PILOT_FIRM,
    enrollment_key,
    process_next_incoming,
    read_credentials,
    require_database_setting,
    require_fictional_designer,
    require_fictional_staff,
)
from qshift.whatsapp_store import Conversation, Receipt, lock_conversation
from qshift.whatsapp_webhook import WebhookCredentials

REPLY_WINDOW = timedelta(hours=24)
TIMEOUT_SECONDS = 10
MIN_WINDOW_REMAINING = timedelta(seconds=15)
MAX_REPLY_CHARS = 4096
PILOT_PREFIX = (
    "QShift staff pilot · AI-assisted draft · fictional data. Drafts require human approval.\n"
)


class DeliveryError(Exception):
    """A sanitized failure suitable for operator logs."""


def reply_text(body: str) -> str:
    text = PILOT_PREFIX + body
    if len(text) > MAX_REPLY_CHARS:
        return text[: MAX_REPLY_CHARS - 1] + "…"
    return text


def meta_config() -> tuple[str, str]:
    if os.getenv("QSHIFT_WHATSAPP_SEND_ENABLED") != "true":
        raise RuntimeError("Live reply delivery is disabled")
    token = os.getenv("QSHIFT_WHATSAPP_ACCESS_TOKEN", "")
    version = os.getenv("QSHIFT_WHATSAPP_GRAPH_VERSION", "")
    if re.fullmatch(r"[!-~]+", token) is None:
        raise RuntimeError("Set the pilot access token in the private environment")
    if re.fullmatch(r"v[0-9]+\.[0-9]+", version) is None:
        raise RuntimeError("Set a Graph API version supported by your Meta app")
    return token, version


def meta_request(path: str, token: str, body: bytes, content_type: str) -> dict:
    connection = http.client.HTTPSConnection("graph.facebook.com", timeout=TIMEOUT_SECONDS)
    try:
        connection.request(
            "POST",
            path,
            body=body,
            headers={"Authorization": f"Bearer {token}", "Content-Type": content_type},
        )
        response = connection.getresponse()
        if not 200 <= response.status < 300:
            raise DeliveryError(f"Meta returned HTTP {response.status}")
        try:
            data = json.loads(response.read(65536))
        except ValueError as exc:
            raise DeliveryError("Meta response did not confirm acceptance") from exc
        if not isinstance(data, dict):
            raise DeliveryError("Meta response did not confirm acceptance")
        return data
    except (OSError, http.client.HTTPException) as exc:
        raise DeliveryError("Meta transport failed or the outcome is unknown") from exc
    finally:
        connection.close()


def send_message(credentials: WebhookCredentials, token: str, version: str, message: dict) -> None:
    payload = json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": credentials.sender_id,
            **message,
        },
        ensure_ascii=False,
    ).encode()
    result = meta_request(
        f"/{version}/{credentials.phone_number_id}/messages", token, payload, "application/json"
    )
    try:
        message_id = result["messages"][0]["id"]
    except (KeyError, IndexError, TypeError) as exc:
        raise DeliveryError("Meta response did not confirm acceptance") from exc
    if not isinstance(message_id, str) or not message_id.startswith("wamid."):
        raise DeliveryError("Meta response did not confirm acceptance")


def meta_sender(credentials: WebhookCredentials) -> Callable[[str], None]:
    token, version = meta_config()

    def send(text: str) -> None:
        send_message(
            credentials,
            token,
            version,
            {
                "type": "text",
                "text": {"body": text, "preview_url": False},
            },
        )

    return send


def meta_document_sender(credentials: WebhookCredentials) -> Callable[[bytes], None]:
    token, version = meta_config()
    filename = "QShift-fictional-pilot-quote.pdf"

    def send(pdf: bytes) -> None:
        boundary = secrets.token_hex(24)
        body = (
            (
                f'--{boundary}\r\nContent-Disposition: form-data; name="messaging_product"\r\n'
                f'\r\nwhatsapp\r\n--{boundary}\r\nContent-Disposition: form-data; name="type"\r\n'
                f"\r\napplication/pdf\r\n--{boundary}\r\nContent-Disposition: form-data; "
                f'name="file"; filename="{filename}"\r\nContent-Type: application/pdf\r\n\r\n'
            ).encode()
            + pdf
            + f"\r\n--{boundary}--\r\n".encode()
        )
        result = meta_request(
            f"/{version}/{credentials.phone_number_id}/media",
            token,
            body,
            f"multipart/form-data; boundary={boundary}",
        )
        media_id = result.get("id")
        if not isinstance(media_id, str) or not re.fullmatch(r"[0-9]+", media_id):
            raise DeliveryError("Meta response did not confirm the PDF upload")
        send_message(
            credentials,
            token,
            version,
            {
                "type": "document",
                "document": {
                    "id": media_id,
                    "filename": filename,
                    "caption": "QShift staff pilot · Human-approved fictional estimate.",
                },
            },
        )

    return send


def approved_first_quote(
    session: Session, conversation: Conversation, content_hash: str
) -> QuoteVersion | None:
    return session.scalar(
        select(QuoteVersion)
        .join(Quote, (Quote.id == QuoteVersion.quote_id) & (Quote.firm_id == QuoteVersion.firm_id))
        .join(Draft, (Draft.quote_id == Quote.id) & (Draft.firm_id == Quote.firm_id))
        .where(
            QuoteVersion.firm_id == conversation.firm_id,
            Quote.project_id == conversation.project_id,
            Quote.current_version == 1,
            QuoteVersion.number == 1,
            QuoteVersion.status == "APPROVED",
            QuoteVersion.content_sha256 == content_hash,
            Draft.id == conversation.draft_id,
            Draft.status == "APPROVED",
            Draft.content_sha256 == content_hash,
        )
    )


def deliver_first_quote(
    database: Engine,
    credentials: WebhookCredentials,
    content_hash: str,
    send: Callable[[bytes], None],
) -> str:
    identity = (PILOT_FIRM, enrollment_key(credentials))
    with Session(database) as session, session.begin():
        conversation = lock_conversation(session, identity)
        now = now_utc()
        if (
            conversation is None
            or conversation.document_state != "pending"
            or not conversation.has_active_consent(now + 2 * MIN_WINDOW_REMAINING)
        ):
            raise ValueError("No eligible first quote or a PDF attempt already exists.")
        require_fictional_designer(session)
        version = approved_first_quote(session, conversation, content_hash)
        if version is None or canonical_hash(version.lines) != content_hash:
            raise ValueError("Approve the exact fictional quote before delivery.")
        recent = session.scalar(
            select(Receipt.message_hash)
            .where(
                Receipt.firm_id == identity[0],
                Receipt.enrollment_key == identity[1],
                Receipt.source_sent_at > now - REPLY_WINDOW + 2 * MIN_WINDOW_REMAINING,
                Receipt.source_sent_at <= now,
            )
            .limit(1)
        )
        if recent is None:
            raise ValueError("Ask the tester to message again to open the reply window.")
        pdf = render_pdf(
            version, "QShift Test Studio", "Maple Apartment (fictional)", fictional_test=True
        )
        conversation.document_state = "attempted"

    # Commit the attempt before contacting Meta. Hold the enrollment lock during
    # the API call so a processed opt-out and a document send cannot cross.
    with Session(database) as session, session.begin():
        conversation = lock_conversation(session, identity)
        assert conversation is not None
        if not conversation.has_active_consent(now_utc() + 2 * MIN_WINDOW_REMAINING):
            state = "suppressed"
        else:
            try:
                send(pdf)
            except DeliveryError as exc:
                logging.warning("WhatsApp PDF needs review: %s", exc)
                state = "needs_review"
            else:
                state = "accepted"
        conversation.document_state = state
    return state


def deliver_pending_pdf(
    database: Engine,
    credentials: WebhookCredentials,
    send: Callable[[bytes], None],
) -> str:
    """Deliver the exact human-approved revision queued by the WhatsApp agent.

    This is deliberately separate from text reply delivery. The version ID is
    stored on the tenant-scoped conversation after ``approve <token>`` and is
    never inferred from a chat message such as ``yes``.
    """

    identity = (PILOT_FIRM, enrollment_key(credentials))
    with Session(database) as session, session.begin():
        conversation = lock_conversation(session, identity)
        now = now_utc()
        if (
            conversation is None
            or conversation.document_state != "approved_pending"
            or not conversation.pending_version_id
            or not conversation.has_active_consent(now + 2 * MIN_WINDOW_REMAINING)
        ):
            raise ValueError("No human-approved WhatsApp PDF is queued for delivery.")
        require_fictional_staff(session, conversation)
        version = session.scalar(
            select(QuoteVersion).where(
                QuoteVersion.id == conversation.pending_version_id,
                QuoteVersion.firm_id == conversation.firm_id,
                QuoteVersion.status == "APPROVED",
            )
        )
        if version is None:
            raise ValueError("The approved quotation version is unavailable.")
        quote = session.scalar(
            select(Quote).where(
                Quote.id == version.quote_id,
                Quote.firm_id == conversation.firm_id,
                Quote.project_id == conversation.project_id,
            )
        )
        if quote is None:
            raise ValueError("The approved quotation is not bound to this project.")
        pdf = render_pdf(
            version,
            "QShift Test Studio",
            "Fictional project",
            fictional_test=True,
        )
        conversation.document_state = "attempted"

    # Mark the attempt before transport. An unknown timeout is never retried
    # automatically, preserving replay safety for document sends.
    with Session(database) as session:
        conversation = session.get(Conversation, identity)
        authorized = conversation is not None and conversation.has_active_consent(
            now_utc() + 2 * MIN_WINDOW_REMAINING
        )
    if not authorized:
        state = "suppressed"
    else:
        try:
            send(pdf)
        except DeliveryError as exc:
            logging.warning("WhatsApp approved PDF needs review: %s", exc)
            state = "needs_review"
        else:
            state = "accepted"
    with Session(database) as session, session.begin():
        conversation = session.get(Conversation, identity)
        if conversation is not None:
            conversation.document_state = state
    return state


def ready_replies(identity: tuple[str, str], now: datetime):
    return (
        select(Receipt)
        .where(
            Receipt.firm_id == identity[0],
            Receipt.enrollment_key == identity[1],
            Receipt.delivery_state == "ready",
            Receipt.source_sent_at > now - REPLY_WINDOW + MIN_WINDOW_REMAINING,
            Receipt.source_sent_at <= now,
        )
        .order_by(Receipt.created_at, Receipt.message_hash)
    )


def deliver_next(
    database: Engine, credentials: WebhookCredentials, send: Callable[[str], None]
) -> str | None:
    identity = (PILOT_FIRM, enrollment_key(credentials))
    with Session(database) as session:
        if session.scalar(ready_replies(identity, now_utc()).limit(1)) is None:
            return None
    with Session(database) as session, session.begin():
        conversation = lock_conversation(session, identity)
        if conversation is None or not conversation.has_active_consent(now_utc()):
            return None
        require_fictional_designer(session)
        receipt = session.scalars(ready_replies(identity, now_utc()).limit(1)).first()
        if receipt is None:
            return None
        receipt.delivery_state = "attempted"
        receipt_key = (*identity, receipt.message_hash)
        text = reply_text(receipt.reply)
        source_sent_at = receipt.source_sent_at
        assert source_sent_at is not None
        if source_sent_at.tzinfo is None:
            source_sent_at = source_sent_at.replace(tzinfo=UTC)

    # The attempt is committed before the request. A crash or timeout can
    # leave an uncertain outcome, so the worker never retries that receipt.
    with Session(database) as session:
        conversation = session.get(Conversation, identity)
        now = now_utc()
        authorized = conversation is not None and conversation.has_active_consent(now)
    if not authorized or now + MIN_WINDOW_REMAINING >= source_sent_at + REPLY_WINDOW:
        state = "suppressed"
    else:
        try:
            send(text)
        except DeliveryError as exc:
            logging.warning("WhatsApp reply needs review: %s", exc)
            state = "needs_review"
        else:
            state = "accepted"

    with Session(database) as session, session.begin():
        receipt = session.get(Receipt, receipt_key)
        if receipt is not None:
            receipt.delivery_state = state
    return state


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview or deliver replies for one pilot sender")
    parser.add_argument(
        "command", choices=["preview", "run", "document", "document-pending"], nargs="?", default="preview"
    )
    parser.add_argument("--once", action="store_true", help="Process at most one reply in run mode")
    parser.add_argument("--hash", help="Exact content hash from the human-approved quote")
    args = parser.parse_args()
    require_database_setting()
    credentials = read_credentials()
    if args.command == "document-pending":
        try:
            state = deliver_pending_pdf(engine, credentials, meta_document_sender(credentials))
        except ValueError as exc:
            parser.error(str(exc))
        print(f"Pilot approved PDF state: {state}. The tester should confirm receipt in WhatsApp.")
        return
    if args.command == "document":
        if not re.fullmatch(r"[a-f0-9]{64}", args.hash or ""):
            parser.error("document requires the exact --hash shown in review")
        try:
            state = deliver_first_quote(
                engine, credentials, args.hash, meta_document_sender(credentials)
            )
        except ValueError as exc:
            parser.error(str(exc))
        print(f"Pilot PDF state: {state}. The tester should confirm receipt in WhatsApp.")
        return
    if args.command == "preview":
        identity = (PILOT_FIRM, enrollment_key(credentials))
        with Session(engine) as session:
            require_fictional_designer(session)
            conversation = session.get(Conversation, identity)
            receipts = (
                session.scalars(ready_replies(identity, now_utc()).limit(10)).all()
                if conversation and conversation.has_active_consent(now_utc())
                else []
            )
            for receipt in receipts:
                print(reply_text(receipt.reply))
            print(f"Previewed {len(receipts)} eligible replies.")
        return

    send = meta_sender(credentials)
    while True:
        try:
            state = deliver_next(engine, credentials, send)
            if state is None and process_next_incoming(engine, credentials):
                state = deliver_next(engine, credentials, send)
        except LocalModelUnavailable:
            logging.warning("Local extraction unavailable. Incoming pilot message remains queued.")
            if args.once:
                return
            time.sleep(5)
            continue
        except OperationalError as exc:
            code = getattr(exc.orig, "sqlite_errorcode", 0) or 0
            if engine.dialect.name != "sqlite" or code & 0xFF not in {
                sqlite3.SQLITE_BUSY,
                sqlite3.SQLITE_LOCKED,
            }:
                raise
            if args.once:
                print("Pilot database is busy. Retry after the current intake finishes.")
                return
            time.sleep(1)
            continue
        if state is not None:
            print(f"Pilot reply state: {state}", flush=True)
        if args.once:
            break
        if state is None:
            time.sleep(1)


if __name__ == "__main__":
    main()
