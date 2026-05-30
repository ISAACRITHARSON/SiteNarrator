"""SiteNarrator — Ingest + Vision Agent.

The first agent in the pipeline. Responsible for:
1. Uploading photos to Box and extracting structured observations via Box AI Extract
2. Transcribing voice notes via AWS Transcribe
3. Extracting structured field data from voice transcripts (labor, equipment, delays, inspections)
4. Fetching weather data from OpenWeatherMap
5. Producing a complete ObservationBundle for the Synthesis Agent

Key insight: The voice note is the PRIMARY data source (~60% of report content).
Photos provide visual evidence (~40%). The voice note carries crew counts, hours,
equipment, delays, and inspections — data invisible in photos.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any

from strands import Agent, tool

from src.config import get_settings
from src.models.schemas import (
    DelayEntry,
    EquipmentEntry,
    InspectionEntry,
    LaborEntry,
    MaterialDelivery,
    ObservationBundle,
    PhotoObservation,
    WeatherData,
)
from src.tools.box_tools import extract_observations, upload_photo
from src.tools.tracing import log_llm_call, trace_span
from src.tools.weather_tools import get_weather


# ─── Strands Tool Definitions ──────────────────────────────────


@tool
def upload_and_extract_photo(
    file_path: str,
    project_id: str,
    report_date: str,
    trade: str,
    zone: str,
    citation_ref: str,
) -> dict:
    """Upload a photo to Box and extract structured construction observations.

    Args:
        file_path: Local path to the photo file
        project_id: Project identifier
        report_date: Date of the report (YYYY-MM-DD)
        trade: Trade tag (e.g., concrete, electrical, plumbing)
        zone: Site zone (e.g., Level 2, North Wing)
        citation_ref: Citation reference (e.g., "Photo 1")

    Returns:
        Dict with box_file_id, citation_ref, trade, zone, and extracted observations.
    """
    with trace_span("ingest.upload_and_extract", {"trade": trade, "citation_ref": citation_ref}):
        # Upload to Box
        box_file_id = upload_photo(file_path, project_id, report_date, trade)

        # Extract observations via Box AI Extract
        observations = extract_observations(box_file_id)

        return {
            "box_file_id": box_file_id,
            "citation_ref": citation_ref,
            "trade": trade,
            "zone": zone or observations.get("zone_estimate", ""),
            "work_type": observations.get("work_type", ""),
            "progress_state": observations.get("progress_state", ""),
            "safety_conditions": observations.get("safety_conditions", ""),
            "materials_present": observations.get("materials_present", ""),
            "extraction_confidence": observations.get("confidence", 0.85),
        }


@tool
def fetch_weather(lat: float, lon: float, report_date: str) -> dict:
    """Fetch weather conditions for the project site on the report date.

    Args:
        lat: Project site latitude
        lon: Project site longitude
        report_date: Date of the report (YYYY-MM-DD)

    Returns:
        Weather data dict with temp_high, temp_low, precipitation, wind, humidity, conditions.
    """
    return get_weather(lat, lon, report_date)


@tool
def extract_structured_data_from_transcript(transcript: str) -> dict:
    """Extract structured field data from a superintendent's voice note transcript.

    This is the CRITICAL extraction step. The voice note carries:
    - Labor: trade, subcontractor, headcount, hours, zone
    - Equipment: type, hours active, hours idle
    - Materials: type, quantity, supplier, time
    - Delays: cause, duration, trades affected, category
    - Inspections: inspector, agency, type, result

    Args:
        transcript: The transcribed text from the superintendent's voice note.

    Returns:
        Structured dict with labor, equipment, materials, delays, inspections arrays.
    """
    # This tool is a pass-through — the LLM does the extraction
    # by analyzing the transcript in context. The agent's system prompt
    # instructs it to call this tool with the parsed structured data.
    return {"transcript_received": True, "length": len(transcript)}


# ─── System Prompt ─────────────────────────────────────────────

INGEST_SYSTEM_PROMPT = """You are the Ingest Agent for SiteNarrator, a construction daily report system.

