---
inclusion: always
---

# SiteNarrator — tech stack constraints

## Stack (do not deviate without asking)
- Language: Python 3.11
- Agent framework: Amazon Strands Agents SDK (strands-agents)
- Agent infra: Amazon Bedrock AgentCore (Runtime, Memory, Gateway, Policy)
- Model: Claude Sonnet via AWS Bedrock
- Content store: Box (Box AI Extract API + Box MCP server)
- Weather: OpenWeatherMap API (GPS-keyed, auto-injected)
- Voice: AWS Transcribe
- API layer: FastAPI
- Output: PDF via WeasyPrint

## File structure
src/agents/   — one file per agent (ingest.py, synthesis.py, quality.py)
src/tools/    — tool functions called by agents (box_tools.py, weather_tools.py)
src/api/      — FastAPI routes (main.py)
.kiro/        — Kiro config only, no code here