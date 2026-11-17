from collections.abc import Generator
from hashlib import sha256
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from qshift.agent.itemized import CEILING, WARDROBE
from qshift.api.main import app
from qshift.db import get_session
from qshift.models import Firm, User
from qshift.services import hash_text, seed_demo
from qshift.simulated_client_demo import payload


@pytest.fixture
def client(session: Session) -> Generator[TestClient, None, None]:
    seed_demo(session)

    def override_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_session)


def test_simulated_api_auth_and_scope(client: TestClient) -> None:
    assert client.get("/health").json()["mode"] == "SIMULATED"
    home = client.get("/")
    assert home.status_code == 200
    assert "SIMULATED" in home.text
    site = client.get("/site")
    assert site.status_code == 200
    assert "Make every change count" in site.text
    assert client.get("/static/marketing.css").status_code == 200
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/api/projects").status_code == 401
    headers = {"Authorization": "Bearer demo-designer-token"}
    transcript = client.get("/api/transcripts/telugu_quartz_change", headers=headers)
    assert transcript.status_code == 200
    assert transcript.json()["requires_confirmation"] == "true"
    assert client.get("/templates/rate_card_template.csv").status_code == 200
    projects = client.get("/api/projects", headers=headers)
    assert projects.status_code == 200
    assert len(projects.json()) == 3
    denied = client.post("/api/projects/pin", headers=headers, json={"project_id": "not-in-tenant"})
    assert denied.status_code == 404
    path = "/api/versions/version-sharma-1/pdf"
    assert client.get(path).status_code == 401
    pdf = client.get(path, headers=headers)
    assert pdf.status_code == 200
    assert pdf.headers["Cache-Control"] == "no-store"
    assert pdf.content.startswith(b"%PDF-")

    preview = client.post(
        "/api/imports/rate-card/preview",
        headers=headers,
        files={
            "file": (
                "rates.csv",
                b"Item Code,Description,Group,UOM,Unit Price\nX-1,Quartz,Countertop,sqft,70000\n",
                "text/csv",
            )
        },
    )
    assert preview.status_code == 200
    assert preview.json()["mapping"]["rate_paise"] == "Unit Price"
    assert preview.json()["writes_database"] is False


def test_chat_can_cancel_open_revision_without_approval(client: TestClient) -> None:
    designer = {"Authorization": "Bearer demo-designer-token"}
    draft = client.post(
        "/api/changes",
        headers=designer,
        json={"project_id": "project-sharma", "text": "Please remove the bedroom false ceiling"},
    ).json()
    response = client.post(
        "/api/simulated-chat/messages",
        headers=designer,
        json={"text": "cancel", "project_id": "project-sharma", "draft_id": draft["id"]},
    )
    assert response.status_code == 200
    assert "approved quote is unchanged" in response.json()["reply"]


def test_founding_subscription_prices(client: TestClient) -> None:
    response = client.get("/api/pricing")
    assert response.status_code == 200
    assert response.json() == {
        "currency": "INR",
        "monthly_paise": 99_900,
        "annual_paise": 999_000,
        "overage_paise": 2_500,
        "onboarding_paise": 0,
        "future_monthly_paise": 249_900,
        "founding_firms": 10,
        "price_lock_months": 12,
        "included_firms": 1,
        "included_users": 3,
        "included_monthly_revisions": 30,
        "revision_unit": "approved_quote_version",
    }


