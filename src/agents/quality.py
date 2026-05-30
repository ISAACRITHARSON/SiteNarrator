"""SiteNarrator — Quality + Compliance Agent.

The third agent in the pipeline. Responsible for:
1. Validating the draft narrative against the 10-section report schema
2. Checking that every claim has a traceable source (photo or voice note)
3. Flagging missing or thin sections
4. Computing a confidence score
5. Producing a QualityReport for the PC

This agent ensures reports meet the standard required for legal documentation
in construction disputes and claims.
"""

from __future__ import annotations

import re
from typing import Any

from strands import Agent, tool

from src.config import get_settings
from src.models.schemas import (
    ObservationBundle,
    QualityReport,
    SectionFlag,
    Severity,
)
from src.tools.box_tools import save_quality_report
from src.tools.tracing import trace_span


# ─── Required Sections ─────────────────────────────────────────

REQUIRED_SECTIONS = [
    "Project Header",
    "Weather & Site Conditions",
    "Manpower Summary",
    "Work Completed by Trade",
    "Equipment on Site",
    "Material Deliveries",
    "Safety Observations",
    "Inspections & Visitors",
    "Delays & Issues",
    "Work Planned for Next Day",
]

MINIMUM_WORD_COUNT = 30


# ─── Validation Functions ──────────────────────────────────────


def _find_sections(narrative: str) -> dict[str, str]:
    """Parse the narrative into sections by heading."""
    sections: dict[str, str] = {}
    current_section = ""
    current_content: list[str] = []

    for line in narrative.split("\n"):
        # Match markdown headings (## or ###)
        heading_match = re.match(r"^#{1,3}\s+\d*\.?\s*(.+)$", line.strip())
        if heading_match:
            if current_section:
                sections[current_section] = "\n".join(current_content).strip()
            current_section = heading_match.group(1).strip()
            current_content = []
        else:
            current_content.append(line)

    if current_section:
        sections[current_section] = "\n".join(current_content).strip()

    return sections


def _check_sections_present(sections: dict[str, str]) -> list[SectionFlag]:
    """Check that all 10 required sections are present."""
    flags = []
    found_sections = {s.lower() for s in sections.keys()}

    for required in REQUIRED_SECTIONS:
        # Fuzzy match — check if the required section name appears in any found section
        matched = any(
            required.lower() in found.lower() or found.lower() in required.lower()
            for found in sections.keys()
        )
        if not matched:
            flags.append(
                SectionFlag(
                    section=required,
                    issue=f"Required section '{required}' is missing from the narrative.",
                    severity=Severity.ERROR,
                )
            )

    return flags


def _check_section_depth(sections: dict[str, str]) -> list[SectionFlag]:
    """Check that each section has sufficient content (>= 30 words)."""
    flags = []

    for section_name, content in sections.items():
        word_count = len(content.split())
        if word_count < MINIMUM_WORD_COUNT:
            flags.append(
                SectionFlag(
                    section=section_name,
                    issue=f"Section has only {word_count} words (minimum: {MINIMUM_WORD_COUNT}). Content may be too thin.",
                    severity=Severity.WARNING,
                )
            )

    return flags


def _check_citations(narrative: str, bundle: ObservationBundle) -> list[SectionFlag]:
    """Check that photo citations exist and map to real photos."""
    flags = []

    # Find all [Photo N] citations in the narrative
    citations = re.findall(r"\[Photo\s+(\d+)\]", narrative)

    if not citations:
        flags.append(
            SectionFlag(
                section="Work Completed by Trade",
                issue="No photo citations found in the narrative. Every trade claim must reference a source photo.",
                severity=Severity.ERROR,
            )
        )
        return flags

    # Count total photos in the bundle
    total_photos = sum(len(photos) for photos in bundle.photos.values())

    # Check for citations referencing non-existent photos
    for citation_num in citations:
        if int(citation_num) > total_photos:
            flags.append(
                SectionFlag(
                    section="Work Completed by Trade",
                    issue=f"[Photo {citation_num}] references a photo that doesn't exist (only {total_photos} photos submitted).",
                    severity=Severity.ERROR,
                )
            )

    return flags


def _check_weather_populated(narrative: str) -> list[SectionFlag]:
    """Check that weather data is actually populated, not placeholder."""
    flags = []

    # Look for the weather section
    weather_section = ""
    in_weather = False
    for line in narrative.split("\n"):
        if "weather" in line.lower() and "#" in line:
            in_weather = True
            continue
        elif in_weather and "#" in line:
            break
        elif in_weather:
            weather_section += line + "\n"

    if not weather_section.strip():
        flags.append(
            SectionFlag(
                section="Weather & Site Conditions",
                issue="Weather section is empty. Weather data must be populated from API.",
                severity=Severity.ERROR,
            )
        )

    return flags


