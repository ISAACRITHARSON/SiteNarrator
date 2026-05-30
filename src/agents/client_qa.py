"""SiteNarrator — Client Q&A Chat Agent.

Post-delivery agent that answers client clarifying questions about
delivered reports. Scoped strictly to report content — never discloses
internal processes or information not in the delivered report.

When confidence is below threshold, transparently escalates to
the Project Operations team with full context.
"""

from __future__ import annotations

from typing import Any

from strands import Agent, tool

from src.config import get_settings
from src.models.schemas import ChatMessage
from src.tools.tracing import trace_span


# ─── Strands Tool Definitions ──────────────────────────────────


@tool
def search_report_content(query: str, report_content: str) -> str:
    """Search the delivered report for content relevant to the client's question.

    Args:
        query: The client's question or search terms.
        report_content: The full approved report narrative.

    Returns:
        Relevant sections and citations from the report.
    """
    # Simple keyword-based search within the report
    query_terms = query.lower().split()
    relevant_lines = []

    for line in report_content.split("\n"):
        line_lower = line.lower()
        if any(term in line_lower for term in query_terms):
            relevant_lines.append(line)

    if relevant_lines:
        return "\n".join(relevant_lines[:10])  # Top 10 relevant lines
    return "No directly relevant content found in the report for this query."


@tool
def escalate_to_ops(
    client_question: str,
    attempted_answer: str,
    reason: str,
    report_id: str,
) -> dict:
    """Escalate a conversation to the Project Operations team.

    Called when the agent cannot answer with sufficient confidence.
    Sends full context so Ops can respond quickly without re-reading the report.

    Args:
        client_question: The client's original question.
        attempted_answer: What the agent tried to answer (if anything).
        reason: Why escalation is needed.
        report_id: The report being discussed.

    Returns:
        Escalation confirmation with ID.
    """
    with trace_span("client_qa.escalation", {"report_id": report_id}):
        # TODO: Send webhook notification to Ops team
        # TODO: Store escalation record in Box

        return {
            "escalated": True,
            "reason": reason,
            "message": "Your question has been forwarded to our Project Operations team. They typically respond within 1 business hour.",
        }


# ─── System Prompt ─────────────────────────────────────────────

CLIENT_QA_SYSTEM_PROMPT = """You are the Client Q&A Assistant for SiteNarrator.

You help clients (Owner Representatives) understand their delivered construction daily reports.

## STRICT RULES:

1. **Only answer from report content.** You may ONLY reference information that appears in the delivered report, source photos, or weather data. Never speculate or add information not in the report.

2. **Cite your sources.** When answering, reference the specific section and/or photo. Example: "As noted in the Work Completed section, the concrete crew completed the Level 2 pour [Photo 3]."

3. **Never disclose internal processes.** Do not mention:
   - Agent architecture or AI systems
   - Draft versions or revision history
   - Quality scores or confidence metrics
   - Internal team communications
   - How the report was generated

4. **Escalate when unsure.** If you cannot answer confidently from the report content:
   - Tell the client: "I don't have enough information in this report to answer that question accurately."
   - Offer to escalate: "Would you like me to connect you with our Project Operations team? They can provide more detail."
   - If they say yes, call `escalate_to_ops` with full context.

5. **Be professional and helpful.** You represent the general contractor to their client. Be courteous, clear, and concise.

6. **Rate limit awareness.** If the conversation exceeds 50 messages, politely suggest the client contact the Project Operations team directly for extended discussions.

## What you CAN answer:
- What work was completed (from Work Completed section)
- Weather conditions (from Weather section)
- Who was on site (from Manpower Summary)
- Equipment used (from Equipment section)
- Inspection results (from Inspections section)
- Delays and their causes (from Delays section)
- Material deliveries (from Materials section)
- Safety observations (from Safety section)
- What's planned for tomorrow (from Work Planned section)

## What you CANNOT answer:
- Budget or cost information (not in daily reports)
- Schedule projections or completion dates
- Contract terms or change order status
- Information about other projects
- Anything not explicitly stated in this specific report
"""


