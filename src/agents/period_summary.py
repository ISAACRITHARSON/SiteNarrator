"""SiteNarrator — Period Summary Agent.

Generates comprehensive summary reports across a date range.
The PC selects a "from" and "to" date, and this agent:

1. Retrieves all daily reports from Box for the selected period
2. Aggregates manpower, equipment, materials, delays, and progress
3. Produces an executive-level narrative summary
4. Generates a detailed, multi-section period report

This is the document clients actually read for progress meetings,
pay applications, and monthly updates. Daily reports are the raw
evidence; period summaries are the synthesized narrative.

Report length is determined by the data — more days, more trades,
more activity = longer, more detailed report.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from strands import Agent, tool

from src.config import get_settings
from src.models.schemas import (
    DelayCause,
    DelayEntry,
    EquipmentEntry,
    LaborEntry,
    MaterialDelivery,
    ObservationBundle,
)
from src.tools.tracing import trace_span



# ─── Aggregation Data Models ───────────────────────────────────


@dataclass
class TradeManpowerSummary:
    """Aggregated manpower for a single trade across the period."""
    trade: str
    subcontractor: str
    total_labor_hours: float = 0.0
    total_headcount_days: int = 0  # sum of daily headcounts
    avg_daily_headcount: float = 0.0
    peak_headcount: int = 0
    days_active: int = 0


@dataclass
class PeriodDelaySummary:
    """Aggregated delay data across the period."""
    total_delay_hours: float = 0.0
    delays_by_cause: dict = field(default_factory=dict)
    worst_delay_day: str = ""
    worst_delay_hours: float = 0.0
    force_majeure_hours: float = 0.0


@dataclass
class PeriodSafetySummary:
    """Safety record for the period."""
    total_days: int = 0
    incident_free_days: int = 0
    incidents: list = field(default_factory=list)
    toolbox_talks_conducted: int = 0


@dataclass
class PeriodProgressSummary:
    """Progress tracking across the period."""
    trades_active: list = field(default_factory=list)
    key_milestones: list = field(default_factory=list)
    work_highlights: list = field(default_factory=list)
    photo_highlights: list = field(default_factory=list)


@dataclass
class PeriodAggregation:
    """Complete aggregated data for a period summary report."""
    project_id: str
    project_name: str
    date_from: date
    date_to: date
    total_days: int
    working_days: int
    manpower: list = field(default_factory=list)  # List[TradeManpowerSummary]
    total_labor_hours: float = 0.0
    equipment_summary: list = field(default_factory=list)
    materials_summary: list = field(default_factory=list)
    delays: PeriodDelaySummary = field(default_factory=PeriodDelaySummary)
    safety: PeriodSafetySummary = field(default_factory=PeriodSafetySummary)
    progress: PeriodProgressSummary = field(default_factory=PeriodProgressSummary)
    inspections_passed: int = 0
    inspections_failed: int = 0
    weather_impact_days: int = 0
    daily_reports_count: int = 0




# ─── Aggregation Logic ─────────────────────────────────────────


def aggregate_daily_reports(
    daily_bundles: list[ObservationBundle],
    project_id: str,
    project_name: str,
    date_from: date,
    date_to: date,
) -> PeriodAggregation:
    """Aggregate multiple daily ObservationBundles into period-level summaries.

    This is pure data aggregation — no LLM calls. The agent uses this
    aggregated data to write the narrative.
    """
    agg = PeriodAggregation(
        project_id=project_id,
        project_name=project_name,
        date_from=date_from,
        date_to=date_to,
        total_days=(date_to - date_from).days + 1,
        working_days=len(daily_bundles),
        daily_reports_count=len(daily_bundles),
    )

    # Aggregate manpower by trade
    trade_data: dict[str, TradeManpowerSummary] = {}
    for bundle in daily_bundles:
        for labor in bundle.labor:
            key = f"{labor.trade}|{labor.subcontractor}"
            if key not in trade_data:
                trade_data[key] = TradeManpowerSummary(
                    trade=labor.trade,
                    subcontractor=labor.subcontractor,
                )
            td = trade_data[key]
            td.total_labor_hours += labor.headcount * labor.hours_worked
            td.total_headcount_days += labor.headcount
            td.peak_headcount = max(td.peak_headcount, labor.headcount)
            td.days_active += 1

    for td in trade_data.values():
        if td.days_active > 0:
            td.avg_daily_headcount = round(td.total_headcount_days / td.days_active, 1)
    agg.manpower = list(trade_data.values())
    agg.total_labor_hours = sum(t.total_labor_hours for t in agg.manpower)

    # Aggregate delays
    delay_summary = PeriodDelaySummary()
    for bundle in daily_bundles:
        day_delay_total = 0.0
        for delay in bundle.delays:
            delay_summary.total_delay_hours += delay.duration_hours
            day_delay_total += delay.duration_hours
            cause = delay.cause_category if isinstance(delay.cause_category, str) else delay.cause_category.value
            delay_summary.delays_by_cause[cause] = (
                delay_summary.delays_by_cause.get(cause, 0) + delay.duration_hours
            )
            if delay.is_force_majeure:
                delay_summary.force_majeure_hours += delay.duration_hours
        if day_delay_total > delay_summary.worst_delay_hours:
            delay_summary.worst_delay_hours = day_delay_total
            delay_summary.worst_delay_day = str(bundle.report_date)
    agg.delays = delay_summary

    # Aggregate equipment
    equip_totals: dict[str, dict] = {}
    for bundle in daily_bundles:
        for equip in bundle.equipment:
            if equip.equipment_type not in equip_totals:
                equip_totals[equip.equipment_type] = {
                    "type": equip.equipment_type,
                    "total_active_hours": 0,
                    "total_idle_hours": 0,
                    "days_on_site": 0,
                }
            equip_totals[equip.equipment_type]["total_active_hours"] += equip.hours_active
            equip_totals[equip.equipment_type]["total_idle_hours"] += equip.hours_idle
            equip_totals[equip.equipment_type]["days_on_site"] += 1
    agg.equipment_summary = list(equip_totals.values())

    # Aggregate materials
    material_totals: dict[str, dict] = {}
    for bundle in daily_bundles:
        for mat in bundle.materials:
            if mat.material not in material_totals:
                material_totals[mat.material] = {
                    "material": mat.material,
                    "total_quantity": mat.quantity,
                    "deliveries": 1,
                    "suppliers": {mat.supplier},
                }
            else:
                material_totals[mat.material]["deliveries"] += 1
                material_totals[mat.material]["suppliers"].add(mat.supplier)
    # Convert sets to lists for serialization
    for m in material_totals.values():
        m["suppliers"] = list(m["suppliers"])
    agg.materials_summary = list(material_totals.values())

    # Safety
    safety = PeriodSafetySummary(total_days=len(daily_bundles))
    safety.incident_free_days = len(daily_bundles)  # Assume all safe unless flagged
    agg.safety = safety

    # Inspections
    for bundle in daily_bundles:
        for insp in bundle.inspections:
            if insp.result.value == "pass":
                agg.inspections_passed += 1
            elif insp.result.value == "fail":
                agg.inspections_failed += 1

    # Weather impact
    agg.weather_impact_days = sum(
        1 for b in daily_bundles
        if b.weather.weather_delays
    )

    return agg




# ─── Strands Tool Definitions ──────────────────────────────────


@tool
def retrieve_daily_reports(project_id: str, date_from: str, date_to: str) -> dict:
    """Retrieve all daily report bundles from Box for the given date range.

    Args:
        project_id: Project identifier.
        date_from: Start date (YYYY-MM-DD).
        date_to: End date (YYYY-MM-DD).

    Returns:
        Dict with daily_reports list and metadata.
    """
    # TODO: Query Box for all observation bundles in the date range
    # For now, returns structure showing what would be retrieved
    return {
        "project_id": project_id,
        "date_from": date_from,
        "date_to": date_to,
        "daily_reports_found": 0,
        "note": "Will retrieve from Box /{project_id}/{date}/drafts/",
    }


@tool
def save_period_report(
    content: str, project_id: str, date_from: str, date_to: str
) -> str:
    """Save the period summary report to Box.

    Saves to: /{project_id}/period-summaries/{date_from}_to_{date_to}/

    Args:
        content: The complete period summary narrative (markdown).
        project_id: Project identifier.
        date_from: Period start date.
        date_to: Period end date.

    Returns:
        Box file ID of the saved report.
    """
    from src.tools.box_tools import get_or_create_folder, _get_box_client
    from io import BytesIO

    folder_name = f"{date_from}_to_{date_to}"
    # TODO: Create period-summaries subfolder and save
    return "box_file_id_placeholder"


# ─── System Prompt ─────────────────────────────────────────────

PERIOD_SUMMARY_SYSTEM_PROMPT = """You are the Period Summary Agent for SiteNarrator.

