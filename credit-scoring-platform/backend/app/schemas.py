from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ClientBase(BaseModel):
    national_id: str
    first_name: str
    last_name: str
    email: str
    mobile_phone: str
    date_of_birth: datetime
    gender: str
    county: str
    employment_status: str
    monthly_income: float


class ClientCreate(ClientBase):
    pass


class ClientOut(ClientBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class LoanOut(BaseModel):
    id: int
    client_id: int
    loan_status: str
    loan_queue: str
    issued_date: datetime
    due_date: datetime
    derived_principal_disbursed: float
    derived_paid_total: float
    derived_outstanding_total: float
    dpd: int
    credit_score: Optional[float]
    ml_approval_probability: Optional[float]

    class Config:
        from_attributes = True


class CRBRecordOut(BaseModel):
    id: int
    client_id: int
    crb_score: int
    total_credit_facilities: int
    non_performing_accounts: int
    total_outstanding_debt: float
    credit_utilization_ratio: float
    has_adverse_listing: bool
    report_date: datetime

    class Config:
        from_attributes = True


class TransUnionRecordOut(BaseModel):
    id: int
    client_id: int
    tu_score: int
    payment_history_score: float
    delinquent_accounts: int
    collections_count: int
    highest_delinquency_dpd: int
    report_date: datetime

    class Config:
        from_attributes = True


class CreditScoreRequest(BaseModel):
    client_id: int
    loan_amount: float
    loan_term_days: int
    payment_method: str = "MOBILE_MONEY"


class CreditScoreResponse(BaseModel):
    client_id: int
    credit_score: float
    approval_probability: float
    risk_band: str
    decision: str
    model_used: str
    crb_score: Optional[int]
    tu_score: Optional[int]
    recommendation: str


# KPI / Dashboard schemas
class KPISummary(BaseModel):
    total_applications: int
    approval_rate: float
    rejection_rate: float
    default_rate: float
    average_credit_score: float
    total_disbursed: float
    total_outstanding: float
    total_collected: float
    collection_rate: float
    average_dpd: float
    ptp_efficiency: float
    npl_ratio: float


class PortfolioAtRisk(BaseModel):
    par_1: float   # PAR > 1 day
    par_7: float   # PAR > 7 days
    par_30: float  # PAR > 30 days
    par_60: float  # PAR > 60 days
    par_90: float  # PAR > 90 days


class RiskBandDistribution(BaseModel):
    band: str
    count: int
    percentage: float
    total_amount: float


class MonthlyTrend(BaseModel):
    month: str
    disbursements: float
    repayments: float
    defaults: float
    new_clients: int
    repeat_clients: int


class CollectionAgentPerformance(BaseModel):
    agent_name: str
    total_ptp: int
    ptp_paid: int
    ptp_efficiency: float
    total_ptp_amount: float
    amount_collected: float
    collection_rate: float
