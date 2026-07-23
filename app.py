"""
Investor Engagement Intelligence — Streamlit interface (Phase 4)

Run locally with:  streamlit run app.py
"""

import json
from datetime import datetime, timezone

import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
import anthropic

from src.data_prep import load_and_prepare
from src.metrics import compute_metrics
from src.ai_layer import (
    build_data_summary,
    get_narrative_report,
    get_structured_highlights,
    verify_highlights,
    log_audit_entry,
    load_audit_log,
    MODEL,
)

AUDIT_LOG_PATH = "audit_trail.jsonl"
SAMPLE_DATA_PATH = "data/sample_clients_ir.csv"

st.set_page_config(page_title="Investor Engagement Intelligence", layout="wide")


# ---------- Data loading ----------

@st.cache_data
def load_sample_data() -> pd.DataFrame:
    df_raw = pd.read_csv(SAMPLE_DATA_PATH)
    reframed, _ = load_and_prepare(df_raw)
    return reframed


def load_uploaded_data(uploaded_file) -> pd.DataFrame:
    df_raw = pd.read_csv(uploaded_file)
    reframed, schema = load_and_prepare(df_raw)
    st.sidebar.success(f"Loaded {len(reframed)} clients (detected schema: {schema}).")
    return reframed


st.title("Investor Engagement Intelligence")
st.caption("Which client relationships are at risk, and what should the IR team do about it in the next 30 days?")

with st.sidebar:
    st.header("Data")
    data_source = st.radio("Data source", ["Use built-in sample dataset", "Upload your own CSV"])

    if data_source == "Upload your own CSV":
        uploaded_file = st.file_uploader(
            "Upload a client engagement CSV",
            type="csv",
            help="Accepts either a raw Telco Customer Churn export or a file already reframed by this project's Phase 1 pipeline.",
        )
        if uploaded_file is not None:
            try:
                df = load_uploaded_data(uploaded_file)
            except ValueError as e:
                st.error(str(e))
                st.stop()
        else:
            st.info("Upload a file to continue, or switch to the built-in sample dataset.")
            st.stop()
    else:
        df = load_sample_data()
        st.caption(f"{len(df)} clients loaded from the built-in sample dataset.")

    st.divider()
    st.header("AI Settings")
    api_key = st.text_input("Anthropic API key", type="password", help="Get one at console.anthropic.com")

st.info(
    "⚠️ This dashboard runs on a structural analog dataset (Telco Customer Churn, "
    "reframed into IR language) — not real investor data. Patterns shown are "
    "illustrative of the analytical approach, not validated claims about real "
    "investor behavior.",
    icon="ℹ️",
)

# ---------- Dashboard ----------

metrics = compute_metrics(df)

st.subheader("Engagement Dashboard")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total clients", f"{metrics['total_clients']:,}")
col2.metric("Overall redemption rate", f"{metrics['overall_redemption']:.1%}")
col3.metric(
    "Tier 4 (Strategic) retention",
    f"{metrics['tier4_retention']:.1%}" if metrics["tier4_retention"] is not None else "n/a",
    delta=(
        f"{(metrics['tier4_retention'] - metrics['overall_retention']):+.1%} vs. book avg"
        if metrics["tier4_retention"] is not None else None
    ),
    delta_color="inverse",
)
col4.metric(
    "Early warning segment lift",
    f"{(metrics['warning_redemption'] / metrics['baseline_redemption']):.1f}x" if metrics["warning_redemption"] else "n/a",
    help=f"{metrics['n_flagged']} clients ({metrics['pct_flagged']:.1%} of book) flagged",
)

tab1, tab2, tab3 = st.tabs(["Redemption risk by segment", "Engagement depth by tenure", "Early warning segment"])

with tab1:
    fig, ax = plt.subplots(figsize=(9, 5))
    metrics["segment"].plot(kind="bar", ax=ax)
    ax.set_ylabel("Redemption risk rate")
    ax.set_xlabel("AUM tier")
    ax.set_title("Redemption risk by AUM tier and commitment term")
    ax.legend(title="Commitment term")
    plt.xticks(rotation=20)
    plt.tight_layout()
    st.pyplot(fig)

with tab2:
    by_tenure = metrics["by_tenure"]
    fig, ax1 = plt.subplots(figsize=(9, 5))
    ax1.bar(by_tenure.index.astype(str), by_tenure["avg_engagement_depth"], color="#4C72B0", alpha=0.7)
    ax1.set_ylabel("Avg engagement depth (0-8)")
    ax1.set_xlabel("Relationship length (months)")
    ax2 = ax1.twinx()
    ax2.plot(by_tenure.index.astype(str), by_tenure["redemption_rate"], color="#C44E52", marker="o", linewidth=2)
    ax2.set_ylabel("Redemption risk rate")
    fig.suptitle("Engagement depth (bars) and redemption risk (line) by relationship length")
    plt.tight_layout()
    st.pyplot(fig)