Your job is to process field inputs (photos + voice notes) and produce a structured ObservationBundle.

## Your Responsibilities:

1. **Photo Processing**: For each photo provided, call `upload_and_extract_photo` to upload it to Box and extract structured observations. Process ALL photos — never skip one.

2. **Weather**: Call `fetch_weather` with the project's GPS coordinates to get weather conditions.

3. **Voice Note Extraction**: This is your MOST IMPORTANT task. The superintendent's voice note contains critical structured data that photos cannot show:
   - **Labor**: Which trades were on site, how many workers, hours worked, which subcontractor
   - **Equipment**: What equipment was on site, hours active vs idle
   - **Materials**: What was delivered, quantity, supplier, time
   - **Delays**: What caused delays, how long, which trades affected
   - **Inspections**: Who inspected, what type, pass/fail result

4. **Grouping**: Group photo observations by trade tag.

## Voice Note Extraction Rules:
- Extract EVERY piece of structured data mentioned
- If the superintendent says "8 guys from Pacific Steel", that's: trade=steel, subcontractor=Pacific Steel, headcount=8
- If they mention "rain delay 2 to 3:30", that's: cause=rain, duration=1.5 hours, category=weather, is_force_majeure=true
- If they say "inspector passed the rough-in", that's: inspection_type=rough-in, result=pass
- If data is ambiguous, note it but still extract your best interpretation

## Output Format:
Return a complete JSON ObservationBundle with all extracted data organized into:
- weather: WeatherData object
- labor: array of LaborEntry objects
- equipment: array of EquipmentEntry objects  
- materials: array of MaterialDelivery objects
- delays: array of DelayEntry objects
- inspections: array of InspectionEntry objects
- photos: dict keyed by trade tag, each containing array of PhotoObservation objects

