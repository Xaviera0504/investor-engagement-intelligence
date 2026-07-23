"""
Data loading, cleaning, and IR-reframing logic.

Mirrors Phase 1 of the project notebook. See docs/assumptions.md in the repo
for the full rationale on why/how each column is reframed.
"""

import pandas as pd

SERVICE_COLUMNS = [
    "PhoneService", "MultipleLines", "OnlineSecurity", "OnlineBackup",
    "DeviceProtection", "TechSupport", "StreamingTV", "StreamingMovies",
]

RAW_REQUIRED_COLUMNS = {"customerID", "tenure", "MonthlyCharges", "TotalCharges", "Churn", "Contract"}
REFRAMED_REQUIRED_COLUMNS = {"client_id", "relationship_length_months", "redemption_risk_flag", "aum_tier"}


def detect_schema(df: pd.DataFrame) -> str:
    """Return 'raw' if this looks like the original Telco export, 'reframed' if
    it's already been through this pipeline, or 'unknown' otherwise."""
    cols = set(df.columns)
    if REFRAMED_REQUIRED_COLUMNS.issubset(cols):
        return "reframed"
    if RAW_REQUIRED_COLUMNS.issubset(cols):
        return "raw"
    return "unknown"


def clean_raw(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    blank_mask = df["TotalCharges"].astype(str).str.strip() == ""
    if blank_mask.any():
        if not (df.loc[blank_mask, "tenure"] == 0).all():
            raise ValueError(
                "Found blank TotalCharges rows with tenure != 0 — "
                "the zero-fill assumption doesn't hold for this file. Investigate before proceeding."
            )
    df["TotalCharges"] = df["TotalCharges"].astype(str).str.strip().replace("", "0").astype(float)
    return df


def _engagement_depth_score(row: pd.Series) -> int:
    return sum(1 for col in SERVICE_COLUMNS if row[col] == "Yes")


def _aum_tier(monthly_value: float, q: dict) -> str:
    if monthly_value <= q[0.25]:
        return "Tier 1 - Emerging"
    elif monthly_value <= q[0.5]:
        return "Tier 2 - Core"
    elif monthly_value <= q[0.75]:
        return "Tier 3 - Growth"
    return "Tier 4 - Strategic"


def reframe(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame()
    out["client_id"] = df["customerID"]
    out["relationship_length_months"] = df["tenure"]
    out["monthly_engagement_value"] = df["MonthlyCharges"]
    out["cumulative_relationship_value"] = df["TotalCharges"]

    q = df["MonthlyCharges"].quantile([0.25, 0.5, 0.75]).to_dict()
    out["aum_tier"] = df["MonthlyCharges"].apply(lambda v: _aum_tier(v, q))

    out["commitment_term"] = df["Contract"]
    out["engagement_channel"] = df["PaymentMethod"]
    out["digital_engagement"] = (df["PaperlessBilling"] == "Yes")
    out["engagement_depth_score"] = df.apply(_engagement_depth_score, axis=1)
    out["primary_product_line"] = df["InternetService"]

    out["household_partner"] = (df["Partner"] == "Yes")
    out["household_dependents"] = (df["Dependents"] == "Yes")
    out["senior_citizen"] = df["SeniorCitizen"].astype(bool)

    out["redemption_risk_flag"] = (df["Churn"] == "Yes")
    return out


def load_and_prepare(df_input: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Accepts either the raw Telco export or an already-reframed IR file.
    Returns (reframed_df, detected_schema)."""
    schema = detect_schema(df_input)
    if schema == "reframed":
        return df_input.copy(), schema
    if schema == "raw":
        cleaned = clean_raw(df_input)
        return reframe(cleaned), schema
    raise ValueError(
        "Unrecognized file format. Expected either the raw Telco Customer Churn "
        "export or a file already reframed by this project's Phase 1 pipeline."
    )