You generate comprehensive summary reports that cover a date range (weekly, bi-weekly, or monthly).
These reports are the primary deliverable to clients/owners for progress meetings and pay applications.

## Your Task:
Given aggregated data from multiple daily reports, produce a detailed, professional period summary.

## Report Structure (ALL sections required):

### 1. Executive Summary
- Period covered (dates)
- Total working days vs calendar days
- Total labor-hours expended
- Key accomplishments (3-5 bullet points)
- Key issues or risks (if any)
- Overall schedule assessment (on track / behind / ahead)

### 2. Manpower & Labor Summary
- Table: Trade | Subcontractor | Total Labor-Hours | Avg Daily Crew | Peak Crew | Days Active
- Total labor-hours for the period
- Manpower trend narrative (increasing/decreasing/stable)
- Comparison to planned manpower if available

### 3. Work Completed — Detailed by Trade
For EACH trade active during the period:
- What was accomplished (specific quantities, locations, milestones)
- Photo citations from daily reports [Photo references]
- Percentage complete (if trackable)
- Any issues or rework

### 4. Schedule & Progress Assessment
- Milestones achieved during the period
- Milestones missed or at risk
- Critical path activities status
- Look-ahead: key activities for next period

### 5. Equipment Utilization
- Table: Equipment | Total Active Hours | Total Idle Hours | Utilization % | Days on Site
- Equipment efficiency narrative
- Any equipment issues or needs

