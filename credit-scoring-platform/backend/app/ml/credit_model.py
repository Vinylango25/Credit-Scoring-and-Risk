"""
Credit Scoring ML Module
Trains and serves Random Forest, XGBoost, and LightGBM models
adapted from the original TWINO credit scoring notebook.
"""
import numpy as np
import pandas as pd
import joblib
import os
import json
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, classification_report
import xgboost as xgb
import lightgbm as lgb

MODEL_DIR = os.path.join(os.path.dirname(__file__), "saved_models")
os.makedirs(MODEL_DIR, exist_ok=True)


def build_feature_vector(client_data: dict, crb_data: dict, tu_data: dict, loan_data: dict) -> np.ndarray:
    """Build feature vector from client, CRB, TransUnion, and loan data."""
    features = [
        # Client features
        client_data.get("monthly_income", 0),
        client_data.get("age", 30),
        1 if client_data.get("employment_status") == "EMPLOYED" else 0,
        1 if client_data.get("gender") == "M" else 0,

        # Loan features
        loan_data.get("loan_amount", 0),
        loan_data.get("loan_term_days", 30),
        loan_data.get("loan_sequence_nr", 1),
        loan_data.get("warning_count", 0),
        1 if loan_data.get("payment_method") == "MOBILE_MONEY" else 0,

        # CRB features
        crb_data.get("crb_score", 500),
        crb_data.get("total_credit_facilities", 0),
        crb_data.get("non_performing_accounts", 0),
        crb_data.get("credit_utilization_ratio", 0),
        crb_data.get("number_of_enquiries_last_6m", 0),
        1 if crb_data.get("has_adverse_listing", False) else 0,
        crb_data.get("months_since_last_default", 999) or 999,

        # TransUnion features
        tu_data.get("tu_score", 350),
        tu_data.get("payment_history_score", 50),
        tu_data.get("delinquent_accounts", 0),
        tu_data.get("collections_count", 0),
        tu_data.get("highest_delinquency_dpd", 0),
        tu_data.get("length_of_credit_history_months", 0),
        tu_data.get("credit_mix_score", 50),
    ]
    return np.array(features).reshape(1, -1)


FEATURE_NAMES = [
    "monthly_income", "age", "is_employed", "is_male",
    "loan_amount", "loan_term_days", "loan_sequence_nr", "warning_count", "is_mobile_money",
    "crb_score", "total_credit_facilities", "non_performing_accounts",
    "credit_utilization_ratio", "enquiries_last_6m", "has_adverse_listing", "months_since_default",
    "tu_score", "payment_history_score", "delinquent_accounts", "collections_count",
    "highest_delinquency_dpd", "credit_history_months", "credit_mix_score"
]


def train_models(df: pd.DataFrame):
    """Train RF, XGBoost, and LightGBM models on provided dataframe."""
    X = df[FEATURE_NAMES]
    y = df["default"]  # 1 = defaulted, 0 = good

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    results = {}

    # Random Forest
    rf = RandomForestClassifier(n_estimators=100, max_depth=8, class_weight="balanced", random_state=42)
    rf.fit(X_train_scaled, y_train)
    rf_auc = roc_auc_score(y_test, rf.predict_proba(X_test_scaled)[:, 1])
    results["random_forest"] = {"auc": rf_auc}
    joblib.dump(rf, os.path.join(MODEL_DIR, "rf_model.pkl"))

    # XGBoost
    scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
    xgb_model = xgb.XGBClassifier(
        n_estimators=200, max_depth=6, learning_rate=0.05,
        scale_pos_weight=scale_pos_weight, use_label_encoder=False,
        eval_metric="auc", random_state=42
    )
    xgb_model.fit(X_train_scaled, y_train)
    xgb_auc = roc_auc_score(y_test, xgb_model.predict_proba(X_test_scaled)[:, 1])
    results["xgboost"] = {"auc": xgb_auc}
    joblib.dump(xgb_model, os.path.join(MODEL_DIR, "xgb_model.pkl"))

    # LightGBM
    lgbm_model = lgb.LGBMClassifier(
        n_estimators=200, max_depth=6, learning_rate=0.05,
        class_weight="balanced", random_state=42, verbose=-1
    )
    lgbm_model.fit(X_train_scaled, y_train)
    lgbm_auc = roc_auc_score(y_test, lgbm_model.predict_proba(X_test_scaled)[:, 1])
    results["lightgbm"] = {"auc": lgbm_auc}
    joblib.dump(lgbm_model, os.path.join(MODEL_DIR, "lgbm_model.pkl"))

    joblib.dump(scaler, os.path.join(MODEL_DIR, "scaler.pkl"))

    # Save best model name
    best_model = max(results, key=lambda k: results[k]["auc"])
    with open(os.path.join(MODEL_DIR, "model_meta.json"), "w") as f:
        json.dump({"best_model": best_model, "results": results}, f)

    return results


def load_model(model_name: str = "xgboost"):
    path = os.path.join(MODEL_DIR, f"{model_name.replace('xgboost','xgb').replace('lightgbm','lgbm').replace('random_forest','rf')}_model.pkl")
    if not os.path.exists(path):
        return None
    return joblib.load(path)


def load_scaler():
    path = os.path.join(MODEL_DIR, "scaler.pkl")
    if not os.path.exists(path):
        return None
    return joblib.load(path)


def predict_credit_score(features: np.ndarray, model_name: str = "xgboost") -> dict:
    """Return credit score, approval probability, risk band, and decision."""
    model = load_model(model_name)
    scaler = load_scaler()

    if model is None or scaler is None:
        # Fallback: rule-based scoring when model not trained yet
        return _rule_based_score(features)

    features_scaled = scaler.transform(features)
    default_prob = model.predict_proba(features_scaled)[0][1]
    approval_prob = 1 - default_prob

    # Scale to 300-850 credit score range
    credit_score = 300 + (approval_prob * 550)

    risk_band, decision = _classify_risk(approval_prob)

    # Feature importance
    try:
        importances = dict(zip(FEATURE_NAMES, model.feature_importances_))
        top_features = sorted(importances.items(), key=lambda x: x[1], reverse=True)[:5]
    except Exception:
        top_features = []

    return {
        "approval_probability": round(float(approval_prob), 4),
        "credit_score": round(float(credit_score), 1),
        "risk_band": risk_band,
        "decision": decision,
        "model_used": model_name,
        "top_features": top_features
    }


def _rule_based_score(features: np.ndarray) -> dict:
    """Simple rule-based fallback scoring."""
    f = features[0]
    score = 500.0
    score += min(f[0] / 1000, 100)   # income
    score += (f[9] - 500) * 0.3       # crb_score contribution
    score += (f[16] - 350) * 0.2      # tu_score contribution
    score -= f[11] * 20               # non_performing_accounts
    score -= f[14] * 50               # adverse_listing
    score = max(300, min(850, score))
    approval_prob = (score - 300) / 550
    risk_band, decision = _classify_risk(approval_prob)
    return {
        "approval_probability": round(float(approval_prob), 4),
        "credit_score": round(float(score), 1),
        "risk_band": risk_band,
        "decision": decision,
        "model_used": "rule_based",
        "top_features": []
    }


def _classify_risk(approval_prob: float):
    if approval_prob >= 0.75:
        return "LOW", "APPROVED"
    elif approval_prob >= 0.55:
        return "MEDIUM", "APPROVED"
    elif approval_prob >= 0.40:
        return "HIGH", "MANUAL_REVIEW"
    else:
        return "VERY_HIGH", "REJECTED"
