"""KPI and dashboard metrics endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from typing import List
from datetime import datetime, timedelta

from ..database import get_db
from .. import models, schemas

router = APIRouter(prefix="/api/kpis", tags=["KPIs"])


@router.get("/summary", response_model=schemas.KPISummary)
def get_kpi_summary(db: Session = Depends(get_db)):
    loans = db.query(models.Loan).all()
    total = len(loans)
    if total == 0:
        return schemas.KPISummary(
            total_applications=0, approval_rate=0, rejection_rate=0,
            default_rate=0, average_credit_score=0, total_disbursed=0,
            total_outstanding=0, total_collected=0, collection_rate=0,
            average_dpd=0, ptp_efficiency=0, npl_ratio=0
        )

    approved = sum(1 for l in loans if l.loan_status in ("ACTIVE", "PAID"))
    rejected = sum(1 for l in loans if l.loan_status == "REJECTED")
    defaulted = sum(1 for l in loans if l.loan_status == "DEFAULTED")

    total_disbursed = sum(l.derived_principal_disbursed or 0 for l in loans)
    total_outstanding = sum(l.derived_outstanding_total or 0 for l in loans)
    total_collected = sum(l.derived_paid_total or 0 for l in loans)
    collection_rate = total_collected / (total_disbursed or 1)

    avg_score = sum(l.credit_score or 0 for l in loans if l.credit_score) / max(1, sum(1 for l in loans if l.credit_score))
    avg_dpd = sum(l.dpd or 0 for l in loans) / total

    # PTP efficiency
    ptps = db.query(models.PromiseToPay).all()
    total_ptp = sum(1 for p in ptps if p.promise_status != "CANCELLED")
    paid_ptp = sum(1 for p in ptps if p.promise_status == "PAID")
    ptp_eff = paid_ptp / max(1, total_ptp)

    # NPL ratio (non-performing loans > 30 DPD)
    npl_amount = sum(l.derived_outstanding_total or 0 for l in loans if (l.dpd or 0) > 30)
    npl_ratio = npl_amount / max(1, total_outstanding)

    return schemas.KPISummary(
        total_applications=total,
        approval_rate=round(approved / total, 4),
        rejection_rate=round(rejected / total, 4),
        default_rate=round(defaulted / total, 4),
        average_credit_score=round(avg_score, 1),
        total_disbursed=round(total_disbursed, 2),
        total_outstanding=round(total_outstanding, 2),
        total_collected=round(total_collected, 2),
        collection_rate=round(collection_rate, 4),
        average_dpd=round(avg_dpd, 1),
        ptp_efficiency=round(ptp_eff, 4),
        npl_ratio=round(npl_ratio, 4),
    )


@router.get("/portfolio-at-risk")
def get_portfolio_at_risk(db: Session = Depends(get_db)):
    loans = db.query(models.Loan).filter(models.Loan.loan_status == "ACTIVE").all()
    total_outstanding = sum(l.derived_outstanding_total or 0 for l in loans) or 1

    def par(days):
        amt = sum(l.derived_outstanding_total or 0 for l in loans if (l.dpd or 0) > days)
        return round(amt / total_outstanding, 4)

    return {
        "par_1": par(1),
        "par_7": par(7),
        "par_30": par(30),
        "par_60": par(60),
        "par_90": par(90),
    }


@router.get("/risk-band-distribution")
def get_risk_band_distribution(db: Session = Depends(get_db)):
    bands = {"LOW": (0.75, 1.0), "MEDIUM": (0.55, 0.75), "HIGH": (0.40, 0.55), "VERY_HIGH": (0.0, 0.40)}
    loans = db.query(models.Loan).all()
    total = len(loans) or 1
    result = []
    for band, (low, high) in bands.items():
        matching = [l for l in loans if l.ml_approval_probability is not None
                    and low <= l.ml_approval_probability < high]
        count = len(matching)
        amount = sum(l.derived_principal_disbursed or 0 for l in matching)
        result.append({
            "band": band,
            "count": count,
            "percentage": round(count / total * 100, 2),
            "total_amount": round(amount, 2),
        })
    return result


@router.get("/monthly-trends")
def get_monthly_trends(db: Session = Depends(get_db)):
    loans = db.query(models.Loan).all()
    trends = {}
    for loan in loans:
        if not loan.issued_date:
            continue
        key = loan.issued_date.strftime("%Y-%m")
        if key not in trends:
            trends[key] = {"disbursements": 0, "repayments": 0, "defaults": 0, "new_clients": 0, "repeat_clients": 0}
        trends[key]["disbursements"] += loan.derived_principal_disbursed or 0
        trends[key]["repayments"] += loan.derived_paid_total or 0
        if loan.loan_status == "DEFAULTED":
            trends[key]["defaults"] += 1
        if loan.loan_sequence_nr == 1:
            trends[key]["new_clients"] += 1
        else:
            trends[key]["repeat_clients"] += 1

    return [
        {"month": k, **{kk: round(v, 2) if isinstance(v, float) else v for kk, v in vals.items()}}
        for k, vals in sorted(trends.items())[-12:]
    ]


@router.get("/collection-agent-performance")
def get_agent_performance(db: Session = Depends(get_db)):
    ptps = db.query(models.PromiseToPay).all()
    agents = {}
    for p in ptps:
        agent = p.created_by or "unknown"
        if agent not in agents:
            agents[agent] = {"total_ptp": 0, "ptp_paid": 0, "total_amount": 0, "amount_collected": 0}
        if p.promise_status != "CANCELLED":
            agents[agent]["total_ptp"] += 1
            agents[agent]["total_amount"] += p.promise_amount or 0
        if p.promise_status == "PAID":
            agents[agent]["ptp_paid"] += 1
            agents[agent]["amount_collected"] += p.amount_paid or 0
        elif p.promise_status == "PARTIALLY_PAID":
            agents[agent]["amount_collected"] += p.amount_paid or 0

    result = []
    for agent, data in agents.items():
        eff = data["ptp_paid"] / max(1, data["total_ptp"])
        coll_rate = data["amount_collected"] / max(1, data["total_amount"])
        result.append({
            "agent_name": agent,
            "total_ptp": data["total_ptp"],
            "ptp_paid": data["ptp_paid"],
            "ptp_efficiency": round(eff, 4),
            "total_ptp_amount": round(data["total_amount"], 2),
            "amount_collected": round(data["amount_collected"], 2),
            "collection_rate": round(coll_rate, 4),
        })
    return sorted(result, key=lambda x: x["ptp_efficiency"], reverse=True)


@router.get("/credit-score-distribution")
def get_credit_score_distribution(db: Session = Depends(get_db)):
    loans = db.query(models.Loan).filter(models.Loan.credit_score.isnot(None)).all()
    bins = [(300, 450, "Poor"), (450, 580, "Fair"), (580, 670, "Good"), (670, 740, "Very Good"), (740, 850, "Excellent")]
    result = []
    for low, high, label in bins:
        count = sum(1 for l in loans if low <= (l.credit_score or 0) < high)
        result.append({"range": f"{low}-{high}", "label": label, "count": count})
    return result


@router.get("/dpd-buckets")
def get_dpd_buckets(db: Session = Depends(get_db)):
    loans = db.query(models.Loan).filter(models.Loan.loan_status == "ACTIVE").all()
    buckets = [(0, 0, "Current"), (1, 7, "1-7 DPD"), (8, 30, "8-30 DPD"),
               (31, 60, "31-60 DPD"), (61, 90, "61-90 DPD"), (91, 9999, "90+ DPD")]
    result = []
    for low, high, label in buckets:
        matching = [l for l in loans if low <= (l.dpd or 0) <= high]
        count = len(matching)
        amount = sum(l.derived_outstanding_total or 0 for l in matching)
        result.append({"bucket": label, "count": count, "outstanding_amount": round(amount, 2)})
    return result


@router.get("/cashflow")
def get_cashflow(db: Session = Depends(get_db)):
    payments = db.query(models.Payment).filter(models.Payment.reversed == False).all()
    daily = {}
    for p in payments:
        if not p.value_date:
            continue
        key = p.value_date.strftime("%Y-%m-%d")
        if key not in daily:
            daily[key] = {"disbursements": 0, "repayments": 0, "charges": 0}
        if p.payment_type == "OUTGOING" and p.tx_type == "Disbursement/Settle":
            daily[key]["disbursements"] += p.amount or 0
        elif p.payment_type == "INCOMING" and p.tx_type == "Loan/Repay":
            daily[key]["repayments"] += p.amount or 0
        elif p.payment_type == "OUTGOING" and p.tx_type == "Other":
            daily[key]["charges"] += p.amount or 0

    return [
        {"date": k, **{kk: round(v, 2) for kk, v in vals.items()}}
        for k, vals in sorted(daily.items())[-90:]
    ]
