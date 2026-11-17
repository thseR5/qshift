from fastapi.testclient import TestClient

from qshift.whatsapp_rehearsal import (
    FIXTURE_VERIFY_TOKEN,
    WEBHOOK_PATH,
    create_rehearsal,
    fixture_payload,
    fixture_signature,
)


def test_callback_challenge_and_signature():
    replies: list[str] = []
    with TestClient(create_rehearsal(replies.append)) as client:
        params = {"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "42"}
        assert client.get(WEBHOOK_PATH, params=params).status_code == 403
        params["hub.verify_token"] = FIXTURE_VERIFY_TOKEN.decode()
        response = client.get(WEBHOOK_PATH, params=params)
        assert response.status_code == 200
        assert response.text == "42"

        body = fixture_payload("wamid.test", "projects")
        response = client.post(
            WEBHOOK_PATH,
            content=body + b" ",
            headers={"X-Hub-Signature-256": fixture_signature(body)},
        )
        assert response.status_code == 401
        assert replies == []


def test_only_enrolled_staff_texts_change_state_and_replays_are_ignored():
    replies: list[str] = []
    with TestClient(create_rehearsal(replies.append)) as client:

        def deliver(body: bytes):
            response = client.post(
                WEBHOOK_PATH, content=body, headers={"X-Hub-Signature-256": fixture_signature(body)}
            )
            assert response.status_code == 200
            assert response.json() == {"ok": True}

        deliver(fixture_payload("wamid.account", "projects", account="other"))
        deliver(fixture_payload("wamid.number", "projects", number="other"))
        deliver(fixture_payload("wamid.sender", "projects", sender="other"))
        assert replies == []

        deliver(fixture_payload("wamid.project", "use project-sharma"))
        scope = fixture_payload(
            "wamid.scope",
            "Kitchen lo granite badulu quartz pettandi, bedroom false ceiling remove cheyyandi.",
        )
        deliver(scope)
        deliver(scope)
        assert len(replies) == 2
        assert "choose <SKU>" in replies[-1]
        deliver(fixture_payload("wamid.choice", "choose COUNTER-QUARTZ-CALACATTA"))
        assert "₹2,43,200" in replies[-1]
        deliver(fixture_payload("wamid.approval", "approve"))
        assert "authenticated Qshift review screen" in replies[-1]
