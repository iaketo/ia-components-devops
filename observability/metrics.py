"""Métricas de cada proceso Streamlit; Prometheus conserva las series por réplica."""
from prometheus_client import Counter, Histogram, start_http_server

RUNS = Counter("gm_agent_runs", "Ejecuciones finalizadas", ["status", "source"])
DURATION = Histogram(
    "gm_agent_duration_seconds", "Duración de una ejecución",
    labelnames=["source"],
    buckets=(0.1, 0.5, 1, 2.5, 5, 10, 30, 60, 120),
)


# Publicar el cero inicial permite que increase() observe también el primer error.
for status in ("success", "error"):
    RUNS.labels(status=status, source="app")
DURATION.labels(source="app")


def record_run(record):
    source = "self_test" if record.get("operation") == "observability_self_test" else "app"
    RUNS.labels(status="success" if record["ok"] else "error", source=source).inc()
    DURATION.labels(source=source).observe(record["duration_ms"] / 1000)


def start_metrics_server(port=9100, addr="0.0.0.0"):
    # Incluye process_cpu_seconds_total y process_resident_memory_bytes en Linux.
    return start_http_server(port, addr=addr)
