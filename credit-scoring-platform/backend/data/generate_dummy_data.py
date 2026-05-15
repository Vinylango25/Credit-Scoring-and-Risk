"""
Generates realistic dummy data for:
- Clients (Kenyan names, counties, demographics)
- Loans with payment history
- CRB (Credit Reference Bureau) records
- TransUnion credit bureau records
- ML training dataset
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import random
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from faker import Faker
from sqlalchemy.orm import Session

from app.database import SessionLocal, engine
from app import models

fake = Faker(["en_GB"])
random.seed(42)
np.random.seed(42)

KENYAN_COUNTIES = [
    "Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret", "Thika",
    "Malindi", "Kitale", "Garissa", "Kakamega", "Nyeri", "Machakos",
    "Meru", "Kisii", "Kericho", "Embu", "Lamu", "Wajir"
]

KENYAN_FIRST_NAMES_M = [
    "James", "John", "Peter", "David", "Michael", "Joseph", "Daniel",
    "Samuel", "Paul", "George", "Kevin", "Brian", "Eric", "Dennis",
    "Patrick", "Francis", "Charles", "Robert", "Thomas", "Andrew"
]

KENYAN_FIRST_NAMES_F = [
    "Mary", "Grace", "Faith", "Joyce", "Agnes", "Caroline", "Judy",
    "Beatrice", "Catherine", "Elizabeth", "Ann", "Rose", "Jane",
    "Esther", "Mercy", "Lydia", "Priscilla", "Naomi", "Ruth", "Sarah"
]

KENYAN_LAST_NAMES = [
    "Kamau", "Wanjiku", "Ochieng", "Otieno", "Mwangi", "Njoroge",
    "Kariuki", "Mutua", "Kibet", "Chebet", "Waweru", "Gitau",
    "Omondi", "Achieng", "Nyambura", "Wangari", "Kimani", "Ndung'u",
    "Mugo", "Kiptoo", "Rotich", "Koech", "Bett", "Sang", "Ruto"
]

COLLECTION_AGENTS = [
    "andrew.kibet", "benadette.omulo", "caroline.mutuse",
    "judy.kinyua", "sammy.chege"
]


def random_date(start_days_ago: int, end_days_ago: int = 0) -> datetime:
    delta = random.randint(end_days_ago, start_days_ago)
    return datetime.now() - timedelta(days=delta)


def generate_client(client_id: int) -> dict:
    gender = random.choice(["M", "F"])
    first_name = random.choice(KENYAN_FIRST_NAMES_M if gender == "M" else KENYAN_FIRST_NAMES_F)
    last_name = random.choice(KENYAN_LAST_NAMES)
    dob = random_date(365 * 60, 365 * 22)  # 22-60 years old
    employment = random.choices(
        ["EMPLOYED", "SELF_EMPLOYED", "UNEMPLOYED", "STUDENT"],
        weights=[50, 30, 15, 5]
    )[0]
    income_map = {
        "EMPLOYED": random.uniform(25000, 200000),
        "SELF_EMPLOYED": random.uniform(15000, 150000),
        "UNEMPLOYED": random.uniform(0, 10000),
        "STUDENT": random.uniform(5000, 20000),
    }
    return {
        "national_id": f"3{random.randint(1000000, 9999999)}",
        "first_name": first_name,
        "last_name": last_name,
        "email": f"{first_name.lower()}.{last_name.lower()}{client_id}@email.com",
        "mobile_phone": f"07{random.randint(10000000, 99999999)}",
        "date_of_birth": dob,
        "gender": gender,
        "county": random.choice(KENYAN_COUNTIES),
        "employment_status": employment,
        "monthly_income": round(income_map[employment], 2),
    }


def generate_crb_record(client_id: int, is_risky: bool = False) -> dict:
    if is_risky:
        crb_score = random.randint(300, 550)
        npa = random.randint(1, 5)
        adverse = random.random() < 0.4
    else:
        crb_score = random.randint(550, 850)
        npa = random.randint(0, 1)
        adverse = random.random() < 0.05

    total_facilities = random.randint(1, 8)
    performing = total_facilities - npa
    total_debt = random.uniform(5000, 500000)
    credit_limit = total_debt / random.uniform(0.3, 0.9)

    return {
        "client_id": client_id,
        "crb_score": crb_score,
        "total_credit_facilities": total_facilities,
        "performing_accounts": max(0, performing),
        "non_performing_accounts": npa,
        "total_outstanding_debt": round(total_debt, 2),
        "total_credit_limit": round(credit_limit, 2),
        "credit_utilization_ratio": round(total_debt / credit_limit, 3),
        "months_since_last_default": random.randint(6, 60) if npa > 0 else None,
        "number_of_enquiries_last_6m": random.randint(0, 10),
        "has_adverse_listing": adverse,
        "adverse_listing_amount": round(random.uniform(1000, 50000), 2) if adverse else 0,
        "report_date": random_date(30, 0),
    }


def generate_transunion_record(client_id: int, is_risky: bool = False) -> dict:
    if is_risky:
        tu_score = random.randint(100, 400)
        delinquent = random.randint(1, 4)
        collections = random.randint(0, 3)
        max_dpd = random.randint(30, 180)
    else:
        tu_score = random.randint(400, 710)
        delinquent = 0
        collections = 0
        max_dpd = random.randint(0, 15)

    total_accounts = random.randint(2, 10)
    open_acc = random.randint(1, total_accounts)

    return {
        "client_id": client_id,
        "tu_score": tu_score,
        "payment_history_score": round(random.uniform(40, 100) if not is_risky else random.uniform(10, 60), 2),
        "amounts_owed_score": round(random.uniform(30, 100), 2),
        "length_of_credit_history_months": random.randint(6, 120),
        "new_credit_score": round(random.uniform(40, 100), 2),
        "credit_mix_score": round(random.uniform(30, 100), 2),
        "total_accounts": total_accounts,
        "open_accounts": open_acc,
        "closed_accounts": total_accounts - open_acc,
        "delinquent_accounts": delinquent,
        "collections_count": collections,
        "public_records_count": random.randint(0, 2),
        "highest_delinquency_dpd": max_dpd,
        "report_date": random_date(30, 0),
    }


def generate_loan(client_id: int, sequence_nr: int, is_risky: bool = False) -> dict:
    issued = random_date(365, 30)
    term = random.choice([7, 14, 21, 30, 60, 90])
    due = issued + timedelta(days=term)
    principal = round(random.uniform(1000, 50000), 2)
    interest_rate = random.uniform(0.05, 0.25)
    charged = round(principal * (1 + interest_rate), 2)

    if is_risky:
        paid_pct = random.uniform(0, 0.5)
        dpd = random.randint(15, 120)
        status = random.choice(["ACTIVE", "DEFAULTED"])
        queue = random.choice(["EARLY_COLLECTIONS", "LATE_COLLECTIONS", "DEFAULTED"])
    else:
        paid_pct = random.uniform(0.7, 1.0)
        dpd = random.randint(0, 5)
        status = random.choice(["PAID", "ACTIVE"])
        queue = "NORMAL"

    paid = round(charged * paid_pct, 2)
    outstanding = round(charged - paid, 2)
    past_due = outstanding if dpd > 0 else 0

    return {
        "client_id": client_id,
        "loan_status": status,
        "loan_queue": queue,
        "loan_sequence_nr": sequence_nr,
        "issued_date": issued,
        "due_date": due,
        "closed_date": due + timedelta(days=dpd) if status == "PAID" else None,
        "derived_principal_disbursed": principal,
        "derived_charged_total": charged,
        "derived_paid_total": paid,
        "derived_outstanding_total": outstanding,
        "derived_past_due_total": past_due,
        "dpd": dpd,
        "interest_rate": round(interest_rate, 4),
        "loan_term_days": term,
        "payment_method": random.choice(["MOBILE_MONEY", "BANK_TRANSFER", "CASH"]),
        "warning_count": random.randint(1, 10),
        "ml_approval_probability": round(random.uniform(0.3, 0.95), 4),
        "ml_model_used": random.choice(["xgboost", "random_forest", "lightgbm"]),
        "credit_score": round(random.uniform(300, 850), 1),
    }


def generate_payments(loan_id: int, loan: dict) -> list:
    payments = []
    # Disbursement
    payments.append({
        "loan_id": loan_id,
        "payment_type": "OUTGOING",
        "tx_type": "Disbursement/Settle",
        "amount": loan["derived_principal_disbursed"],
        "value_date": loan["issued_date"],
        "reversed": False,
    })
    # Repayments
    if loan["derived_paid_total"] > 0:
        num_payments = random.randint(1, 3)
        remaining = loan["derived_paid_total"]
        for i in range(num_payments):
            amt = remaining if i == num_payments - 1 else round(remaining * random.uniform(0.3, 0.7), 2)
            remaining -= amt
            payments.append({
                "loan_id": loan_id,
                "payment_type": "INCOMING",
                "tx_type": "Loan/Repay",
                "amount": amt,
                "value_date": loan["issued_date"] + timedelta(days=random.randint(1, loan["loan_term_days"])),
                "reversed": False,
            })
    return payments


def generate_promises(loan_id: int, loan: dict) -> list:
    if loan["dpd"] == 0:
        return []
    promises = []
    agent = random.choice(COLLECTION_AGENTS)
    status = random.choice(["ACTIVE", "PAID", "PARTIALLY_PAID", "CANCELLED"])
    promise_amount = round(loan["derived_outstanding_total"] * random.uniform(0.3, 1.0), 2)
    promise_date = datetime.now() - timedelta(days=random.randint(1, 30))
    due_date = promise_date + timedelta(days=random.randint(3, 14))
    amount_paid = round(promise_amount * random.uniform(0, 1), 2) if status in ("PAID", "PARTIALLY_PAID") else 0

    promises.append({
        "loan_id": loan_id,
        "created_by": agent,
        "promise_status": status,
        "promise_amount": promise_amount,
        "promise_date": promise_date,
        "due_date": due_date,
        "amount_paid": amount_paid,
    })
    return promises


def seed_database(n_clients: int = 500):
    """Seed the database with dummy data."""
    models.Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    print(f"Seeding {n_clients} clients with loans, CRB, and TransUnion data...")

    for i in range(1, n_clients + 1):
        is_risky = random.random() < 0.25  # 25% risky clients

        # Client
        client_data = generate_client(i)
        client = models.Client(**client_data)
        db.add(client)
        db.flush()

        # CRB Record
        crb_data = generate_crb_record(client.id, is_risky)
        db.add(models.CRBRecord(**crb_data))

        # TransUnion Record
        tu_data = generate_transunion_record(client.id, is_risky)
        db.add(models.TransUnionRecord(**tu_data))

        # Loans (1-3 per client)
        n_loans = random.randint(1, 3)
        for seq in range(1, n_loans + 1):
            loan_data = generate_loan(client.id, seq, is_risky)
            loan = models.Loan(**loan_data)
            db.add(loan)
            db.flush()

            # Payments
            for p in generate_payments(loan.id, loan_data):
                db.add(models.Payment(**p))

            # Promises to Pay
            for ptp in generate_promises(loan.id, loan_data):
                db.add(models.PromiseToPay(**ptp))

        if i % 100 == 0:
            db.commit()
            print(f"  {i}/{n_clients} clients seeded...")

    db.commit()
    db.close()
    print("Database seeding complete.")


def generate_ml_training_data(n_samples: int = 5000) -> pd.DataFrame:
    """Generate a training dataset for ML models."""
    records = []
    for i in range(n_samples):
        is_default = random.random() < 0.20  # 20% default rate
        is_risky = is_default or random.random() < 0.15

        crb = generate_crb_record(i, is_risky)
        tu = generate_transunion_record(i, is_risky)
        loan = generate_loan(i, random.randint(1, 5), is_risky)
        age = random.randint(22, 60)
        income = random.uniform(5000, 200000)
        employed = random.random() < 0.7

        records.append({
            "monthly_income": income,
            "age": age,
            "is_employed": int(employed),
            "is_male": random.randint(0, 1),
            "loan_amount": loan["derived_principal_disbursed"],
            "loan_term_days": loan["loan_term_days"],
            "loan_sequence_nr": loan["loan_sequence_nr"],
            "warning_count": loan["warning_count"],
            "is_mobile_money": 1 if loan["payment_method"] == "MOBILE_MONEY" else 0,
            "crb_score": crb["crb_score"],
            "total_credit_facilities": crb["total_credit_facilities"],
            "non_performing_accounts": crb["non_performing_accounts"],
            "credit_utilization_ratio": crb["credit_utilization_ratio"],
            "enquiries_last_6m": crb["number_of_enquiries_last_6m"],
            "has_adverse_listing": int(crb["has_adverse_listing"]),
            "months_since_default": crb["months_since_last_default"] or 999,
            "tu_score": tu["tu_score"],
            "payment_history_score": tu["payment_history_score"],
            "delinquent_accounts": tu["delinquent_accounts"],
            "collections_count": tu["collections_count"],
            "highest_delinquency_dpd": tu["highest_delinquency_dpd"],
            "credit_history_months": tu["length_of_credit_history_months"],
            "credit_mix_score": tu["credit_mix_score"],
            "default": int(is_default),
        })

    return pd.DataFrame(records)


if __name__ == "__main__":
    seed_database(500)

    print("\nGenerating ML training data and training models...")
    from app.ml.credit_model import train_models
    df = generate_ml_training_data(5000)
    results = train_models(df)
    print("Model training results:")
    for model, metrics in results.items():
        print(f"  {model}: AUC = {metrics['auc']:.4f}")
    print("\nAll done!")