def test_itemized_intake_prices_both_lines_and_edits_only_target(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    designer = {"Authorization": "Bearer demo-designer-token"}
    approver = {"Authorization": "Bearer demo-approver-token"}
    path = "/api/simulated-intakes"
    assert client.post(path, headers=designer, json={"scenario": "itemized"}).status_code == 409
    monkeypatch.setenv("QSHIFT_INTAKE_MODEL", "ollama")

    def proposal(messages: list[dict]) -> tuple[list[dict], str | None]:
        first_client = messages[1]["id"]
        wardrobe = {
            "sku": WARDROBE,
            "facts": {
                key: {"value": value, "source": first_client}
                for key, value in {
                    "room": "Second Bedroom",
                    "finish": "White laminate",
                    "width_ft": "8",
                    "height_ft": "7",
                }.items()
            },
        }
        ceiling = {
            "sku": CEILING,
            "facts": {
                "room": {"value": "Living Room", "source": first_client},
            },
        }
        if len(messages) == 2:
            return [wardrobe, ceiling], "ceiling_area"
        ceiling["facts"]["area"] = {"value": "100", "source": messages[-1]["id"]}
        return [wardrobe, ceiling], None

    monkeypatch.setattr("qshift.intake.propose_items", proposal)
    response = client.post(path, headers=designer, json={"scenario": "itemized"})
    assert response.status_code == 200
    scope = f"{path}/{response.json()['project_id']}"
    first = client.post(f"{scope}/messages", headers=designer, json={"text": "Fictional inquiry"})
    assert first.json()["missing"] == "ceiling_area"
    assert first.json()["draft"] is None
    final = client.post(f"{scope}/messages", headers=designer, json={"text": "100 sq ft"})
    draft = final.json()["draft"]
    assert draft["total"] == "₹78,500"
    assert [row["sku"] for row in draft["lines"]] == [WARDROBE, CEILING]
    token_path = f"/api/drafts/{draft['id']}/approval-token"
    old_token = client.post(
        token_path, headers=approver, json={"expected_hash": draft["hash"]}
    ).json()
    patch = {"expected_hash": draft["hash"], "quantity": "90"}
    assert client.patch(f"{scope}/draft", headers=designer, json=patch).status_code == 409
    patch["line_id"] = draft["lines"][1]["line_id"]
    edited = client.patch(f"{scope}/draft", headers=designer, json=patch).json()["draft"]
    assert edited["lines"][0] == draft["lines"][0]
    assert edited["lines"][1]["quantity"] == "90"
    assert edited["total"] == "₹77,650"
    approve_path = "/api/approvals/commit"
    assert client.post(approve_path, headers=approver, json=old_token).status_code == 409
    new_token = client.post(
        token_path, headers=approver, json={"expected_hash": edited["hash"]}
    ).json()
    approved = client.post(approve_path, headers=approver, json=new_token)
    assert approved.status_code == 200
    delivered = client.get(scope, headers=designer).json()["messages"][-1]["pdf_path"]
    assert client.get(delivered, headers=designer).content.startswith(b"%PDF-")


def test_whatsapp_bridge_routes_imported_rates_and_delivers_one_exact_document(
    client: TestClient, session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    designer = {"Authorization": "Bearer demo-designer-token"}
    approver = {"Authorization": "Bearer demo-approver-token"}
    monkeypatch.setenv("QSHIFT_INTAKE_MODEL", "ollama")
    templates = Path("qshift/fixtures/templates/whatsapp_rehearsal_rates.csv")
    imported = client.post(
        "/api/imports/rate-card",
        headers=designer,
        files={"file": (templates.name, templates.read_bytes(), "text/csv")},
    ).json()
    config = {"rate_card_id": imported["rate_card_id"]}
    chats = "/api/simulated-whatsapp/chats"
    assert client.post(chats, headers=designer, json=config).status_code == 409
    for rate in imported["entries"]:
        response = client.post(
            "/api/imports/rate-card/verify", headers=approver, json={"entry_id": rate["id"]}
        )
        assert response.status_code == 200
    chat = client.post(chats, headers=designer, json=config).json()
    other_chat = client.post(chats, headers=designer, json=config).json()
    assert chat["chat_id"] != other_chat["chat_id"]
    session.add(Firm(id="bridge-other", name="Another fictional firm"))
    session.flush()
    session.add(
        User(
            id="bridge-other-designer",
            firm_id="bridge-other",
            name="Fictional designer",
            role="DESIGNER",
            demo_token_hash=hash_text("bridge-other-demo"),
        )
    )
    session.commit()
    other_firm = {"Authorization": "Bearer bridge-other-demo"}
    assert client.post(chats, headers=other_firm, json=config).status_code == 404

    calls = []

    def proposal(messages: list[dict]) -> tuple[list[dict], str | None]:
        calls.append(messages[-1]["text"])
        facts = {
            "room": {"value": "Living Room", "source": messages[1]["id"]},
        }
        if len(calls) == 2:
            facts["area"] = {"value": "100", "source": messages[-1]["id"]}
        return [{"sku": CEILING, "facts": facts}], None if len(calls) == 2 else "ceiling_area"

    monkeypatch.setattr("qshift.intake.propose_items", proposal)
    first = payload(chat["chat_id"], "Gypsum ceiling in the living room.")
    endpoint = "/api/simulated-whatsapp/webhook"
    assert client.post(endpoint, json=first).status_code == 401
    assert client.post(endpoint, headers=other_firm, json=first).status_code == 404
    wrong = payload(chat["chat_id"], "Not a fictional destination.")
    wrong["entry"][0]["id"] = "invalid-account"
    assert client.post(endpoint, headers=designer, json=wrong).status_code == 422
    intake_url = f"/api/simulated-intakes/{chat['project_id']}"
    assert (
        client.post(
            f"{intake_url}/messages", headers=designer, json={"text": "100 sq ft"}
        ).status_code
        == 409
    )
    response = client.post(endpoint, headers=designer, json=first).json()
    assert response["missing"] == "ceiling_area"
    assert not response["duplicate"]
    assert client.post(endpoint, headers=designer, json=first).json()["duplicate"]
    original = first["entry"][0]["changes"][0]["value"]["messages"][0]
    original["text"]["body"] = "Another body"
    assert client.post(endpoint, headers=designer, json=first).status_code == 409
    assert len(calls) == 1

    followup = payload(chat["chat_id"], "100 sq ft.")
    state = client.post(endpoint, headers=designer, json=followup).json()
    draft = state["draft"]
    assert draft["total"] == "₹8,500"
    assert all("pdf_path" not in message for message in state["messages"])
    token = client.post(
        f"/api/drafts/{draft['id']}/approval-token",
        headers=approver,
        json={"expected_hash": draft["hash"]},
    ).json()
    approval = client.post("/api/approvals/commit", headers=approver, json=token).json()
    path = f"{chats}/{chat['chat_id']}/quotes/{approval['version_id']}/pdf"
    assert approval["pdf_path"] == path
    state = client.get(intake_url, headers=designer).json()
    assert [m["pdf_path"] for m in state["messages"] if "pdf_path" in m] == [path]
    assert client.post(endpoint, headers=designer, json=followup).json()["duplicate"]
    assert client.post("/api/approvals/commit", headers=approver, json=token).status_code == 403
    document = client.get(path, headers=designer)
    assert document.content.startswith(b"%PDF-")
    assert sha256(document.content).hexdigest() == document.headers["X-QShift-PDF-SHA256"]
    assert client.get(path, headers=designer).content == document.content
    assert (
        client.get(
            path.replace(chat["chat_id"], other_chat["chat_id"]), headers=designer
        ).status_code
        == 404
    )
    assert client.get(path, headers=other_firm).status_code == 404


def test_first_quote_from_chat_to_approved_pdf(client: TestClient, session: Session) -> None:
    designer = {"Authorization": "Bearer demo-designer-token"}
    approver = {"Authorization": "Bearer demo-approver-token"}
    url = "/api/simulated-intakes"
    assert "SIMULATED" in client.get("/intake").text
    assert client.post(url).status_code == 401
    started = client.post(url, headers=designer)
    assert started.status_code == 200
    project = f"{url}/{started.json()['project_id']}"

    session.add(Firm(id="firm-other", name="Other fictional firm"))
    session.flush()
    session.add(
        User(
            id="other-approver",
            firm_id="firm-other",
            name="Fictional approver",
            role="APPROVER",
            demo_token_hash=hash_text("other-test-token"),
        )
    )
    session.commit()
    other = {"Authorization": "Bearer other-test-token"}
    assert client.get(project, headers=other).status_code == 404
    assert (
        client.post(f"{project}/messages", headers=other, json={"text": "7 feet"}).status_code
        == 404
    )

    def send(text: str) -> dict:
        response = client.post(f"{project}/messages", headers=designer, json={"text": text})
        assert response.status_code == 200
        return response.json()

    first = send("Hi, need a wardrobe in the second bedroom.")
    assert first["missing"] == "finish"
    assert first["brief"]["room"]["source"] == first["messages"][0]["id"]
    second = send("White laminate please. About 8 ft wide.")
    assert second["draft"] is None
    assert second["messages"][-1]["text"] == "How tall is the wardrobe in feet?"
    ready = send("7 feet")
    draft = ready["draft"]
    assert draft["line"]["quantity"] == "56"
    assert draft["line"]["total_paise"] == 7_000_000
    assert not any("pdf_path" in message for message in ready["messages"])
    assert client.get(project, headers=designer).json() == ready
    concept_url = f"{project}/concept"
    sample = client.get(draft["concept_preview"])
    assert sample.status_code == 200
    assert sample.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert (
        client.post(concept_url, headers=approver, json={"version_id": "draft"}).status_code == 409
    )

    draft_token_path = "/api/drafts/" + draft["id"] + "/approval-token"
    review = {"expected_hash": draft["hash"]}
    assert client.post(draft_token_path, headers=designer, json=review).status_code == 403
    assert client.post(draft_token_path, headers=approver).status_code == 409
    old_token = client.post(draft_token_path, headers=approver, json=review).json()["token"]
    edited = client.patch(f"{project}/draft", headers=designer, json={**review, "quantity": "55.5"})
    assert edited.status_code == 200
    edited_draft = edited.json()["draft"]
    assert edited_draft["line"]["total_paise"] == 6_937_500
    approval_path = "/api/approvals/commit"
    assert (
        client.post(approval_path, headers=approver, json={"token": old_token}).status_code == 409
    )
    assert client.post(draft_token_path, headers=approver, json=review).status_code == 409
    fresh = {"expected_hash": edited_draft["hash"]}
    token = client.post(draft_token_path, headers=approver, json=fresh).json()["token"]
    approved = client.post(approval_path, headers=approver, json={"token": token})
    assert approved.status_code == 200
    assert approved.json()["version"] == 1
    assert client.post(approval_path, headers=approver, json={"token": token}).status_code == 403
    complete = client.get(project, headers=designer).json()
    delivery = complete["messages"][-1]
    assert delivery["text"] == "SIMULATED DELIVERY · Approved quotation v1 · ₹69,375"
    pdf = client.get(delivery["pdf_path"], headers=designer)
    assert pdf.content.startswith(b"%PDF-")
    assert b"Maple Apartment" in pdf.content
    assert client.get(delivery["pdf_path"], headers=other).status_code == 404
    version = {"version_id": approved.json()["version_id"]}
    assert client.post(concept_url, headers=designer, json=version).status_code == 403
    assert client.post(concept_url, headers=other, json=version).status_code == 404
    assert (
        client.post(
            concept_url, headers=approver, json={"version_id": "version-sharma-1"}
        ).status_code
        == 409
    )
    attached = client.post(concept_url, headers=approver, json=version)
    assert attached.status_code == 200
    shared = attached.json()
    assert shared["messages"][-2] == delivery
    assert shared["messages"][-1]["concept_preview"] == draft["concept_preview"]
    assert shared["draft"]["concept_attached"]
    assert shared["draft"]["hash"] == complete["draft"]["hash"]
    assert client.post(concept_url, headers=approver, json=version).json() == shared
    assert client.get(project, headers=designer).json() == shared
    assert (
        client.patch(
            f"{project}/draft",
            headers=designer,
            json={
                **fresh,
                "quantity": "50",
            },
        ).status_code
        == 409
    )


def test_chat_clarifies_prices_and_keeps_approval_in_review(client: TestClient) -> None:
    path = "/api/simulated-chat/messages"
    headers = {"Authorization": "Bearer demo-designer-token"}

    def send(text: str, **context: str):
        return client.post(path, headers=headers, json={"text": text, **context})

    assert client.post(path, json={"text": "projects"}).status_code == 401
    assert "Sharma Residence" in send("projects").json()["reply"]
    assert send("use not-in-tenant").status_code == 404
    project_id = send("use project-sharma").json()["project_id"]
    draft = send(
        "Kitchen lo granite badulu quartz pettandi, bedroom false ceiling remove cheyyandi.",
        project_id=project_id,
    ).json()
    assert "choose <SKU>" in draft["reply"]
    draft_id = draft["draft"]["id"]
    assert send("status", project_id=project_id).json()["draft"]["id"] == draft_id
    choice = "choose COUNTER-QUARTZ-CALACATTA"
    assert send(choice, project_id="project-mehta", draft_id=draft_id).status_code == 404
    assert send("choose DEMO-013", project_id=project_id, draft_id=draft_id).status_code == 409
    ready = send(choice, project_id=project_id, draft_id=draft_id).json()
    assert ready["draft"]["status"] == "DRAFT_READY"
    assert "₹2,43,200" in ready["reply"]
    assert send(choice, project_id=project_id, draft_id=draft_id).status_code == 409

    reply = client.post(
        path,
        headers={"Authorization": "Bearer demo-approver-token"},
        json={"text": "approve", "project_id": project_id, "draft_id": draft_id},
    )
    assert "authenticated Qshift review screen" in reply.json()["reply"]
    assert "v2" not in send("history", project_id=project_id).json()["reply"]
