"""SiteNarrator — Eval + Observability Agent.

The fourth agent in the pipeline. Responsible for:
1. Running AI evaluations: hallucination detection, citation accuracy, tone consistency
2. Computing per-run quality scores
3. Detecting quality regressions against rolling averages
4. Logging all metrics to CloudWatch
5. Providing trace_id for full pipeline replay

This agent ensures the system maintains quality over time and provides
the observability needed for production operations.
"""

from __future__ import annotations

import re
from typing import Any

from strands import Agent, tool

from src.config import get_settings
from src.models.schemas import EvalReport, ObservationBundle
from src.tools.tracing import trace_span


# ─── Evaluation Functions ──────────────────────────────────────


def _check_hallucinations(
    narrative: str, bundle: ObservationBundle
) -> float:
    """Check for hallucinated content not supported by source data.

    Compares narrative claims against the ObservationBundle.
    Returns a score from 0.0 (no hallucinations) to 1.0 (fully hallucinated).
    """
    with trace_span("eval.hallucination_check"):
        # Extract factual claims from the narrative
        # A claim is hallucinated if it mentions specific data not in the bundle

        hallucination_indicators = 0
        total_claims = 0

        # Check trade names mentioned vs. trades in bundle
        bundle_trades = set(bundle.photos.keys())
        for labor in bundle.labor:
            bundle_trades.add(labor.trade)

        # Find trade mentions in narrative
        for line in narrative.split("\n"):
            if any(keyword in line.lower() for keyword in ["crew", "workers", "completed", "installed", "poured"]):
                total_claims += 1
                # Check if the line references a trade not in the bundle
                line_lower = line.lower()
                has_valid_trade = any(trade.lower() in line_lower for trade in bundle_trades)
                if not has_valid_trade and total_claims > 0:
                    # Could be a hallucination — trade mentioned that wasn't submitted
                    hallucination_indicators += 0.5  # Soft flag

        if total_claims == 0:
            return 0.0

        score = min(hallucination_indicators / max(total_claims, 1), 1.0)
        return round(score, 3)


def _check_citation_accuracy(
    narrative: str, bundle: ObservationBundle
) -> float:
    """Verify that every [Photo N] citation maps to a real photo in the bundle.

    Returns accuracy from 0.0 to 1.0.
    """
    with trace_span("eval.citation_accuracy"):
        citations = re.findall(r"\[Photo\s+(\d+)\]", narrative)

        if not citations:
            return 0.0  # No citations = 0% accuracy (they should exist)

        total_photos = sum(len(photos) for photos in bundle.photos.values())
        valid_citations = sum(1 for c in citations if int(c) <= total_photos)

        return round(valid_citations / len(citations), 3) if citations else 1.0


def _check_tone_consistency(narrative: str, project_memory: dict) -> float:
    """Check if the narrative matches the project's established tone.

    Compares against approved_phrase_examples and preferred_tone from memory.
    Returns consistency score from 0.0 to 1.0.
    """
    with trace_span("eval.tone_consistency"):
        preferred_tone = project_memory.get("preferred_tone", "professional")

        # Basic tone checks
        tone_score = 1.0

        # Check for first person (should be third person)
        first_person = re.findall(r"\b(I|we|my|our)\b", narrative, re.IGNORECASE)
        if first_person:
            tone_score -= 0.2 * min(len(first_person) / 10, 1.0)

        # Check for present tense where past tense expected
        present_indicators = re.findall(r"\b(is working|are installing|is pouring)\b", narrative, re.IGNORECASE)
        if present_indicators:
            tone_score -= 0.1 * min(len(present_indicators) / 5, 1.0)

        # Check for informal language
        informal = re.findall(r"\b(gonna|wanna|kinda|stuff|things|guys)\b", narrative, re.IGNORECASE)
        if informal:
            tone_score -= 0.3 * min(len(informal) / 3, 1.0)

        return round(max(tone_score, 0.0), 3)


def _estimate_cost(
    prompt_tokens: int, completion_tokens: int, model: str
) -> float:
    """Estimate the cost of LLM calls for this report.

    Based on Claude Sonnet pricing via AWS Bedrock.
    """
    # Claude Sonnet pricing (approximate, per 1K tokens)
    input_cost_per_1k = 0.003
    output_cost_per_1k = 0.015

    input_cost = (prompt_tokens / 1000) * input_cost_per_1k
    output_cost = (completion_tokens / 1000) * output_cost_per_1k

    return round(input_cost + output_cost, 4)


# ─── Agent Runner ──────────────────────────────────────────────


def run_eval(
    narrative: str,
    bundle: ObservationBundle,
    trace_id: str = "",
    total_latency_ms: int = 0,
    total_prompt_tokens: int = 0,
    total_completion_tokens: int = 0,
) -> EvalReport:
    """Run the Eval + Observability Agent on a completed draft.

    Performs AI evaluations and produces an EvalReport with quality metrics.

    Args:
        narrative: The draft narrative from the Synthesis Agent.
        bundle: The ObservationBundle used to generate the narrative.
        trace_id: The trace ID for this report's pipeline run.
        total_latency_ms: Total pipeline latency so far.
        total_prompt_tokens: Total prompt tokens used across all agents.
        total_completion_tokens: Total completion tokens used.

    Returns:
        EvalReport with scores, cost, and recommendations.
    """
    settings = get_settings()

    with trace_span("eval.agent_total", {
        "project_id": bundle.project_id,
        "trace_id": trace_id,
    }):
        # Run evaluations
        hallucination_score = _check_hallucinations(narrative, bundle)
        citation_accuracy = _check_citation_accuracy(narrative, bundle)

        # Get project memory for tone check
        project_memory = {}  # TODO: Query from AgentCore Memory
        tone_consistency = _check_tone_consistency(narrative, project_memory)

        # Compute overall score (weighted average)
        overall_score = (
            (1.0 - hallucination_score) * 0.4  # Lower hallucination = better
            + citation_accuracy * 0.35
            + tone_consistency * 0.25
        )

        # Estimate cost
        cost = _estimate_cost(
            total_prompt_tokens, total_completion_tokens, settings.bedrock_model_id
        )

        # Generate recommendations
        recommendations = []
        if hallucination_score > 0.1:
            recommendations.append(
                "Potential hallucinations detected. Review claims not backed by source photos or voice notes."
            )
        if citation_accuracy < 0.9:
            recommendations.append(
                "Some photo citations may reference incorrect photos. Verify citation-to-photo mapping."
            )
        if tone_consistency < 0.8:
            recommendations.append(
                "Tone inconsistency detected. Check for first-person language or informal phrasing."
            )
        if not recommendations:
            recommendations.append("Report meets all quality thresholds. No action needed.")

        report = EvalReport(
            hallucination_score=hallucination_score,
            citation_accuracy=citation_accuracy,
            tone_consistency=tone_consistency,
            overall_score=round(overall_score, 3),
            cost_usd=cost,
            latency_ms=total_latency_ms,
            trace_id=trace_id,
            recommendations=recommendations,
        )

        # TODO: Log metrics to CloudWatch
        # TODO: Compare against 7-day rolling average for regression detection

        return report