Be thorough. A construction daily report is a legal document used in disputes worth millions of dollars. Missing data has real consequences.
"""


# ─── Agent Runner ──────────────────────────────────────────────


def run_ingest(
    photos: list[dict],
    voice_transcript: str,
    text_notes: str,
    project_id: str,
    report_date: str,
    superintendent: str,
    lat: float,
    lon: float,
) -> ObservationBundle:
    """Run the Ingest Agent to process field inputs into an ObservationBundle.

    Args:
        photos: List of dicts with keys: file_path, trade, zone
        voice_transcript: Transcribed text from voice note (already transcribed)
        text_notes: Additional text notes from superintendent
        project_id: Project identifier
        report_date: Report date (YYYY-MM-DD)
        superintendent: Superintendent name
        lat: Project site latitude
        lon: Project site longitude

    Returns:
        Complete ObservationBundle ready for the Synthesis Agent.
    """
    settings = get_settings()

    with trace_span("ingest.agent_total", {
        "project_id": project_id,
        "photo_count": len(photos),
        "has_voice_note": bool(voice_transcript),
    }):
        agent = Agent(
            model=settings.bedrock_model_id,
            tools=[upload_and_extract_photo, fetch_weather, extract_structured_data_from_transcript],
            system_prompt=INGEST_SYSTEM_PROMPT,
        )

        # Build the prompt with all inputs
        prompt = _build_ingest_prompt(
            photos=photos,
            voice_transcript=voice_transcript,
            text_notes=text_notes,
            project_id=project_id,
            report_date=report_date,
            superintendent=superintendent,
            lat=lat,
            lon=lon,
        )

        # Run the agent
        response = agent(prompt)

        # Parse the agent's structured output into an ObservationBundle
        bundle = _parse_agent_response(
            response=str(response),
            project_id=project_id,
            report_date=report_date,
            superintendent=superintendent,
            voice_transcript=voice_transcript,
            text_notes=text_notes,
        )

        return bundle


def _build_ingest_prompt(
    photos: list[dict],
    voice_transcript: str,
    text_notes: str,
    project_id: str,
    report_date: str,
    superintendent: str,
    lat: float,
    lon: float,
) -> str:
    """Build the prompt for the Ingest Agent."""
    prompt_parts = [
        f"## Daily Report Submission",
        f"- Project ID: {project_id}",
        f"- Date: {report_date}",
        f"- Superintendent: {superintendent}",
        f"- Location: ({lat}, {lon})",
        f"",
        f"## Photos to Process ({len(photos)} total)",
    ]

    for i, photo in enumerate(photos, 1):
        prompt_parts.append(
            f"- Photo {i}: file_path={photo['file_path']}, "
            f"trade={photo['trade']}, zone={photo.get('zone', '')}"
        )

    prompt_parts.append("")
    prompt_parts.append("## Voice Note Transcript")
    if voice_transcript:
        prompt_parts.append(voice_transcript)
    else:
        prompt_parts.append("(No voice note provided)")

    if text_notes:
        prompt_parts.append("")
        prompt_parts.append("## Additional Text Notes")
        prompt_parts.append(text_notes)

    prompt_parts.append("")
    prompt_parts.append("## Instructions")
    prompt_parts.append(
        "1. Call fetch_weather with the GPS coordinates to get today's weather."
    )
    prompt_parts.append(
        "2. Call upload_and_extract_photo for EACH photo listed above."
    )
    prompt_parts.append(
        "3. Extract ALL structured data from the voice note transcript: "
        "labor entries, equipment, materials, delays, inspections."
    )
    prompt_parts.append(
        "4. Return the complete ObservationBundle as structured JSON."
    )

    return "\n".join(prompt_parts)


def _parse_agent_response(
    response: str,
    project_id: str,
    report_date: str,
    superintendent: str,
    voice_transcript: str,
    text_notes: str,
) -> ObservationBundle:
    """Parse the agent's response into a validated ObservationBundle.

    The agent returns structured JSON which we validate through Pydantic.
    If parsing fails, we return a minimal bundle with what we have.
    """
    try:
        # Try to extract JSON from the response
        json_start = response.find("{")
        json_end = response.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            data = json.loads(response[json_start:json_end])
        else:
            data = {}
    except json.JSONDecodeError:
        data = {}

    # Build the ObservationBundle from parsed data
    weather_data = data.get("weather", {})
    weather = WeatherData(
        temp_high=weather_data.get("temp_high", 0),
        temp_low=weather_data.get("temp_low", 0),
        precipitation_mm=weather_data.get("precipitation_mm", 0),
        wind_kph=weather_data.get("wind_kph", 0),
        humidity=weather_data.get("humidity", 0),
        conditions=weather_data.get("conditions", ""),
        weather_delays=[
            DelayEntry(**d) for d in weather_data.get("weather_delays", [])
        ],
    )

    labor = [LaborEntry(**entry) for entry in data.get("labor", [])]
    equipment = [EquipmentEntry(**entry) for entry in data.get("equipment", [])]
    materials = [MaterialDelivery(**entry) for entry in data.get("materials", [])]
    delays = [DelayEntry(**entry) for entry in data.get("delays", [])]
    inspections = [InspectionEntry(**entry) for entry in data.get("inspections", [])]

    # Parse photos grouped by trade
    photos_by_trade: dict[str, list[PhotoObservation]] = {}
    for trade, photo_list in data.get("photos", {}).items():
        photos_by_trade[trade] = [
            PhotoObservation(**p) for p in photo_list
        ]

    return ObservationBundle(
        project_id=project_id,
        report_date=date.fromisoformat(report_date),
        superintendent=superintendent,
        weather=weather,
        labor=labor,
        equipment=equipment,
        materials=materials,
        delays=delays,
        inspections=inspections,
        photos=photos_by_trade,
        voice_transcript=voice_transcript,
        text_notes=text_notes,
    )
