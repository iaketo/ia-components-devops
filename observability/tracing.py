from __future__ import annotations
import json
import os
import time
import uuid
from contextlib import contextmanager
from datetime import datetime
from statistics import mean
from typing import Any, Iterator


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OBSERVABILITY_DIR = os.path.join(PROJECT_ROOT, "observability_data")
TRACES_FILE = os.path.join(OBSERVABILITY_DIR, "traces.jsonl")
SUMMARY_FILE = os.path.join(OBSERVABILITY_DIR, "metrics_summary.json")


def _utc_now() -> str:
    return datetime.utcnow().isoformat(timespec="milliseconds") + "Z"


def _duration_ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 2)


class TraceRun:
    """Representa una ejecucion trazable del agente."""

    def __init__(self, recorder: "ObservabilityRecorder", operation: str, metadata: dict[str, Any] | None = None):
        self.recorder = recorder
        self.trace_id = str(uuid.uuid4())
        self.operation = operation
        self.started_at = _utc_now()
        self._start = time.perf_counter()
        self.metadata = metadata or {}
        self.steps: list[dict[str, Any]] = []
        self.finished = False

    @contextmanager
    def step(self, name: str, **metadata: Any) -> Iterator[None]:
        """Mide duracion y estado de un paso interno."""
        start = time.perf_counter()
        event = {
            "name": name,
            "started_at": _utc_now(),
            "metadata": metadata,
        }
        try:
            yield
            event["ok"] = True
        except Exception as exc:
            event["ok"] = False
            event["error"] = str(exc)
            raise
        finally:
            event["duration_ms"] = _duration_ms(start)
            self.steps.append(event)

    def finish(self, ok: bool, metrics: dict[str, Any] | None = None, error: str | None = None) -> dict[str, Any]:
        """Cierra la traza y la persiste en JSONL."""
        if self.finished:
            return {}

        record = {
            "trace_id": self.trace_id,
            "operation": self.operation,
            "started_at": self.started_at,
            "finished_at": _utc_now(),
            "duration_ms": _duration_ms(self._start),
            "ok": ok,
            "error": error,
            "metadata": self.metadata,
            "metrics": metrics or {},
            "steps": self.steps,
        }
        self.recorder.write_trace(record)
        self.finished = True
        return record


class ObservabilityRecorder:
    """Crea trazas y mantiene un resumen agregado de metricas."""

    def __init__(self, traces_file: str = TRACES_FILE, summary_file: str = SUMMARY_FILE):
        self.traces_file = traces_file
        self.summary_file = summary_file
        os.makedirs(os.path.dirname(self.traces_file), exist_ok=True)

    def start_trace(self, operation: str, metadata: dict[str, Any] | None = None) -> TraceRun:
        return TraceRun(self, operation, metadata)

    def write_trace(self, record: dict[str, Any]) -> None:
        with open(self.traces_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        self.write_summary(summarize_traces(load_traces(self.traces_file)))

    def write_summary(self, summary: dict[str, Any]) -> None:
        with open(self.summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)


def load_traces(path: str = TRACES_FILE) -> list[dict[str, Any]]:
    """Lee trazas JSONL ignorando lineas corruptas para no romper el dashboard."""
    if not os.path.exists(path):
        return []

    traces: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                traces.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return traces


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0
    ordered = sorted(values)
    index = min(len(ordered) - 1, round((percentile / 100) * (len(ordered) - 1)))
    return round(ordered[index], 2)


def summarize_traces(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """Calcula metricas agregadas para informe y dashboard."""
    total = len(traces)
    successful = [t for t in traces if t.get("ok")]
    failed = [t for t in traces if not t.get("ok")]
    durations = [float(t.get("duration_ms", 0)) for t in traces]
    cache_hits = [t for t in traces if t.get("metrics", {}).get("cache_hit")]

    step_durations: dict[str, list[float]] = {}
    step_errors: dict[str, int] = {}
    for trace in traces:
        for step in trace.get("steps", []):
            name = step.get("name", "unknown")
            step_durations.setdefault(name, []).append(float(step.get("duration_ms", 0)))
            if not step.get("ok", True):
                step_errors[name] = step_errors.get(name, 0) + 1

    slowest_steps = sorted(
        [
            {
                "step": name,
                "avg_duration_ms": round(mean(values), 2),
                "runs": len(values),
                "errors": step_errors.get(name, 0),
            }
            for name, values in step_durations.items()
        ],
        key=lambda item: item["avg_duration_ms"],
        reverse=True,
    )

    return {
        "generated_at": _utc_now(),
        "total_traces": total,
        "successful_traces": len(successful),
        "failed_traces": len(failed),
        "success_rate": round((len(successful) / total) * 100, 2) if total else 0,
        "cache_hit_rate": round((len(cache_hits) / total) * 100, 2) if total else 0,
        "avg_duration_ms": round(mean(durations), 2) if durations else 0,
        "p95_duration_ms": _percentile(durations, 95),
        "slowest_steps": slowest_steps[:5],
    }
