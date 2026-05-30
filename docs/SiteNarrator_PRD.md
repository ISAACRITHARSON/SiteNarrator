# SiteNarrator — Product Requirements Document

**Version:** 3.0
**Date:** May 30, 2026
**Status:** Final — Synced with Implementation

---

## 1. Executive Summary

SiteNarrator is an AI-powered, multi-agent system that automates end-to-end construction daily narrative report generation. Field inputs — photos, PDFs, Excel files, voice notes, and text observations — flow into a four-agent pipeline that ingests, synthesizes, quality-checks, and evaluates a draft narrative. A Project Coordinator reviews and approves before delivery. Post-delivery, clients interact with an AI-powered chat widget for clarifying questions, with automatic escalation to the Project Operations team when needed.

The system stores all artifacts in Box (photos, documents, drafts, approved PDFs, chat transcripts) with full version history. It provides distributed tracing and AI evaluation metrics across every interaction.

---

## 2. Technology Stack (Implemented)

| Component | Technology |
|---|---|
| Agent Development | Kiro (spec-driven development) |
| Language | Python 3.11 |
| Agent Framework | Strands Agents SDK |
| Agent Infra | Amazon Bedrock AgentCore (Runtime, Memory, Gateway, Policy, Observability) |
| Model | Claude Sonnet via AWS Bedrock (configurable — supports Opus, GPT-4o, Gemini, Llama) |
| Content Store | Box (AI Extract API + direct REST API) |
| Weather | OpenWeatherMap API |
| Voice | AWS Transcribe |
| API Layer | FastAPI (Python) |
| Frontend | React 18 + TypeScript + TailwindCSS + Vite |
| PDF Output | WeasyPrint |
| Tracing | OpenTelemetry → CloudWatch |
| Policy | Cedar (via AgentCore Policy) |

---

## 3. System Architecture

### Four-Agent Pipeline

```
[User Upload: Photos + PDFs + Excel + Voice Notes]
        |
        v
[Box Storage: /project/date/sources/]
        |
        v
[Ingest Agent] → Box AI Extract + Weather API + Transcribe
        |
        v
[Synthesis Agent] → 10-section narrative + AgentCore Memory
        |
        v
[Quality Agent] → Validation + Confidence scoring
        |
        v
[Eval Agent] → Hallucination check + Citation verify + Tracing
        |
        v
[PC Review] → Approve / Reject / Edit (Cedar Policy guardrail)
        |
        v
[PDF Generation + Box Storage: /approved/]
        |
        v
[Client Report View + AI Chat Widget + Escalation]
```

### Box Folder Structure (Implemented)

```
/SiteNarrator/
  /{project_id}/
    /{YYYY-MM-DD}/
      /sources/       ← photos, PDFs, Excel files
      /drafts/        ← draft versions, quality report
      /approved/      ← final PDF, approval record
      /client-qa/     ← chat transcripts
```

---

## 4. Features (Implemented)

### 4.1 Conversational Agent Interface (Capture Page)
- Agent greets user by name and project
- Drag-and-drop upload: JPG/PNG photos, PDF, Excel files
- Agent acknowledges uploads, separates photos from documents
- Agent asks for additional context (crew counts, delays)
- User can type notes or skip
- Pipeline runs synchronously, returns draft

### 4.2 Multi-Format Input
- Photos: JPG/PNG (up to 20 per submission)
- Documents: PDF, Excel (.xlsx/.xls), CSV
- Voice notes: .m4a, .wav, .mp3, .webm
- Text notes: free-form field input
- All files uploaded to Box on submission

### 4.3 Four-Agent Pipeline
- **Ingest Agent**: Box AI Extract on photos, weather API, voice transcription, structured data extraction from documents
- **Synthesis Agent**: 10-section narrative with [Photo N] citations, AgentCore Memory for style
- **Quality Agent**: Schema validation, citation check, confidence scoring
- **Eval Agent**: Hallucination detection, citation accuracy, tone consistency, cost tracking

### 4.4 Report Structure (10 Sections)
1. Project Header
2. Weather & Site Conditions
3. Manpower Summary (table)
4. Work Completed by Trade (narrative + photo citations)
5. Equipment on Site (table)
6. Material Deliveries (table)
7. Safety Observations
8. Inspections & Visitors
9. Delays & Issues
10. Work Planned for Next Day