# ─── Agent Runner ──────────────────────────────────────────────


def run_client_qa(
    client_message: str,
    report_content: str,
    report_id: str,
    conversation_history: list[dict] | None = None,
    message_count: int = 0,
) -> ChatMessage:
    """Process a client Q&A message and generate a response.

    Args:
        client_message: The client's question.
        report_content: The full approved report narrative.
        report_id: The report being discussed.
        conversation_history: Previous messages in this session.
        message_count: Number of messages in this session (for rate limiting).

    Returns:
        ChatMessage with the agent's response, citations, and confidence.
    """
    settings = get_settings()

    with trace_span("client_qa.respond", {
        "report_id": report_id,
        "message_count": message_count,
    }):
        # Rate limit check
        if message_count >= 50:
            return ChatMessage(
                role="assistant",
                content=(
                    "We've had a detailed conversation about this report. "
                    "For further questions, I'd recommend reaching out to the "
                    "Project Operations team directly. They can provide more "
                    "comprehensive assistance."
                ),
                citations=[],
                confidence=1.0,
                escalated=False,
            )

        agent = Agent(
            model=settings.bedrock_model_id,
            tools=[search_report_content, escalate_to_ops],
            system_prompt=CLIENT_QA_SYSTEM_PROMPT,
        )

        # Build prompt with context
        prompt = _build_qa_prompt(
            client_message, report_content, report_id, conversation_history
        )

        response = agent(prompt)
        response_text = str(response)

        # Determine if escalation occurred
        escalated = "escalat" in response_text.lower() and "project operations" in response_text.lower()

        # Extract citations from response
        import re
        citations = re.findall(r"\[Photo\s+\d+\]|\[(?:Section|see)\s+[^\]]+\]", response_text)

        # Estimate confidence based on response characteristics
        confidence = _estimate_confidence(response_text, report_content)

        return ChatMessage(
            role="assistant",
            content=response_text,
            citations=citations,
            confidence=confidence,
            escalated=escalated,
        )


def _build_qa_prompt(
    client_message: str,
    report_content: str,
    report_id: str,
    conversation_history: list[dict] | None = None,
) -> str:
    """Build the prompt for the Q&A agent."""
    parts = [
        f"## Report Content (Report ID: {report_id})",
        "---",
        report_content,
        "---",
        "",
    ]

    if conversation_history:
        parts.append("## Previous Messages in This Conversation")
        for msg in conversation_history[-10:]:  # Last 10 messages for context
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            parts.append(f"**{role}:** {content}")
        parts.append("")

    parts.append("## Client's Question")
    parts.append(client_message)
    parts.append("")
    parts.append("## Instructions")
    parts.append("Answer the client's question using ONLY the report content above.")
    parts.append("Cite specific sections and photos. If you cannot answer confidently, offer to escalate.")

    return "\n".join(parts)


def _estimate_confidence(response: str, report_content: str) -> float:
    """Estimate confidence of the response based on how well it's grounded in report content."""
    # Higher confidence if response contains citations
    import re
    citations = re.findall(r"\[Photo\s+\d+\]", response)
    citation_boost = min(len(citations) * 0.1, 0.3)

    # Higher confidence if key phrases from report appear in response
    report_words = set(report_content.lower().split())
    response_words = set(response.lower().split())
    overlap = len(report_words & response_words) / max(len(response_words), 1)

    # Lower confidence if hedging language present
    hedging = ["might", "possibly", "unclear", "not sure", "cannot determine", "don't have"]
    hedge_penalty = sum(0.1 for h in hedging if h in response.lower())

    confidence = 0.5 + citation_boost + (overlap * 0.3) - hedge_penalty
    return round(max(min(confidence, 1.0), 0.0), 2)
