"""Ordena evidencias existentes y crea un resumen HTML local para cada ZIP."""
import argparse
from html import escape
import json
import math
import os
from pathlib import Path
import shutil
from urllib.parse import quote
import xml.etree.ElementTree as ET

QUALITY = 'quality'
COMPOSE = 'compose'
KUBERNETES = 'kubernetes'
BLOCKING = 'blocking'
COVERAGE_REPORT = 'coverage.xml'
MONITORING_REPORT = 'monitoring.json'
COMPLIANCE_REPORT = 'compliance.json'
RUNTIME_REPORT = 'runtime-verification.json'
AUDIT_REPORT = 'dependency-audit.json'
SONAR_REPORT = 'sonarqube.json'
CI_METRICS_REPORT = 'ci-metrics.prom'

PACKAGES = {
    QUALITY: ("01-Pruebas-y-seguridad", "Pruebas, cobertura y seguridad"),
    COMPOSE: ("02-Graficos-y-metricas-locales", "Gráficos y métricas locales - Docker Compose"),
    KUBERNETES: ("03-Kubernetes-graficos-logs-y-alertas", "Kubernetes - gráficos, logs y alertas"),
    BLOCKING: ("04-Demostracion-de-bloqueo", "Demostración de bloqueo - fallo esperado"),
}
FILES = {
    "tests.xml": "Resultado de las pruebas automatizadas",
    COVERAGE_REPORT: "Cobertura de pruebas",
    AUDIT_REPORT: "Auditoría de dependencias Python",
    "audit-requirements.txt": "Versiones de dependencias auditadas",
    SONAR_REPORT: "Resultado del Quality Gate de SonarQube",
    "sonarqube-issues.json": "Incidencias críticas o bloqueantes de SonarQube",
    "sonarqube-server.log": "Registro del análisis SonarQube",
    COMPLIANCE_REPORT: "Resultado de la política de cumplimiento",
    "containers.json": "Estado de los contenedores locales",
    "deployment.log": "Registro del despliegue local",
    "image.txt": "Identificación de la imagen y del commit",
    CI_METRICS_REPORT: "Cobertura y duración enviadas a Prometheus",
    MONITORING_REPORT: "Verificación de métricas y disponibilidad",
    "grafana-health.json": "Estado de Grafana",
    "grafana-dashboard.json": "Dashboard consultado en Grafana",
    RUNTIME_REPORT: "Comprobaciones de Kubernetes, logs, alerta y recuperación",
    "resources.json": "Pods, despliegues y servicios de Kubernetes",
    "nodes.txt": "Nodos del clúster Kubernetes",
    "version.json": "Versión de Kubernetes",
    "events.txt": "Eventos del clúster",
    "application.log": "Logs de la aplicación por pod",
    "alloy.log": "Logs del recolector Alloy",
    "loki.log": "Logs del servicio de registros Loki",
    "fixture-metadata.json": "Identificación de datos sintéticos de demostración",
}
SELECTION = {
    QUALITY: ("tests.xml", COVERAGE_REPORT, AUDIT_REPORT, "audit-requirements.txt",
                SONAR_REPORT, "sonarqube-issues.json", "sonarqube-server.log", COMPLIANCE_REPORT),
    COMPOSE: ("containers.json", "deployment.log", "image.txt", CI_METRICS_REPORT, MONITORING_REPORT,
                "grafana-health.json", "grafana-dashboard.json"),
    KUBERNETES: (RUNTIME_REPORT, MONITORING_REPORT, CI_METRICS_REPORT, "resources.json",
                   "nodes.txt", "version.json", "events.txt", "application.log", "alloy.log", "loki.log"),
    BLOCKING: ("fixture-metadata.json", COVERAGE_REPORT, AUDIT_REPORT, SONAR_REPORT, COMPLIANCE_REPORT),
}
UNAVAILABLE = "Sin reporte disponible"


def read_json(path):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def display_number(value, unit=""):
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        return UNAVAILABLE
    return f"{value:g}{unit}"


def first_value(values):
    return values[0] if isinstance(values, list) and values else None


def metric_rows(output):
    rows = []
    monitor = read_json(output / MONITORING_REPORT)
    for key, label, unit in (
        ("coverage_percent", "Cobertura de pruebas", "%"),
        ("deployment_seconds", "Duración medida del despliegue", " s"),
    ):
        if monitor:
            rows.append((label, display_number(first_value(monitor.get(key)), unit)))
    if "replicas_up" in monitor:
        rows.append(("Réplicas con métricas disponibles", str(sum(v == 1 for v in monitor["replicas_up"])) ))
    runtime = read_json(output / RUNTIME_REPORT)
    if runtime:
        rows.extend([
            ("Carga de verificación", "Sintética; separada de las métricas de usuarios"),
            ("Detección y recepción de alerta", display_number(runtime.get("outage", {}).get("detected_seconds"), " s")),
            ("Reposición del pod", display_number(runtime.get("self_healing", {}).get("recovered_seconds"), " s")),
        ])
    compliance = read_json(output / COMPLIANCE_REPORT)
    state = {True: "Aprobado", False: "Rechazado"}.get(compliance.get("passed"), UNAVAILABLE)
    if compliance:
        rows.append(("Gate de cumplimiento", state))
    coverage = output / COVERAGE_REPORT
    if coverage.exists() and not monitor:
        try:
            rate = float(ET.parse(coverage).getroot().attrib["line-rate"]) * 100
            rows.append(("Cobertura de pruebas", display_number(rate, "%")))
        except (OSError, ValueError, KeyError, ET.ParseError):
            rows.append(("Cobertura de pruebas", UNAVAILABLE))
    return rows


