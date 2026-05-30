# SiteNarrator — Design

## System Overview

Four-layer architecture:
1. **Field Input Layer** — Mobile-optimized React UI for Superintendent/Foreman submissions
2. **Agent Processing Pipeline** — Strands orchestrates four sequential agents (Ingest -> Synthesis -> Quality -> Eval)
3. **Human Review Layer** — Professional PC review interface with real-time WebSocket notifications
4. **Client Delivery Layer** — Report view + AI-powered Q&A chat widget with escalation to Project Ops

## Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Language | Python 3.11 | Team expertise, ML ecosystem |
| Agent Framework | Strands Agents SDK | Native AWS, multi-agent orchestration |
| Agent Infra | Amazon Bedrock AgentCore | Runtime, Memory, Gateway, Policy, Observability |
| Model | Claude Sonnet via AWS Bedrock | Best multimodal reasoning |
| Content Store | Box (AI Extract + MCP Server) | Enterprise content mgmt, OCR, audit trail |
| Weather | OpenWeatherMap API | GPS-keyed, construction-grade accuracy |
| Voice | AWS Transcribe | Native AWS, multi-format support |
| API Layer | FastAPI | Async, WebSocket, OpenAPI docs |
| Frontend | React 18 + TypeScript + TailwindCSS | Professional UI, responsive |
| State Mgmt | Zustand | Lightweight, no boilerplate |
| Real-time | WebSocket (native) | Industry standard for time-sensitive workflows |
| Charts | Recharts | Observability dashboard |
| PDF Output | WeasyPrint | CSS-based PDF, professional formatting |
| Notifications | WebSocket + SES email | Real-time + offline fallback |
| Tracing | OpenTelemetry -> CloudWatch | Native AgentCore integration |
| Policy | Cedar (AgentCore Policy) | Deterministic authorization |
| Demo Data | HuggingFace ConstructionSite dataset | 10K+ real construction photos, open access |

## API Endpoints

### Submission API
| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/submissions | Upload photos + voice notes + metadata |
| GET | /api/v1/submissions/{id}/status | Poll processing status |
| GET | /api/v1/projects/{id}/submissions | List submissions for a project |

### Review API
| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/drafts/{id} | Retrieve draft + QualityReport + EvalReport |
| POST | /api/v1/drafts/{id}/approve | Approve (triggers PDF + Box upload) |
| POST | /api/v1/drafts/{id}/reject | Reject with section comments |
| PATCH | /api/v1/drafts/{id} | Direct edit by PC |
| WS | /ws/notifications | Real-time PC notifications |

### Client Q&A API
| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/reports/{id}/chat | Send message in client Q&A |
| GET | /api/v1/reports/{id}/chat/history | Chat history for a report |
| WS | /ws/client-chat/{report_id} | Real-time chat WebSocket |

### Observability API
| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/traces/{trace_id} | Full trace for a report |
| GET | /api/v1/metrics/dashboard | Aggregated metrics |
| GET | /api/v1/evals/{report_id} | Eval results for a report |

### Admin API
| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/projects | Create/configure a project |
| PUT | /api/v1/projects/{id}/config | Update project config |
| GET | /api/v1/projects/{id}/memory | View episodic memory entries |

## Agent Pipeline — Strands Orchestration

```
[Superintendent Mobile Upload]
        |
        v
+---------------------+
|  Ingest + Vision    | <- Box AI Extract, AWS Transcribe, OpenWeatherMap
|  Agent              |    Parallel photo extraction for speed
+--------+------------+
         | ObservationBundle JSON
         v
+---------------------+
|  Synthesis Agent    | <- AgentCore Episodic Memory (style/tone)
|                     |    6-section narrative with [Photo N] citations
+--------+------------+
         | Draft narrative
         v
+---------------------+
|  Quality +          | <- Report schema validation
|  Compliance Agent   |    Confidence scoring
+--------+------------+
         | Scored draft + annotations
         v
+---------------------+
|  Eval +             | <- Hallucination check, citation verify
|  Observability Agent|    Trace emit, cost tracking
+--------+------------+
         | Evaluated draft + trace_id
         v
+---------------------+
|  PC Review UI       | <- WebSocket notification
|  (Human-in-Loop)    |    Side-by-side: narrative + photos
+--------+------------+
         | Approved report
         v
+---------------------+
|  PDF Generation     | <- WeasyPrint
|  + Box Storage      |    Version history maintained
+--------+------------+
         | Delivered report + client link
         v
+---------------------+
|  Client Q&A Chat    | <- Report-scoped, floating widget
|  Agent              |    Escalation to Project Ops
+---------------------+
```