with tab3:
    st.write(
        f"**{metrics['n_flagged']} clients** ({metrics['pct_flagged']:.1%} of the book) match all three "
        f"early-warning conditions: low engagement depth (≤2), short tenure (≤12 months), "
        f"and above-median monthly value."
    )
    fig, ax = plt.subplots(figsize=(5, 5))
    bars = ax.bar(
        ["Baseline clients", "Early warning flag"],
        [metrics["baseline_redemption"], metrics["warning_redemption"]],
        color=["#8C8C8C", "#C44E52"],
    )
    ax.set_ylabel("Redemption risk rate")
    ax.set_ylim(0, 1)
    for bar, rate in zip(bars, [metrics["baseline_redemption"], metrics["warning_redemption"]]):
        ax.text(bar.get_x() + bar.get_width() / 2, rate + 0.02, f"{rate:.1%}", ha="center", fontweight="bold")
    plt.tight_layout()
    st.pyplot(fig)

st.divider()

# ---------- AI report generation ----------

st.subheader("AI Strategic Report")

if st.button("Generate AI Report", type="primary", disabled=not api_key):
    if not api_key:
        st.warning("Enter your Anthropic API key in the sidebar first.")
    else:
        with st.spinner("Analyzing engagement patterns..."):
            try:
                client = anthropic.Anthropic(api_key=api_key)
                data_summary = build_data_summary(metrics)

                narrative, narrative_prompt = get_narrative_report(client, data_summary)
                entry1 = log_audit_entry(
                    AUDIT_LOG_PATH, "See src/ai_layer.py NARRATIVE_SYSTEM_PROMPT", narrative_prompt,
                    narrative, MODEL, data_summary, call_type="narrative",
                )

                highlights, structured_prompt, raw_json = get_structured_highlights(client, data_summary)
                highlights = verify_highlights(highlights, data_summary)
                entry2 = log_audit_entry(
                    AUDIT_LOG_PATH, "See src/ai_layer.py STRUCTURED_SYSTEM_PROMPT", structured_prompt,
                    raw_json, MODEL, data_summary, call_type="structured",
                )

                st.session_state["narrative"] = narrative
                st.session_state["highlights"] = highlights
                st.session_state["report_generated_at"] = datetime.now(timezone.utc).isoformat()

            except json.JSONDecodeError:
                st.error("The structured report came back malformed. Try generating again.")
            except Exception as e:
                st.error(f"Report generation failed: {e}")

if "highlights" in st.session_state:
    highlights = st.session_state["highlights"]
    narrative = st.session_state["narrative"]

    unverified_count = sum(1 for s in highlights["highest_risk_segments"] if not s["verified"])
    if unverified_count:
        st.warning(
            f"{unverified_count} risk segment(s) cited a number not found in the source data — "
            f"shown in gray below. Treat with caution."
        )

    st.markdown("#### Highest-Risk Segments")
    segs_sorted = sorted(highlights["highest_risk_segments"], key=lambda s: s["redemption_rate"], reverse=True)
    names = [s["segment"] for s in segs_sorted]
    rates = [s["redemption_rate"] for s in segs_sorted]
    colors = ["#C44E52" if s["verified"] else "#CCCCCC" for s in segs_sorted]

    fig, ax = plt.subplots(figsize=(9, max(3, len(names) * 0.7)))
    bars = ax.barh(names, rates, color=colors)
    ax.set_xlabel("Redemption risk rate")
    ax.invert_yaxis()
    for bar, rate in zip(bars, rates):
        ax.text(rate + 0.01, bar.get_y() + bar.get_height() / 2, f"{rate:.1%}", va="center", fontweight="bold")
    plt.tight_layout()
    st.pyplot(fig)

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### Patterns Preceding Redemption")
        for p in highlights["patterns_preceding_redemption"]:
            st.markdown(f"- {p}")
    with col_b:
        st.markdown("#### Top 3 Strategic Actions (Next 30 Days)")
        for i, a in enumerate(highlights["top_actions"], 1):
            st.markdown(f"**{i}. {a['action']}**")
            st.caption(f"Target: {a['target_segment']} · Expected impact: {a['expected_impact']}")

    with st.expander("Full narrative report"):
        st.markdown(narrative)

    # ---------- Export ----------
    report_md = (
        f"# Investor Engagement Intelligence — Strategic Report\n"
        f"_Generated {st.session_state['report_generated_at']}_\n\n"
        f"{narrative}\n"
    )
    st.download_button(
        "Export report (Markdown)",
        data=report_md,
        file_name=f"ir_engagement_report_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
        mime="text/markdown",
    )

st.divider()

# ---------- Audit trail ----------

with st.expander("Audit Trail"):
    log = load_audit_log(AUDIT_LOG_PATH)
    if not log:
        st.caption("No AI calls logged yet in this environment.")
    else:
        log_df = pd.DataFrame(log)[["timestamp_utc", "call_type", "model", "data_summary_hash"]]
        st.dataframe(log_df, use_container_width=True)
        selected_idx = st.selectbox("Inspect a logged call", options=range(len(log)), format_func=lambda i: f"{log[i]['timestamp_utc']} ({log[i]['call_type']})")
        st.json(log[selected_idx])
