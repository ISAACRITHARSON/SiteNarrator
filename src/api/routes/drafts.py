"""SiteNarrator — Draft review and approval routes.

Handles the PC review workflow: view drafts, approve, reject, edit.
AgentCore Policy enforces that no report is delivered without PC approval.
"""

from __future__ import annotations

import base64
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from src.models.schemas import ApprovalRequest, RejectionRequest, ReportStatus

router = APIRouter()


@router.get("/drafts/{draft_id}")
async def get_draft(draft_id: str):
    """Retrieve a draft narrative with quality report for PC review."""
    from src.api.store import draft_store

    record = draft_store.get_by_draft_id(draft_id)
    if not record:
        raise HTTPException(status_code=404, detail="Draft not found")

    if record.pipeline_result is None:
        return {
            "draft_id": draft_id,
            "status": record.status,
            "narrative": "",
            "quality_report": None,
            "eval_report": None,
            "photo_citations": [],
            "trace_id": "",
            "created_at": record.created_at.isoformat(),
            "updated_at": record.updated_at.isoformat(),
        }

    pr = record.pipeline_result
    return {
        "draft_id": draft_id,
        "status": record.status,
        "narrative": pr.narrative,
        "quality_report": pr.quality_report.model_dump() if pr.quality_report else None,
        "eval_report": pr.eval_report.model_dump() if pr.eval_report else None,
        "photo_citations": [],
        "trace_id": pr.trace_id,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
    }


@router.post("/drafts/{draft_id}/approve")
async def approve_draft(draft_id: str, request: ApprovalRequest):
    """Approve a draft — generates PDF and updates status."""
    from src.api.store import draft_store
    from src.tools.pdf_tools import generate_pdf

    record = draft_store.get_by_draft_id(draft_id)
    if not record:
        raise HTTPException(status_code=404, detail="Draft not found")
    if not record.pipeline_result or not record.pipeline_result.narrative:
        raise HTTPException(status_code=400, detail="No narrative to approve")

    # Generate PDF
    pdf_bytes = generate_pdf(
        narrative=record.pipeline_result.narrative,
        project_id=record.project_id,
        report_date=record.report_date,
        superintendent=record.superintendent,
        project_name=record.project_id,
        gc_company="General Contractor",
        report_number=1,
        approved_by=request.approved_by,
        approved_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
    )

    # Update status in store
    record.status = ReportStatus.APPROVED
    record.updated_at = datetime.utcnow()

    # Store PDF bytes for download
    record.pdf_bytes = pdf_bytes  # type: ignore

    return {
        "draft_id": draft_id,
        "status": ReportStatus.APPROVED,
        "approved_by": request.approved_by,
        "approved_at": datetime.utcnow().isoformat(),
        "pdf_size_bytes": len(pdf_bytes),
        "pdf_download_url": f"/api/v1/drafts/{draft_id}/pdf",
        "client_report_url": f"/report/{draft_id}",
        "message": "Report approved. PDF generated.",
    }


@router.get("/drafts/{draft_id}/pdf")
async def download_pdf(draft_id: str):
    """Download the approved PDF report."""
    from src.api.store import draft_store

    record = draft_store.get_by_draft_id(draft_id)
    if not record:
        raise HTTPException(status_code=404, detail="Draft not found")

    pdf_bytes = getattr(record, "pdf_bytes", None)
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="PDF not yet generated. Approve the draft first.")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=report_{record.project_id}_{record.report_date}.pdf"},
    )


@router.post("/drafts/{draft_id}/reject")
async def reject_draft(draft_id: str, request: RejectionRequest):
    """Reject sections — re-runs synthesis with comments and updates the draft."""
    from src.agents.pipeline import run_revision
    from src.api.store import draft_store

    record = draft_store.get_by_draft_id(draft_id)
    if not record:
        raise HTTPException(status_code=404, detail="Draft not found")
    if not record.pipeline_result or not record.pipeline_result.observation_bundle:
        raise HTTPException(status_code=400, detail="No pipeline data to revise")

    if not request.section_comments:
        raise HTTPException(status_code=400, detail="At least one section comment required.")

    # Re-run the pipeline with revision comments
    revised_result = await run_revision(
        narrative=record.pipeline_result.narrative,
        bundle=record.pipeline_result.observation_bundle,
        section_comments=request.section_comments,
        version=2,
    )

    # Update the store with revised result
    record.pipeline_result.narrative = revised_result.narrative
    record.pipeline_result.quality_report = revised_result.quality_report
    record.pipeline_result.eval_report = revised_result.eval_report
    record.status = ReportStatus.DRAFT_READY
    record.updated_at = datetime.utcnow()

    return {
        "draft_id": draft_id,
        "status": ReportStatus.DRAFT_READY,
        "rejected_by": request.rejected_by,
        "sections_flagged": list(request.section_comments.keys()),
        "narrative_length": len(revised_result.narrative),
        "message": "Revision complete. Updated draft ready for review.",
    }
