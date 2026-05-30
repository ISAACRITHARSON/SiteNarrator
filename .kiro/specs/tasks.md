# SiteNarrator — Tasks

Priority order for MVP build. Each task is sized for sequential execution.
Each task references the requirement it satisfies.
Sized for sequential execution by one developer.

---

## TASK-01: Environment + Project Scaffolding
**Priority**: 1 (do this first)
**Requirements**: NFR-13, NFR-14
**Time**: 30 min

- [ ] Create requirements.txt: strands-agents, bedrock-agentcore, boto3, fastapi, uvicorn, weasyprint, python-multipart, requests, python-dotenv, boxsdk, opentelemetry-api, opentelemetry-sdk, opentelemetry-exporter-otlp
- [ ] Create .env.example with all variable names (no real keys)
- [ ] Create all __init__.py files for src/ packages
- [ ] Create Makefile with targets: dev, demo, test, lint
- [ ] Verify AWS credentials: boto3 bedrock-runtime client
- [ ] Verify Box credentials: hit /users/me
- [ ] Create frontend/ scaffold: `npm create vite@latest frontend -- --template react-ts`
- [ ] Install frontend deps: tailwindcss, zustand, recharts, react-pdf

---

## TASK-02: Tracing Infrastructure (src/tools/tracing.py)
**Priority**: 2 (everything else emits spans)
**Requirements**: REQ-05.3, REQ-05.6, NFR-09
**Time**: 30 min

- [ ] Set up OpenTelemetry TracerProvider with OTLP exporter to CloudWatch
- [ ] Create helper: `start_report_trace(project_id, date)` -> trace_id
- [ ] Create decorator: `@traced(span_name)` for wrapping tool functions
- [ ] Create helper: `log_llm_call(model, prompt_tokens, completion_tokens, latency, cost)`
- [ ] Verify spans appear in CloudWatch console

---

## TASK-03: Box Tools (src/tools/box_tools.py)
**Priority**: 3
**Requirements**: REQ-02.1, REQ-02.2, REQ-03.4, REQ-08.1, REQ-08.2, REQ-08.4
**Time**: 45 min

- [ ] `upload_photo(file_path, project_id, date, trade)` -> box_file_id
- [ ] `extract_observations(box_file_id)` -> {work_type, progress_state, safety_conditions, materials_present, confidence}
- [ ] `save_draft(content, project_id, date, version)` -> box_file_id
- [ ] `save_approved(content, pdf_bytes, project_id, date)` -> {json_id, pdf_id}
- [ ] `get_or_create_folder(project_id, date, subfolder)` -> folder_id
- [ ] `save_chat_session(session_data, project_id, date)` -> box_file_id
- [ ] All functions decorated with @traced

---

## TASK-04: Weather + Transcribe Tools
**Priority**: 4
**Requirements**: REQ-02.3, REQ-01.4
**Time**: 30 min

- [ ] `src/tools/weather_tools.py`: `get_weather(lat, lon, date)` -> WeatherData dict
- [ ] `src/tools/transcribe_tools.py`: `transcribe_audio(file_path, format)` -> text
- [ ] Weather: OpenWeatherMap current + historical endpoints
- [ ] Transcribe: AWS Transcribe async job, poll for completion
- [ ] Both decorated with @traced

---

## TASK-05: Ingest Agent (src/agents/ingest.py)
**Priority**: 5
**Requirements**: REQ-01.1 through REQ-02.7
**Time**: 60 min

- [ ] Define Strands tools: upload_and_extract, fetch_weather, transcribe_voice
- [ ] System prompt: extract observations, group by trade, emit ObservationBundle
- [ ] Parallel photo extraction (asyncio.gather on Box AI Extract calls)
- [ ] Handle low-confidence extractions: flag for PC review
- [ ] Emit trace spans for each photo + weather + transcription
- [ ] Return complete ObservationBundle with trace_id

---

## TASK-06: Synthesis Agent (src/agents/synthesis.py)
**Priority**: 6
**Requirements**: REQ-03.1 through REQ-03.6
**Time**: 75 min

- [ ] System prompt enforcing 6-section structure with [Photo N] citations
- [ ] AgentCore Memory query at start: retrieve project tone/preferences
- [ ] Cold-start handling: use default professional template if no memory
- [ ] Each trade entry must include: crew, zone, quantity, conditions
- [ ] Save draft to Box via box_tools.save_draft()
- [ ] Emit trace spans per section generation
- [ ] Handle re-draft flow: accept section_comments, re-draft only flagged sections

