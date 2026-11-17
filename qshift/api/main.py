"""FastAPI application for the simulated designer workflow."""

from __future__ import annotations

import os
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from qshift.agent.chat import respond_to_message
from qshift.agent.extraction import MockTranscriber
from qshift.agent.local_model import LocalModelUnavailable
from qshift.db import Base, engine, get_session
from qshift.intake import (
    add_client_message,
    attach_concept,
    edit_quantity,
    intake_view,
    start_sample,
)
from qshift.models import Firm, Project, Quote, QuoteVersion, RateCard, RateEntry, User
from qshift.services import (
    approve_draft,
    create_project,
    import_quotation,
    import_rate_card,
    issue_approval_token,
    pin_project,
    preview_import,
    project_memory,
    projects_for_user,
    reject_draft,
    render_pdf,
    resolve_catalogue,
    seed_demo,
    submit_change,
    user_from_demo_token,
    verify_rate,
    versions,
)
from qshift.simulated_whatsapp import create_chat, delivery_pdf, parse_event, receive_event, replay
from qshift.studio_auth import COOKIE, SESSION_SECONDS, login, logout, session_user
from qshift.whatsapp_webhook import Event

PRIVATE_REVIEW = os.getenv("QSHIFT_PRIVATE_REVIEW") == "true"
STUDIO_MODE = os.getenv("QSHIFT_STUDIO_MODE") == "true"
STUDIO_ORIGIN = os.getenv("QSHIFT_STUDIO_ORIGIN", "http://127.0.0.1:8079")
if STUDIO_MODE and PRIVATE_REVIEW:
    raise RuntimeError("Run the studio and legacy staff review as separate processes.")
if STUDIO_MODE and len(os.getenv("QSHIFT_APPROVAL_SECRET", "")) < 32:
    raise RuntimeError("Studio mode requires a dedicated approval secret.")
if PRIVATE_REVIEW:
    if len(os.getenv("QSHIFT_APPROVAL_SECRET", "")) < 32:
        raise RuntimeError("Set a random QSHIFT_APPROVAL_SECRET for the hosted review service")
else:
    Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Qshift Demo",
    version="0.1.0",
    description="Clearly simulated, offline-first quotation workflow",
)
if PRIVATE_REVIEW or STUDIO_MODE:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1"])
SessionDep = Annotated[Session, Depends(get_session)]


@app.exception_handler(RequestValidationError)
async def validation_errors(request: Request, exc: RequestValidationError) -> Response:
    if request.method == "POST" and request.url.path == "/api/studio/session":
        return JSONResponse({"detail": "Check your sign-in fields."}, status_code=422)
    return await request_validation_exception_handler(request, exc)


def current_user(
    request: Request, session: SessionDep, authorization: Annotated[str | None, Header()] = None
) -> User:
    if STUDIO_MODE:
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            check_origin(request)
        user = session_user(session, request.cookies.get(COOKIE))
        if user is None:
            raise HTTPException(401, "Sign in to your fictional studio.")
        return user
    token = authorization.removeprefix("Bearer ") if authorization else None
    user = user_from_demo_token(session, token)
    if not user:
        raise HTTPException(
            status_code=401, detail="Use a fictional demo bearer token from the README"
        )
    return user


UserDep = Annotated[User, Depends(current_user)]


def check_origin(request: Request) -> None:
    if request.headers.get("origin") != STUDIO_ORIGIN:
        raise HTTPException(403, "The request must come from the studio workspace.")


class LoginRequest(BaseModel):
    studio: str = Field(min_length=2, max_length=64)
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class PinRequest(BaseModel):
    project_id: str


class ProjectRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    client_label: str = Field(default="Fictional client", max_length=120)


class ChangeRequest(BaseModel):
    project_id: str
    text: str = Field(min_length=1, max_length=4000)


