"""SiteNarrator — Client Q&A chat routes.

The client sees a floating chat widget on their report page.
The agent answers ONLY from report content. When it can't answer
confidently, it transparently escalates to the Project Operations team.

This is the "Aha" moment: the client gets instant answers without
calling anyone. And when the AI can't help, a human steps in seamlessly.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.models.schemas import ReportStatus

router = APIRouter()

# In-memory chat sessions and escalations
_chat_sessions: dict[str, list[dict]] = {}
_escalations: list[dict] = []


class ChatRequest(BaseModel):
    message: str


def _answer_from_report(question: str, narrative: str) -> tuple[str, float, list[str], bool]:
    """Answer a client question using only the report content.

    Returns: (answer, confidence, citations, should_escalate)
    """
    question_lower = question.lower()
    narrative_lower = narrative.lower()

    # Handle greetings and general questions
    greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "thanks", "thank you"]
    if any(question_lower.strip() == g or question_lower.strip().startswith(g + " ") for g in greetings):
        return (
            "Hi! I'm here to help you understand this daily construction report. "
            "You can ask me about work completed, weather conditions, crew details, "
            "equipment used, material deliveries, safety observations, inspections, "
            "or delays. What would you like to know?",
            1.0, [], False
        )

    # Handle "what's in this report" / summary questions
    summary_triggers = ["summary", "summarize", "what's in", "overview", "tell me about", "what happened"]
    if any(t in question_lower for t in summary_triggers):
        # Return first few meaningful lines as a summary
        lines = [l.strip() for l in narrative.split("\n") if l.strip() and not l.startswith("|--") and not l.startswith("##")]
        summary_lines = lines[:8]
        answer = "Here's a quick overview of today's report:\n\n" + "\n".join(f"• {l}" for l in summary_lines)
        return answer, 0.9, [], False

    # Find relevant sections
    sections = {}
    current_section = ""
    current_lines: list[str] = []
    for line in narrative.split("\n"):
        if line.startswith("## "):
            if current_section:
                sections[current_section] = "\n".join(current_lines)
            current_section = line.replace("## ", "").strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_section:
        sections[current_section] = "\n".join(current_lines)

    # Match question to relevant section(s)
    keywords_to_sections = {
        "weather": ["Weather", "Site Conditions"],
        "rain": ["Weather", "Delays"],
        "delay": ["Delays", "Issues"],
        "concrete": ["Work Completed", "Manpower"],
        "electrical": ["Work Completed", "Manpower"],
        "plumbing": ["Work Completed", "Manpower"],
        "crew": ["Manpower", "Summary"],
        "worker": ["Manpower", "Summary"],
        "safety": ["Safety"],
        "inspection": ["Inspections", "Visitors"],
        "passed": ["Inspections"],
        "failed": ["Inspections"],
        "equipment": ["Equipment"],
        "crane": ["Equipment"],
        "material": ["Material", "Deliveries"],
        "delivery": ["Material", "Deliveries"],
        "tomorrow": ["Work Planned", "Next Day"],
        "next day": ["Work Planned", "Next Day"],
        "planned": ["Work Planned", "Next Day"],
    }

    matched_sections: list[str] = []
    for keyword, section_names in keywords_to_sections.items():
        if keyword in question_lower:
            for sname in section_names:
                for actual_section in sections:
                    if sname.lower() in actual_section.lower():
                        matched_sections.append(actual_section)

    # Extract citations from matched content
    citations: list[str] = []
    relevant_content = ""

    if matched_sections:
        for section_name in set(matched_sections):
            content = sections.get(section_name, "")
            if content.strip():
                relevant_content += f"\n{content}"
                found_citations = re.findall(r"\[Photo \d+\]", content)
                citations.extend(found_citations)

    # Build answer
    if relevant_content.strip():
        # Clean up the content for a conversational response
        lines = [l.strip() for l in relevant_content.split("\n") if l.strip() and not l.startswith("|---")]
        answer_lines = lines[:5]  # Top 5 relevant lines
        answer = "Based on today's report:\n\n" + "\n".join(f"• {l}" for l in answer_lines if l)

        if citations:
            answer += f"\n\n(See {', '.join(set(citations[:3]))} for visual reference)"

        confidence = 0.85
        return answer, confidence, list(set(citations[:3])), False

    # Check if the question is about something NOT in daily reports
    out_of_scope = ["budget", "cost", "price", "schedule", "deadline", "contract", "payment", "invoice"]
    if any(word in question_lower for word in out_of_scope):
        answer = (
            "That's a great question, but daily reports don't cover "
            "budget, schedule, or contract details. "
            "Would you like me to connect you with the Project Operations team? "
            "They can help with that."
        )
        return answer, 0.4, [], True

    # Broad search — look for any word from the question in the narrative
    question_words = [w for w in question_lower.split() if len(w) > 3]
    broad_matches = []
    for line in narrative.split("\n"):
        line_lower = line.lower()
        if any(w in line_lower for w in question_words) and line.strip() and not line.startswith("|--"):
            broad_matches.append(line.strip())

    if broad_matches:
        answer = "Based on the report:\n\n" + "\n".join(f"• {l}" for l in broad_matches[:5])
        citations = re.findall(r"\[Photo \d+\]", " ".join(broad_matches))
        return answer, 0.75, list(set(citations[:3])), False

    # Can't find relevant content — offer escalation
    answer = (
        "I couldn't find specific information about that in today's report. "
        "You can ask me about weather, crew/manpower, work completed, equipment, "
        "materials, safety, inspections, or delays. "
        "Or I can connect you with the Project Operations team if you need more detail."
    )
    return answer, 0.5, [], False


@router.post("/reports/{report_id}/chat")
async def send_chat_message(report_id: str, request: ChatRequest):
    """Client sends a message — agent answers from report content or escalates."""
    from src.api.store import draft_store

    # Get the report narrative + document context
    record = draft_store.get_by_draft_id(report_id)
    narrative = ""
    document_context = ""
    if record and record.pipeline_result:
        narrative = record.pipeline_result.narrative
        document_context = getattr(record.pipeline_result, "document_context", "")

    if not narrative:
        return {
            "report_id": report_id,
            "response": {
                "role": "assistant",
                "content": "I'm having trouble loading this report. Please try refreshing the page.",
                "citations": [],
                "confidence": 0.0,
                "escalated": False,
            },
        }

    # Initialize session
    if report_id not in _chat_sessions:
        _chat_sessions[report_id] = []

    # Check rate limit (50 messages per session)
    if len(_chat_sessions[report_id]) >= 100:  # 50 pairs
        return {
            "report_id": report_id,
            "response": {
                "role": "assistant",
                "content": "We've had a detailed conversation. For further questions, please contact the Project Operations team directly.",
                "citations": [],
                "confidence": 1.0,
                "escalated": True,
            },
        }

    # Store user message
    _chat_sessions[report_id].append({"role": "client", "content": request.message, "timestamp": datetime.utcnow().isoformat()})

    # Check if user is confirming escalation
    confirm_words = ["yes", "yeah", "please", "sure", "connect me", "escalate"]
    if any(w in request.message.lower() for w in confirm_words) and len(_chat_sessions[report_id]) > 2:
        # Check if previous message offered escalation
        prev_messages = _chat_sessions[report_id]
        if len(prev_messages) >= 2 and "project operations" in str(prev_messages[-2].get("content", "")).lower():
            # Perform escalation
            escalation_id = str(uuid.uuid4())[:8]
            _escalations.append({
                "escalation_id": escalation_id,
                "report_id": report_id,
                "client_question": request.message,
                "conversation_history": _chat_sessions[report_id][-6:],
                "status": "open",
                "created_at": datetime.utcnow().isoformat(),
            })

            response_content = (
                "Done — I've connected you with the Project Operations team. "
                f"They have the full context of our conversation (ref: #{escalation_id}). "
                "You'll hear back within 1 business hour. Is there anything else about the report I can help with?"
            )
            _chat_sessions[report_id].append({"role": "assistant", "content": response_content, "escalated": True})

            return {
                "report_id": report_id,
                "response": {
                    "role": "assistant",
                    "content": response_content,
                    "citations": [],
                    "confidence": 1.0,
                    "escalated": True,
                },
            }

    # Answer from report content + document context
    full_context = narrative
    if document_context:
        full_context += "\n\n" + document_context
    answer, confidence, citations, should_escalate = _answer_from_report(request.message, full_context)

    # Store assistant response
    _chat_sessions[report_id].append({"role": "assistant", "content": answer, "confidence": confidence})

    return {
        "report_id": report_id,
        "response": {
            "role": "assistant",
            "content": answer,
            "citations": citations,
            "confidence": confidence,
            "escalated": False,
        },
    }


@router.get("/reports/{report_id}/chat/history")
async def get_chat_history(report_id: str):
    """Retrieve chat history for a report."""
    messages = _chat_sessions.get(report_id, [])
    return {
        "report_id": report_id,
        "messages": messages,
        "total": len(messages),
    }


@router.get("/escalations")
async def list_escalations(status: str = "open"):
    """List escalated conversations for the Ops team."""
    filtered = [e for e in _escalations if e["status"] == status] if status != "all" else _escalations
    return {
        "escalations": filtered,
        "total": len(filtered),
        "status_filter": status,
    }
