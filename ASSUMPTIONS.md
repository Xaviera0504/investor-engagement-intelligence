# Data Assumptions & Reframing Rationale

## What this dataset actually is

This project uses the [Telco Customer Churn dataset](https://www.kaggle.com/datasets/blastchar/telco-customer-churn)
(IBM sample data, via Kaggle). It is **not real investor or client data**. It is
used here as a **structural analog** — a publicly available dataset that shares
the same underlying shape as an IR engagement problem:

| Telco concept | Shares structure with | IR concept |
|---|---|---|
| Subscriber tenure | Length of an ongoing relationship | Relationship length |
| Monthly/total billing | Recurring and cumulative capital contribution | Engagement value / AUM proxy |
| Service add-ons subscribed | Breadth of products/touchpoints a client uses | Engagement depth |
| Contract length (month-to-month / 1yr / 2yr) | Commitment horizon | Commitment term |
| Customer churn | Client exit / capital withdrawal | Redemption risk |

**Why this is a reasonable proxy:** all five of these are relationship-lifecycle
signals — how long someone has been engaged, how much value they contribute, how
many products/services they touch, how locked-in their commitment is, and whether
they eventually leave. That lifecycle structure is domain-agnostic.

**Why this is NOT a validated model of investor behavior:** telco churn drivers
(price sensitivity, service quality, contract terms) are not proven to be the same
drivers behind investor redemption (fund performance, market conditions, personal
relationship with IR/portfolio teams, liquidity needs). The goal of this project is
to demonstrate an **analytical + AI-synthesis pipeline** that would be directly
transferable to real engagement data — not to claim a specific finding about why
investors redeem.

This distinction is stated explicitly in the README and should be stated explicitly
if asked about in an interview.

## Column-level reframing

- `client_id` ← `customerID` — direct rename, no transformation.
- `relationship_length_months` ← `tenure` — direct rename, no transformation.
- `monthly_engagement_value` ← `MonthlyCharges` — direct rename, no transformation.
- `cumulative_relationship_value` ← `TotalCharges` — direct rename, no transformation (see data quality note below).
- `aum_tier` — derived. Clients bucketed into 4 tiers by quartile of `MonthlyCharges`
  (Emerging / Core / Growth / Strategic). Quartile cuts, not fixed dollar thresholds,
  so tiers are evenly populated by construction (~25% each) rather than reflecting
  a real AUM distribution.
- `commitment_term` ← `Contract` — direct rename, no transformation.
- `engagement_channel` ← `PaymentMethod` — direct rename, no transformation.
- `digital_engagement` ← `PaperlessBilling` — direct rename, boolean cast.
- `engagement_depth_score` — derived. Count (0–8) of active service add-ons
  (`PhoneService`, `MultipleLines`, `OnlineSecurity`, `OnlineBackup`,
  `DeviceProtection`, `TechSupport`, `StreamingTV`, `StreamingMovies`) where the
  client has an active "Yes." Used as an engagement-breadth proxy.
- `primary_product_line` ← `InternetService` — direct rename, no transformation.
- `household_partner`, `household_dependents`, `senior_citizen` — demographic
  controls, kept as-is. **Deliberately not renamed into IR language** — there's no
  honest client-relationship analog for "has a partner" or "is a senior citizen,"
  and forcing one would misrepresent the data. These are retained as segmentation
  controls only.
- `redemption_risk_flag` ← `Churn` — direct rename, boolean cast. This is the
  target variable / outcome of interest.

## Data quality notes

- **11 rows had a blank-string `TotalCharges`.** All 11 have `tenure == 0` (i.e.,
  brand-new clients with no completed billing cycle). This was verified
  programmatically (an assertion in `01_data_prep.py` fails if this assumption
  ever breaks on a data refresh). These were set to `0`, which is a real,
  defensible value here — not an imputed guess — because no engagement cycle has
  occurred yet for these clients. None of these 11 rows have churned.
- No other missing values or duplicate client IDs in the raw data.

## What downstream phases should NOT do

- Do not present `aum_tier` labels or `redemption_risk_flag` rates as reflective of
  any real fund's actual investor base.
- Do not let the AI intelligence layer (Phase 3) phrase output as if it has
  discovered validated investor behavior — prompts should frame the data
  explicitly as an illustrative/proxy dataset, and outputs should be reviewed to
  make sure that framing survives into the generated report.
