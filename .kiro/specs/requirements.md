# SiteNarrator — Requirements (Synced with Implementation)

## FR-01: Multi-Format Input
- REQ-01.1: System SHALL accept JPG/PNG photos (up to 20 per submission)
- REQ-01.2: System SHALL accept PDF and Excel (.xlsx/.xls/.csv) documents
- REQ-01.3: System SHALL accept voice notes (.m4a, .wav, .mp3, .webm)
- REQ-01.4: System SHALL accept free-form text notes
- REQ-01.5: All uploaded files SHALL be stored in Box under /project_id/date/sources/

## FR-02: Ingest Agent
- REQ-02.1: SHALL call Box AI Extract on each photo for structured observations
- REQ-02.2: SHALL extract text from PDF/Excel documents
- REQ-02.3: SHALL call OpenWeatherMap API using GPS coordinates
- REQ-02.4: SHALL transcribe voice notes via AWS Transcribe
- REQ-02.5: SHALL produce a structured ObservationBundle JSON

## FR-03: Synthesis Agent
- REQ-03.1: SHALL produce a 10-section narrative report
- REQ-03.2: SHALL include inline [Photo N] citations per trade entry
- REQ-03.3: SHALL query AgentCore Episodic Memory for project style
- REQ-03.4: SHALL save draft to Box /drafts/ folder

## FR-04: Quality Agent
- REQ-04.1: SHALL validate all 10 sections present
- REQ-04.2: SHALL check citation accuracy against source photos
- REQ-04.3: SHALL compute confidence score (citation density 40% + completeness 40% + specificity 20%)
- REQ-04.4: SHALL flag missing or thin sections

## FR-05: Eval Agent
- REQ-05.1: SHALL run hallucination detection
- REQ-05.2: SHALL verify citation accuracy
- REQ-05.3: SHALL check tone consistency
- REQ-05.4: SHALL log metrics via OpenTelemetry
- REQ-05.5: SHALL support multiple model selection (Claude, GPT-4o, Gemini, Llama)

## FR-06: Human-in-the-Loop Review
- REQ-06.1: PC SHALL approve, reject with comments, or edit directly
- REQ-06.2: Rejection SHALL trigger re-draft of flagged sections only
- REQ-06.3: Approval SHALL generate PDF and store in Box /approved/
- REQ-06.4: Cedar Policy SHALL block delivery without approval

## FR-07: Client Q&A Chat
- REQ-07.1: Floating chat widget on client report page
- REQ-07.2: Suggested questions generated dynamically from report content
- REQ-07.3: Agent answers from report + document content only
- REQ-07.4: Escalation to Project Ops when confidence < 0.6
- REQ-07.5: Rate limited to 50 messages per session

## FR-08: Period Summary Reports
- REQ-08.1: PC selects date range via calendar
- REQ-08.2: System aggregates all daily reports in range
- REQ-08.3: Generates comprehensive multi-page summary (5-25+ pages)

## FR-09: Project Management
- REQ-09.1: Support multiple projects
- REQ-09.2: Switch between projects via sidebar
- REQ-09.3: Create new projects with name, ID, location

## FR-10: Evaluation & Traceability
- REQ-10.1: Display AI evaluation metrics per report
- REQ-10.2: Model selector for report generation
- REQ-10.3: Collapsible agent traceability showing end-to-end workflow
- REQ-10.4: Token usage and cost tracking

## FR-11: Box Storage
- REQ-11.1: All files uploaded to Box on submission
- REQ-11.2: Folder structure: /SiteNarrator/{project}/{date}/{subfolder}/
- REQ-11.3: CCG authentication with enterprise credentials
- REQ-11.4: Version history maintained for all artifacts

## NFR: Non-Functional
- NFR-01: Pipeline completes in under 90 seconds
- NFR-02: Dark desktop UI theme (navy + amber accent)
- NFR-03: Sidebar navigation with project context
- NFR-04: All agent invocations produce OpenTelemetry spans
- NFR-05: Cedar Policy enforces approval guardrail