def copy_reports(kind, source, output, coverage):
    for name in SELECTION[kind]:
        origin = coverage if name == COVERAGE_REPORT and coverage is not None else source / name
        if origin.is_file():
            shutil.copyfile(origin, output / name)
    if kind == QUALITY:
        for path in sorted((source / "negative-gate-tests").glob("*.json")):
            destination = output / "negative-gate-tests" / path.name
            destination.parent.mkdir(exist_ok=True)
            shutil.copyfile(path, destination)


def render_index(kind, output, revision):
    title = PACKAGES[kind][1]
    rows = "".join(f"<tr><th>{escape(label)}</th><td>{escape(value)}</td></tr>" for label, value in metric_rows(output))
    links = []
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.name != "ABRIR-RESUMEN.html":
            relative = path.relative_to(output).as_posix()
            description = FILES.get(path.name, "Evidencia de prueba negativa" if path.parent.name == "negative-gate-tests" else "Identificación de esta ejecución")
            links.append(f'<li><a href="{quote(relative)}">{escape(description)}</a> <code>{escape(relative)}</code></li>')
    missing = [FILES[name] for name in SELECTION[kind] if not (output / name).is_file()]
    missing_note = "" if not missing else "<p>Sin reporte disponible: " + escape("; ".join(missing)) + ".</p>"
    note = "Esta demostración debe rechazar el gate y omitir el despliegue; sus datos son sintéticos." if kind == BLOCKING else "Este resumen muestra evidencias existentes. Si una comprobación falló, consulta el resultado del workflow y sus registros."
    return f'''<!doctype html>
<html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)}</title>
<style>body{{font:16px system-ui,sans-serif;max-width:1000px;margin:32px auto;padding:0 20px;color:#172033;background:#f5f7fb}}article{{background:white;padding:24px;border-radius:12px}}h1{{color:#213f8c}}a{{color:#1749a4}}li{{margin:14px 0}}code{{overflow-wrap:anywhere}}th,td{{text-align:left;padding:10px;border-bottom:1px solid #ddd}}aside{{padding:14px;background:#edf3ff;border-radius:8px}}</style>
<article><h1>{escape(title)}</h1><p>{escape(note)}</p>
<p>Commit: <code>{escape(revision['commit'])}</code></p>
<p><a href="{escape(revision['run_url'], quote=True)}">Ver ejecución y descargas en GitHub</a> · <a href="https://github.com/iaketo/ia-components-devops/blob/main/monitoring/README.md">Servicios y paneles: guía de acceso</a></p>
<table>{rows}</table>{missing_note}<h2>Reportes de este paquete</h2><ul>{''.join(links)}</ul>
<aside>Extrae el ZIP completo y conserva los archivos junto a este HTML. Los gráficos interactivos se abren en Grafana con Docker iniciado en tu PC. El clúster de Actions es temporal; este archivo no inicia servicios.</aside>
</article></html>'''


def build_bundle(kind, source, output, coverage=None, environment=None):
    environment = os.environ if environment is None else environment
    source, output = Path(source), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    copy_reports(kind, source, output, Path(coverage) if coverage else None)
    server = environment.get("GITHUB_SERVER_URL", "https://github.com")
    repository = environment.get("GITHUB_REPOSITORY", "iaketo/ia-components-devops")
    run_id = environment.get("GITHUB_RUN_ID")
    run_url = f"{server}/{repository}/actions/runs/{run_id}" if run_id else f"{server}/{repository}/actions/workflows/ci.yml"
    revision = {"package": PACKAGES[kind][0], "commit": environment.get("GITHUB_SHA", "local"),
                "branch": environment.get("GITHUB_REF_NAME", "local"), "run_url": run_url}
    (output / "REVISION.json").write_text(json.dumps(revision, indent=2) + "\n", encoding="utf-8")
    (output / "ABRIR-RESUMEN.html").write_text(render_index(kind, output, revision), encoding="utf-8")
    summary = environment.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a", encoding="utf-8") as stream:
            stream.write(f"\n## {PACKAGES[kind][0]}\n\n[Descargar este paquete en Artifacts]({run_url}#artifacts) · [Abrir guía de servicios](https://github.com/iaketo/ia-components-devops/blob/main/monitoring/README.md)\n\nExtrae el ZIP y abre **ABRIR-RESUMEN.html**.\n")
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", required=True, choices=PACKAGES)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--coverage", type=Path)
    args = parser.parse_args()
    build_bundle(args.kind, args.source, args.output, args.coverage)


if __name__ == "__main__":
    main()
