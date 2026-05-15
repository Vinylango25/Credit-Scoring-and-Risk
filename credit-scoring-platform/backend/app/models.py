from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
import enum


class LoanStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    PAID = "PAID"
    DEFAULTED = "DEFAULTED"
    REJECTED = "REJECTED"


class LoanQueue(str, enum.Enum):
    NORMAL = "NORMAL"
    EARLY_COLLECTIONS = "EARLY_COLLECTIONS"
    LATE_COLLECTIONS = "LATE_COLLECTIONS"
    DEFAULTED = "DEFAULTED"


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    national_id = Column(String(20), unique=True, index=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    email = Column(String(200))
    mobile_phone = Column(String(20))
    date_of_birth = Column(DateTime)
    gender = Column(String(10))
    county = Column(String(100))
    employment_status = Column(String(50))
    monthly_income = Column(Float)
    created_at = Column(DateTime, server_default=func.now())

    loans = relationship("Loan", back_populates="client")
    crb_records = relationship("CRBRecord", back_populates="client")
    transunion_records = relationship("TransUnionRecord", back_populates="client")


class Loan(Base):
    __tablename__ = "loans"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    loan_status = Column(String(20), default="ACTIVE")
    loan_queue = Column(String(30), default="NORMAL")
    loan_sequence_nr = Column(Integer, default=1)  # 1=new, >1=repeat
    issued_date = Column(DateTime)
    due_date = Column(DateTime)
    closed_date = Column(DateTime, nullable=True)
    derived_principal_disbursed = Column(Float)
    derived_charged_total = Column(Float)
    derived_paid_total = Column(Float, default=0)
    derived_outstanding_total = Column(Float)
    derived_past_due_total = Column(Float, default=0)
    dpd = Column(Integer, default=0)  # Days Past Due
    interest_rate = Column(Float)
    loan_term_days = Column(Integer)
    payment_method = Column(String(20))
    credit_score = Column(Float, nullable=True)
    ml_approval_probability = Column(Float, nullable=True)
    ml_model_used = Column(String(50), nullable=True)
    warning_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    client = relationship("Client", back_populates="loans")
    payments = relationship("Payment", back_populates="loan")
    promises = relationship("PromiseToPay", back_populates="loan")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    loan_id = Column(Integer, ForeignKey("loans.id"))
    payment_type = Column(String(20))  # INCOMING / OUTGOING
    tx_type = Column(String(50))
    amount = Column(Float)
    value_date = Column(DateTime)
    reversed = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

    loan = relationship("Loan", back_populates="payments")


class PromiseToPay(Base):
    __tablename__ = "promises_to_pay"

    id = Column(Integer, primary_key=True, index=True)
    loan_id = Column(Integer, ForeignKey("loans.id"))
    created_by = Column(String(100))
    promise_status = Column(String(30))  # ACTIVE, PAID, PARTIALLY_PAID, CANCELLED
    promise_amount = Column(Float)
    promise_date = Column(DateTime)
    due_date = Column(DateTime)
    amount_paid = Column(Float, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    loan = relationship("Loan", back_populates="promises")


class CRBRecord(Base):
    """Credit Reference Bureau (CRB) data - simulating Kenya CRB"""
    __tablename__ = "crb_records"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    crb_score = Column(Integer)  # 300-850
    total_credit_facilities = Column(Integer)
    performing_accounts = Column(Integer)
    non_performing_accounts = Column(Integer)
    total_outstanding_debt = Column(Float)
    total_credit_limit = Column(Float)
    credit_utilization_ratio = Column(Float)
    months_since_last_default = Column(Integer, nullable=True)
    number_of_enquiries_last_6m = Column(Integer)
    has_adverse_listing = Column(Boolean, default=False)
    adverse_listing_amount = Column(Float, default=0)
    report_date = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

    client = relationship("Client", back_populates="crb_records")


class TransUnionRecord(Base):
    """TransUnion credit bureau data"""
    __tablename__ = "transunion_records"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    tu_score = Column(Integer)  # 0-710 TransUnion Africa scale
    payment_history_score = Column(Float)  # 0-100
    amounts_owed_score = Column(Float)
    length_of_credit_history_months = Column(Integer)
    new_credit_score = Column(Float)
    credit_mix_score = Column(Float)
    total_accounts = Column(Integer)
    open_accounts = Column(Integer)
    closed_accounts = Column(Integer)
    delinquent_accounts = Column(Integer)
    collections_count = Column(Integer)
    public_records_count = Column(Integer)
    highest_delinquency_dpd = Column(Integer)
    report_date = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

    client = relationship("Client", back_populates="transunion_records")


class MLPrediction(Base):
    """Store ML model predictions for audit trail"""
    __tablename__ = "ml_predictions"

    id = Column(Integer, primary_key=True, index=True)
    loan_id = Column(Integer, ForeignKey("loans.id"), nullable=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    model_name = Column(String(50))
    approval_probability = Column(Float)
    credit_score = Column(Float)
    risk_band = Column(String(20))  # LOW, MEDIUM, HIGH, VERY_HIGH
    decision = Column(String(20))   # APPROVED, REJECTED, MANUAL_REVIEW
    feature_importance = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime, server_default=func.now())
