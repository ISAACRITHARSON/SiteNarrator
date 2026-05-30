"""SiteNarrator — Report generation routes.

Handles period summary report generation. The PC selects a date range
and the system generates a comprehensive summary across all daily reports
in that period.
"""

from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.models.schemas import ReportStatus

router = APIRouter()


class PeriodReportRequest(BaseModel):
    """Request to generate a period summary report."""

    project_id: str
    date_from: date = Field(description="Period start date")
    date_to: date = Field(description="Period end date")
    report_type: str = Field(
        default="period_summary",
        description="Report type: 'period_summary' or 'daily'",
    )
    additional_context: str = Field(
        default="",
        description="Optional instructions from PC (e.g., 'focus on delays', 'highlight safety')",
    )
    requested_by: str = Field(description="PC name requesting the report")


class PeriodReportResponse(BaseModel):
    """Response after period report generation is triggered."""

    report_id: str
    project_id: str
    date_from: date
    date_to: date
    status: ReportStatus
    working_days: int
    estimated_pages: int
    message: str


@router.post("/reports/generate", response_model=PeriodReportResponse)
async def generate_period_report(request: PeriodReportRequest):
    """Generate a period summary report for a date range.

    The PC selects a from/to date range. The system:
    1. Retrieves all daily reports from Box for that period
    2. Aggregates manpower, equipment, materials, delays
    3. Runs the Period Summary Agent to produce a comprehensive narrative
    4. Saves the draft for PC review before client delivery

    Report length is determined by the data — the agent decides how
    detailed to be based on the number of days and activity level.
    """
    # Validate date range
    if request.date_from > request.date_to:
        raise HTTPException(
            status_code=400,
            detail="date_from must be before date_to",
        )

    days_in_range = (request.date_to - request.date_from).days + 1
    if days_in_range > 90:
        raise HTTPException(
            status_code=400,
            detail="Maximum report period is 90 days. For longer periods, generate multiple reports.",
        )

    # Estimate report length based on period
    if days_in_range <= 7:
        estimated_pages = max(5, days_in_range * 2)
    elif days_in_range <= 14:
        estimated_pages = max(8, days_in_range)
    elif days_in_range <= 30:
        estimated_pages = max(12, int(days_in_range * 0.7))
    else:
        estimated_pages = max(15, int(days_in_range * 0.5))

    import uuid
    report_id = str(uuid.uuid4())

    # TODO: Trigger Period Summary Agent asynchronously
    # 1. Retrieve daily bundles from Box
    # 2. Run aggregate_daily_reports()
    # 3. Run run_period_summary()
    # 4. Save draft for PC review

    return PeriodReportResponse(
        report_id=report_id,
        project_id=request.project_id,
        date_from=request.date_from,
        date_to=request.date_to,
        status=ReportStatus.PROCESSING,
        working_days=days_in_range,  # Will be refined after checking actual reports
        estimated_pages=estimated_pages,
        message=f"Period summary generation started for {days_in_range} days. "
        f"Estimated {estimated_pages} pages. You will be notified when the draft is ready for review.",
    )


@router.get("/reports/{report_id}")
async def get_report(report_id: str):
    """Retrieve a generated report (daily or period summary)."""
    # TODO: Retrieve from storage
    return {
        "report_id": report_id,
        "status": ReportStatus.PROCESSING,
        "narrative": None,
        "pdf_url": None,
    }


@router.get("/projects/{project_id}/reports")
async def list_project_reports(
    project_id: str,
    report_type: str = "all",
):
    """List all reports for a project (daily + period summaries)."""
    # TODO: Query from Box
    return {
        "project_id": project_id,
        "reports": [],
        "total": 0,
        "filter": report_type,
    }
