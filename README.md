# SiteNarrator

> **Ai4Humans**

![SiteNarrator](https://github.com/ISAACRITHARSON/sitenarrator/blob/main/civil-engineer-construction-worker-manager-holding-digital-tablet-blueprints-talking-planing-about-construction-site-cooperation-teamwork-concept.jpg)

---

## The Problem

Construction project documentation follows a consistent, manual pattern across virtually every general contracting organization. Foremen capture site conditions throughout the day via smartphone photos and voice memos. The Superintendent consolidates inputs from multiple Foremen and subcontractors at end of day, packages everything, and sends it to the Project Coordinator in the office — who then manually reads the notes, reviews each photo, decides what to include, writes the narrative, formats the report, and emails it to the client.

**This process takes 1–3 hours per project per day, repeated for every active project in the portfolio.**

| Pain Point | Impact |
|---|---|
| Manual synthesis is slow | PCs managing 3+ projects spend half their day on reports |
| Inconsistent narrative quality | Different PCs, different tones — clients notice the variation |
| No photo traceability | Narrative claims can't be linked back to source photos, creating liability risk in disputes |
| Weather data missing or wrong | Manually entered weather is often skipped or estimated, undermining delay documentation |
| Vague trade attribution | "Work continued" instead of "Concrete crew completed Level 2 slab pour" |
| No audit trail | Report edits aren't versioned; original field input is discarded after the report is sent |
| Informal approval | No structured review step — PCs send reports without PM sign-off, creating liability exposure |

---

## Demo

### Sample Field Photos (Input)

| Site Photo 1 | Site Photo 2 |
|---|---|
| ![Site Photo 1](https://raw.githubusercontent.com/ISAACRITHARSON/sitenarrator/main/demo/sample_photos/pexels-keat007-32716845.jpg) | ![Site Photo 2]([https://raw.githubusercontent.com/ISAACRITHARSON/sitenarrator/main/demo/sample_photos/pexels-mahmutyilmaz-35300835.jpg](https://github.com/ISAACRITHARSON/sitenarrator/blob/main/demo/sample_photos/pexels-njeromin-12314551.jpg)) |

### Generated Report (Output)

**[View Sample Report →](https://github.com/ISAACRITHARSON/sitenarrator/blob/main/demo/sample_report.pdf)**

---
## The Solution

SiteNarrator is an AI-powered, multi-agent system that automates this end-to-end process. Hundreds of field inputs — photos, voice notes, and text observations — flow into a **three-agent Strands pipeline** that ingests, synthesizes, and quality-checks a draft narrative. A Project Coordinator reviews and approves before delivery. The final signed-off report and all source evidence are stored in **Box** with a complete audit trail.

**SiteNarrator doesn't replace the Project Coordinator. It eliminates the 1–3 hours of manual synthesis so the PC can focus on accuracy, client relationships, and exception handling — the work only a human should do.**

---

## What It Eliminates

- ✅ Manual photo review and narrative writing
- ✅ Inconsistent report quality across project coordinators
- ✅ Missing or estimated weather data
- ✅ Vague, non-attributable trade progress entries
- ✅ Unversioned report edits and lost field input
- ✅ Reports reaching clients without PM approval

---

## How It Works

```
Field Input (photos, voice notes, text)
        │
        ▼
┌─────────────────────────┐
│  Ingest + Vision Agent  │  ← Box AI Extract · AWS Transcribe · Weather API
└────────────┬────────────┘
             │ Structured JSON observation bundle
             ▼
┌─────────────────────────┐
│    Synthesis Agent      │  ← AgentCore Memory · narrative tone · photo citations
└────────────┬────────────┘
             │ Draft narrative
             ▼
┌─────────────────────────┐
│ Quality + Compliance    │  ← Schema validation · confidence score · missing section flags
│       Agent             │
└────────────┬────────────┘
             │
             ▼
    Project Coordinator Review  (approve · reject · edit)
             │
             ▼
    Box: Final PDF + source photos + full audit trail
```

---

## Tech Stack

| Component | Technology |
|---|---|
| Agent Orchestration | Amazon Strands Agents SDK |
| Agent Infrastructure | Amazon Bedrock AgentCore (Gateway · Memory · Policy) |
| IDE & Spec | AWS Kiro (Spec-Driven Development) |
| Content Store & Vision | Box (AI Extract + MCP Server) |
| Voice Transcription | AWS Transcribe |
| Weather Injection | OpenWeatherMap API |
| Web Scraping (Phase 2) | Apify |
| Report Generation | PDF (WeasyPrint / Puppeteer) |
| LLM | Claude Sonnet via Amazon Bedrock |

---

## Compatibility

- Web-accessible interface for field submission and PC review
- Photo uploads: JPEG / PNG, up to 20 per daily submission
- Voice notes: transcribed via AWS Transcribe before agent processing
- Output: formatted PDF report stored in Box
- Agent memory persists across session boundaries (AgentCore episodic memory)

---

## Team Ai4Humans

Built in 24 hours at the **Cascadia AI Hackathon 2026, Seattle WA**.

| Name | GitHub / LinkedIn |
|---|---|
| Isaac Ritharson | [LinkedIn](https://www.linkedin.com/in/isaacritharson/) |
| Ajith Aredla | [LinkedIn](https://www.linkedin.com/in/ajitharedla/) |
| Zeina Moneib | [LinkedIn](https://www.linkedin.com/in/zeinamoneeb/) |
| Kailash Dattkaya | [LinkedIn](https://www.linkedin.com/in/kailashdattkaya/) |

Special thanks to **Yujian Tang** and the **Box Dev team** for their support throughout the hackathon.

---

## Sponsors & Tools

[![Box](https://img.shields.io/badge/Box-0061D5?style=for-the-badge&logo=box&logoColor=white)](https://www.box.com)
[![AWS](https://img.shields.io/badge/AWS-232F3E?style=for-the-badge&logo=amazon-aws&logoColor=white)](https://aws.amazon.com)
[![Apify](https://img.shields.io/badge/Apify-00B09B?style=for-the-badge)](https://apify.com)

---

*SiteNarrator · Cascadia AI Hackathon 2026 · Version 1.0 MVP*