## Client Q&A Chat Architecture

```
[Client opens report link -> sees floating chat widget (bottom-right)]
        |
        v
+---------------------+
|  Q&A Chat Agent     | <- Scoped to: approved report + source photos + weather
|  (Strands Agent)    |    Uses AgentCore Memory for session context
+--------+------------+
         |
    +----+----+
    |         |
 Answerable  Not Answerable (confidence < 0.6)
    |         |
    v         v
[Respond    [Inform client transparently ->
 with        Escalate to Project Ops via webhook
 citations]  with full context: question + attempted answer + report ref]
        |
        v
[Project Ops sees in Escalation Queue UI with full context]
```

## AgentCore Configuration

### AgentCore Memory (Episodic Strategy)
- **Strategy**: Episodic with reflections
- **Namespace**: `/strategy/{strategyId}/actor/{projectId}/`
- **What it stores per project**:
  - client_name, preferred_tone, trade_name_preferences
  - approved_phrase_examples (from successful reports)
  - correction_history (diffs between draft and PC-approved version)
  - reflection: patterns across multiple reports (e.g., "this client prefers quantitative progress")
- **Cold start**: First 3-5 reports use a default professional template. Memory kicks in after episode consolidation.

### AgentCore Policy (Cedar)
```cedar
// Block report delivery without PC approval
forbid(
  principal,
  action == AgentCore::Action::"deliver_report",
  resource
)
unless {
  context.report.approval_status == "approved" &&
  context.report.approved_by_role == "project_coordinator"
};

// Block client Q&A from disclosing internal data
forbid(
  principal,
  action == AgentCore::Action::"chat_respond",
  resource
)
when {
  context.response.contains_internal_data == true
};

// Rate-limit client chat
forbid(
  principal,
  action == AgentCore::Action::"chat_respond",
  resource
)
when {
  context.session.message_count > 50
};
```

### AgentCore Observability
- **Exporter**: OpenTelemetry -> CloudWatch
- **Custom spans**: Each agent step, each tool call, each LLM invocation
- **Custom metrics**: quality_score, hallucination_rate, citation_accuracy, cost_per_report, latency_p95
- **Dashboard**: CloudWatch console with pre-built widgets

## Box Folder Structure

```
/SiteNarrator/
  /{ProjectID}/
    /project-config.json          <- GPS coords, active trades, client prefs
    /{YYYY-MM-DD}/
      /sources/
        photo-001.jpg
        photo-002.jpg
        voice-note-001.m4a
        observations.json         <- Ingest Agent output
      /drafts/
        draft-v1.md
        draft-v2.md               <- After PC revision request
        quality-report.json
        eval-report.json
      /approved/
        final-report.pdf
        approval-record.json      <- PC identity, timestamp, edits
      /client-qa/
        session-{id}.json         <- Chat transcript + escalation records
```

## Observability & Tracing

Every report gets a unique `trace_id`. All spans are children of this root trace:

| Span Name | Parent | Key Attributes |
|-----------|--------|---------------|
| report.submission | root | file_count, project_id, superintendent |
| ingest.voice_transcription | report.submission | duration, word_count, format |
| ingest.box_extract.{n} | report.submission | photo_id, duration, confidence |
| ingest.weather_api | report.submission | lat, lon, status_code |
| ingest.total | report.submission | total_observations, tokens |
| synthesis.memory_query | ingest.total | memory_entries_found |
| synthesis.narrative | ingest.total | sections_generated, tokens, cost |
| quality.validation | synthesis.narrative | score, flags_count, passed |
| eval.hallucination_check | quality.validation | hallucination_score |
| eval.citation_verify | quality.validation | accuracy_pct |
| eval.total | quality.validation | overall_score, cost |
| review.notification_sent | eval.total | channel, recipient |
| review.pc_action | eval.total | action, wait_time_seconds |
| output.pdf_generation | review.pc_action | pages, duration |
| output.box_upload | review.pc_action | file_id, folder |
| client_qa.message | output.box_upload | message_count, escalated |

## Frontend Architecture

### Screen Inventory

