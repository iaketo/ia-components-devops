"""Métricas de cada proceso Streamlit; Prometheus conserva las series por réplica."""
from prometheus_client import Counter, Histogram, start_http_server

RUNS = Counter("gm_agent_runs", "Ejecuciones finalizadas", ["status"])
DURATION = Histogram(
    "gm_agent_duration_seconds", "Duración de una ejecución",
    buckets=(0.1, 0.5, 1, 2.5, 5, 10, 30, 60, 120),
)


def record_run(record):
    RUNS.labels(status="success" if record["ok"] else "error").inc()
    DURATION.observe(record["duration_ms"] / 1000)


def start_metrics_server(port=9100, addr="0.0.0.0"):
    # Incluye process_cpu_seconds_total y process_resident_memory_bytes en Linux.
    return start_http_server(port, addr=addr)
