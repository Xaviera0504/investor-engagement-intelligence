"""
AI intelligence layer — mirrors Phase 3 of the project notebook.

Sends only aggregated metrics to Claude (never raw client rows). Produces two
outputs from the same data: a narrative leadership report, and a structured,
numerically-verified set of highlights for the dashboard. Every call is logged
to an append-only audit trail.
"""

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import anthropic

MODEL = "claude-sonnet-5"

NARRATIVE_SYSTEM_PROMPT = """You are a strategy analyst supporting an Investor Relations (IR) team. You will be given a structured summary of aggregated client engagement metrics — not raw client records — derived from a proxy/analog dataset (explicitly noted in the data). Your job is to translate these patterns into plain-English, senior-leadership-ready analysis and recommendations.

Rules:
- Do not claim these patterns are proven facts about real investor behavior — the data is an illustrative analog, and your response should reflect that framing where relevant.
- Write for a senior leadership audience: no jargon, no methodology walkthroughs, lead with the takeaway.
- Ground every claim in the numbers provided — do not invent data points.
- Structure your response in exactly three sections with the headers: '## Highest-Risk Segments', '## Patterns Preceding Redemption', '## Top 3 Strategic Actions (Next 30 Days)'.
- Recommendations must be concrete and actionable — name the segment, the action, and the expected effect."""

STRUCTURED_SYSTEM_PROMPT = """You are a data analyst. You will be given an aggregated IR client engagement data summary. Extract structured highlights for a dashboard. Return ONLY valid JSON, no markdown code fences, no commentary — just the raw JSON object.

Every numeric value you return must be copied exactly from the input data summary — do not invent, round further, or estimate any number.

Schema:
{
  "highest_risk_segments": [ {"segment": string, "redemption_rate": number, "why": string} ],
  "patterns_preceding_redemption": [string, string, string],
  "top_actions": [ {"action": string, "target_segment": string, "expected_impact": string} ]
}

"highest_risk_segments" must have 3 to 5 items, each redemption_rate copied exactly from the input. "patterns_preceding_redemption" must have exactly 3 short bullets. "top_actions" must have exactly 3 items."""


def build_data_summary(metrics: dict) -> dict:
    return {
        "dataset_context": (
            "Structural analog dataset (Telco Customer Churn, reframed into IR language). "
            "NOT real investor data. Use only to demonstrate analytical patterns, "
            "not to assert real-world investor behavior."
        ),
        "overall_metrics": {
            "total_clients": metrics["total_clients"],
            "overall_redemption_rate": round(metrics["overall_redemption"], 3),
            "overall_retention_rate": round(metrics["overall_retention"], 3),
        },
        "redemption_by_aum_tier_and_commitment": metrics["segment"].round(3).to_dict(),
        "engagement_and_redemption_by_tenure": metrics["by_tenure"].round(3).to_dict(),
        "high_value_retention_comparison": {
            "overall_retention_rate": round(metrics["overall_retention"], 3),
            "tier4_strategic_retention_rate": (
                round(metrics["tier4_retention"], 3) if metrics["tier4_retention"] is not None else None
            ),
        },
        "early_warning_segment": {
            "definition": "engagement_depth_score <= 2 AND relationship_length_months <= 12 AND monthly_engagement_value >= median",
            "n_clients_flagged": metrics["n_flagged"],
            "pct_of_book": round(metrics["pct_flagged"], 3),
            "redemption_rate_in_segment": (
                round(metrics["warning_redemption"], 3) if metrics["warning_redemption"] is not None else None
            ),
            "redemption_rate_baseline": round(metrics["baseline_redemption"], 3),
        },
    }


def _extract_text(response) -> str:
    """Claude responses can include non-text blocks (e.g. thinking) before the
    text block — find it by type rather than assuming position."""
    return next(block.text for block in response.content if block.type == "text").strip()


def get_narrative_report(client: anthropic.Anthropic, data_summary: dict, max_tokens: int = 1500) -> str:
    user_prompt = (
        f"Here is the aggregated client engagement data summary:\n\n"
        f"{json.dumps(data_summary, indent=2)}\n\n"
        f"Based on this data, answer:\n"
        f"1. Which client segments are highest risk?\n"
        f"2. What patterns precede redemption?\n"
        f"3. What are the top 3 strategic actions the IR team should take in the next 30 days?"
    )
    response = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=NARRATIVE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return _extract_text(response), user_prompt


def get_structured_highlights(client: anthropic.Anthropic, data_summary: dict, max_tokens: int = 2000) -> tuple[dict, str, str]:
    user_prompt = f"Data summary:\n{json.dumps(data_summary, indent=2)}\n\nReturn the JSON now."
    response = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=STRUCTURED_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    if response.stop_reason == "max_tokens":
        raise ValueError("Response was cut off at the token limit — retry with a higher max_tokens.")

    raw = _extract_text(response)
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw

    highlights = json.loads(raw)
    return highlights, user_prompt, raw


def _flatten_numbers(obj) -> set:
    nums = set()
    if isinstance(obj, dict):
        for v in obj.values():
            nums |= _flatten_numbers(v)
    elif isinstance(obj, list):
        for v in obj:
            nums |= _flatten_numbers(v)
    elif isinstance(obj, (int, float)):
        nums.add(round(float(obj), 3))
    return nums


def verify_highlights(highlights: dict, data_summary: dict) -> dict:
    """Mutates each segment in-place, adding a 'verified' bool: True only if its
    redemption_rate matches a number that actually appears in the source data."""
    known_values = _flatten_numbers(data_summary)
    for seg in highlights["highest_risk_segments"]:
        val = round(seg["redemption_rate"], 3)
        seg["verified"] = any(abs(val - k) < 0.001 for k in known_values)
    return highlights


def log_audit_entry(
    audit_log_path: str,
    system_prompt: str,
    user_prompt: str,
    response_text: str,
    model: str,
    data_summary: dict,
    call_type: str,
) -> dict:
    entry = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "call_type": call_type,  # "narrative" or "structured"
        "model": model,
        "data_summary_hash": hashlib.sha256(
            json.dumps(data_summary, sort_keys=True).encode()
        ).hexdigest()[:16],
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "response": response_text,
    }
    path = Path(audit_log_path)
    with path.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def load_audit_log(audit_log_path: str) -> list:
    path = Path(audit_log_path)
    if not path.exists():
        return []
    with path.open() as f:
        return [json.loads(line) for line in f if line.strip()]
