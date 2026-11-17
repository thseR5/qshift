from io import BytesIO

from openpyxl import Workbook
from sqlalchemy import select

from qshift.models import RateEntry, User
from qshift.services import (
    create_project,
    import_quotation,
    import_rate_card,
    seed_demo,
    verify_rate,
)


def test_imported_rate_is_unverified_until_approver_confirms(session):
    seed_demo(session)
    owner = session.scalar(select(User).where(User.id == "user-owner"))
    designer = session.scalar(select(User).where(User.id == "user-designer"))
    assert owner and designer
    result = import_rate_card(
        session,
        owner,
        "rates.csv",
        b"sku,name,category,unit,rate_paise\nNEW-1,New quartz,Countertop,sqft,70000\n",
    )
    assert result["accepted"] == 1
    entry = session.scalar(select(RateEntry).where(RateEntry.sku == "NEW-1"))
    assert entry and not entry.verified
    try:
        verify_rate(session, designer, entry.id)
    except PermissionError:
        pass
    else:
        raise AssertionError("Designer must not verify rates")
    verify_rate(session, owner, entry.id)
    assert entry.verified
    project = create_project(session, owner, "Test Loft", "Fictional client")
    book = Workbook()
    sheet = book.active
    sheet.append(["room", "sku", "quantity"])
    sheet.append(["Kitchen", "NEW-1", 2.5])
    payload = BytesIO()
    book.save(payload)
    quotation = import_quotation(session, owner, project["id"], "quote.xlsx", payload.getvalue())
    assert quotation["valid_rows"] == 1
    assert quotation["total"] == "₹1,750"