---

## TASK-07: Quality Agent (src/agents/quality.py)
**Priority**: 7
**Requirements**: REQ-04.1 through REQ-04.6
**Time**: 45 min

- [ ] Validation checklist: 6 sections present, word count, citations, weather, trade coverage, date match
- [ ] Confidence score: citation_density(40%) + completeness(40%) + specificity(20%)
- [ ] Source traceability check: every claim maps to a photo or note
- [ ] Return QualityReport with flags, score, summary, passed boolean
- [ ] Emit trace spans for each validation check

---

## TASK-08: Eval + Observability Agent (src/agents/eval_agent.py)
**Priority**: 8
**Requirements**: REQ-05.1 through REQ-05.6
**Time**: 60 min

- [ ] Hallucination detection: compare narrative claims against ObservationBundle
- [ ] Citation verification: every [Photo N] maps to correct box_file_id
- [ ] Tone consistency: compare against AgentCore Memory style entries
- [ ] Compute overall score, log to CloudWatch as custom metric
- [ ] Compare against 7-day rolling average, flag regressions
- [ ] Log all LLM calls: tokens, latency, cost
- [ ] Return EvalReport with trace_id

---

## TASK-09: FastAPI Core (src/api/main.py + routes/)
**Priority**: 9
**Requirements**: REQ-06.1 through REQ-06.7, NFR-13
**Time**: 75 min

- [ ] POST /api/v1/submissions — multipart upload, triggers pipeline
- [ ] GET /api/v1/submissions/{id}/status — processing status
- [ ] GET /api/v1/drafts/{id} — draft + QualityReport + EvalReport
- [ ] POST /api/v1/drafts/{id}/approve — AgentCore Policy check, PDF gen, Box save
- [ ] POST /api/v1/drafts/{id}/reject — section comments, trigger re-draft
- [ ] PATCH /api/v1/drafts/{id} — direct edit
- [ ] WebSocket /ws/notifications — real-time PC notifications
- [ ] Auth middleware: JWT-based, role: superintendent | pc | client | ops
- [ ] CORS configured for frontend origin

---

## TASK-10: Client Q&A Agent (src/agents/client_qa.py)
**Priority**: 10
**Requirements**: REQ-07.1 through REQ-07.9
**Time**: 60 min

- [ ] Strands agent scoped to: approved report content + source photos + weather
- [ ] System prompt: answer from report only, cite sections/photos, never disclose internals
- [ ] Confidence scoring on each response
- [ ] Escalation logic: confidence < 0.6 -> inform client, offer escalation
- [ ] Webhook to Project Ops with full context on escalation
- [ ] Rate limiting: 50 messages per session
- [ ] AgentCore Memory for session context
- [ ] All interactions traced with parent trace_id from report

---

## TASK-11: Client Q&A API Routes (src/api/routes/chat.py)
**Priority**: 11
**Requirements**: REQ-07.1, REQ-07.5, REQ-07.7
**Time**: 30 min

- [ ] POST /api/v1/reports/{id}/chat — send message, get response
- [ ] GET /api/v1/reports/{id}/chat/history — retrieve session history
- [ ] WebSocket /ws/client-chat/{report_id} — real-time chat
- [ ] POST /api/v1/escalations — webhook receiver for Ops team
- [ ] GET /api/v1/escalations — list escalated conversations
- [ ] Auth: client token required, scoped to their reports only

---

## TASK-12: Observability API Routes (src/api/routes/observability.py)
**Priority**: 12
**Requirements**: REQ-05.2, REQ-05.3, NFR-10
**Time**: 30 min

- [ ] GET /api/v1/traces/{trace_id} — full trace with all spans
- [ ] GET /api/v1/metrics/dashboard — aggregated: latency, errors, cost, quality
- [ ] GET /api/v1/evals/{report_id} — eval results for specific report
- [ ] GET /api/v1/metrics/cost — cost breakdown per report, per agent
- [ ] Data sourced from CloudWatch via boto3

---

## TASK-13: PDF Generation (src/tools/pdf_tools.py)
**Priority**: 13
**Requirements**: REQ-08.1
**Time**: 30 min

- [ ] HTML template: company header, 6 sections, photo thumbnails at citations, footer
- [ ] WeasyPrint rendering with professional CSS (clean typography, proper margins)
- [ ] Include: project name, date, superintendent, report number
- [ ] Photo thumbnails fetched from Box preview URLs
- [ ] Footer: "Generated by SiteNarrator | Confidential | {date}"

