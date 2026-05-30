---
inclusion: always
---

# SiteNarrator — Product Context (v3)

SiteNarrator automates construction daily narrative reports.
Field inputs (photos, PDFs, Excel, voice notes) from Superintendents
flow through a 4-agent pipeline to produce client-ready narrative
drafts. A Project Coordinator reviews and approves before delivery.
Box stores all reports and source evidence as an audit trail.
Clients can ask clarifying questions via an AI chat widget.

## The four agents
1. Ingest Agent — extracts structured observations from photos using Box AI Extract, extracts text from PDFs/Excel, transcribes voice notes, pulls weather data by GPS
2. Synthesis Agent — combines observations into a 10-section narrative draft with inline photo citations, uses AgentCore Memory for style
3. Quality + Compliance Agent — validates draft completeness, scores confidence, flags missing trade entries
4. Eval Agent — hallucination detection, citation verification, tone consistency, cost tracking, OpenTelemetry tracing

## Additional capabilities
- Period Summary Agent — aggregates daily reports across a date range into comprehensive multi-page summaries
- Client Q&A Chat — answers from report content, escalates to Project Ops when unsure
- Multi-project support — create and switch between construction sites

## Non-negotiable rules
- NO report is ever sent to a client without explicit PC approval
- Every narrative claim must be traceable to a source photo or document
- Box is the system of record — all versions retained indefinitely
- AgentCore Policy (Cedar) enforces the approval guardrail at the tool-call level
- Chat agent NEVER discloses internal processes or fabricates data
