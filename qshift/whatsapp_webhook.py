"""Inbound WhatsApp webhook protocol shared by the pilot and rehearsal."""

import hashlib
import hmac
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field, ValidationError

WEBHOOK_PATH = "/webhooks/whatsapp"
MAX_PAYLOAD_BYTES = 1024 * 1024


@dataclass(frozen=True)
class WebhookCredentials:
    account_id: str
    phone_number_id: str
    sender_id: str = field(repr=False)
    app_secret: bytes = field(repr=False)
    verify_token: bytes = field(repr=False)


@dataclass(frozen=True)
class IncomingText:
    message_id: str
    body: str
    sent_at: datetime | None = None


class TextBody(BaseModel):
    body: str


class Message(BaseModel):
    id: str = Field(min_length=1, max_length=512)
    text: TextBody
    timestamp: str | None = None


class Metadata(BaseModel):
    phone_number_id: str


class EventValue(BaseModel):
    metadata: Metadata | None = None
    messages: list[dict] = Field(default_factory=list)


class Change(BaseModel):
    field: str
    value: EventValue


class Entry(BaseModel):
    id: str
    changes: list[Change] = Field(default_factory=list)


class Event(BaseModel):
    object: str
    entry: list[Entry] = Field(default_factory=list)


def signature_for(body: bytes, app_secret: bytes) -> str:
    return "sha256=" + hmac.new(app_secret, body, hashlib.sha256).hexdigest()


def provider_time(timestamp: str | None) -> datetime | None:
    if not timestamp or not timestamp.isascii() or not timestamp.isdecimal() or len(timestamp) > 12:
        return None
    try:
        return datetime.fromtimestamp(int(timestamp), tz=UTC)
    except (ValueError, OverflowError, OSError):
        return None


def staff_texts(event: Event, credentials: WebhookCredentials) -> Iterator[IncomingText]:
    if event.object != "whatsapp_business_account":
        return
    for entry in event.entry:
        if entry.id != credentials.account_id:
            continue
        for change in entry.changes:
            value = change.value
            if change.field != "messages" or value.metadata is None:
                continue
            if value.metadata.phone_number_id != credentials.phone_number_id:
                continue
            for raw in value.messages:
                if raw.get("type") != "text" or raw.get("from") != credentials.sender_id:
                    continue
                try:
                    message = Message.model_validate(raw)
                except ValidationError:
                    continue
                body = message.text.body.strip()
                if 0 < len(body) <= 4000:
                    yield IncomingText(message.id, body, provider_time(message.timestamp))


def webhook_routes(
    credentials: WebhookCredentials, handle_messages: Callable[[list[IncomingText]], None]
) -> APIRouter:
    router = APIRouter()

    @router.get(WEBHOOK_PATH, response_class=PlainTextResponse)
    def verify_callback(
        mode: Annotated[str, Query(alias="hub.mode")] = "",
        token: Annotated[str, Query(alias="hub.verify_token")] = "",
        challenge: Annotated[str, Query(alias="hub.challenge")] = "",
    ) -> str:
        if mode != "subscribe" or not hmac.compare_digest(token.encode(), credentials.verify_token):
            raise HTTPException(403, "Webhook verification failed")
        if not challenge:
            raise HTTPException(400, "Missing webhook challenge")
        return challenge

    @router.post(WEBHOOK_PATH)
    async def receive(
        request: Request,
        signature: Annotated[str, Header(alias="X-Hub-Signature-256")] = "",
    ) -> dict[str, bool]:
        body = bytearray()
        async for chunk in request.stream():
            if len(body) + len(chunk) > MAX_PAYLOAD_BYTES:
                raise HTTPException(413, "Webhook payload is too large")
            body.extend(chunk)
        raw = bytes(body)
        if not hmac.compare_digest(
            signature.encode(), signature_for(raw, credentials.app_secret).encode()
        ):
            raise HTTPException(401, "Invalid webhook signature")
        try:
            event = Event.model_validate_json(raw)
        except ValidationError as exc:
            raise HTTPException(400, "Invalid webhook payload") from exc
        messages = list(staff_texts(event, credentials))
        if messages:
            await run_in_threadpool(handle_messages, messages)
        return {"ok": True}

    return router
