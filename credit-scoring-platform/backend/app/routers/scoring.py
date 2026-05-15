"""Credit scoring and loan application endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from ..database import get_db
from .. import models, schemas
from ..ml.credit_model import build_feature_vector, predict_credit_score

router = APIRouter(prefix="/api/scoring", tags=["Credit Scoring"])


@router.post("/score", response_model=schemas.CreditScoreResponse)
def score_application(request: schemas.CreditScoreRequest, db: Session = Depends(get_db)):
    client = db.query(models.Client).filter(models.Client.id == request.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    crb = db.query(models.CRBRecord).filter(
        models.CRBRecord.client_id == request.client_id
    ).order_by(models.CRBRecord.report_date.desc()).first()

    tu = db.query(models.TransUnionRecord).filter(
        models.TransUnionRecord.client_id == request.client_id
    ).order_by(models.TransUnionRecord.report_date.desc()).first()

    loan_count = db.query(models.Loan).filter(models.Loan.client_id == request.client_id).count()

    dob = client.date_of_birth
    age = (datetime.now() - dob).days // 365 if dob else 30

    client_data = {
        "monthly_income": client.monthly_income or 0,
        "age": age,
        "employment_status": client.employment_status or "",
        "gender": client.gender or "M",
    }
    crb_data = {
        "crb_score": crb.crb_score if crb else 500,
        "total_credit_facilities": crb.total_credit_facilities if crb else 0,
        "non_performing_accounts": crb.non_performing_accounts if crb else 0,
        "credit_utilization_ratio": crb.credit_utilization_ratio if crb else 0.5,
        "number_of_enquiries_last_6m": crb.number_of_enquiries_last_6m if crb else 0,
        "has_adverse_listing": crb.has_adverse_listing if crb else False,
        "months_since_last_default": crb.months_since_last_default if crb else None,
    }
    tu_data = {
        "tu_score": tu.tu_score if tu else 350,
        "payment_history_score": tu.payment_history_score if tu else 50,
        "delinquent_accounts": tu.delinquent_accounts if tu else 0,
        "collections_count": tu.collections_count if tu else 0,
        "highest_delinquency_dpd": tu.highest_delinquency_dpd if tu else 0,
        "length_of_credit_history_months": tu.length_of_credit_history_months if tu else 0,
        "credit_mix_score": tu.credit_mix_score if tu else 50,
    }
    loan_data = {
        "loan_amount": request.loan_amount,
        "loan_term_days": request.loan_term_days,
        "loan_sequence_nr": loan_count + 1,
        "warning_count": 2,
        "payment_method": request.payment_method,
    }

    features = build_feature_vector(client_data, crb_data, tu_data, loan_data)
    result = predict_credit_score(features, model_name="xgboost")

    # Persist prediction
    prediction = models.MLPrediction(
        client_id=request.client_id,
        model_name=result["model_used"],
        approval_probability=result["approval_probability"],
        credit_score=result["credit_score"],
        risk_band=result["risk_band"],
        decision=result["decision"],
    )
    db.add(prediction)
    db.commit()

    recommendation = _build_recommendation(result, crb_data, tu_data)

    return schemas.CreditScoreResponse(
        client_id=request.client_id,
        credit_score=result["credit_score"],
        approval_probability=result["approval_probability"],
        risk_band=result["risk_band"],
        decision=result["decision"],
        model_used=result["model_used"],
        crb_score=crb.crb_score if crb else None,
        tu_score=tu.tu_score if tu else None,
        recommendation=recommendation,
    )


def _build_recommendation(result: dict, crb: dict, tu: dict) -> str:
    if result["decision"] == "APPROVED":
        return "Application meets credit criteria. Proceed with disbursement."
    elif result["decision"] == "MANUAL_REVIEW":
        flags = []
        if crb.get("has_adverse_listing"):
            flags.append("adverse CRB listing")
        if crb.get("non_performing_accounts", 0) > 0:
            flags.append("non-performing accounts")
        if tu.get("delinquent_accounts", 0) > 0:
            flags.append("delinquent TransUnion accounts")
        return f"Manual review required. Flags: {', '.join(flags) or 'borderline score'}."
    else:
        return "Application rejected due to high credit risk. CRB/TransUnion adverse records detected."


@router.get("/clients/{client_id}/history")
def get_client_credit_history(client_id: int, db: Session = Depends(get_db)):
    client = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    loans = db.query(models.Loan).filter(models.Loan.client_id == client_id).all()
    crb = db.query(models.CRBRecord).filter(models.CRBRecord.client_id == client_id).first()
    tu = db.query(models.TransUnionRecord).filter(models.TransUnionRecord.client_id == client_id).first()
    predictions = db.query(models.MLPrediction).filter(models.MLPrediction.client_id == client_id).all()

    return {
        "client": {
            "id": client.id,
            "name": f"{client.first_name} {client.last_name}",
            "national_id": client.national_id,
            "employment_status": client.employment_status,
            "monthly_income": client.monthly_income,
            "county": client.county,
        },
        "crb": {
            "score": crb.crb_score if crb else None,
            "non_performing_accounts": crb.non_performing_accounts if crb else None,
            "has_adverse_listing": crb.has_adverse_listing if crb else None,
            "credit_utilization_ratio": crb.credit_utilization_ratio if crb else None,
        },
        "transunion": {
            "score": tu.tu_score if tu else None,
            "payment_history_score": tu.payment_history_score if tu else None,
            "delinquent_accounts": tu.delinquent_accounts if tu else None,
            "highest_delinquency_dpd": tu.highest_delinquency_dpd if tu else None,
        },
        "loans": [
            {
                "id": l.id,
                "status": l.loan_status,
                "principal": l.derived_principal_disbursed,
                "paid": l.derived_paid_total,
                "outstanding": l.derived_outstanding_total,
                "dpd": l.dpd,
                "issued_date": l.issued_date.isoformat() if l.issued_date else None,
            }
            for l in loans
        ],
        "ml_predictions": [
            {
                "model": p.model_name,
                "score": p.credit_score,
                "probability": p.approval_probability,
                "decision": p.decision,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in predictions
        ],
    }