### 6. Materials & Procurement
- Table: Material | Total Quantity | Deliveries | Suppliers
- Any material delays or shortages
- Upcoming material needs

### 7. Weather Impact Analysis
- Days with weather impact
- Total weather delay hours
- Comparison to historical norms (if available)
- Impact on schedule

### 8. Delay & Issue Log
- Table: Date | Cause | Duration | Trades Affected | Category | Resolution
- Total delay hours by category (pie chart data)
- Cumulative delay impact on schedule
- Force majeure hours (for claims)

### 9. Safety Performance
- Incident-free days / total days
- Any incidents or near-misses (details)
- Toolbox talks conducted
- Safety compliance observations

### 10. Inspections & Quality
- Table: Date | Type | Result | Inspector | Notes
- Pass rate
- Any failed inspections and corrective actions
- Upcoming inspections

### 11. Issues Carried Forward
- Unresolved issues from the period
- Owner action items pending
- Design clarifications needed
- Permit or approval holds

### 12. Photo Documentation
- Key photos from the period with captions
- Before/after comparisons if applicable
- Progress photos by zone/area

### 13. Next Period Look-Ahead
- Planned activities by trade
- Expected manpower levels
- Key milestones targeted
- Known constraints or risks
- Required inspections
- Material deliveries expected

