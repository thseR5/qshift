import io
import zipfile

import pytest

from qshift.models import StaffEnrollment
from qshift.services import seed_demo
from qshift.whatsapp_identity import register_staff_identity, resolve_staff_sender
from qshift.whatsapp_media import MediaDownloadError, validate_document
from qshift.whatsapp_webhook import WebhookCredentials

CREDENTIALS = WebhookCredentials(
    account_id="10001",
    phone_number_id="10002",
    sender_id="10003",
    app_secret=b"synthetic-app-secret",
    verify_token=b"synthetic-webhook-verification",
)


def test_identity_resolution_is_tenant_and_sender_scoped(session):
    seed_demo(session)
    resolved = register_staff_identity(
        session,
        CREDENTIALS,
        firm_id="firm-demo",
        user_id="user-approver",
        consent_reference="V8-001",
    )
    session.commit()
    found = resolve_staff_sender(session, CREDENTIALS)
    assert found is not None
    assert resolved.enrollment_id
    assert found.firm_id == "firm-demo"
    assert found.user_id == "user-approver"
    assert session.query(StaffEnrollment).count() == 1
    unknown = WebhookCredentials(
        account_id=CREDENTIALS.account_id,
        phone_number_id=CREDENTIALS.phone_number_id,
        sender_id="99999",
        app_secret=CREDENTIALS.app_secret,
        verify_token=CREDENTIALS.verify_token,
    )
    assert resolve_staff_sender(session, unknown) is None


def test_document_validation_is_bounded_and_signature_checked():
    assert validate_document("rates.csv", "text/csv", b"sku,name\nA,Item\n").filename == "rates.csv"
    package = io.BytesIO()
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
    assert validate_document(
        "rates.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        package.getvalue(),
    ).filename == "rates.xlsx"
    with pytest.raises(MediaDownloadError):
        validate_document("rates.xlsx", "text/plain", b"not-a-zip")
