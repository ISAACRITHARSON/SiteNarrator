# SiteNarrator

**AI-powered construction daily narrative report generation.**

Built with Kiro • Powered by AWS Bedrock AgentCore • Stored in Box

---

![SiteNarrator](frontend/public/hero.jpg)

---

## Problem

Construction project documentation is one of the most labor-intensive workflows in the industry. Every day, Superintendents collect photos, voice notes, and field observations. A Project Coordinator then spends **1–3 hours** manually synthesizing this into a client-facing narrative report — work that is repetitive, subjective, and chronically delayed.

Post-delivery, clients call or email with clarifying questions, creating another round of manual work. When disputes arise (a $40B/year problem in US construction), daily reports are the #1 evidence document — but they're often incomplete, inconsistent, or missing critical details.

## Solution

SiteNarrator automates the entire workflow end-to-end:

1. **Superintendent uploads photos + voice note** (2 minutes, end of shift)
2. **AI agents analyze, extract, and write** a professional 10-section report (90 seconds)
3. **Project Coordinator reviews and approves** (10–15 minutes of editing, not writing)
4. **Client receives report** with an AI chat widget for instant Q&A
5. **Everything stored in Box** with full audit trail for dispute resolution

The system reduces PC time from 1–3 hours to under 15 minutes per project per day.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Superintendent: Photos + PDFs + Voice Notes + Text             │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Box Storage: /SiteNarrator/{project}/{date}/sources/            │
└────────────────────────────┬────────────────────────────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
     ┌──────────────┐ ┌───────────┐ ┌────────────┐
     │ Box AI       │ │ Weather   │ │ AWS        │
     │ Extract      │ │ API       │ │ Transcribe │
     └──────┬───────┘ └─────┬─────┘ └──────┬─────┘
            └───────────────┼───────────────┘
                            ▼
              ┌──────────────────────────┐
              │  Ingest Agent            │
              │  → ObservationBundle     │
              └────────────┬─────────────┘
                           ▼
              ┌──────────────────────────┐
              │  Synthesis Agent         │
              │  → 10-section narrative  │
              │  → AgentCore Memory      │
              └────────────┬─────────────┘
                           ▼
              ┌──────────────────────────┐
              │  Quality Agent           │
              │  → Validation + Score    │
              └────────────┬─────────────┘
                           ▼
              ┌──────────────────────────┐
              │  Eval Agent              │
              │  → Hallucination check   │
              │  → Citation verify       │
              │  → OpenTelemetry trace   │
              └────────────┬─────────────┘
                           ▼
              ┌──────────────────────────┐
              │  PC Review (Human)       │
              │  Cedar Policy guardrail  │
              └────────────┬─────────────┘
                           ▼
              ┌──────────────────────────┐
              │  PDF → Box /approved/    │
              │  Client Report + Chat    │
              └──────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent Development | **Kiro** (spec-driven development) |
| Backend | Python 3.11, FastAPI |
| Agent Framework | Strands Agents SDK |
| Agent Infrastructure | Amazon Bedrock AgentCore (Runtime, Memory, Gateway, Policy, Observability) |
| LLM | Claude Sonnet 4.5 via AWS Bedrock |
| Content Store | **Box** (AI Extract API + file storage + audit trail) |
| Weather | OpenWeatherMap API |
| Voice | AWS Transcribe |
| Frontend | React 18 + TypeScript + TailwindCSS + Vite |
| PDF Generation | WeasyPrint |
| Tracing | OpenTelemetry → CloudWatch |
| Authorization | Cedar (via AgentCore Policy) |

## Key Features

| Feature | Description |
|---------|-------------|
| Conversational Agent UI | Agent greets user, asks for photos, handles the rest — not a form |
| Multi-format Input | Photos (JPG/PNG), PDFs, Excel, voice notes, text |
| 10-Section Report | Industry-standard format with photo citations, tables, sign-off block |
| Box Integration | All files stored with version history and audit trail |
| AI Evaluation | Hallucination detection, citation accuracy, tone consistency |
| Client Q&A Chat | Floating widget with dynamic suggested questions + escalation |
| Period Summaries | Select date range → comprehensive multi-page summary |
| Guardrails | Cedar Policy blocks delivery without PC approval |
| Traceability | Full pipeline trace with collapsible agent phases |
| Multi-Model | Supports Claude, GPT-4o, Gemini, Llama (configurable) |

## Run Locally

```bash
# Backend (Terminal 1)
cd sitenarrator
pip install -r requirements.txt
make dev
# → http://localhost:8000

# Frontend (Terminal 2)
cd sitenarrator/frontend
npm install
npm run dev
# → http://localhost:5173
```

## Environment Variables

Copy `.env.example` to `.env` and fill in:

```
BOX_CLIENT_ID=your_box_client_id
BOX_CLIENT_SECRET=your_box_client_secret
BOX_ENTERPRISE_ID=your_enterprise_id
BOX_ROOT_FOLDER_ID=your_folder_id
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-5-20250514
OPENWEATHER_API_KEY=your_key
```

## Project Structure

```
sitenarrator/
├── src/
│   ├── agents/          # Ingest, Synthesis, Quality, Eval, Client Q&A, Period Summary
│   ├── tools/           # Box, Weather, Transcribe, PDF, Tracing
│   ├── api/             # FastAPI routes (submissions, drafts, chat, reports)
│   ├── models/          # Pydantic data models
│   └── config.py        # Environment-based settings
├── frontend/
│   └── src/pages/       # Capture, Review, Dashboard, History, Evaluation, ReportView
├── .kiro/
│   ├── specs/           # requirements.md, design.md, tasks.md
│   └── steering/        # product.md, tech.md, design.md
├── docs/
│   └── SiteNarrator_PRD.md
└── demo/
    └── sample_photos/
```

## How It Was Built

This project was built using **Kiro's spec-driven development** workflow:

1. Requirements defined in EARS notation (`.kiro/specs/requirements.md`)
2. Architecture designed with data models and API contracts (`.kiro/specs/design.md`)
3. Tasks prioritized and sized (`.kiro/specs/tasks.md`)
4. Implementation guided by steering files (`.kiro/steering/`)
5. Code generated and iterated with Kiro assistance

## Guardrails & Compliance

- **No report delivered without PC approval** — enforced by Cedar Policy at the tool-call level
- **Every claim traceable** — photo citations link narrative to source evidence
- **Hallucination detection** — Eval Agent checks every report before PC sees it
- **Chat scoped to report content** — never fabricates or discloses internals
- **Escalation path** — when AI can't answer, transparently hands off to humans
- **Full audit trail** — all versions retained in Box indefinitely
- **OpenTelemetry tracing** — every agent step logged with duration and cost

## License

Confidential — Cascadia AI 2026
