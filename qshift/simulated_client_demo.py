"""Exercise the full fictional client quote using the running local AI app."""

import argparse
import hashlib
from pathlib import Path
from uuid import uuid4

import httpx


def payload(chat_id: str, text: str) -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "qshift-sim-account",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "metadata": {"phone_number_id": "qshift-sim-number"},
                            "messages": [
                                {
                                    "id": "sim-msg-" + str(uuid4()),
                                    "from": "sim-client-" + chat_id,
                                    "type": "text",
                                    "text": {"body": text},
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8078)
    args = parser.parse_args()
    catalogue = Path(__file__).parent / "fixtures" / "templates" / "whatsapp_rehearsal_rates.csv"
    with httpx.Client(
        base_url=f"http://127.0.0.1:{args.port}", timeout=50, trust_env=False
    ) as client:

        def call(method: str, path: str, *, role: str = "designer", **kwargs):
            response = client.request(
                method, path, headers={"Authorization": f"Bearer demo-{role}-token"}, **kwargs
            )
            if response.is_error:
                raise RuntimeError(f"{response.status_code} {path}: {response.text}")
            return response

        call("POST", "/api/demo/seed")
        card = call(
            "POST",
            "/api/imports/rate-card",
            files={
                "file": (catalogue.name, catalogue.read_bytes(), "text/csv"),
            },
        ).json()
        for entry in card["entries"]:
            call(
                "POST",
                "/api/imports/rate-card/verify",
                role="approver",
                json={"entry_id": entry["id"]},
            )
        setup = "/api/simulated-whatsapp/chats"
        first = call("POST", setup, json={"rate_card_id": card["rate_card_id"]}).json()
        other = call("POST", setup, json={"rate_card_id": card["rate_card_id"]}).json()
        chat_id = first["chat_id"]
        webhook = "/api/simulated-whatsapp/webhook"
        inquiry = payload(
            chat_id,
            "Need a white laminate wardrobe in the second bedroom, 8 ft wide "
            "and 7 ft tall. Also a gypsum false ceiling in the living room.",
        )
        intake = call("POST", webhook, json=inquiry).json()
        assert intake["extraction"] and intake["missing"] == "ceiling_area", intake
        print("SIMULATED | QShift asked for the ceiling area", flush=True)
        assert call("POST", webhook, json=inquiry).json()["duplicate"]
        intake = call(
            "POST", webhook, json=payload(chat_id, "Living room gypsum ceiling area is 100 sq ft.")
        ).json()
        draft = intake["draft"]
        assert draft and draft["total"] == "₹78,500", intake
        print(
            f"SIMULATED | {intake['extraction']} drafted {len(draft['lines'])} lines · {draft['total']}",
            flush=True,
        )
        token = call(
            "POST",
            f"/api/drafts/{draft['id']}/approval-token",
            role="approver",
            json={"expected_hash": draft["hash"]},
        ).json()
        approved = call("POST", "/api/approvals/commit", role="approver", json=token).json()
        refreshed = call("GET", f"/api/simulated-intakes/{first['project_id']}").json()
        pdf_path = refreshed["messages"][-1]["pdf_path"]
        assert pdf_path == f"{setup}/{chat_id}/quotes/{approved['version_id']}/pdf"
        pdf = call("GET", pdf_path)
        assert pdf.content.startswith(b"%PDF-")
        assert hashlib.sha256(pdf.content).hexdigest() == pdf.headers["X-QShift-PDF-SHA256"]
        wrong = client.get(
            pdf_path.replace(chat_id, other["chat_id"]),
            headers={
                "Authorization": "Bearer demo-designer-token",
            },
        )
        assert wrong.status_code == 404
        print("SIMULATED | Approved v1 PDF verified in the original chat only")


if __name__ == "__main__":
    main()
