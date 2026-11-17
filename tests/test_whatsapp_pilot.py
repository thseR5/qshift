import json
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

import qshift.whatsapp_pilot as pilot
from alembic import command
from qshift import whatsapp_delivery as delivery
from qshift.models import AuditEvent, Draft, Project, RateEntry, now_utc
from qshift.services import seed_demo
from qshift.whatsapp_rehearsal import fixture_payload
from qshift.whatsapp_store import Conversation, Receipt
from qshift.whatsapp_webhook import WEBHOOK_PATH, WebhookCredentials, signature_for

CREDENTIALS = WebhookCredentials(
    account_id="10001",
    phone_number_id="10002",
    sender_id="10003",
    app_secret=b"synthetic-app-secret",
    verify_token=b"synthetic-webhook-verification",
)


@pytest.fixture
def pilot_db(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'pilot.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    config = Config("alembic.ini")
    command.upgrade(config, "0001_initial")
    db = create_engine(url)
    try:
        with Session(db) as session:
            seed_demo(session)
        command.upgrade(config, "head")
        yield db
    finally:
        db.dispose()


@pytest.fixture
def enrolled_db(pilot_db):
    pilot.record_staff_consent(pilot_db, CREDENTIALS, "CONSENT-001")
    return pilot_db


def payload(
    message_id: str,
    text: str,
    *,
    sender: str = CREDENTIALS.sender_id,
    timestamp: str | None = "current",
) -> bytes:
    return fixture_payload(
        message_id,
        text,
        account=CREDENTIALS.account_id,
        number=CREDENTIALS.phone_number_id,
        sender=sender,
        timestamp=str(int(now_utc().timestamp())) if timestamp == "current" else timestamp,
    )


def deliver(client: TestClient, body: bytes) -> None:
    response = client.post(
        WEBHOOK_PATH,
        content=body,
        headers={"X-Hub-Signature-256": signature_for(body, CREDENTIALS.app_secret)},
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_pilot_factory_stays_disabled_by_default(pilot_db, monkeypatch):
    monkeypatch.delenv("QSHIFT_WHATSAPP_RECEIVE_ENABLED", raising=False)
    with pytest.raises(RuntimeError, match="QSHIFT_WHATSAPP_RECEIVE_ENABLED"):
        pilot.create_app()


def test_pilot_keeps_context_and_deduplicates_across_restart(enrolled_db):
    request = payload(
        "wamid.scope",
        "Kitchen lo granite badulu quartz pettandi, bedroom false ceiling remove cheyyandi.",
    )
    with TestClient(pilot.create_receive_app(CREDENTIALS, enrolled_db)) as client:
        assert client.get("/api/demo/seed").status_code == 404
        assert client.get("/docs").status_code == 404
        deliver(client, payload("wamid.unknown", "use project-sharma", sender="99999"))
        with Session(enrolled_db) as session:
            assert session.scalars(select(Conversation)).one().project_id is None
        deliver(client, payload("wamid.project", "use project-sharma"))
        with ThreadPoolExecutor(max_workers=2) as workers:
            deliveries = [workers.submit(deliver, client, request) for _ in range(2)]
            for delivery in deliveries:
                delivery.result()

    enrolled_db.dispose()
    with TestClient(pilot.create_receive_app(CREDENTIALS, enrolled_db)) as client:
        deliver(client, request)
        deliver(client, payload("wamid.choice", "choose COUNTER-QUARTZ-CALACATTA"))

    with Session(enrolled_db) as session:
        draft = session.scalars(select(Draft)).one()
        assert draft.status == "DRAFT_READY"
        assert draft.total_paise == 24_320_000
        replies = session.scalars(select(Receipt.reply)).all()
        assert len(replies) == 3
        assert any("₹2,43,200" in reply for reply in replies)


def test_business_changes_and_receipts_roll_back_together(enrolled_db, monkeypatch):
    original = pilot.respond_to_message

    def fail_second_message(session, user, message, *args, **kwargs):
        if message == "fail":
            raise RuntimeError("simulated processing failure")
        return original(session, user, message, *args, **kwargs)

    monkeypatch.setattr(pilot, "respond_to_message", fail_second_message)
    body = json.loads(payload("wamid.project", "use project-sharma"))
    messages = body["entry"][0]["changes"][0]["value"]["messages"]
    messages.append({**messages[0], "id": "wamid.failure", "text": {"body": "fail"}})
    with TestClient(
        pilot.create_receive_app(CREDENTIALS, enrolled_db), raise_server_exceptions=False
    ) as client:
        raw = json.dumps(body).encode()
        response = client.post(
            WEBHOOK_PATH,
            content=raw,
            headers={"X-Hub-Signature-256": signature_for(raw, CREDENTIALS.app_secret)},
        )
        assert response.status_code == 500

    with Session(enrolled_db) as session:
        assert session.get(Project, "project-sharma").pinned_by is None
        assert session.scalar(select(func.count()).select_from(Receipt)) == 0


def test_two_way_pilot_against_fake_meta_endpoint(enrolled_db, monkeypatch):
    for setting, value in {
        "QSHIFT_WHATSAPP_SEND_ENABLED": "true",
        "QSHIFT_WHATSAPP_ACCESS_TOKEN": "synthetic-access-token",
        "QSHIFT_WHATSAPP_GRAPH_VERSION": "v99.0",
    }.items():
        monkeypatch.setenv(setting, value)
    requests = []

    class Response:
        status = 200

        def read(self, _limit):
            return b'{"messages":[{"id":"wamid.accepted-fixture"}]}'

    class Connection:
        def __init__(self, host, *, timeout):
            assert host == "graph.facebook.com"
            assert timeout > 0

        def request(self, method, path, *, body, headers):
            assert method == "POST"
            assert path == "/v99.0/10002/messages"
            assert headers["Authorization"] == "Bearer synthetic-access-token"
            requests.append(json.loads(body))

        def getresponse(self):
            return Response()

        def close(self):
            pass

    monkeypatch.setattr(delivery.http.client, "HTTPSConnection", Connection)
    sender = delivery.meta_sender(CREDENTIALS)
    timestamp = str(int(now_utc().timestamp()))
    with TestClient(pilot.create_receive_app(CREDENTIALS, enrolled_db)) as client:
        messages = [
            "use project-sharma",
            "Kitchen lo granite badulu quartz pettandi, bedroom false ceiling remove cheyyandi.",
            "choose COUNTER-QUARTZ-CALACATTA",
        ]
        for index, message in enumerate(messages):
            incoming = payload(f"wamid.reply-{index}", message, timestamp=timestamp)
            deliver(client, incoming)
            deliver(client, incoming)
            assert delivery.deliver_next(enrolled_db, CREDENTIALS, sender) == "accepted"
        assert delivery.deliver_next(enrolled_db, CREDENTIALS, sender) is None

    assert len(requests) == 3
    assert {request["to"] for request in requests} == {CREDENTIALS.sender_id}
    assert all(request["type"] == "text" for request in requests)
    assert "choose <SKU>" in requests[1]["text"]["body"]
    assert "₹2,43,200" in requests[2]["text"]["body"]
    assert requests[2]["text"]["body"].startswith(delivery.PILOT_PREFIX)


def test_delivery_requires_recent_timestamp_and_honors_opt_out(enrolled_db, monkeypatch):
    monkeypatch.delenv("QSHIFT_WHATSAPP_SEND_ENABLED", raising=False)
    with pytest.raises(RuntimeError, match="disabled"):
        delivery.meta_sender(CREDENTIALS)

    sent: list[str] = []
    now = now_utc()
    with TestClient(pilot.create_receive_app(CREDENTIALS, enrolled_db)) as client:
        deliver(client, payload("wamid.unknown-time", "projects", timestamp=None))
        deliver(
            client,
            payload(
                "wamid.expired",
                "projects",
                timestamp=str(int((now - timedelta(days=2)).timestamp())),
            ),
        )
        deliver(
            client,
            payload(
                "wamid.future",
                "projects",
                timestamp=str(int((now + timedelta(hours=1)).timestamp())),
            ),
        )
        assert delivery.deliver_next(enrolled_db, CREDENTIALS, sent.append) is None
        timestamp = str(int(now.timestamp()))
        deliver(client, payload("wamid.eligible", "projects", timestamp=timestamp))
        deliver(client, payload("wamid.stop", "STOP", timestamp=timestamp))
        deliver(client, payload("wamid.after-stop", "use project-sharma", timestamp=timestamp))
        assert delivery.deliver_next(enrolled_db, CREDENTIALS, sent.append) is None
    assert sent == []
    with Session(enrolled_db) as session:
        conversation = session.scalars(select(Conversation)).one()
        assert conversation.delivery_opted_out is True
        assert conversation.project_id is None
        assert session.scalars(select(Receipt.delivery_state)).all() == ["suppressed"]


def test_uncertain_delivery_is_not_retried(enrolled_db):
    def fail(_text):
        raise delivery.DeliveryError("simulated network timeout")

    timestamp = str(int(now_utc().timestamp()))
    body = payload("wamid.uncertain", "projects", timestamp=timestamp)
    with TestClient(pilot.create_receive_app(CREDENTIALS, enrolled_db)) as client:
        deliver(client, body)
        assert delivery.deliver_next(enrolled_db, CREDENTIALS, fail) == "needs_review"
        deliver(client, body)

    sent: list[str] = []
    assert delivery.deliver_next(enrolled_db, CREDENTIALS, sent.append) is None
    assert sent == []
    with Session(enrolled_db) as session:
        assert session.scalars(select(Receipt.delivery_state)).one() == "needs_review"


def test_consent_is_required_and_expires(pilot_db, monkeypatch):
    with TestClient(pilot.create_receive_app(CREDENTIALS, pilot_db)) as client:
        deliver(client, payload("wamid.before-consent", "use project-sharma"))
        with Session(pilot_db) as session:
            assert session.scalar(select(func.count()).select_from(Conversation)) == 0
            assert session.scalar(select(func.count()).select_from(Receipt)) == 0

        pilot.record_staff_consent(pilot_db, CREDENTIALS, "CONSENT-001")
        with pytest.raises(ValueError, match="already recorded"):
            pilot.record_staff_consent(pilot_db, CREDENTIALS, "CONSENT-002")
        deliver(client, payload("wamid.active", "projects"))

        now = now_utc()
        with Session(pilot_db) as session, session.begin():
            session.scalars(select(Conversation)).one().consent_recorded_at = now - timedelta(
                days=2
            )
        monkeypatch.setattr(
            pilot, "respond_to_message", lambda *_a, **_kw: pytest.fail("Expired consent")
        )
        deliver(client, payload("wamid.after-expiry", "use project-sharma"))
        assert (
            delivery.deliver_next(pilot_db, CREDENTIALS, lambda _: pytest.fail("Expired consent"))
            is None
        )
        with Session(pilot_db) as session:
            assert session.scalar(select(func.count()).select_from(Receipt)) == 1
            assert session.scalars(select(Conversation)).one().project_id is None


def test_seeded_verified_rates_have_provenance(pilot_db):
    with Session(pilot_db) as session:
        entries = session.scalars(select(RateEntry).where(RateEntry.verified.is_(True))).all()
        audits = session.scalars(
            select(AuditEvent).where(AuditEvent.action == "RATE_VERIFIED")
        ).all()
        assert len(entries) == len(audits) == 60
        assert {entry.id for entry in entries} == {event.object_id for event in audits}
        assert all(
            event.created_at and "Fictional seed catalogue" in event.detail for event in audits
        )


def test_first_quote_pilot_requires_exact_approval_and_sends_one_pdf(pilot_db, monkeypatch):
    monkeypatch.delenv("QSHIFT_INTAKE_MODEL", raising=False)
    pilot.record_staff_consent(pilot_db, CREDENTIALS, "CONSENT-001", first_quote=True)
    with TestClient(
        pilot.create_receive_app(CREDENTIALS, pilot_db, health_endpoint=False)
    ) as client:
        assert client.get("/healthz").status_code == 404
        message = "Need a wardrobe for the guest bedroom, white laminate, 6 ft wide."
        deliver(client, payload("wamid.unknown", message, sender="99999"))
        deliver(client, payload("wamid.brief", message))
        deliver(client, payload("wamid.height", "7 feet"))
        deliver(client, payload("wamid.height", "7 feet"))

    captured = []

    def graph(path, token, body, content_type):
        assert token == "synthetic-access-token"
        captured.append((path, body, content_type))
        if path.endswith("/media"):
            assert b"%PDF-" in body
            return {"id": "12345"}
        return {"messages": [{"id": "wamid.fixture-document"}]}

    monkeypatch.setattr(delivery, "meta_request", graph)
    monkeypatch.setenv("QSHIFT_WHATSAPP_SEND_ENABLED", "true")
    monkeypatch.setenv("QSHIFT_WHATSAPP_ACCESS_TOKEN", "synthetic-access-token")
    monkeypatch.setenv("QSHIFT_WHATSAPP_GRAPH_VERSION", "v99.0")
    send = delivery.meta_document_sender(CREDENTIALS)
    with Session(pilot_db) as session:
        draft = pilot.first_quote_draft(session, CREDENTIALS)
        assert draft is not None
        assert draft.total_paise == 5_250_000
        assert session.scalar(select(func.count()).select_from(Receipt)) == 2
        content_hash = draft.content_sha256
        with pytest.raises(ValueError, match="Approve the exact"):
            delivery.deliver_first_quote(pilot_db, CREDENTIALS, content_hash, send)
        assert not captured
        result = pilot.approve_first_quote(session, CREDENTIALS, content_hash)
        assert result["total"] == "₹52,500"

    with pytest.raises(ValueError, match="Approve the exact"):
        delivery.deliver_first_quote(pilot_db, CREDENTIALS, "0" * 64, send)
    assert not captured
    assert delivery.deliver_first_quote(pilot_db, CREDENTIALS, content_hash, send) == "accepted"
    assert [request[0] for request in captured] == ["/v99.0/10002/media", "/v99.0/10002/messages"]
    assert captured[0][2].startswith("multipart/form-data; boundary=")
    document = json.loads(captured[1][1])
    assert document["type"] == "document"
    assert document["to"] == CREDENTIALS.sender_id
    assert document["document"]["id"] == "12345"
    with pytest.raises(ValueError, match="a PDF attempt already exists"):
        delivery.deliver_first_quote(pilot_db, CREDENTIALS, content_hash, send)
    assert len(captured) == 2


def test_reply_worker_recovers_from_sqlite_busy(pilot_db, monkeypatch, capsys):
    busy = sqlite3.OperationalError("database is locked")
    busy.sqlite_errorcode = sqlite3.SQLITE_BUSY
    steps = iter([OperationalError("claim", {}, busy), "accepted"])

    def deliver_again(*_args):
        outcome = next(steps)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(sys, "argv", ["whatsapp_delivery", "run"])
    monkeypatch.setattr(delivery, "engine", pilot_db)
    monkeypatch.setattr(delivery, "read_credentials", lambda: CREDENTIALS)
    monkeypatch.setattr(delivery, "meta_sender", lambda _credentials: None)
    monkeypatch.setattr(delivery, "deliver_next", deliver_again)
    pauses = []
    monkeypatch.setattr(delivery.time, "sleep", pauses.append)

    with pytest.raises(StopIteration):
        delivery.main()

    assert pauses == [1]
    assert "Pilot reply state: accepted" in capsys.readouterr().out


def test_durable_inbox_survives_process_restart_and_model_failure(pilot_db, monkeypatch):
    monkeypatch.delenv("QSHIFT_INTAKE_MODEL", raising=False)
    pilot.record_staff_consent(pilot_db, CREDENTIALS, "CONSENT-001", first_quote=True)
    broken_attempts = []

    def unavailable(*_args, **_kwargs):
        broken_attempts.append(True)
        raise pilot.LocalModelUnavailable("offline model fixture")

    original = pilot.add_client_message
    monkeypatch.setattr(pilot, "add_client_message", unavailable)
    brief = payload(
        "wamid.durable-1", "Need a wardrobe for the guest bedroom, white laminate, 6 ft wide."
    )
    with TestClient(pilot.create_receive_app(CREDENTIALS, pilot_db, durable_inbox=True)) as client:
        deliver(client, brief)
        deliver(client, brief)
    assert broken_attempts == []

    pilot_db.dispose()
    with pytest.raises(pilot.LocalModelUnavailable):
        pilot.process_next_incoming(pilot_db, CREDENTIALS)
    with Session(pilot_db) as session:
        receipt = session.scalars(select(Receipt)).one()
        assert receipt.delivery_state == "queued"
        assert receipt.inbound_text is not None

    monkeypatch.setattr(pilot, "add_client_message", original)
    assert pilot.process_next_incoming(pilot_db, CREDENTIALS)
    assert not pilot.process_next_incoming(pilot_db, CREDENTIALS)
    with TestClient(pilot.create_receive_app(CREDENTIALS, pilot_db, durable_inbox=True)) as client:
        deliver(client, payload("wamid.durable-2", "7 feet"))
    assert pilot.process_next_incoming(pilot_db, CREDENTIALS)
    with Session(pilot_db) as session:
        draft = pilot.first_quote_draft(session, CREDENTIALS)
        assert draft is not None and draft.total_paise == 5_250_000
        assert session.scalars(select(Receipt.inbound_text)).all() == [None, None]


def test_opt_out_discards_unprocessed_inbox_text(enrolled_db):
    with TestClient(
        pilot.create_receive_app(CREDENTIALS, enrolled_db, durable_inbox=True)
    ) as client:
        deliver(client, payload("wamid.queued", "use project-sharma"))
        deliver(client, payload("wamid.stop", "STOP"))
    assert not pilot.process_next_incoming(enrolled_db, CREDENTIALS)
    with Session(enrolled_db) as session:
        assert session.scalars(select(Conversation.project_id)).one() is None
        receipt = session.scalars(select(Receipt)).one()
        assert receipt.delivery_state == "suppressed"
        assert receipt.inbound_text is None
