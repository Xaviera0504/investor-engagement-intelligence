# Investor Engagement Intelligence

An AI-powered client retention and engagement analysis tool, built for IR and strategy teams.

**The business question:** Which client relationships are at risk, and what should the IR team do about it in the next 30 days?

## Why this project

IR and strategy teams manage complex client relationships at scale. The hard part usually isn't collecting data — it's translating engagement signals into a clear, actionable next step before a client disengages. This project builds a small end-to-end pipeline for that: clean data → quantitative risk signals → AI-synthesized, plain-English recommendations for leadership — with every step logged for auditability.

## ⚠️ About the data

This project uses the public [Telco Customer Churn dataset](https://www.kaggle.com/datasets/blastchar/telco-customer-churn) (IBM sample data) as a **structural analog**, not real investor data. Subscriber tenure, billing, service usage, and contract terms share the same relationship-lifecycle shape as investor engagement data (relationship length, capital contribution, product usage, commitment term) — which is why it's a reasonable stand-in for building and demonstrating the pipeline.

**This is not a validated model of real investor behavior.** The goal is to demonstrate the analytical + AI-synthesis approach in a way that's directly transferable to real engagement data — not to claim a specific finding about why investors redeem. Full column-by-column rationale and data quality notes are in [`ASSUMPTIONS.md`](./ASSUMPTIONS.md).

## What it does

| Phase | What happens |
|---|---|
| 1 — Data Foundation | Pull the dataset, clean it, reframe columns into IR language, document every assumption |
| 2 — Analytical Layer | Compute redemption risk by segment, engagement depth by tenure, high-value retention rate, and a composite early-warning signal |
| 3 — AI Intelligence Layer | Send an aggregated data summary (never raw client rows) to the Claude API for a plain-English leadership report, plus a separate structured/numerically-verified extraction for the dashboard. Every call is logged to an audit trail |
| 4 — Streamlit Interface | A clean, non-technical dashboard: load or upload data, view metrics and charts, generate the AI report on demand, inspect the audit trail, export the report |

Phases 1–3 were prototyped in [`Investor_Engagement_Intelligence.ipynb`](./Investor_Engagement_Intelligence.ipynb); Phase 4 packages the pipeline into the Streamlit app (`app.py` + `src/`).

## Key findings (illustrative — see the data caveat above)

- **Redemption risk is heavily front-loaded**: 47.4% in the first 12 months of a relationship, dropping to 6.6% after 5+ years.
- **High value ≠ high loyalty.** The highest-value tier (Tier 4 – Strategic) retains at 67.1%, *worse* than the overall book average of 73.5%.
- **A narrow, composite early-warning flag** — low engagement depth + short tenure + above-median value — isolates just 4.8% of clients with a 68.6% redemption rate, nearly 3x the baseline. Small enough for a team to act on individually.

## Tech stack

Python · pandas · matplotlib · Anthropic Claude API · Streamlit

## Project structure
## Running locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Paste an Anthropic API key ([console.anthropic.com](https://console.anthropic.com)) into the sidebar to enable AI report generation. The dashboard itself works immediately with the bundled sample dataset — no key or upload required.

## Roadmap status

- [x] Phase 1 — Data Foundation
- [x] Phase 2 — Analytical Layer
- [x] Phase 3 — AI Intelligence Layer
- [x] Phase 4 — Streamlit Interface
- [ ] Phase 5 — Deploy to Streamlit Cloud + showcase
