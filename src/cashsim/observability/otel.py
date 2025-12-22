from __future__ import annotations

import os
from functools import lru_cache

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def _truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "t", "yes", "y", "on"}


def otel_enabled() -> bool:
    if "CASHSIM_OTEL_ENABLED" in os.environ:
        return _truthy(os.getenv("CASHSIM_OTEL_ENABLED"))

    return bool(os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"))


@lru_cache
def get_tracer() -> trace.Tracer:
    return trace.get_tracer("cashsim")


def configure_tracing(service_name: str = "cashsim") -> None:
    """Initialize tracing only once.

    Uses OTLP/gRPC exporter (endpoint from OTEL_EXPORTER_OTLP_ENDPOINT).
    """
    if not otel_enabled():
        return

    current = trace.get_tracer_provider()
    if isinstance(current, TracerProvider):
        return

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    insecure = _truthy(os.getenv("OTEL_EXPORTER_OTLP_INSECURE", "true"))

    resource = Resource.create(
        {
            "service.name": os.getenv("OTEL_SERVICE_NAME", service_name),
            "service.version": os.getenv("OTEL_SERVICE_VERSION", "dev"),
        }
    )

    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=endpoint, insecure=insecure)
    provider.add_span_processor(BatchSpanProcessor(exporter))

    trace.set_tracer_provider(provider)


def instrument_fastapi(app: FastAPI) -> None:
    """Auto-instrument FastAPI request handling."""
    if not otel_enabled():
        return

    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    excluded = os.getenv("OTEL_EXCLUDED_URLS", "health")
    FastAPIInstrumentor.instrument_app(app, excluded_urls=excluded)