| Screen | User | Key Components |
|--------|------|---------------|
| Upload Flow | Superintendent | Camera capture, drag-drop, trade tag selector, voice recorder, submit button |
| Dashboard | PC | Pending drafts list, quality scores, aging indicators, quick-approve |
| Review Interface | PC | Split-pane: editable narrative (left) + photo gallery with citations (right) |
| Client Report View | Client | Read-only formatted report + embedded photos + floating chat widget |
| Chat Widget | Client | Bottom-right floating bubble, expandable, message history, escalation notice |
| Ops Escalation Queue | Project Ops | Table: client name, question, AI attempt, report link, timestamp, status |
| Observability Dashboard | Admin/PM | Latency charts, error rates, cost per report, quality trends, trace explorer |

### Design System (inspired by curious.pm)
- **Typography**: Inter (headings), system font stack (body)
- **Colors**: Warm neutrals (cream/off-white backgrounds), black text, accent yellow for highlights/CTAs
- **Cards**: Rounded corners (12px), subtle shadows, clean borders
- **Layout**: Generous whitespace, max-width containers, responsive grid
- **Chat Widget**: Floating bottom-right, pill-shaped trigger button, expandable panel with message bubbles
- **Animations**: Subtle transitions (200ms), no jarring movements
- **Mobile**: Bottom sheet patterns for upload, thumb-zone optimized buttons

## Data Models

### ObservationBundle (Ingest Agent output)
```python
@dataclass
class PhotoObservation:
    box_file_id: str
    citation_ref: str          # e.g., "Photo 1"
    trade: str
    zone: str
    work_type: str
    progress_state: str
    safety_conditions: str
    materials_present: str
    extraction_confidence: float

@dataclass
class WeatherData:
    temp_high: float
    temp_low: float
    precipitation_mm: float
    wind_kph: float
    humidity: float
    conditions: str

@dataclass
class ObservationBundle:
    project_id: str
    date: str
    superintendent: str
    weather: WeatherData
    notes: str
    trades: Dict[str, List[PhotoObservation]]
    trace_id: str
```

### QualityReport
```python
@dataclass
class SectionFlag:
    section: str
    issue: str
    severity: str  # "warning" | "error"

@dataclass
class QualityReport:
    confidence_score: float
    flags: List[SectionFlag]
    summary: str
    passed: bool
    trace_id: str
```

### EvalReport
```python
@dataclass
class EvalReport:
    hallucination_score: float    # 0.0 = no hallucinations
    citation_accuracy: float      # 1.0 = all citations correct
    tone_consistency: float       # 1.0 = matches project memory
    overall_score: float
    cost_usd: float
    latency_ms: int
    trace_id: str
    recommendations: List[str]
```

## File Structure (Updated)

```
sitenarrator/
+-- .kiro/
|   +-- steering/
|   |   +-- product.md
|   |   +-- tech.md
|   +-- specs/
|   |   +-- requirements.md
|   |   +-- design.md
|   |   +-- tasks.md
|   +-- hooks/
|   +-- mcp.json
+-- docs/
|   +-- SiteNarrator_PRD.md
+-- src/
|   +-- agents/
|   |   +-- __init__.py
|   |   +-- ingest.py
|   |   +-- synthesis.py
|   |   +-- quality.py
|   |   +-- eval_agent.py        <- NEW: AI evals + observability
|   |   +-- client_qa.py         <- NEW: Client Q&A chat agent
|   +-- tools/
|   |   +-- __init__.py
|   |   +-- box_tools.py
|   |   +-- weather_tools.py
|   |   +-- transcribe_tools.py  <- NEW: AWS Transcribe wrapper
|   |   +-- pdf_tools.py         <- PDF generation
|   |   +-- tracing.py           <- NEW: OTEL instrumentation helpers
|   +-- api/
|   |   +-- __init__.py
|   |   +-- main.py
|   |   +-- routes/
|   |   |   +-- submissions.py
|   |   |   +-- drafts.py
|   |   |   +-- reports.py
|   |   |   +-- chat.py          <- NEW: Client Q&A endpoints
|   |   |   +-- observability.py <- NEW: Traces/metrics endpoints
|   |   +-- websocket.py         <- NEW: WebSocket manager
|   |   +-- auth.py              <- NEW: Authentication (PC + Client)
+-- frontend/                     <- NEW: React frontend
|   +-- package.json
|   +-- vite.config.ts
|   +-- tailwind.config.ts
|   +-- src/
|   |   +-- App.tsx
|   |   +-- pages/
|   |   |   +-- Upload.tsx        <- Superintendent mobile upload
|   |   |   +-- Dashboard.tsx     <- PC dashboard
|   |   |   +-- Review.tsx        <- PC review interface
|   |   |   +-- ReportView.tsx    <- Client report + chat
|   |   |   +-- Escalations.tsx   <- Ops escalation queue
|   |   |   +-- Observability.tsx <- Admin dashboard
|   |   +-- components/
|   |   |   +-- ChatWidget.tsx    <- Floating chat (bottom-right)
|   |   |   +-- PhotoGallery.tsx
|   |   |   +-- NarrativeEditor.tsx
|   |   |   +-- QualityBadge.tsx
|   |   |   +-- TraceViewer.tsx
|   |   +-- hooks/
|   |   |   +-- useWebSocket.ts
|   |   |   +-- useChat.ts
|   |   +-- stores/
|   |   |   +-- appStore.ts      <- Zustand store
+-- demo/
|   +-- run_demo.py
|   +-- seed_data.py              <- Populates Box with sample data
|   +-- sample_photos/            <- From HuggingFace dataset
|   +-- sample_voice_notes/
+-- .env.example
+-- .gitignore
+-- requirements.txt
+-- Makefile                      <- make demo, make dev, make test
+-- README.md
```