---

## TASK-14: AgentCore Memory Integration
**Priority**: 14
**Requirements**: REQ-03.3, REQ-08.3
**Time**: 45 min

- [ ] Create memory with episodic strategy via AgentCore CLI or SDK
- [ ] Namespace: /strategy/{strategyId}/actor/{projectId}/
- [ ] On synthesis: query memory for tone, preferences, correction_history
- [ ] On approval: compute diff, store as preference signal
- [ ] Reflection generation: patterns across multiple reports
- [ ] Fallback: local JSON file if AgentCore Memory not configured

---

## TASK-15: AgentCore Policy Setup
**Priority**: 15
**Requirements**: REQ-06.4, NFR-08
**Time**: 30 min

- [ ] Create policy engine via AgentCore CLI
- [ ] Write Cedar policy: block deliver_report without approval
- [ ] Write Cedar policy: block chat_respond with internal data
- [ ] Write Cedar policy: rate-limit client chat (50 msgs)
- [ ] Associate policy engine with Gateway
- [ ] Test: attempt delivery without approval -> verify 403

---

## TASK-16: Frontend — Upload Flow (Superintendent)
**Priority**: 16
**Requirements**: REQ-09.1, REQ-09.2, REQ-01.6
**Time**: 60 min

- [ ] Mobile-first responsive layout
- [ ] Camera capture + file picker (photos)
- [ ] Voice recorder component (MediaRecorder API) + file upload for pre-recorded
- [ ] Trade tag selector (tap to select from predefined list)
- [ ] Zone selector (optional, text input)
- [ ] Submit button with progress indicator
- [ ] 3-tap max flow: select photos -> tag trade -> submit
- [ ] Success confirmation with submission ID

---

## TASK-17: Frontend — PC Dashboard + Review Interface
**Priority**: 17
**Requirements**: REQ-09.3, REQ-06.2
**Time**: 90 min

- [ ] Dashboard: list of pending drafts with quality scores, aging indicators
- [ ] Review interface: split-pane layout
  - Left: editable narrative (markdown editor)
  - Right: photo gallery with clickable citation links
- [ ] Quality badge showing confidence score + flags
- [ ] Approve / Reject / Edit buttons
- [ ] Reject flow: select sections, add comments, submit
- [ ] WebSocket integration: real-time notification when new draft arrives
- [ ] Keyboard shortcuts: Cmd+Enter to approve, Cmd+R to reject

---

## TASK-18: Frontend — Client Report View + Chat Widget
**Priority**: 18
**Requirements**: REQ-09.4, REQ-07.1
**Time**: 75 min

- [ ] Read-only formatted report with embedded photos
- [ ] Floating chat widget (bottom-right, pill-shaped trigger)
- [ ] Chat UI: message bubbles, typing indicator, citation links in responses
- [ ] Escalation notice: "I'll connect you with our Project Operations team"
- [ ] Post-chat satisfaction rating (1-5 stars)
- [ ] Responsive: works on tablet + desktop
- [ ] Auth: client token from shareable link

---

## TASK-19: Frontend — Ops Escalation Queue + Observability Dashboard
**Priority**: 19
**Requirements**: REQ-09.7, REQ-09.8
**Time**: 60 min

- [ ] Escalation queue: table with client name, question, AI attempt, report link, timestamp
- [ ] Status management: open / in-progress / resolved
- [ ] Observability dashboard:
  - Pipeline latency chart (p50/p95/p99 over time)
  - Error rate chart
  - Cost per report trend
  - Quality score trend
  - Trace explorer: click trace_id to see full span tree
- [ ] Recharts for all visualizations
- [ ] Auto-refresh via WebSocket

---

## TASK-20: Demo Data + Seed Script
**Priority**: 20
**Requirements**: REQ-10.1 through REQ-10.4
**Time**: 45 min

- [ ] Download 20-30 photos from HuggingFace ConstructionSite dataset
- [ ] Curate into trade categories: concrete(5), electrical(5), framing(5), plumbing(5), safety(5)
- [ ] Record 3 sample voice notes (or use TTS to generate realistic superintendent narration)
- [ ] Create demo/seed_data.py: populates Box with project structure + photos
- [ ] Create demo/run_demo.py: full pipeline run with sample data
- [ ] Create Makefile target: `make demo` runs seed + pipeline + opens browser
- [ ] Verify demo runs end-to-end in under 3 minutes

---

## TASK-21: Integration Testing + Polish
**Priority**: 21 (final)
**Requirements**: All
**Time**: 45 min

