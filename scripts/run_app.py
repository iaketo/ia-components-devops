"""Inicia el exporter antes de recibir sesiones de Streamlit."""
import logging
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def telemetry_self_test():
    """Carga sintética explícita, habilitada solo en la validación de Kubernetes."""
    from observability import ObservabilityRecorder
    recorder = ObservabilityRecorder()
    for ok in (True, False):
        run = recorder.start_trace("observability_self_test")
        run.finish(ok=ok, error=None if ok else "Falla sintética de observabilidad")


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if os.getenv("METRICS_ENABLED", "false").lower() == "true":
        from observability.metrics import start_metrics_server
        start_metrics_server()
        if os.getenv("OBSERVABILITY_SELF_TEST", "false").lower() == "true":
            telemetry_self_test()
    from streamlit.web import cli
    sys.argv = [
        "streamlit", "run", str(ROOT / "app.py"),
        "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true",
    ]
    cli.main()


if __name__ == "__main__":
    main()