## Demo Strategy

### Data Source (NOT Apify)
- **Use HuggingFace ConstructionSite dataset** (10,013 real construction site images, open access, no scraping needed)
- Download 20-30 representative photos covering: concrete work, electrical, framing, plumbing, safety equipment
- Create 3 sample voice notes (pre-recorded .m4a files with realistic superintendent narration)
- Pre-configure a demo project with GPS coords (Seattle area) for weather data

### Why NOT Apify
- Legal risk: scraping construction company photos without permission
- Quality: random scraped images may not show clear trade work
- Reliability: scraper can break during demo
- The HuggingFace dataset is purpose-built, labeled, and free to use

### Demo Flow (single command: `make demo`)
1. Seed script creates Box folder structure for demo project
2. Uploads 5 sample photos + 1 voice note
3. Triggers full pipeline (Ingest -> Synthesis -> Quality -> Eval)
4. Opens browser to PC review interface showing the draft
5. PC approves (or demo script auto-approves after 10s)
6. Opens client report view with chat widget
7. Sends 3 sample questions (2 answerable, 1 triggers escalation)
8. Shows observability dashboard with the trace

## Environment Variables

```
# AWS
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=

# Box
BOX_CLIENT_ID=
BOX_CLIENT_SECRET=
BOX_ENTERPRISE_ID=
BOX_ROOT_FOLDER_ID=

# OpenWeatherMap
OPENWEATHER_API_KEY=

# AgentCore
AGENTCORE_MEMORY_ID=
AGENTCORE_GATEWAY_ID=
AGENTCORE_POLICY_ENGINE_ID=

# App
APP_SECRET_KEY=
FRONTEND_URL=http://localhost:3000
API_URL=http://localhost:8000

# Email (SES)
SES_SENDER_EMAIL=
```

## Notification Architecture

| Event | Channel | Recipient | Latency |
|-------|---------|-----------|---------|
| Draft ready | WebSocket push | PC (active) | < 1s |
| Draft ready | Email (SES) | PC (offline) | < 30s |
| Draft aging > 4hrs | Email (SES) | PM | < 1 min |
| Client Q&A escalation | Webhook + WebSocket | Project Ops | < 2s |
| Report approved | WebSocket | Superintendent | < 1s |

## Construction Domain Model (CRITICAL)

### The Real Workflow (How Construction Actually Works)

