"""SiteNarrator — Box integration layer.

Handles all interactions with Box using direct REST API calls.
Stores photos, documents, drafts, approved PDFs, and chat transcripts.
Box is the system of record for all project artifacts.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests

from src.config import get_settings
from src.tools.tracing import traced

_token_cache: dict[str, str] = {}


def _get_access_token() -> str:
    """Get Box access token via CCG (Client Credentials Grant)."""
    if "token" in _token_cache:
        return _token_cache["token"]

    settings = get_settings()
    resp = requests.post("https://api.box.com/oauth2/token", data={
        "grant_type": "client_credentials",
        "client_id": settings.box_client_id,
        "client_secret": settings.box_client_secret,
        "box_subject_type": "enterprise",
        "box_subject_id": settings.box_enterprise_id,
    })
    resp.raise_for_status()
    token = resp.json()["access_token"]
    _token_cache["token"] = token
    return token


def _headers() -> dict:
    return {"Authorization": f"Bearer {_get_access_token()}"}


@traced("box.get_or_create_folder")
def get_or_create_folder(project_id: str, date: str, subfolder: str) -> str:
    """Get or create folder at /{project_id}/{date}/{subfolder}/. Returns folder ID."""
    settings = get_settings()
    parent_id = settings.box_root_folder_id

    for folder_name in [project_id, date, subfolder]:
        # Try to create subfolder
        resp = requests.post(
            "https://api.box.com/2.0/folders",
            headers={**_headers(), "Content-Type": "application/json"},
            json={"name": folder_name, "parent": {"id": parent_id}},
        )
        if resp.status_code == 201:
            parent_id = resp.json()["id"]
        elif resp.status_code == 409:
            # Already exists
            parent_id = resp.json().get("context_info", {}).get("conflicts", [{}])[0].get("id", parent_id)
        else:
            resp.raise_for_status()

    return parent_id


@traced("box.upload_file")
def upload_file(file_path: str, folder_id: str, filename: str = "") -> str:
    """Upload a file to a Box folder. Returns file ID."""
    if not filename:
        filename = Path(file_path).name

    attributes = json.dumps({"name": filename, "parent": {"id": folder_id}})
    with open(file_path, "rb") as f:
        resp = requests.post(
            "https://upload.box.com/api/2.0/files/content",
            headers=_headers(),
            files={"attributes": (None, attributes), "file": (filename, f)},
        )

    if resp.status_code == 201:
        return resp.json()["entries"][0]["id"]
    elif resp.status_code == 409:
        # File exists — return existing ID
        return resp.json().get("context_info", {}).get("conflicts", {}).get("id", "")
    else:
        resp.raise_for_status()
        return ""


@traced("box.upload_photo")
def upload_photo(file_path: str, project_id: str, date: str, trade: str) -> str:
    """Upload a photo to the project's sources folder. Returns Box file ID."""
    folder_id = get_or_create_folder(project_id, date, "sources")
    filename = f"{trade}_{Path(file_path).name}"
    return upload_file(file_path, folder_id, filename)


@traced("box.upload_document")
def upload_document(file_path: str, project_id: str, date: str, filename: str) -> str:
    """Upload a document (PDF/Excel) to the project's sources folder. Returns Box file ID."""
    folder_id = get_or_create_folder(project_id, date, "sources")
    return upload_file(file_path, folder_id, filename)


@traced("box.extract_observations")
def extract_observations(box_file_id: str) -> dict[str, Any]:
    """Call Box AI Extract on a photo to extract construction observations."""
    headers = {**_headers(), "Content-Type": "application/json"}

    payload = {
        "items": [{"id": box_file_id, "type": "file"}],
        "fields": [
            {"key": "work_type", "type": "string", "prompt": "What type of construction work is visible?"},
            {"key": "progress_state", "type": "string", "prompt": "Describe the progress state."},
            {"key": "safety_conditions", "type": "string", "prompt": "Note any safety observations."},
            {"key": "materials_present", "type": "string", "prompt": "List materials visible."},
        ],
    }

    resp = requests.post("https://api.box.com/2.0/ai/extract_structured", headers=headers, json=payload, timeout=30)

    if resp.status_code == 200:
        result = resp.json()
        return {
            "work_type": result.get("work_type", ""),
            "progress_state": result.get("progress_state", ""),
            "safety_conditions": result.get("safety_conditions", ""),
            "materials_present": result.get("materials_present", ""),
            "confidence": 0.85,
        }
    else:
        return {"work_type": "", "progress_state": "", "safety_conditions": "", "materials_present": "", "confidence": 0.5}


