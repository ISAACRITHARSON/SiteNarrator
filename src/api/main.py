"""SiteNarrator — FastAPI application entry point.

Professional-grade API for construction daily narrative report generation.
Handles multimodal submissions, draft review, approval workflow,
client Q&A chat, and observability endpoints.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_settings
from src.tools.tracing import init_tracing


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: startup and shutdown."""
    # Startup
    init_tracing()
    yield
    # Shutdown (cleanup if needed)


app = FastAPI(
    title="SiteNarrator",
    description="AI-powered construction daily narrative report generation",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend origin
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Health Check ──────────────────────────────────────────────


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "sitenarrator", "version": "1.0.0"}


# ─── Register Route Modules ───────────────────────────────────

from src.api.routes import chat, drafts, observability, reports, submissions  # noqa: E402

app.include_router(submissions.router, prefix="/api/v1", tags=["Submissions"])
app.include_router(drafts.router, prefix="/api/v1", tags=["Drafts & Review"])
app.include_router(reports.router, prefix="/api/v1", tags=["Reports"])
app.include_router(chat.router, prefix="/api/v1", tags=["Client Q&A"])
app.include_router(observability.router, prefix="/api/v1", tags=["Observability"])
