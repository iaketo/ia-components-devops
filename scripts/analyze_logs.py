"""
Analiza las trazas del agente y genera un resumen de metricas.

Uso:
    python scripts/analyze_logs.py

Salidas:
    observability_data/metrics_summary.json
    Impresion por consola con KPIs principales.
"""

import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from observability import load_traces, summarize_traces  # noqa: E402
from observability.tracing import SUMMARY_FILE, TRACES_FILE  # noqa: E402


def main() -> int:
    traces = load_traces(TRACES_FILE)
    summary = summarize_traces(traces)

    os.makedirs(os.path.dirname(SUMMARY_FILE), exist_ok=True)
    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("Resumen de observabilidad")
    print("=========================")
    print(f"Trazas totales: {summary['total_traces']}")
    print(f"Tasa de exito: {summary['success_rate']}%")
    print(f"Latencia promedio: {summary['avg_duration_ms']} ms")
    print(f"P95 latencia: {summary['p95_duration_ms']} ms")
    print(f"Cache hit: {summary['cache_hit_rate']}%")
    print(f"Resumen escrito en: {SUMMARY_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
