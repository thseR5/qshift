"""Exercise the WhatsApp receive path in-process with fictional data."""

import json
from collections.abc import Callable
from contextlib import asynccontextmanager
from threading import Lock

from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from qshift.agent.chat import respond_to_message
from qshift.db import Base
from qshift.models import User
from qshift.services import seed_demo
from qshift.whatsapp_webhook import (
    WEBHOOK_PATH,
    IncomingText,
    WebhookCredentials,
    signature_for,
    webhook_routes,
)

FIXTURE_ACCOUNT = "qshift-fixture-account"
FIXTURE_NUMBER = "qshift-fixture-number"
FIXTURE_SENDER = "qshift-fixture-staff"
FIXTURE_SECRET = b"local-rehearsal-app-secret"
FIXTURE_VERIFY_TOKEN = b"local-rehearsal-verify-token"


def fixture_signature(body: bytes) -> str:
    return signature_for(body, FIXTURE_SECRET)


def create_rehearsal(record_reply: Callable[[str], None]) -> FastAPI:
    """Create an isolated app for the synthetic webhook exercise."""
    db = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    lock = Lock()
    delivered: set[str] = set()
    project_id: str | None = None
    draft_id: str | None = None

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        nonlocal project_id, draft_id
        project_id, draft_id = None, None
        delivered.clear()
        Base.metadata.create_all(db)
        try:
            with Session(db) as session:
                seed_demo(session)
            yield
        finally:
            db.dispose()

    app = FastAPI(title="QShift SIMULATED webhook rehearsal", lifespan=lifespan)

    def handle_messages(messages: list[IncomingText]) -> None:
        nonlocal project_id, draft_id
        with lock, Session(db) as session:
            user = session.get(User, "user-designer")
            if user is None:
                raise RuntimeError("Missing fictional staff identity")
            for message in messages:
                if message.message_id in delivered:
                    continue
                try:
                    result = respond_to_message(session, user, message.body, project_id, draft_id)
                except (LookupError, ValueError) as exc:
                    session.rollback()
                    record_reply(str(exc))
                else:
                    selected = result.get("project_id")
                    if selected and selected != project_id:
                        project_id, draft_id = selected, None
                    if "draft" in result:
                        draft_id = result["draft"]["id"]
                    record_reply(result["reply"])
                delivered.add(message.message_id)

    credentials = WebhookCredentials(
        FIXTURE_ACCOUNT, FIXTURE_NUMBER, FIXTURE_SENDER, FIXTURE_SECRET, FIXTURE_VERIFY_TOKEN
    )
    app.include_router(webhook_routes(credentials, handle_messages))
    return app


def fixture_payload(
    message_id: str,
    text: str,
    *,
    account: str = FIXTURE_ACCOUNT,
    number: str = FIXTURE_NUMBER,
    sender: str = FIXTURE_SENDER,
    timestamp: str | None = None,
) -> bytes:
    message = {"id": message_id, "from": sender, "type": "text", "text": {"body": text}}
    if timestamp is not None:
        message["timestamp"] = timestamp
    value = {
        "metadata": {"phone_number_id": number},
        "messages": [message],
    }
    return json.dumps(
        {
            "object": "whatsapp_business_account",
            "entry": [{"id": account, "changes": [{"field": "messages", "value": value}]}],
        }
    ).encode()


def main() -> None:
    from fastapi.testclient import TestClient

    replies: list[str] = []
    with TestClient(create_rehearsal(replies.append)) as client:
        challenge = client.get(
            WEBHOOK_PATH,
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": FIXTURE_VERIFY_TOKEN.decode(),
                "hub.challenge": "123456",
            },
        )
        challenge.raise_for_status()
        if challenge.text != "123456":
            raise RuntimeError("Webhook challenge was not echoed")
        print("SIMULATED | Webhook challenge passed")
        for index, message in enumerate(
            (
                "use project-sharma",
                "Kitchen lo granite badulu quartz pettandi, bedroom false ceiling remove cheyyandi.",
                "choose COUNTER-QUARTZ-CALACATTA",
            )
        ):
            body = fixture_payload(f"wamid.fixture-{index}", message)
            client.post(
                WEBHOOK_PATH,
                content=body,
                headers={"X-Hub-Signature-256": fixture_signature(body)},
            ).raise_for_status()
            print(f"Staff: {message}\nQShift (captured locally): {replies[-1]}")


if __name__ == "__main__":
    main()