- [ ] End-to-end test: upload -> draft -> review -> approve -> PDF -> client chat
- [ ] Verify all traces appear in CloudWatch
- [ ] Verify Cedar policy blocks unapproved delivery
- [ ] Verify client chat escalation reaches Ops queue
- [ ] Write README.md: what it does, how to run, demo instructions, architecture diagram
- [ ] Verify .env is in .gitignore
- [ ] Push to GitHub
- [ ] Prepare demo script: what to show in what order during pitch

---

## Time Budget Summary

| Phase | Tasks | Time |
|-------|-------|------|
| Infrastructure | TASK-01 to TASK-04 | 2h 15min |
| Agent Pipeline | TASK-05 to TASK-08 | 4h 0min |
| API Layer | TASK-09 to TASK-12 | 2h 45min |
| Output + Memory + Policy | TASK-13 to TASK-15 | 1h 45min |
| Frontend | TASK-16 to TASK-19 | 4h 45min |
| Demo + Polish | TASK-20 to TASK-21 | 1h 30min |
| **TOTAL** | **21 tasks** | **17h 0min** |
| Buffer (breaks, debugging) | — | 7h 0min |
| **Grand Total** | — | **24h 0min** |

---

## TASK-22: Voice Note Structured Extraction (CRITICAL PATH)
**Priority**: INSERT AFTER TASK-05 (renumber as needed)
**Requirements**: REQ-11.1 through REQ-11.6
**Time**: 60 min

This is the most important extraction step. The voice note carries crew counts, equipment, delays, inspections — data that photos cannot provide.

- [ ] Extend Ingest Agent system prompt to extract structured data from voice transcript:
  - Labor: trade, subcontractor, headcount, hours, zone
  - Equipment: type, hours active, hours idle
  - Materials: type, quantity, supplier, time
  - Delays: cause, duration, trades affected, category
  - Inspections: inspector, agency, type, result
- [ ] Use structured output (JSON mode) for extraction reliability
- [ ] Confidence scoring per extracted field
- [ ] WHEN confidence < 0.7 on a field, generate a follow-up clarification question
- [ ] Store clarification questions for Superintendent to answer (async)
- [ ] Merge photo observations + voice extraction into complete ObservationBundle

---

## TASK-23: Expanded Report Template (10 Sections)
**Priority**: INSERT INTO TASK-06 (Synthesis Agent)
**Requirements**: REQ-12.1 through REQ-12.10
**Time**: Included in TASK-06 (adds 30 min)

Update Synthesis Agent to produce 10-section report:
- [ ] Project Header (with report number, GC company)
- [ ] Weather & Site Conditions (include delay durations)
- [ ] Manpower Summary (table format: trade | sub | headcount | hours | zone)
- [ ] Work Completed by Trade (narrative + [Photo N] citations)
- [ ] Equipment on Site (table format)
- [ ] Material Deliveries (table format)
- [ ] Safety Observations (incidents, near-misses, toolbox talks)
- [ ] Inspections & Visitors (who, why, outcome)
- [ ] Delays & Issues (cause, duration, impact, responsible party)
- [ ] Work Planned for Next Day (by trade, with constraints)

---

## TASK-24: Delay Log & Claims Support
**Priority**: After TASK-08
**Requirements**: REQ-13.1 through REQ-13.4
**Time**: 30 min

- [ ] Auto-categorize delays: weather, owner-directed, design error, subcontractor, other
- [ ] Flag delays > 2 hours as potential change order evidence
- [ ] Generate delay notice draft for PC review when threshold exceeded
- [ ] Maintain running delay log per project (aggregated from daily reports)
- [ ] Store in Box: /{project_id}/delay-log.json (append-only)

---

## REVISED TIME BUDGET

| Phase | Tasks | Time |
|-------|-------|------|
| Infrastructure | TASK-01 to TASK-04 | 2h 15min |
| Agent Pipeline (expanded) | TASK-05, 22, 06, 23, 07, 08, 24 | 5h 30min |
| API Layer | TASK-09 to TASK-12 | 2h 45min |
| Output + Memory + Policy | TASK-13 to TASK-15 | 1h 45min |
| Frontend | TASK-16 to TASK-19 | 4h 45min |
| Demo + Polish | TASK-20 to TASK-21 | 1h 30min |
| **TOTAL** | **24 tasks** | **18h 30min** |
| Buffer (breaks, debugging) | — | 5h 30min |
| **Grand Total** | — | **24h 0min** |
