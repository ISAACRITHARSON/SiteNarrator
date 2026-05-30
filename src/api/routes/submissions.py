"""SiteNarrator — Submission routes.

Handles photo + voice note uploads from Superintendents.
Triggers the full agent pipeline: Ingest -> Synthesis -> Quality -> Eval.
"""

from __future__ import annotations

import os
import tempfile
import uuid
from datetime import datetime

from fastapi import APIRouter, File, Form, UploadFile

from src.agents.pipeline import run_pipeline
from src.api.store import draft_store
from src.models.schemas import ReportStatus

router = APIRouter()


@router.post("/submissions")
async def create_submission(
    project_id: str = Form(...),
    report_date: str = Form(...),
    superintendent_name: str = Form(...),
    lat: float = Form(...),
    lon: float = Form(...),
    trade_tags: str = Form(..., description="Comma-separated trade tags"),
    zones: str = Form(default="", description="Comma-separated zones"),
    text_notes: str = Form(default=""),
    photos: list[UploadFile] = File(default=[]),
    documents: list[UploadFile] = File(default=[]),
    voice_note: UploadFile | None = File(default=None),
):
    """Submit photos, documents (PDF/Excel), and voice notes for daily report generation.

    Accepts:
    - photos: JPEG/PNG site photos
    - documents: PDF and Excel files (specs, schedules, RFIs, submittals)
    - voice_note: audio file (.m4a, .wav, .mp3)
    """
    submission_id = str(uuid.uuid4())
    draft_id = str(uuid.uuid4())

    # Save uploaded photos to temp files
    tags = [t.strip() for t in trade_tags.split(",")]
    zone_list = [z.strip() for z in zones.split(",") if z.strip()]
    photo_paths: list[dict] = []

    for i, photo in enumerate(photos):
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        content = await photo.read()
        tmp.write(content)
        tmp.close()
        photo_paths.append({
            "file_path": tmp.name,
            "trade": tags[i % len(tags)] if tags else "general",
            "zone": zone_list[i % len(zone_list)] if zone_list else "",
        })

    # Save uploaded documents (PDF/Excel) to temp files
    document_paths: list[dict] = []
    for doc in documents:
        ext = os.path.splitext(doc.filename or "")[1].lower() or ".pdf"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        content = await doc.read()
        tmp.write(content)
        tmp.close()
        document_paths.append({
            "file_path": tmp.name,
            "filename": doc.filename or f"document{ext}",
            "content_type": doc.content_type or "application/octet-stream",
        })

    # Transcribe voice note if provided
    voice_transcript = ""
    if voice_note:
        voice_content = await voice_note.read()
        try:
            voice_transcript = voice_content.decode("utf-8")
        except UnicodeDecodeError:
            voice_transcript = ""

    # Create draft record in store
    draft_store.create(
        draft_id=draft_id,
        submission_id=submission_id,
        project_id=project_id,
        report_date=report_date,
        superintendent=superintendent_name,
    )

    # Run pipeline synchronously
    result = await run_pipeline(
        photos=photo_paths,
        documents=document_paths,
        voice_transcript=voice_transcript,
        text_notes=text_notes,
        project_id=project_id,
        report_date=report_date,
        superintendent=superintendent_name,
        lat=lat,
        lon=lon,
    )
    result.draft_id = draft_id
    draft_store.update_with_result(draft_id, result)

    return {
        "submission_id": submission_id,
        "draft_id": draft_id,
        "project_id": project_id,
        "report_date": report_date,
        "status": result.status,
        "photo_count": len(photos),
        "document_count": len(documents),
        "has_voice_note": voice_note is not None,
        "narrative_length": len(result.narrative),
        "quality_passed": result.quality_report.passed if result.quality_report else None,
        "trace_id": result.trace_id,
        "created_at": datetime.utcnow().isoformat(),
        "message": "Pipeline complete. Draft ready for review at GET /api/v1/drafts/{draft_id}",
    }


@router.get("/submissions/{submission_id}/status")
async def get_submission_status(submission_id: str):
    """Check the processing status of a submission."""
    record = draft_store.get_by_submission_id(submission_id)
    if not record:
        return {
            "submission_id": submission_id,
            "status": ReportStatus.PROCESSING,
            "draft_id": None,
            "updated_at": datetime.utcnow().isoformat(),
        }
    return {
        "submission_id": submission_id,
        "status": record.status,
        "draft_id": record.draft_id,
        "updated_at": record.updated_at.isoformat(),
    }


@router.get("/projects/{project_id}/submissions")
async def list_project_submissions(project_id: str):
    """List all submissions for a project."""
    records = draft_store.list_by_project(project_id)
    return {
        "project_id": project_id,
        "submissions": [
            {
                "draft_id": r.draft_id,
                "submission_id": r.submission_id,
                "report_date": r.report_date,
                "status": r.status,
                "created_at": r.created_at.isoformat(),
            }
            for r in records
        ],
        "total": len(records),
    }
