"""
Analytical layer — mirrors Phase 2 of the project notebook.
Every function here is pure: takes the reframed dataframe, returns numbers.
"""

import pandas as pd

TENURE_BINS = [-1, 12, 24, 36, 48, 60, 72]
TENURE_LABELS = ["0-12", "13-24", "25-36", "37-48", "49-60", "61-72"]


def compute_metrics(df: pd.DataFrame) -> dict:
    df = df.copy()

    segment = (
        df.groupby(["aum_tier", "commitment_term"], observed=True)["redemption_risk_flag"]
        .mean()
        .unstack()
    )
    ordered_cols = [c for c in ["Month-to-month", "One year", "Two year"] if c in segment.columns]
    segment = segment[ordered_cols]

    df["tenure_bucket"] = pd.cut(df["relationship_length_months"], bins=TENURE_BINS, labels=TENURE_LABELS)
    by_tenure = df.groupby("tenure_bucket", observed=True).agg(
        avg_engagement_depth=("engagement_depth_score", "mean"),
        redemption_rate=("redemption_risk_flag", "mean"),
    )

    overall_redemption = float(df["redemption_risk_flag"].mean())
    overall_retention = 1 - overall_redemption

    tier4_mask = df["aum_tier"] == "Tier 4 - Strategic"
    tier4_redemption = float(df.loc[tier4_mask, "redemption_risk_flag"].mean()) if tier4_mask.any() else None
    tier4_retention = (1 - tier4_redemption) if tier4_redemption is not None else None

    median_value = df["monthly_engagement_value"].median()
    warning_mask = (
        (df["engagement_depth_score"] <= 2)
        & (df["relationship_length_months"] <= 12)
        & (df["monthly_engagement_value"] >= median_value)
    )
    n_flagged = int(warning_mask.sum())
    pct_flagged = float(warning_mask.mean())
    warning_redemption = float(df.loc[warning_mask, "redemption_risk_flag"].mean()) if n_flagged > 0 else None
    baseline_redemption = float(df.loc[~warning_mask, "redemption_risk_flag"].mean())

    return {
        "segment": segment,
        "by_tenure": by_tenure,
        "overall_redemption": overall_redemption,
        "overall_retention": overall_retention,
        "tier4_redemption": tier4_redemption,
        "tier4_retention": tier4_retention,
        "n_flagged": n_flagged,
        "pct_flagged": pct_flagged,
        "warning_redemption": warning_redemption,
        "baseline_redemption": baseline_redemption,
        "total_clients": len(df),
    }