class ChatMessage(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    project_id: str | None = Field(default=None, max_length=36)
    draft_id: str | None = Field(default=None, max_length=36)


class SelectRequest(BaseModel):
    sku: str


class ApproveRequest(BaseModel):
    token: str


class ApprovalTokenRequest(BaseModel):
    expected_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class IntakeMessageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


class IntakeStartRequest(BaseModel):
    scenario: Literal["wardrobe", "itemized"] = "wardrobe"


class IntakeEditRequest(BaseModel):
    quantity: Decimal = Field(gt=0, le=400, max_digits=7, decimal_places=4)
    expected_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    line_id: str | None = Field(default=None, max_length=36)


class IntakeConceptRequest(BaseModel):
    version_id: str = Field(min_length=1, max_length=36)


class SimulatedChatRequest(BaseModel):
    rate_card_id: str = Field(min_length=1, max_length=36)
    project_id: str | None = Field(default=None, min_length=1, max_length=36)


class VerifyRequest(BaseModel):
    entry_id: str


@app.get("/", response_class=HTMLResponse)
def index() -> FileResponse:
    return FileResponse("qshift/web/studio.html" if STUDIO_MODE else "qshift/web/index.html")


@app.post("/api/studio/session")
def studio_login(
    body: LoginRequest, request: Request, response: Response, session: SessionDep
) -> dict:
    if not STUDIO_MODE:
        raise HTTPException(404, "Not found")
    check_origin(request)
    token = login(session, body.studio, body.username, body.password)
    if token is None:
        raise HTTPException(401, "Studio, username, or password is incorrect.")
    logout(session, request.cookies.get(COOKIE))
    response.headers["Cache-Control"] = "no-store"
    response.set_cookie(
        COOKIE,
        token,
        max_age=SESSION_SECONDS,
        secure=STUDIO_ORIGIN.startswith("https://"),
        httponly=True,
        samesite="strict",
    )
    return {"status": "signed_in"}


@app.get("/api/studio/session")
def studio_identity(session: SessionDep, response: Response, user: UserDep) -> dict:
    if not STUDIO_MODE:
        raise HTTPException(404, "Not found")
    firm = session.scalar(select(Firm).where(Firm.id == user.firm_id))
    response.headers["Cache-Control"] = "no-store"
    return {"name": user.name, "role": user.role, "firm": firm.name if firm else ""}


@app.delete("/api/studio/session", status_code=204)
def studio_logout(request: Request, session: SessionDep) -> Response:
    if not STUDIO_MODE:
        raise HTTPException(404, "Not found")
    check_origin(request)
    logout(session, request.cookies.get(COOKIE))
    response = Response(status_code=204, headers={"Cache-Control": "no-store"})
    response.delete_cookie(
        COOKIE, secure=STUDIO_ORIGIN.startswith("https://"), httponly=True, samesite="strict"
    )
    return response


@app.get("/api/studio/rate-cards")
def studio_rate_cards(session: SessionDep, user: UserDep) -> list[dict]:
    if not STUDIO_MODE:
        raise HTTPException(404, "Not found")
    scoped_cards = session.scalars(
        select(RateCard).where(RateCard.firm_id == user.firm_id).order_by(RateCard.version.desc())
    )
    cards = [{"id": card.id, "version": card.version, "entries": []} for card in scoped_cards]
    by_id = {card["id"]: card for card in cards}
    entries = session.scalars(
        select(RateEntry)
        .where(RateEntry.firm_id == user.firm_id, RateEntry.rate_card_id.in_(by_id))
        .order_by(RateEntry.sku)
    )
    for entry in entries:
        by_id[entry.rate_card_id]["entries"].append(
            {
                "id": entry.id,
                "sku": entry.sku,
                "name": entry.name,
                "unit": entry.unit,
                "verified": entry.verified,
                "rate_paise": entry.rate_paise,
            }
        )
    return cards


@app.get("/intake", response_class=HTMLResponse)
def intake_page() -> FileResponse:
    if PRIVATE_REVIEW or STUDIO_MODE:
        raise HTTPException(404, "Not found")
    return FileResponse("qshift/web/intake.html")


@app.post("/api/simulated-intakes")
def intake_start(
    session: SessionDep, user: UserDep, body: IntakeStartRequest | None = None
) -> dict:
    if PRIVATE_REVIEW or STUDIO_MODE:
        raise HTTPException(404, "Not found")
    try:
        scenario = body.scenario if body else "wardrobe"
        if scenario == "itemized" and os.getenv("QSHIFT_INTAKE_MODEL") != "ollama":
            raise ValueError("The itemized sample requires local AI mode.")
        return start_sample(session, user, scenario)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(409, "The sample changed. Try starting it again.") from exc


@app.post("/api/simulated-whatsapp/chats")
def simulated_chat_start(body: SimulatedChatRequest, session: SessionDep, user: UserDep) -> dict:
    if PRIVATE_REVIEW:
        raise HTTPException(404, "Not found")
    if os.getenv("QSHIFT_INTAKE_MODEL") != "ollama":
        raise HTTPException(409, "Start QShift with the local AI model for this rehearsal.")
    if STUDIO_MODE and body.project_id is None:
        raise HTTPException(422, "Select a studio project before starting the rehearsal.")
    try:
        return create_chat(session, user, body.rate_card_id, body.project_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(409, "The setup changed. Try starting the chat again.") from exc


@app.post("/api/simulated-whatsapp/webhook")
def simulated_webhook(body: Event, session: SessionDep, user: UserDep) -> dict:
    if PRIVATE_REVIEW:
        raise HTTPException(404, "Not found")
    try:
        event = parse_event(body)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    try:
        return receive_event(session, user, event)
    except LocalModelUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except (IntegrityError, StaleDataError, ValueError) as exc:
        session.rollback()
        try:
            previous = replay(session, user, event)
        except ValueError as replay_error:
            raise HTTPException(409, str(replay_error)) from replay_error
        if previous is not None:
            return previous
        detail = str(exc) if isinstance(exc, ValueError) else "Chat changed. Retry the same event."
        raise HTTPException(409, detail) from exc


@app.get("/api/simulated-whatsapp/chats/{chat_id}/quotes/{version_id}/pdf")
def simulated_chat_pdf(
    chat_id: str, version_id: str, session: SessionDep, user: UserDep
) -> Response:
    if PRIVATE_REVIEW:
        raise HTTPException(404, "Not found")
    try:
        document = delivery_pdf(session, user, chat_id, version_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(500, str(exc)) from exc
    return Response(
        document.pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="qshift-simulated-approved-quote.pdf"',
            "Cache-Control": "no-store",
            "X-QShift-PDF-SHA256": document.pdf_sha256,
        },
    )


@app.get("/api/simulated-intakes/{project_id}")
def intake_get(project_id: str, session: SessionDep, user: UserDep) -> dict:
    try:
        return intake_view(session, user, project_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.post("/api/simulated-intakes/{project_id}/messages")
def intake_message(
    project_id: str, body: IntakeMessageRequest, session: SessionDep, user: UserDep
) -> dict:
    try:
        return add_client_message(session, user, project_id, body.text)
    except LocalModelUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    except (IntegrityError, StaleDataError) as exc:
        session.rollback()
        raise HTTPException(409, "The conversation changed. Reload it and retry.") from exc


@app.patch("/api/simulated-intakes/{project_id}/draft")
def intake_edit(
    project_id: str, body: IntakeEditRequest, session: SessionDep, user: UserDep
) -> dict:
    try:
        return edit_quantity(
            session, user, project_id, body.quantity, body.expected_hash, body.line_id
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.post("/api/simulated-intakes/{project_id}/concept")
def intake_attach_concept(
    project_id: str, body: IntakeConceptRequest, session: SessionDep, user: UserDep
) -> dict:
    try:
        return attach_concept(session, user, project_id, body.version_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    except StaleDataError as exc:
        session.rollback()
        raise HTTPException(409, "The conversation changed. Reload it and retry.") from exc


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": "SIMULATED"}


@app.get("/api/pricing")
def subscription_pricing() -> dict[str, int | str]:
    return {
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


@app.post("/api/demo/seed")
def seed(session: SessionDep, reset: bool = False) -> dict:
    if PRIVATE_REVIEW or STUDIO_MODE:
        raise HTTPException(404, "Not found")
    return seed_demo(session, reset=reset)


@app.get("/api/projects")
def projects(session: SessionDep, user: UserDep) -> list[dict[str, str]]:
    return projects_for_user(session, user)


@app.post("/api/projects")
def project_create(body: ProjectRequest, session: SessionDep, user: UserDep) -> dict[str, str]:
    try:
        return create_project(session, user, body.name, body.client_label)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/projects/pin")
def pin(body: PinRequest, session: SessionDep, user: UserDep) -> dict:
    try:
        return pin_project(session, user, body.project_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.post("/api/changes")
def changes(body: ChangeRequest, session: SessionDep, user: UserDep) -> dict:
    try:
        return submit_change(session, user, body.project_id, body.text)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.post("/api/simulated-chat/messages")
def chat_message(body: ChatMessage, session: SessionDep, user: UserDep) -> dict:
    try:
        return respond_to_message(session, user, body.text, body.project_id, body.draft_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.get("/api/transcripts/{fixture_name}")
def transcript(fixture_name: str, user: UserDep) -> dict[str, str]:
    try:
        return MockTranscriber().transcribe(fixture_name)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.post("/api/drafts/{draft_id}/catalogue-selection")
def selection(draft_id: str, body: SelectRequest, session: SessionDep, user: UserDep) -> dict:
    try:
        return resolve_catalogue(session, user, draft_id, body.sku)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/drafts/{draft_id}/approval-token")
def approval_token(
    draft_id: str, session: SessionDep, user: UserDep, body: ApprovalTokenRequest | None = None
) -> dict[str, str]:
    try:
        return {"token": issue_approval_token(session, user, draft_id, body and body.expected_hash)}
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(409, "Another approval was requested. Reload the draft.") from exc


@app.post("/api/drafts/{draft_id}/reject")
def reject(draft_id: str, session: SessionDep, user: UserDep) -> dict[str, str]:
    try:
        return reject_draft(session, user, draft_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.post("/api/approvals/commit")
def approve(body: ApproveRequest, session: SessionDep, user: UserDep) -> dict:
    try:
        return approve_draft(
            session, user, body.token, write_pdf=not (PRIVATE_REVIEW or STUDIO_MODE)
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.get("/api/projects/{project_id}/versions")
def quote_versions(project_id: str, session: SessionDep, user: UserDep) -> list[dict]:
    try:
        return versions(session, user, project_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.get("/api/projects/{project_id}/memory")
def memory(project_id: str, session: SessionDep, user: UserDep) -> dict:
    try:
        return project_memory(session, user, project_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.get("/api/versions/{version_id}/pdf")
def pdf(version_id: str, session: SessionDep, user: UserDep) -> Response:
    row = session.execute(
        select(QuoteVersion, Firm.name, Project.name)
        .join(Firm, Firm.id == QuoteVersion.firm_id)
        .join(Quote, (Quote.id == QuoteVersion.quote_id) & (Quote.firm_id == Firm.id))
        .join(Project, (Project.id == Quote.project_id) & (Project.firm_id == Firm.id))
        .where(QuoteVersion.id == version_id, Firm.id == user.firm_id)
    ).one_or_none()
    if row is None:
        raise HTTPException(404, "Quotation version not found")
    version, firm_name, project_name = row
    return Response(
        render_pdf(version, firm_name, project_name),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="qshift-quotation-v{version.number}.pdf"',
            "Cache-Control": "no-store",
        },
    )


@app.post("/api/imports/rate-card")
def rate_card_import(
    session: SessionDep, user: UserDep, file: Annotated[UploadFile, File()]
) -> dict:
    try:
        return import_rate_card(session, user, file.filename or "upload", file.file.read())
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/imports/rate-card/preview")
def rate_card_preview(
    session: SessionDep, user: UserDep, file: Annotated[UploadFile, File()]
) -> dict:
    del session, user
    try:
        return preview_import(file.filename or "upload", file.file.read(), "rate_card")
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/imports/quotation")
def quotation_import(
    project_id: str,
    session: SessionDep,
    user: UserDep,
    file: Annotated[UploadFile, File()],
) -> dict:
    try:
        return import_quotation(
            session, user, project_id, file.filename or "upload", file.file.read()
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/imports/quotation/preview")
def quotation_preview(
    session: SessionDep, user: UserDep, file: Annotated[UploadFile, File()]
) -> dict:
    del session, user
    try:
        return preview_import(file.filename or "upload", file.file.read(), "quotation")
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/imports/rate-card/verify")
def verify(body: VerifyRequest, session: SessionDep, user: UserDep) -> dict[str, str]:
    try:
        verify_rate(session, user, body.entry_id)
        return {"status": "verified"}
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc


app.mount("/static", StaticFiles(directory="qshift/web"), name="static")
app.mount(
    "/templates",
    StaticFiles(directory="qshift/fixtures/templates"),
    name="templates",
)
