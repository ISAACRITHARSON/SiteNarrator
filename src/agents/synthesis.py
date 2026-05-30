"""SiteNarrator — Synthesis Agent.

The second agent in the pipeline. Responsible for:
1. Querying AgentCore Episodic Memory for project tone/style preferences
2. Consuming the ObservationBundle from the Ingest Agent
3. Producing a 10-section daily narrative report with inline photo citations
4. Saving the draft to Box

The narrative must be professional, past-tense, third-person, and include
inline [Photo N] citations at every claim backed by visual evidence.
"""

from __future__ import annotations

from typing import Any

from strands import Agent, tool

from src.config import get_settings
from src.models.schemas import ObservationBundle
from src.tools.box_tools import save_draft
from src.tools.tracing import trace_span


# ─── Strands Tool Definitions ──────────────────────────────────


@tool
def query_project_memory(project_id: str) -> dict:
    """Query AgentCore Episodic Memory for project-specific preferences.

    Retrieves: client_name, preferred_tone, trade_name_preferences,
    approved_phrase_examples, and correction_history.

    Args:
        project_id: The project identifier to query memory for.

    Returns:
        Dict with project preferences. Empty dict if no memory exists (cold start).
    """
    with trace_span("synthesis.memory_query", {"project_id": project_id}):
        settings = get_settings()

        # If AgentCore Memory is configured, query it
        if settings.agentcore_memory_id:
            try:
                from bedrock_agentcore.memory import MemoryClient

                client = MemoryClient(region_name=settings.aws_region)
                # Query for project-specific memories
                results = client.retrieve_memories(
                    memory_id=settings.agentcore_memory_id,
                    query=f"project preferences and style for {project_id}",
                    namespace=f"/strategy/sitenarrator/actor/{project_id}/",
                )
                if results:
                    return results[0] if isinstance(results, list) else results
            except Exception:
                pass

        # Fallback: return default preferences (cold start)
        return {
            "client_name": "",
            "preferred_tone": "professional",
            "trade_name_preferences": {},
            "approved_phrase_examples": [],
            "correction_history": [],
            "note": "No project memory found. Using default professional tone.",
        }


@tool
def save_narrative_draft(
    narrative: str, project_id: str, report_date: str, version: int
) -> str:
    """Save the draft narrative to Box.

    Args:
        narrative: The complete narrative text (markdown format).
        project_id: Project identifier.
        report_date: Report date (YYYY-MM-DD).
        version: Draft version number (1 for initial, 2+ for revisions).

    Returns:
        Box file ID of the saved draft.
    """
    return save_draft(narrative, project_id, report_date, version)


# ─── System Prompt ─────────────────────────────────────────────

SYNTHESIS_SYSTEM_PROMPT = """You are the Synthesis Agent for SiteNarrator, a construction daily report system.

Your job is to transform a structured ObservationBundle into a professional, client-ready daily narrative report.

## Report Structure (10 Sections — ALL REQUIRED):

### 1. Project Header
- Project name, project number, date, report number, superintendent name, general contractor

### 2. Weather & Site Conditions
- Temperature (high/low), precipitation, wind, humidity
- Ground conditions and their impact on work
- If weather caused any delays, state duration and affected trades

### 3. Manpower Summary
Format as a table:
| Trade | Subcontractor | Headcount | Hours | Zone |
Include EVERY trade that was on site. If data is from the voice note, include it.

### 4. Work Completed by Trade
- One paragraph per trade
- MUST include at least one [Photo N] citation per trade entry
- Include: what was done, where (zone), quantity or percentage complete, crew size
- Write in past tense, third person, professional tone
- Example: "The concrete crew (8 workers, Pacific Steel) completed the Level 2 slab pour, approximately 400 sq ft [Photo 3]. Forms were stripped on the north elevation [Photo 5]."

### 5. Equipment on Site
Format as a table:
| Equipment | Hours Active | Hours Idle | Notes |

### 6. Material Deliveries
Format as a table:
| Material | Quantity | Supplier | Time Received |

### 7. Safety Observations
- PPE compliance, housekeeping, fall protection
- Any incidents or near-misses
- Toolbox talks conducted
- If nothing notable: "No safety incidents observed. All personnel observed in compliance with site safety requirements."

### 8. Inspections & Visitors
- Inspector name, agency, inspection type, result
- Any other visitors and purpose of visit
- If none: "No inspections or notable visitors today."

### 9. Delays & Issues
- Cause, duration, trades affected, responsible party
- Categorize: weather, owner-directed, design error, subcontractor, material delivery, other
- If no delays: "No delays or issues to report."

### 10. Work Planned for Next Day
- By trade, what is planned
- Any known constraints (inspections needed, material deliveries expected, weather forecast)

## Writing Rules:
- Past tense, third person, professional tone
- Every factual claim about visible work MUST have a [Photo N] citation
- Use the project's preferred trade names from memory (if available)
- Match the project's established tone from memory (if available)
- Be specific: quantities, percentages, zone locations, crew sizes
- Never fabricate data — if something wasn't reported, don't include it
- Sections with no data should still appear with a "Nothing to report" statement

## After Drafting:
Call `save_narrative_draft` to save the draft to Box.
"""


# ─── Agent Runner ──────────────────────────────────────────────


