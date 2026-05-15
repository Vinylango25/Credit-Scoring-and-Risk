"""Loan management endpoints - mirrors SQL Reports queries."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional
from datetime import datetime

from ..database import get_db
from .. import models

router = APIRouter(prefix="/api/loans", tags=["Loans"])


@router.get("/collections")
def get_collections(
    queue: Optional[str] = Query(None, description="EARLY_COLLECTIONS | LATE_COLLECTIONS | DEFAULTED"),
    db: Session = Depends(get_db)
):
    """Dialer Accounts - Early/Late Collections (mirrors SQL Reports query)."""
    query = db.query(models.Loan).filter(
        models.Loan.loan_status == "ACTIVE",
        models.Loan.dpd > 0
    )
    if queue:
        query = query.filter(models.Loan.loan_queue == queue)
    else:
        query = query.filter(models.Loan.loan_queue.in_(
            ["EARLY_COLLECTIONS", "LATE_COLLECTIONS", "DEFAULTED"]
        ))

    loans = query.order_by(models.Loan.dpd.asc()).all()
    result = []
    for loan in loans:
        client = loan.client
        paid_status = (
            "Partially Paid" if (loan.derived_paid_total or 0) > 0
            else "Not Paid"
        )
        result.append({
            "loan_id": loan.id,
            "client_id": loan.client_id,
            "client_name": f"{client.first_name} {client.last_name}" if client else "",
            "national_id": client.national_id if client else "",
            "mobile_phone": client.mobile_phone if client else "",
            "email": client.email if client else "",
            "issued_date": loan.issued_date.isoformat() if loan.issued_date else None,
            "due_date": loan.due_date.isoformat() if loan.due_date else None,
            "dpd": loan.dpd,
            "payment_status": paid_status,
            "loan_type": "new" if loan.loan_sequence_nr == 1 else "repeat",
            "loan_queue": loan.loan_queue,
            "principal_disbursed": loan.derived_principal_disbursed,
            "paid_total": loan.derived_paid_total,
            "outstanding_total": loan.derived_outstanding_total,
        })
    return result


@router.get("/disbursements-vs-repayments")
def get_disbursements_vs_repayments(
    issued_date_from: Optional[str] = None,
    issued_date_to: Optional[str] = None,
    client_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Disbursements vs Repayments report."""
    query = db.query(models.Loan).filter(
        models.Loan.loan_status.in_(["ACTIVE", "PAID"])
    )
    if issued_date_from:
        query = query.filter(models.Loan.issued_date >= datetime.fromisoformat(issued_date_from))
    if issued_date_to:
        query = query.filter(models.Loan.issued_date <= datetime.fromisoformat(issued_date_to))
    if client_type == "New":
        query = query.filter(models.Loan.loan_sequence_nr == 1)
    elif client_type == "Repeated":
        query = query.filter(models.Loan.loan_sequence_nr > 1)

    loans = query.order_by(models.Loan.issued_date).all()
    return [
        {
            "loan_id": l.id,
            "client_id": l.client_id,
            "loan_status": l.loan_status,
            "issued_date": l.issued_date.isoformat() if l.issued_date else None,
            "due_date": l.due_date.isoformat() if l.due_date else None,
            "client_type": "New" if l.loan_sequence_nr == 1 else "Repeated",
            "payment_status": (
                "Paid" if l.loan_status == "PAID"
                else ("Not_paid" if (l.derived_paid_total or 0) == 0 else "Partially_paid")
            ),
            "principal_disbursed": l.derived_principal_disbursed,
            "charged_total": l.derived_charged_total,
            "paid_total": l.derived_paid_total,
            "outstanding_total": l.derived_outstanding_total,
            "past_due_total": l.derived_past_due_total,
        }
        for l in loans
    ]


@router.get("/expected-vs-paid")
def get_expected_vs_paid(
    due_date_from: Optional[str] = None,
    due_date_to: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Expected vs Paid by Due Date."""
    query = db.query(models.Loan)
    if due_date_from:
        query = query.filter(models.Loan.due_date >= datetime.fromisoformat(due_date_from))
    if due_date_to:
        query = query.filter(models.Loan.due_date <= datetime.fromisoformat(due_date_to))

    loans = query.order_by(models.Loan.due_date).all()
    daily = {}
    for l in loans:
        if not l.due_date:
            continue
        key = l.due_date.strftime("%Y-%m-%d")
        if key not in daily:
            daily[key] = {"charged": 0, "paid": 0, "outstanding": 0}
        daily[key]["charged"] += l.derived_charged_total or 0
        daily[key]["paid"] += l.derived_paid_total or 0
        daily[key]["outstanding"] += l.derived_outstanding_total or 0

    return [
        {
            "due_date": k,
            "total_charged": round(v["charged"], 2),
            "total_paid": round(v["paid"], 2),
            "total_outstanding": round(v["outstanding"], 2),
        }
        for k, v in sorted(daily.items())
    ]
