import logging
from dataclasses import dataclass

from opentelemetry import trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


@dataclass
class ObservabilityProviders:
    trace_provider: TracerProvider
    log_provider: LoggerProvider

    def shutdown(self) -> None:
        self.log_provider.shutdown()
        self.trace_provider.shutdown()


_observability_providers: ObservabilityProviders | None = None


def configure_observability() -> ObservabilityProviders:
    global _observability_providers

    if _observability_providers is not None:
        return _observability_providers

    resource = Resource.create({"service.name": "sftp-watcher"})

    trace_provider = TracerProvider(resource=resource)
    trace_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(trace_provider)

    log_provider = LoggerProvider(resource=resource)
    log_provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
    set_logger_provider(log_provider)

    otel_handler = LoggingHandler(
        level=logging.INFO,
        logger_provider=log_provider,
    )

    app_logger = logging.getLogger("sftp_watcher")
    app_logger.addHandler(otel_handler)

    _observability_providers = ObservabilityProviders(
        trace_provider=trace_provider,
        log_provider=log_provider,
    )

    return _observability_providers