def run_synthesis(
    observation_bundle: ObservationBundle,
    version: int = 1,
    section_comments: dict[str, str] | None = None,
) -> str:
    """Run the Synthesis Agent to produce a narrative draft.

    Args:
        observation_bundle: Complete ObservationBundle from the Ingest Agent.
        version: Draft version (1 for initial, 2+ for revisions).
        section_comments: If revising, dict of section_name -> PC comment.
                         Only flagged sections will be re-drafted.

    Returns:
        The complete narrative text (markdown format).
    """
    settings = get_settings()

    with trace_span("synthesis.agent_total", {
        "project_id": observation_bundle.project_id,
        "version": version,
        "is_revision": section_comments is not None,
    }):
        agent = Agent(
            model=settings.bedrock_model_id,
            tools=[query_project_memory, save_narrative_draft],
            system_prompt=SYNTHESIS_SYSTEM_PROMPT,
        )

        prompt = _build_synthesis_prompt(observation_bundle, version, section_comments)
        response = agent(prompt)

        return str(response)


def _build_synthesis_prompt(
    bundle: ObservationBundle,
    version: int,
    section_comments: dict[str, str] | None = None,
) -> str:
    """Build the prompt for the Synthesis Agent."""
    parts = [
        "## Task: Generate Daily Narrative Report",
        "",
        f"Project ID: {bundle.project_id}",
        f"Date: {bundle.report_date}",
        f"Superintendent: {bundle.superintendent}",
        f"Draft Version: {version}",
        "",
    ]

    # Step 1: Query memory
    parts.append("## Step 1: Query Project Memory")
    parts.append(f"Call `query_project_memory` with project_id='{bundle.project_id}' to get tone/style preferences.")
    parts.append("")

    # Weather data
    parts.append("## Weather Data")
    w = bundle.weather
    parts.append(f"- High: {w.temp_high}°F, Low: {w.temp_low}°F")
    parts.append(f"- Precipitation: {w.precipitation_mm}mm")
    parts.append(f"- Wind: {w.wind_kph} kph")
    parts.append(f"- Humidity: {w.humidity}%")
    parts.append(f"- Conditions: {w.conditions}")
    if w.weather_delays:
        for d in w.weather_delays:
            parts.append(f"- Weather delay: {d.cause}, {d.duration_hours}hrs, affected: {', '.join(d.trades_affected)}")
    parts.append("")

    # Labor data
    if bundle.labor:
        parts.append("## Labor Data (from voice note)")
        for entry in bundle.labor:
            parts.append(
                f"- {entry.trade}: {entry.subcontractor}, "
                f"{entry.headcount} workers, {entry.hours_worked}hrs, zone: {entry.zone}"
            )
        parts.append("")

    # Equipment data
    if bundle.equipment:
        parts.append("## Equipment Data (from voice note)")
        for entry in bundle.equipment:
            parts.append(
                f"- {entry.equipment_type}: {entry.hours_active}hrs active, "
                f"{entry.hours_idle}hrs idle ({entry.owned_or_rental})"
            )
        parts.append("")

    # Material deliveries
    if bundle.materials:
        parts.append("## Material Deliveries (from voice note)")
        for entry in bundle.materials:
            parts.append(
                f"- {entry.material}: {entry.quantity} from {entry.supplier} at {entry.time_received}"
            )
        parts.append("")

    # Delays
    if bundle.delays:
        parts.append("## Delays (from voice note)")
        for entry in bundle.delays:
            parts.append(
                f"- {entry.cause} ({entry.cause_category}): {entry.duration_hours}hrs, "
                f"affected: {', '.join(entry.trades_affected)}"
            )
        parts.append("")

    # Inspections
    if bundle.inspections:
        parts.append("## Inspections (from voice note)")
        for entry in bundle.inspections:
            parts.append(
                f"- {entry.inspection_type}: {entry.result} by {entry.inspector_name} ({entry.agency}) at {entry.time}"
            )
        parts.append("")

    # Photo observations
    parts.append("## Photo Observations (from Box AI Extract)")
    for trade, photos in bundle.photos.items():
        parts.append(f"### Trade: {trade}")
        for photo in photos:
            parts.append(
                f"- [{photo.citation_ref}] (Box ID: {photo.box_file_id}): "
                f"work_type={photo.work_type}, progress={photo.progress_state}, "
                f"zone={photo.zone}, safety={photo.safety_conditions}"
            )
    parts.append("")

    # Voice transcript (for additional context)
    if bundle.voice_transcript:
        parts.append("## Raw Voice Transcript (for additional context)")
        parts.append(bundle.voice_transcript)
        parts.append("")

    # Text notes
    if bundle.text_notes:
        parts.append("## Additional Text Notes")
        parts.append(bundle.text_notes)
        parts.append("")

    # Revision instructions
    if section_comments:
        parts.append("## REVISION INSTRUCTIONS")
        parts.append("The PC has requested revisions to the following sections ONLY.")
        parts.append("Re-draft these sections. Keep all other sections unchanged.")
        for section, comment in section_comments.items():
            parts.append(f"- **{section}**: {comment}")
        parts.append("")

    # Final instruction
    parts.append("## Final Step")
    parts.append(
        f"After generating the complete narrative, call `save_narrative_draft` "
        f"with project_id='{bundle.project_id}', report_date='{bundle.report_date}', version={version}."
    )

    return "\n".join(parts)
