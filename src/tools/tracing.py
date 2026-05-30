"""SiteNarrator — OpenTelemetry tracing infrastructure.

Provides distributed tracing across the entire agent pipeline.
Every report gets a unique trace_id that links all operations
from submission through client Q&A.
"""

from __future__ import annotations

import functools
import time
import uuid
from contextlib import contextmanager
from typing import Any, Callable, Generator

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import StatusCode

from src.config import get_settings


def init_tracing() -> None:
    """Initialize OpenTelemetry tracing.

    Call this once at application startup. Configures the tracer provider
    with OTLP exporter for CloudWatch and console exporter for development.
    """
    settings = get_settings()

    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "service.version": "1.0.0",
            "deployment.environment": settings.app_env,
        }
    )

    provider = TracerProvider(resource=resource)

    # OTLP exporter for CloudWatch (production)
    if settings.otel_exporter_otlp_endpoint:
        otlp_exporter = OTLPSpanExporter(
            endpoint=settings.otel_exporter_otlp_endpoint
        )
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    # Console exporter for development visibility
    if settings.is_development:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)


def get_tracer(name: str = "sitenarrator") -> trace.Tracer:
    """Get a named tracer instance."""
    return trace.get_tracer(name)


def start_report_trace(project_id: str, report_date: str) -> str:
    """Start a new root trace for a report submission.

    Returns a trace_id that should be passed through the entire pipeline.
    """
    tracer = get_tracer()
    span = tracer.start_span(
        "report.submission",
        attributes={
            "report.project_id": project_id,
            "report.date": report_date,
            "report.trace_id": str(uuid.uuid4()),
        },
    )
    trace_id = format(span.get_span_context().trace_id, "032x")
    span.end()
    return trace_id


@contextmanager
def trace_span(
    name: str,
    attributes: dict[str, Any] | None = None,
) -> Generator[trace.Span, None, None]:
    """Context manager for creating a traced span.

    Usage:
        with trace_span("ingest.box_extract", {"photo_id": "123"}) as span:
            result = do_extraction()
            span.set_attribute("confidence", result.confidence)
    """
    tracer = get_tracer()
    with tracer.start_as_current_span(name, attributes=attributes or {}) as span:
        try:
            yield span
        except Exception as e:
            span.set_status(StatusCode.ERROR, str(e))
            span.record_exception(e)
            raise


def traced(span_name: str) -> Callable:
    """Decorator to automatically trace a function.

    Usage:
        @traced("ingest.weather_api")
        def get_weather(lat: float, lon: float) -> dict:
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = get_tracer()
            with tracer.start_as_current_span(span_name) as span:
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    span.set_status(StatusCode.OK)
                    return result
                except Exception as e:
                    span.set_status(StatusCode.ERROR, str(e))
                    span.record_exception(e)
                    raise
                finally:
                    duration_ms = int((time.time() - start_time) * 1000)
                    span.set_attribute("duration_ms", duration_ms)

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = get_tracer()
            with tracer.start_as_current_span(span_name) as span:
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    span.set_status(StatusCode.OK)
                    return result
                except Exception as e:
                    span.set_status(StatusCode.ERROR, str(e))
                    span.record_exception(e)
                    raise
                finally:
                    duration_ms = int((time.time() - start_time) * 1000)
                    span.set_attribute("duration_ms", duration_ms)

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper

    return decorator


def log_llm_call(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: int,
    cost_usd: float | None = None,
) -> None:
    """Log an LLM invocation as a span event on the current span.

    Call this after each LLM call to track token usage and cost.
    """
    span = trace.get_current_span()
    if span.is_recording():
        attributes = {
            "llm.model": model,
            "llm.prompt_tokens": prompt_tokens,
            "llm.completion_tokens": completion_tokens,
            "llm.total_tokens": prompt_tokens + completion_tokens,
            "llm.latency_ms": latency_ms,
        }
        if cost_usd is not None:
            attributes["llm.cost_usd"] = cost_usd
        span.add_event("llm_call", attributes=attributes)
