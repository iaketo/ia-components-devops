"""Observabilidad para GMcomponents"""

from .tracing import ObservabilityRecorder, load_traces, summarize_traces

__all__ = ["ObservabilityRecorder", "load_traces", "summarize_traces"]
