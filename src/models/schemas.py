"""SiteNarrator — Core data models.

These Pydantic models define the data contracts between agents,
tools, and the API layer. They represent the real-world entities
in construction daily reporting.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ─── Enums ─────────────────────────────────────────────────────


class TradeTag(str, Enum):
    """Standard construction trade categories."""

    CONCRETE = "concrete"
    ELECTRICAL = "electrical"
    PLUMBING = "plumbing"
    FRAMING = "framing"
    HVAC = "hvac"
    ROOFING = "roofing"
    DRYWALL = "drywall"
    PAINTING = "painting"
    MASONRY = "masonry"
    STEEL = "steel"
    EXCAVATION = "excavation"
    LANDSCAPING = "landscaping"
    FIRE_PROTECTION = "fire_protection"
    INSULATION = "insulation"
    GLAZING = "glazing"
    OTHER = "other"


class DelayCause(str, Enum):
    """Categorization of delay causes for claims documentation."""

    WEATHER = "weather"
    OWNER_DIRECTED = "owner_directed"
    DESIGN_ERROR = "design_error"
    SUBCONTRACTOR = "subcontractor"
    MATERIAL_DELIVERY = "material_delivery"
    INSPECTION_HOLD = "inspection_hold"
    PERMIT = "permit"
    OTHER = "other"


class InspectionResult(str, Enum):
    """Inspection outcome categories."""

    PASS = "pass"
    FAIL = "fail"
    PARTIAL = "partial"
    DEFERRED = "deferred"


class Severity(str, Enum):
    """Quality flag severity levels."""

    WARNING = "warning"
    ERROR = "error"


class ReportStatus(str, Enum):
    """Report lifecycle states."""

    PROCESSING = "processing"
    DRAFT_READY = "draft_ready"
    IN_REVIEW = "in_review"
    REVISION_REQUESTED = "revision_requested"
    APPROVED = "approved"
    DELIVERED = "delivered"


# ─── Ingest Agent Models ───────────────────────────────────────


class PhotoObservation(BaseModel):
    """Structured observation extracted from a single photo via Box AI Extract."""

    box_file_id: str
    citation_ref: str = Field(description="e.g., 'Photo 1'")
    trade: TradeTag
    zone: str = Field(default="", description="Site zone, e.g., 'Level 2 North Wing'")
    work_type: str = Field(description="Type of work visible")
    progress_state: str = Field(description="Apparent progress state")
    safety_conditions: str = Field(default="")
    materials_present: str = Field(default="")
    extraction_confidence: float = Field(ge=0.0, le=1.0)


class LaborEntry(BaseModel):
    """Crew/labor data extracted from voice note or text input."""

    trade: TradeTag
    subcontractor: str
    headcount: int = Field(ge=0)
    hours_worked: float = Field(ge=0.0)
    zone: str = Field(default="")
    notes: str = Field(default="")


class EquipmentEntry(BaseModel):
    """Equipment usage data for the day."""

    equipment_type: str
    hours_active: float = Field(ge=0.0)
    hours_idle: float = Field(ge=0.0, default=0.0)
    owned_or_rental: str = Field(default="owned")
    notes: str = Field(default="")


class MaterialDelivery(BaseModel):
    """Material delivery record."""

    material: str
    quantity: str
    supplier: str = Field(default="")
    time_received: str = Field(default="")
    notes: str = Field(default="")


class DelayEntry(BaseModel):
    """Delay record for claims documentation."""

    cause: str
    cause_category: DelayCause
    duration_hours: float = Field(ge=0.0)
    trades_affected: list[str] = Field(default_factory=list)
    is_force_majeure: bool = False
    notes: str = Field(default="")


class InspectionEntry(BaseModel):
    """Inspection or visitor record."""

    inspector_name: str = Field(default="")
    agency: str = Field(default="")
    inspection_type: str
    result: InspectionResult
    time: str = Field(default="")
    notes: str = Field(default="")


class WeatherData(BaseModel):
    """Weather conditions for the report date."""

    temp_high: float
    temp_low: float
    precipitation_mm: float = Field(default=0.0)
    wind_kph: float = Field(default=0.0)
    humidity: float = Field(default=0.0)
    conditions: str
    weather_delays: list[DelayEntry] = Field(default_factory=list)


class ObservationBundle(BaseModel):
    """Complete output of the Ingest Agent.

    This is the primary data structure passed from Ingest -> Synthesis.
    It combines photo observations, voice note extractions, and weather data.
    """

    project_id: str
    report_date: date
    superintendent: str
    weather: WeatherData
    labor: list[LaborEntry] = Field(default_factory=list)
    equipment: list[EquipmentEntry] = Field(default_factory=list)
    materials: list[MaterialDelivery] = Field(default_factory=list)
    delays: list[DelayEntry] = Field(default_factory=list)
    inspections: list[InspectionEntry] = Field(default_factory=list)
    photos: dict[str, list[PhotoObservation]] = Field(
        default_factory=dict, description="Keyed by trade tag"
    )
    voice_transcript: str = Field(default="")
    text_notes: str = Field(default="")
    trace_id: str = Field(default="")


# ─── Quality Agent Models ──────────────────────────────────────


class SectionFlag(BaseModel):
    """A quality issue flagged by the Quality Agent."""

    section: str
    issue: str
    severity: Severity


class QualityReport(BaseModel):
    """Output of the Quality + Compliance Agent."""

    confidence_score: float = Field(ge=0.0, le=1.0)
    flags: list[SectionFlag] = Field(default_factory=list)
    summary: str
    passed: bool
    trace_id: str = Field(default="")


# ─── Eval Agent Models ─────────────────────────────────────────


class EvalReport(BaseModel):
    """Output of the Eval + Observability Agent."""

    hallucination_score: float = Field(
        ge=0.0, le=1.0, description="0.0 = no hallucinations detected"
    )
    citation_accuracy: float = Field(
        ge=0.0, le=1.0, description="1.0 = all citations map correctly"
    )
    tone_consistency: float = Field(
        ge=0.0, le=1.0, description="1.0 = matches project memory style"
    )
    overall_score: float = Field(ge=0.0, le=1.0)
    cost_usd: float = Field(ge=0.0)
    latency_ms: int = Field(ge=0)
    trace_id: str = Field(default="")
    recommendations: list[str] = Field(default_factory=list)


# ─── API Models ────────────────────────────────────────────────


class SubmissionRequest(BaseModel):
    """Metadata accompanying a photo/voice submission."""

    project_id: str
    report_date: date
    superintendent_name: str
    lat: float
    lon: float
    trade_tags: list[TradeTag]
    zones: list[str] = Field(default_factory=list)
    text_notes: str = Field(default="")


class DraftResponse(BaseModel):
    """Response when retrieving a draft for PC review."""

    draft_id: str
    project_id: str
    report_date: date
    narrative: str
    quality_report: QualityReport
    eval_report: Optional[EvalReport] = None
    status: ReportStatus
    photo_citations: list[dict] = Field(default_factory=list)
    trace_id: str = Field(default="")
    created_at: datetime
    updated_at: datetime


class ApprovalRequest(BaseModel):
    """PC approval action."""

    approved_by: str
    edits_made: bool = False
    edited_narrative: Optional[str] = None


class RejectionRequest(BaseModel):
    """PC rejection with section-level comments."""

    rejected_by: str
    section_comments: dict[str, str] = Field(
        description="Map of section name -> revision comment"
    )


class ChatMessage(BaseModel):
    """A single message in the client Q&A chat."""

    role: str = Field(description="'client' or 'assistant'")
    content: str
    citations: list[str] = Field(default_factory=list)
    confidence: Optional[float] = None
    escalated: bool = False
    timestamp: datetime = Field(default_factory=datetime.utcnow)