def _check_trade_coverage(
    narrative: str, bundle: ObservationBundle
) -> list[SectionFlag]:
    """Check that every trade in the submission has an entry in the narrative."""
    flags = []

    # Get all trades from the bundle
    submitted_trades = set(bundle.photos.keys())
    for labor in bundle.labor:
        submitted_trades.add(labor.trade)

    # Check each trade appears in the narrative
    narrative_lower = narrative.lower()
    for trade in submitted_trades:
        if trade.lower() not in narrative_lower:
            flags.append(
                SectionFlag(
                    section="Work Completed by Trade",
                    issue=f"Trade '{trade}' was in the submission but has no entry in the narrative.",
                    severity=Severity.WARNING,
                )
            )

    return flags


def _compute_confidence_score(
    narrative: str, bundle: ObservationBundle, flags: list[SectionFlag]
) -> float:
    """Compute confidence score based on citation density, completeness, and specificity.

    Formula:
        citation_density (40%) + completeness (40%) + specificity (20%)
    """
    # Citation density: citations per trade section (max 1.0)
    citations = re.findall(r"\[Photo\s+\d+\]", narrative)
    total_trades = len(bundle.photos) + len(bundle.labor)
    if total_trades > 0:
        citation_density = min(len(citations) / max(total_trades, 1), 1.0)
    else:
        citation_density = 0.0

    # Completeness: sections without errors / total required sections
    error_sections = {f.section for f in flags if f.severity == Severity.ERROR}
    completeness = (len(REQUIRED_SECTIONS) - len(error_sections)) / len(REQUIRED_SECTIONS)

    # Specificity: check if trade entries have zone + quantity indicators
    specificity_indicators = ["level", "floor", "zone", "wing", "sq ft", "linear ft", "%", "percent"]
    narrative_lower = narrative.lower()
    specificity_hits = sum(1 for ind in specificity_indicators if ind in narrative_lower)
    specificity = min(specificity_hits / 4, 1.0)  # 4+ indicators = full score

    score = (citation_density * 0.4) + (completeness * 0.4) + (specificity * 0.2)
    return round(score, 3)


# ─── Agent Runner ──────────────────────────────────────────────


def run_quality_check(
    narrative: str,
    bundle: ObservationBundle,
) -> QualityReport:
    """Run the Quality + Compliance Agent on a draft narrative.

    Performs all validation checks and produces a QualityReport.

    Args:
        narrative: The draft narrative text from the Synthesis Agent.
        bundle: The ObservationBundle used to generate the narrative.

    Returns:
        QualityReport with confidence score, flags, summary, and pass/fail.
    """
    with trace_span("quality.agent_total", {"project_id": bundle.project_id}):
        flags: list[SectionFlag] = []

        # Parse sections
        with trace_span("quality.parse_sections"):
            sections = _find_sections(narrative)

        # Run all validation checks
        with trace_span("quality.check_sections_present"):
            flags.extend(_check_sections_present(sections))

        with trace_span("quality.check_section_depth"):
            flags.extend(_check_section_depth(sections))

        with trace_span("quality.check_citations"):
            flags.extend(_check_citations(narrative, bundle))

        with trace_span("quality.check_weather"):
            flags.extend(_check_weather_populated(narrative))

        with trace_span("quality.check_trade_coverage"):
            flags.extend(_check_trade_coverage(narrative, bundle))

        # Compute confidence score
        with trace_span("quality.compute_score"):
            confidence = _compute_confidence_score(narrative, bundle, flags)

        # Determine pass/fail
        has_errors = any(f.severity == Severity.ERROR for f in flags)
        passed = confidence >= 0.7 and not has_errors

        # Generate summary
        if passed:
            summary = f"Report passes quality check with confidence {confidence:.0%}. {len(flags)} minor flags."
        else:
            error_count = sum(1 for f in flags if f.severity == Severity.ERROR)
            summary = f"Report needs attention: {error_count} errors, confidence {confidence:.0%}."

        report = QualityReport(
            confidence_score=confidence,
            flags=flags,
            summary=summary,
            passed=passed,
        )

        # Save quality report to Box
        with trace_span("quality.save_report"):
            save_quality_report(
                report.model_dump(),
                bundle.project_id,
                str(bundle.report_date),
            )

        return report
