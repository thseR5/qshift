from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from qshift.api import main
from qshift.db import get_session
from qshift.models import StudioSession, now_utc
from qshift.services import seed_demo
from qshift.simulated_client_demo import payload
from qshift.studio_auth import COOKIE, get_session_record, provision

ORIGIN = {"Origin": "http://127.0.0.1:8079"}
FIXTURE_CARD = (
    b"sku,name,category,unit,rate_paise,gst_bps\n"
    b"WARDROBE-WHITE-LAMINATE,White laminate wardrobe,Wardrobe,sqft,125000,0\n"
    b"FALSE-CEILING-GYPSUM,Gypsum false ceiling,Ceiling,sqft,8700,0\n"
)


def test_studio_accounts_control_projects_rates_and_approvals(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_demo(session)
    monkeypatch.setattr(main, "STUDIO_MODE", True)
    monkeypatch.setenv("QSHIFT_INTAKE_MODEL", "ollama")
    monkeypatch.setitem(main.app.dependency_overrides, get_session, lambda: session)
    password = uuid4().hex
    provision(session, "maple", "owner", "Maple Owner", password, firm_name="Fictional Maple")
    provision(session, "maple", "designer", "Maple Designer", password, role="DESIGNER")
    provision(session, "cedar", "owner", "Cedar Owner", password, firm_name="Fictional Cedar")

    def signin(client: TestClient, studio: str, username: str):
        response = client.post(
            "/api/studio/session",
            headers=ORIGIN,
            json={"studio": studio, "username": username, "password": password},
        )
        assert response.status_code == 200
        assert "HttpOnly" in response.headers["Set-Cookie"]
        assert "SameSite=strict" in response.headers["Set-Cookie"]

    with (
        TestClient(main.app) as maple,
        TestClient(main.app) as cedar,
        TestClient(main.app) as designer,
    ):
        assert (
            maple.get(
                "/api/projects", headers={"Authorization": "Bearer demo-owner-token"}
            ).status_code
            == 401
        )
        assert maple.post("/api/demo/seed").status_code == 404
        signin(maple, "maple", "owner")
        signin(cedar, "cedar", "owner")
        signin(designer, "maple", "designer")
        assert cedar.get("/api/studio/session").json()["firm"] == "Fictional Cedar"
        assert maple.post("/api/projects", json={"name": "Wrong origin"}).status_code == 403
        project = maple.post(
            "/api/projects", headers=ORIGIN, json={"name": "Fictional loft"}
        ).json()
        assert cedar.get("/api/projects").json() == []
        assert cedar.get(f"/api/projects/{project['id']}/versions").status_code == 404
        imported = maple.post(
            "/api/imports/rate-card",
            headers=ORIGIN,
            files={"file": ("fictional.csv", FIXTURE_CARD, "text/csv")},
        ).json()
        assert cedar.get("/api/studio/rate-cards").json() == []
        for entry in imported["entries"]:
            rate = {"entry_id": entry["id"]}
            url = "/api/imports/rate-card/verify"
            assert cedar.post(url, headers=ORIGIN, json=rate).status_code == 404
            assert designer.post(url, headers=ORIGIN, json=rate).status_code == 403
            assert maple.post(url, headers=ORIGIN, json=rate).status_code == 200
        create = {"project_id": project["id"], "rate_card_id": imported["rate_card_id"]}
        path = "/api/simulated-whatsapp/chats"
        assert cedar.post(path, headers=ORIGIN, json=create).status_code == 404
        opened = designer.post(path, headers=ORIGIN, json=create)
        assert opened.status_code == 200
        chat_id = opened.json()["chat_id"]

        def proposal(messages):
            facts = [
                ("WARDROBE-WHITE-LAMINATE", {"room": "Bedroom", "width_ft": "6", "height_ft": "7"}),
                ("FALSE-CEILING-GYPSUM", {"room": "Bedroom", "area": "100"}),
            ]
            items = [
                {
                    "sku": sku,
                    "facts": {
                        key: {"value": value, "source": messages[-1]["id"]}
                        for key, value in fields.items()
                    },
                }
                for sku, fields in facts
            ]
            return items, None

        monkeypatch.setattr("qshift.intake.propose_items", proposal)
        event = payload(
            chat_id,
            "6 ft by 7 ft white laminate wardrobe and a 100 sq ft gypsum ceiling in the bedroom.",
        )
        state = designer.post("/api/simulated-whatsapp/webhook", headers=ORIGIN, json=event).json()
        draft = state["draft"]
        assert draft["total"] == "₹61,200"
        token_path = f"/api/drafts/{draft['id']}/approval-token"
        review = {"expected_hash": draft["hash"]}
        assert designer.post(token_path, headers=ORIGIN, json=review).status_code == 403
        assert cedar.post(token_path, headers=ORIGIN, json=review).status_code == 404
        token = maple.post(token_path, headers=ORIGIN, json=review).json()
        approval = maple.post("/api/approvals/commit", headers=ORIGIN, json=token).json()
        original_pdf = maple.get(approval["pdf_path"]).content
        assert original_pdf.startswith(b"%PDF-")
        assert cedar.get(approval["pdf_path"]).status_code == 404
        change = designer.post(
            "/api/changes",
            headers=ORIGIN,
            json={"project_id": project["id"], "text": "Remove the bedroom false ceiling."},
        ).json()
        assert change["status"] == "DRAFT_READY"
        assert change["revised_total"] == "₹52,500"
        update_token = f"/api/drafts/{change['id']}/approval-token"
        exact = {"expected_hash": change["content_sha256"]}
        assert designer.post(update_token, headers=ORIGIN, json=exact).status_code == 403
        assert cedar.post(update_token, headers=ORIGIN, json=exact).status_code == 404
        token = maple.post(update_token, headers=ORIGIN, json=exact).json()
        revised = maple.post("/api/approvals/commit", headers=ORIGIN, json=token).json()
        assert revised["version"] == 2
        assert revised["pdf_path"].startswith(f"{path}/{chat_id}/quotes/")
        assert maple.get(revised["pdf_path"]).content.startswith(b"%PDF-")
        assert cedar.get(revised["pdf_path"]).status_code == 404
        assert maple.get(approval["pdf_path"]).content == original_pdf

        cookie = maple.cookies[COOKIE]
        assert maple.delete("/api/studio/session", headers=ORIGIN).status_code == 204
        assert get_session_record(session, cookie) is None
        assert maple.get("/api/projects").status_code == 401
        record = get_session_record(session, cedar.cookies[COOKIE])
        assert isinstance(record, StudioSession)
        record.expires_at = now_utc()
        session.commit()
        assert cedar.get("/api/projects").status_code == 401
