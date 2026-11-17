"""Tenant-scoped WhatsApp account and staff identity resolution.

The fixture pilot uses this same resolver, but registration is an operator action. An inbound
sender can never create its own firm, role or enrollment through chat.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from qshift.models import (
    Firm,
    StaffEnrollment,
    User,
    WhatsAppBusinessAccount,
    WhatsAppPhoneNumber,
)
from qshift.services import uid
from qshift.whatsapp_webhook import WebhookCredentials


@dataclass(frozen=True)
class ResolvedStaff:
    firm_id: str
    user_id: str
    role: str
    enrollment_id: str
    phone_number_id: str


def register_staff_identity(
    session: Session,
    credentials: WebhookCredentials,
    *,
    firm_id: str,
    user_id: str,
    consent_reference: str,
) -> ResolvedStaff:
    """Create or return an operator-authorized fixture/staging enrollment."""

    firm = session.get(Firm, firm_id)
    user = session.scalar(select(User).where(User.id == user_id, User.firm_id == firm_id))
    if firm is None or user is None or not firm.illustrative:
        raise ValueError("Only an existing tenant and staff user can be enrolled")
    if user.role not in {"OWNER", "APPROVER", "DESIGNER"}:
        raise PermissionError("This staff role cannot use the quotation workflow")
    account = session.scalar(
        select(WhatsAppBusinessAccount).where(
            WhatsAppBusinessAccount.firm_id == firm_id,
            WhatsAppBusinessAccount.provider_account_id == credentials.account_id,
        )
    )
    if account is None:
        account = WhatsAppBusinessAccount(
            id=uid(), firm_id=firm_id, provider_account_id=credentials.account_id, status="active"
        )
        session.add(account)
        session.flush()
    phone = session.scalar(
        select(WhatsAppPhoneNumber).where(
            WhatsAppPhoneNumber.firm_id == firm_id,
            WhatsAppPhoneNumber.provider_phone_number_id == credentials.phone_number_id,
        )
    )
    if phone is None:
        phone = WhatsAppPhoneNumber(
            id=uid(),
            firm_id=firm_id,
            business_account_id=account.id,
            provider_phone_number_id=credentials.phone_number_id,
            status="active",
        )
        session.add(phone)
        session.flush()
    enrollment = session.scalar(
        select(StaffEnrollment).where(
            StaffEnrollment.firm_id == firm_id,
            StaffEnrollment.phone_number_id == phone.id,
            StaffEnrollment.provider_sender_id == credentials.sender_id,
        )
    )
    if enrollment is None:
        enrollment = StaffEnrollment(
            id=uid(),
            firm_id=firm_id,
            phone_number_id=phone.id,
            provider_sender_id=credentials.sender_id,
            user_id=user.id,
            consent_reference=consent_reference,
            status="active",
        )
        session.add(enrollment)
    elif enrollment.status != "active" or enrollment.user_id != user.id:
        raise PermissionError("This WhatsApp sender is not actively enrolled for this firm")
    return ResolvedStaff(firm_id, user.id, user.role, enrollment.id, phone.id)


def resolve_staff_sender(
    session: Session, credentials: WebhookCredentials
) -> ResolvedStaff | None:
    """Resolve provider account + phone + sender; unknown identities return None."""

    row = session.execute(
        select(StaffEnrollment, WhatsAppPhoneNumber, WhatsAppBusinessAccount, User)
        .join(
            WhatsAppPhoneNumber,
            (WhatsAppPhoneNumber.id == StaffEnrollment.phone_number_id)
            & (WhatsAppPhoneNumber.firm_id == StaffEnrollment.firm_id),
        )
        .join(
            WhatsAppBusinessAccount,
            (WhatsAppBusinessAccount.id == WhatsAppPhoneNumber.business_account_id)
            & (WhatsAppBusinessAccount.firm_id == StaffEnrollment.firm_id),
        )
        .join(User, (User.id == StaffEnrollment.user_id) & (User.firm_id == StaffEnrollment.firm_id))
        .join(Firm, Firm.id == StaffEnrollment.firm_id)
        .where(
            WhatsAppBusinessAccount.provider_account_id == credentials.account_id,
            WhatsAppPhoneNumber.provider_phone_number_id == credentials.phone_number_id,
            StaffEnrollment.provider_sender_id == credentials.sender_id,
            StaffEnrollment.status == "active",
            WhatsAppBusinessAccount.status == "active",
            WhatsAppPhoneNumber.status == "active",
            Firm.illustrative.is_(True),
        )
    ).first()
    if row is None:
        return None
    enrollment, phone, _account, user = row
    return ResolvedStaff(enrollment.firm_id, user.id, user.role, enrollment.id, phone.id)