### 4.5 PC Review Interface
- Quality confidence badge
- Full narrative display with section headings
- Approve → generates PDF, stores in Box
- Reject → sends back with comments, agent re-drafts
- PDF download link after approval

### 4.6 Client Report View + Chat Widget
- Read-only formatted report
- Floating chat widget (bottom-right, construction worker icon)
- Suggested questions generated dynamically from report content
- Agent answers from report content only
- Escalation to Project Ops when confidence < 0.6
- Rate limited (50 messages per session)

### 4.7 Period Summary Reports
- PC selects date range (From/To calendar)
- System aggregates all daily reports in range
- Generates comprehensive multi-page summary (5-25+ pages)
- Includes: manpower trends, delay analysis, equipment utilization, progress tracking

### 4.8 Evaluation & Traceability
- Model selector dropdown (Claude Sonnet, Opus, GPT-4o, Gemini, Llama)
- Metrics: Overall Score, Hallucination %, Citation Accuracy
- Quality Breakdown: Factual Grounding, Citation Accuracy, Relevancy, Tone Consistency
- Token usage and cost per report
- Collapsible agent traceability (6 phases, expandable sub-steps)
- Full pipeline trace with durations

### 4.9 Project Management
- Multi-project support (create new, switch between previous)
- Project stored in sidebar with active indicator
- History tab with all generated reports

### 4.10 Box Integration (Live)
- CCG authentication (Client Credentials Grant)
- Auto-creates folder structure per project/date
- Uploads all source files on submission
- Stores drafts, quality reports, approved PDFs
- Enterprise ID: configured
- Root folder: /SiteNarrator/

---

## 5. Frontend Pages (Implemented)

| Page | Route | Purpose |
|---|---|---|
| Capture | / | Conversational agent — upload files, generate report |
| Review | /review | PC reviews draft, approve/reject |
| Reports | /dashboard | Recent reports, period summary generator, stats |
| History | /history | All reports with status, quality scores |
| Evaluation | /evaluation | AI metrics, model selector, traceability |
| Client Report | /report/:id | Client reads report + chat widget |
| New Project | /new-project | Create or switch projects |

### Design System
- Dark desktop theme (navy: #1a1a2e, surface: #16213e, cards: #1f2b47)
- Amber/gold primary accent (#e8a830)
- Inter font family
- Sidebar navigation (fixed, 240px)
- Rounded corners (1rem)
- Construction hero image on capture page

---

## 6. API Endpoints (Implemented)

| Method | Path | Description |
|---|---|---|
| POST | /api/v1/submissions | Upload photos + docs + metadata, runs pipeline |
| GET | /api/v1/drafts/{id} | Get draft narrative + quality + eval reports |
| POST | /api/v1/drafts/{id}/approve | Approve, generate PDF |
| POST | /api/v1/drafts/{id}/reject | Reject with comments, re-draft |
| GET | /api/v1/drafts/{id}/pdf | Download approved PDF |
| POST | /api/v1/reports/{id}/chat | Client Q&A message |
| GET | /api/v1/reports/{id}/chat/history | Chat history |
| POST | /api/v1/reports/generate | Period summary generation |
| GET | /api/v1/escalations | Ops escalation queue |
| GET | /health | Health check |

---

## 7. Guardrails & Compliance

- AgentCore Policy (Cedar): blocks delivery without PC approval
- Chat agent scoped to report content only — never discloses internals
- Escalation when confidence < 0.6
- All versions retained in Box indefinitely
- OpenTelemetry tracing on every agent invocation
- Eval Agent checks for hallucinations on every report

---

## 8. Deployment

| Environment | Setup |
|---|---|
| Local development | `make dev` (backend) + `npm run dev` (frontend) |
| GitHub | Source code repository |
| AWS (production) | App Runner (backend) + S3/CloudFront (frontend) |
| Box | Connected — Enterprise ID: 1489146840, Root Folder: 385713220051 |

---

*SiteNarrator PRD v3.0 — Confidential*
