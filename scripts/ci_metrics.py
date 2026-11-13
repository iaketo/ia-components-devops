"""Convierte evidencia real del CI a métricas Prometheus, sin generar valores ficticios."""
import argparse
import math
from pathlib import Path
import xml.etree.ElementTree as ET


def render(coverage_path, deployment_seconds):
    coverage = float(ET.parse(coverage_path).getroot().attrib["line-rate"]) * 100
    if not math.isfinite(coverage) or not 0 <= coverage <= 100:
        raise ValueError("Cobertura inválida")
    if not math.isfinite(deployment_seconds) or deployment_seconds < 0:
        raise ValueError("Duración inválida")
    return (
        "# HELP gm_ci_test_coverage_percent Cobertura del commit desplegado\n"
        "# TYPE gm_ci_test_coverage_percent gauge\n"
        f"gm_ci_test_coverage_percent {coverage}\n"
        "# HELP gm_ci_deployment_duration_seconds Tiempo de compose up hasta smoke exitoso\n"
        "# TYPE gm_ci_deployment_duration_seconds gauge\n"
        f"gm_ci_deployment_duration_seconds {deployment_seconds}\n"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coverage", default="coverage.xml")
    parser.add_argument("--deployment-seconds", required=True, type=float)
    parser.add_argument("--output", default="reports/ci-metrics.prom")
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(args.coverage, args.deployment_seconds))


if __name__ == "__main__":
    main()