@traced("box.save_draft")
def save_draft(content: str, project_id: str, date: str, version: int) -> str:
    """Save draft narrative to Box. Returns file ID."""
    folder_id = get_or_create_folder(project_id, date, "drafts")
    filename = f"draft_v{version}.md"

    attributes = json.dumps({"name": filename, "parent": {"id": folder_id}})
    resp = requests.post(
        "https://upload.box.com/api/2.0/files/content",
        headers=_headers(),
        files={"attributes": (None, attributes), "file": (filename, content.encode("utf-8"), "text/markdown")},
    )

    if resp.status_code == 201:
        return resp.json()["entries"][0]["id"]
    elif resp.status_code == 409:
        return resp.json().get("context_info", {}).get("conflicts", {}).get("id", "")
    return ""


@traced("box.save_approved")
def save_approved(narrative_json: str, pdf_bytes: bytes, project_id: str, date: str) -> dict[str, str]:
    """Save approved narrative + PDF to Box. Returns {json_id, pdf_id}."""
    folder_id = get_or_create_folder(project_id, date, "approved")

    # Save JSON
    attributes = json.dumps({"name": "narrative_approved.json", "parent": {"id": folder_id}})
    resp1 = requests.post(
        "https://upload.box.com/api/2.0/files/content",
        headers=_headers(),
        files={"attributes": (None, attributes), "file": ("narrative_approved.json", narrative_json.encode(), "application/json")},
    )
    json_id = resp1.json()["entries"][0]["id"] if resp1.status_code == 201 else ""

    # Save PDF
    attributes = json.dumps({"name": f"report_{project_id}_{date}.pdf", "parent": {"id": folder_id}})
    resp2 = requests.post(
        "https://upload.box.com/api/2.0/files/content",
        headers=_headers(),
        files={"attributes": (None, attributes), "file": (f"report_{project_id}_{date}.pdf", pdf_bytes, "application/pdf")},
    )
    pdf_id = resp2.json()["entries"][0]["id"] if resp2.status_code == 201 else ""

    return {"json_file_id": json_id, "pdf_file_id": pdf_id}


@traced("box.save_quality_report")
def save_quality_report(report_data: dict, project_id: str, date: str) -> str:
    """Save quality report JSON to Box."""
    folder_id = get_or_create_folder(project_id, date, "drafts")
    content = json.dumps(report_data, indent=2, default=str)

    attributes = json.dumps({"name": "quality-report.json", "parent": {"id": folder_id}})
    resp = requests.post(
        "https://upload.box.com/api/2.0/files/content",
        headers=_headers(),
        files={"attributes": (None, attributes), "file": ("quality-report.json", content.encode(), "application/json")},
    )
    return resp.json()["entries"][0]["id"] if resp.status_code == 201 else ""


@traced("box.save_chat_session")
def save_chat_session(session_data: dict, project_id: str, date: str, session_id: str) -> str:
    """Save chat session to Box."""
    folder_id = get_or_create_folder(project_id, date, "client-qa")
    content = json.dumps(session_data, indent=2, default=str)

    attributes = json.dumps({"name": f"session-{session_id}.json", "parent": {"id": folder_id}})
    resp = requests.post(
        "https://upload.box.com/api/2.0/files/content",
        headers=_headers(),
        files={"attributes": (None, attributes), "file": (f"session-{session_id}.json", content.encode(), "application/json")},
    )
    return resp.json()["entries"][0]["id"] if resp.status_code == 201 else ""