## Writing Rules:
- Professional, factual, third-person, past tense for completed work
- Quantify everything: hours, quantities, percentages, dates
- The report length should match the data — a 5-day period with 3 trades might be 5-8 pages; a 30-day period with 10 trades could be 15-25 pages
- Every claim must be traceable to a daily report
- Include specific dates for key events
- Use tables for structured data, narrative for context and analysis
- Flag any items requiring client/owner action or decision
"""




# ─── Agent Runner ──────────────────────────────────────────────


def run_period_summary(
    daily_bundles: list[ObservationBundle],
    project_id: str,
    project_name: str,
    date_from: date,
    date_to: date,
    gc_company: str = "",
    additional_context: str = "",
) -> str:
    """Run the Period Summary Agent to generate a comprehensive report.

    Args:
        daily_bundles: List of ObservationBundles for each day in the period.
        project_id: Project identifier.
        project_name: Human-readable project name.
        date_from: Period start date.
        date_to: Period end date.
        gc_company: General contractor company name.
        additional_context: Any additional context from the PC (e.g., "focus on delays").

    Returns:
        Complete period summary narrative (markdown format).
    """
    settings = get_settings()

    with trace_span("period_summary.agent_total", {
        "project_id": project_id,
        "date_from": str(date_from),
        "date_to": str(date_to),
        "daily_reports_count": len(daily_bundles),
    }):
        # Step 1: Aggregate all daily data
        with trace_span("period_summary.aggregation"):
            aggregation = aggregate_daily_reports(
                daily_bundles=daily_bundles,
                project_id=project_id,
                project_name=project_name,
                date_from=date_from,
                date_to=date_to,
            )

        # Step 2: Build prompt with aggregated data
        prompt = _build_period_prompt(aggregation, gc_company, additional_context)

        # Step 3: Run the agent
        agent = Agent(
            model=settings.bedrock_model_id,
            tools=[retrieve_daily_reports, save_period_report],
            system_prompt=PERIOD_SUMMARY_SYSTEM_PROMPT,
        )

        response = agent(prompt)
        return str(response)


def _build_period_prompt(
    agg: PeriodAggregation,
    gc_company: str,
    additional_context: str,
) -> str:
    """Build the prompt for the Period Summary Agent with all aggregated data."""
    parts = [
        "## Period Summary Report Generation",
        "",
        f"**Project:** {agg.project_name} ({agg.project_id})",
        f"**General Contractor:** {gc_company}",
        f"**Period:** {agg.date_from} to {agg.date_to}",
        f"**Calendar Days:** {agg.total_days}",
        f"**Working Days (reports filed):** {agg.working_days}",
        f"**Total Labor-Hours:** {agg.total_labor_hours:,.1f}",
        "",
    ]

    # Manpower data
    parts.append("## Manpower Data (Aggregated)")
    parts.append("| Trade | Subcontractor | Total LH | Avg Daily Crew | Peak | Days Active |")
    parts.append("|-------|--------------|----------|---------------|------|-------------|")
    for t in agg.manpower:
        parts.append(
            f"| {t.trade} | {t.subcontractor} | {t.total_labor_hours:.1f} | "
            f"{t.avg_daily_headcount} | {t.peak_headcount} | {t.days_active} |"
        )
    parts.append("")

    # Equipment data
    if agg.equipment_summary:
        parts.append("## Equipment Data (Aggregated)")
        parts.append("| Equipment | Total Active Hrs | Total Idle Hrs | Days on Site |")
        parts.append("|-----------|-----------------|---------------|-------------|")
        for e in agg.equipment_summary:
            parts.append(
                f"| {e['type']} | {e['total_active_hours']:.1f} | "
                f"{e['total_idle_hours']:.1f} | {e['days_on_site']} |"
            )
        parts.append("")

    # Materials data
    if agg.materials_summary:
        parts.append("## Materials Data (Aggregated)")
        parts.append("| Material | Total Quantity | Deliveries | Suppliers |")
        parts.append("|----------|--------------|-----------|----------|")
        for m in agg.materials_summary:
            suppliers = ", ".join(m["suppliers"]) if isinstance(m["suppliers"], list) else str(m["suppliers"])
            parts.append(
                f"| {m['material']} | {m['total_quantity']} | "
                f"{m['deliveries']} | {suppliers} |"
            )
        parts.append("")

    # Delay data
    parts.append("## Delay Data (Aggregated)")
    parts.append(f"- Total delay hours: {agg.delays.total_delay_hours:.1f}")
    parts.append(f"- Force majeure hours: {agg.delays.force_majeure_hours:.1f}")
    parts.append(f"- Worst delay day: {agg.delays.worst_delay_day} ({agg.delays.worst_delay_hours:.1f} hrs)")
    parts.append("- Delays by cause:")
    for cause, hours in agg.delays.delays_by_cause.items():
        parts.append(f"  - {cause}: {hours:.1f} hours")
    parts.append("")

    # Safety
    parts.append("## Safety Data")
    parts.append(f"- Total days: {agg.safety.total_days}")
    parts.append(f"- Incident-free days: {agg.safety.incident_free_days}")
    parts.append("")

    # Inspections
    parts.append("## Inspections")
    parts.append(f"- Passed: {agg.inspections_passed}")
    parts.append(f"- Failed: {agg.inspections_failed}")
    parts.append(f"- Weather impact days: {agg.weather_impact_days}")
    parts.append("")

    # Additional context from PC
    if additional_context:
        parts.append("## Additional Instructions from Project Coordinator")
        parts.append(additional_context)
        parts.append("")

    # Final instruction
    parts.append("## Instructions")
    parts.append(
        "Generate a comprehensive period summary report using ALL the data above. "
        "The report should be detailed and professional — length is determined by "
        "the amount of data. A week with 3 trades might be 5-8 pages. A month with "
        "10 trades should be 15-25 pages. Do not truncate or summarize excessively. "
        "Every trade, every delay, every inspection should be covered."
    )
    parts.append("")
    parts.append(
        f"After generating, call `save_period_report` with project_id='{agg.project_id}', "
        f"date_from='{agg.date_from}', date_to='{agg.date_to}'."
    )

    return "\n".join(parts)
