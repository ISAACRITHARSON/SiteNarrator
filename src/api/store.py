"""SiteNarrator — In-memory store for pipeline results.

Bridges the gap between submission (triggers pipeline) and
draft retrieval (PC reads the result). In production this would
be backed by a database; for now we use a simple dict.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from src.agents.pipeline import PipelineResult
from src.models.schemas import ReportStatus


@dataclass
class DraftRecord:
    """A stored draft with its pipeline result."""
    draft_id: str
    submission_id: str
    project_id: str
    report_date: str
    superintendent: str
    status: ReportStatus
    pipeline_result: Optional[PipelineResult] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class DraftStore:
    """In-memory store for draft records.

    Keyed by both draft_id and submission_id for lookup flexibility.
    """

    def __init__(self):
        self._by_draft_id: dict[str, DraftRecord] = {}
        self._by_submission_id: dict[str, DraftRecord] = {}
        self._by_project: dict[str, list[str]] = {}  # project_id -> [draft_ids]

    def create(
        self,
        draft_id: str,
        submission_id: str,
        project_id: str,
        report_date: str,
        superintendent: str,
    ) -> DraftRecord:
        """Create a new draft record in PROCESSING state."""
        record = DraftRecord(
            draft_id=draft_id,
            submission_id=submission_id,
            project_id=project_id,
            report_date=report_date,
            superintendent=superintendent,
            status=ReportStatus.PROCESSING,
        )
        self._by_draft_id[draft_id] = record
        self._by_submission_id[submission_id] = record
        if project_id not in self._by_project:
            self._by_project[project_id] = []
        self._by_project[project_id].append(draft_id)
        return record

    def update_with_result(self, draft_id: str, result: PipelineResult) -> None:
        """Update a draft record with the completed pipeline result."""
        if draft_id in self._by_draft_id:
            record = self._by_draft_id[draft_id]
            record.pipeline_result = result
            record.status = result.status
            record.updated_at = datetime.utcnow()

    def get_by_draft_id(self, draft_id: str) -> Optional[DraftRecord]:
        return self._by_draft_id.get(draft_id)

    def get_by_submission_id(self, submission_id: str) -> Optional[DraftRecord]:
        return self._by_submission_id.get(submission_id)

    def list_by_project(self, project_id: str) -> list[DraftRecord]:
        draft_ids = self._by_project.get(project_id, [])
        return [self._by_draft_id[did] for did in draft_ids if did in self._by_draft_id]


# Singleton instance
draft_store = DraftStore()
