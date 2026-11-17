"""Local client webhook and PDF delivery. This module has no external transport."""

import hashlib
import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from qshift.agent.itemized import CEILING, WARDROBE
from qshift.intake import add_client_message, intake_view, start_project_intake, start_sample
from qshift.models import (
    Firm,
    RateCard,
    RateEntry,
    SimulatedChat,
    SimulatedQuoteDelivery,
    SimulatedReceipt,
    User,
)
from qshift.services import hash_text, uid
from qshift.whatsapp_webhook import Event, Message


@dataclass(frozen=True)
class SimulatedEvent:
    chat_id: str
    event_id: str
    text: str


def create_chat(
    session: Session,
    user: User,
    rate_card_id: str,
    project_id: str | None = None,
) -> dict:
    if (
        session.scalar(select(Firm.id).where(Firm.id == user.firm_id, Firm.illustrative.is_(True)))
        is None
    ):
        raise LookupError("Fictional studio not found")
    card = session.scalar(
        select(RateCard).where(RateCard.id == rate_card_id, RateCard.firm_id == user.firm_id)
    )
    if card is None:
        raise LookupError("Rate card not found")
    verified = set(
        session.scalars(
            select(RateEntry.sku).where(
                RateEntry.firm_id == user.firm_id,
                RateEntry.rate_card_id == card.id,
                RateEntry.verified.is_(True),
                RateEntry.unit == "sqft",
                RateEntry.sku.in_([WARDROBE, CEILING]),
            )
        )
    )
    if verified != {WARDROBE, CEILING}:
        raise ValueError("Verify both sample rates on the selected card before starting the chat.")
    if project_id is None:
        project_id = start_sample(session, user, "itemized", commit=False)["project_id"]
    else:
        start_project_intake(session, user, project_id)
    session.add(
        SimulatedChat(
            id=uid(),
            firm_id=user.firm_id,
            project_id=project_id,
            rate_card_id=card.id,
        )
    )
    session.flush()
    session.commit()
    return intake_view(session, user, project_id)


def parse_event(event: Event) -> SimulatedEvent:
    if event.object != "whatsapp_business_account" or len(event.entry) != 1:
        raise ValueError("Send one simulated WhatsApp message event.")
    entry = event.entry[0]
    if entry.id != "qshift-sim-account" or len(entry.changes) != 1:
        raise ValueError("Use the fictional QShift account and exactly one message change.")
    change = entry.changes[0]
    value = change.value
    if (
        change.field != "messages"
        or value.metadata is None
        or value.metadata.phone_number_id != "qshift-sim-number"
        or len(value.messages) != 1
    ):
        raise ValueError("Use the fictional QShift number and exactly one inbound message.")
    raw = value.messages[0]
    if raw.get("type") != "text":
        raise ValueError("Only simulated text messages are currently supported.")
    message = Message.model_validate(raw)
    sender = raw.get("from")
    if not isinstance(sender, str) or not re.fullmatch(r"sim-client-[0-9a-f-]{36}", sender):
        raise ValueError("Use the simulator's fictional client identity.")
    if not re.fullmatch(r"sim-msg-[0-9a-f-]{36}", message.id):
        raise ValueError("Use a simulator-generated message ID.")
    text = message.text.body.strip()
    if not 0 < len(text) <= 1000:
        raise ValueError("Enter up to 1,000 characters of fictional text.")
    return SimulatedEvent(sender.removeprefix("sim-client-"), message.id, text)


def receive_event(session: Session, user: User, event: SimulatedEvent) -> dict:
    chat = session.get(SimulatedChat, (user.firm_id, event.chat_id))
    if chat is None:
        raise LookupError("Simulated conversation not found")
    if (previous := replay(session, user, event)) is not None:
        return previous
    result = add_client_message(session, user, chat.project_id, event.text, commit=False, chat=chat)
    session.add(
        SimulatedReceipt(
            firm_id=user.firm_id,
            chat_id=chat.id,
            event_id=event.event_id,
            body_sha256=hash_text(event.text),
        )
    )
    session.commit()
    return {**result, "duplicate": False}


def replay(session: Session, user: User, event: SimulatedEvent) -> dict | None:
    receipt = session.get(SimulatedReceipt, (user.firm_id, event.chat_id, event.event_id))
    if receipt is None:
        return None
    if receipt.body_sha256 != hash_text(event.text):
        raise ValueError("This event ID is already bound to a different message.")
    chat = session.get(SimulatedChat, (user.firm_id, event.chat_id))
    if chat is None:
        raise LookupError("Simulated conversation not found")
    return {**intake_view(session, user, chat.project_id), "duplicate": True}


def delivery_pdf(
    session: Session, user: User, chat_id: str, version_id: str
) -> SimulatedQuoteDelivery:
    delivery = session.get(SimulatedQuoteDelivery, (user.firm_id, chat_id, version_id))
    if delivery is None:
        raise LookupError("Approved PDF not found in this simulated conversation")
    if hashlib.sha256(delivery.pdf_bytes).hexdigest() != delivery.pdf_sha256:
        raise ValueError("Stored PDF verification failed")
    return delivery