```
6:00 AM  - Superintendent arrives, checks weather, decides if work proceeds
6:30 AM  - Crews arrive, Superintendent counts heads by trade
7:00 AM  - Work begins. Superintendent walks site, takes photos of progress
           throughout the day (not just at end of day)
10:00 AM - Inspector arrives for rough-in inspection (Superintendent notes result)
12:00 PM - Material delivery arrives (Superintendent notes what, how much, from whom)
2:00 PM  - Rain starts. Superintendent calls stop on exterior work.
           Notes: "Rain delay 2pm-3:30pm, exterior trades idle, interior continued"
3:30 PM  - Rain stops, exterior work resumes
5:00 PM  - Crews leave. Superintendent does final walkthrough.
5:15 PM  - Superintendent opens SiteNarrator on phone:
           1. Uploads 8-12 photos taken throughout the day
           2. Records 2-3 minute voice note summarizing the day
           3. Tags photos by trade (quick tap)
           4. Hits submit
5:16 PM  - SiteNarrator pipeline runs (< 90 seconds)
5:18 PM  - PC gets notification. Reviews draft in 10-15 minutes.
5:30 PM  - PC approves. PDF generated. Client can access report.
5:35 PM  - Client opens report, asks "Was the Level 2 inspection passed?"
           Chat agent responds: "Yes, per the Inspections section, the rough-in
           inspection was passed at 10:15 AM by Inspector Mike Chen from
           King County Building Dept [see Photo 4]."
```

### Key Domain Insight: Voice Note is the Primary Data Source

The voice note carries ~60% of the report's structured data:
- Crew counts and hours (not visible in photos)
- Equipment usage (partially visible, but hours are verbal)
- Delays and their causes (context not visible in photos)
- Inspections and visitors (may not be photographed)
- Next-day plans (never in photos)

Photos carry ~40%:
- Visual evidence of work completed
- Safety conditions (PPE, housekeeping)
- Material presence on site
- Progress state (formwork up, rebar placed, concrete poured)

### Updated ObservationBundle Schema

```python
@dataclass
class LaborEntry:
    trade: str
    subcontractor: str
    headcount: int
    hours_worked: float
    zone: str
    notes: str

@dataclass
class EquipmentEntry:
    equipment_type: str
    hours_active: float
    hours_idle: float
    owned_or_rental: str
    notes: str

@dataclass
class MaterialDelivery:
    material: str
    quantity: str
    supplier: str
    time_received: str
    notes: str

@dataclass
class DelayEntry:
    cause: str
    cause_category: str  # weather | owner | design | subcontractor | other
    duration_hours: float
    trades_affected: List[str]
    is_force_majeure: bool
    notes: str

@dataclass
class InspectionEntry:
    inspector_name: str
    agency: str
    inspection_type: str
    result: str  # pass | fail | partial
    time: str
    notes: str

@dataclass
class PhotoObservation:
    box_file_id: str
    citation_ref: str
    trade: str
    zone: str
    work_type: str
    progress_state: str
    safety_conditions: str
    materials_present: str
    extraction_confidence: float

@dataclass
class WeatherData:
    temp_high: float
    temp_low: float
    precipitation_mm: float
    wind_kph: float
    humidity: float
    conditions: str
    weather_delays: List[DelayEntry]

@dataclass
class ObservationBundle:
    project_id: str
    date: str
    superintendent: str
    weather: WeatherData
    labor: List[LaborEntry]
    equipment: List[EquipmentEntry]
    materials: List[MaterialDelivery]
    delays: List[DelayEntry]
    inspections: List[InspectionEntry]
    photos: Dict[str, List[PhotoObservation]]  # keyed by trade
    voice_transcript: str
    text_notes: str
    trace_id: str
```

### Why This Matters for Claims & Disputes

Construction disputes are a $40B/year problem. Daily reports are the #1 evidence document in:
- Delay claims (contractor claims extra time/money due to owner-caused delays)
- Change orders (scope changed, need documentation of original vs. actual)
- Safety incidents (OSHA investigations reference daily logs)
- Payment disputes (subcontractor says they had 10 workers, GC says 6)

SiteNarrator's value proposition is NOT just "faster reports." It's:
1. **Contemporaneous documentation** — generated same-day, timestamped, immutable in Box
2. **Structured data extraction** — crew counts, delays, equipment automatically captured
3. **Photo-linked evidence** — every claim traceable to a source photo
4. **Dispute-ready** — delay log, change order evidence, inspection records all structured

### Competitive Landscape Context

| Competitor | What They Do | What They Don't Do |
|-----------|-------------|-------------------|
| Procore Daily Log | Digital form, manual entry | No AI, no photo extraction, no narrative generation |
| Raken | Photo + voice capture, basic reports | No AI synthesis, no structured extraction, no client Q&A |
| Fieldwire | Task management + daily logs | No narrative generation, no multimodal AI |
| SiteNarrator | AI-powered end-to-end: capture -> extract -> synthesize -> review -> deliver -> Q&A | — |
