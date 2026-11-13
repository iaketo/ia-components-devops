"""Inicia el exporter antes de recibir sesiones de Streamlit."""
import logging
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if os.getenv("METRICS_ENABLED", "false").lower() == "true":
        from observability.metrics import start_metrics_server
        start_metrics_server()
    from streamlit.web import cli
    sys.argv = [
        "streamlit", "run", str(ROOT / "app.py"),
        "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true",
    ]
    cli.main()


if __name__ == "__main__":
    main()
