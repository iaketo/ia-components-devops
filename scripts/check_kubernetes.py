"""Comprueba telemetría, logs, alertas y recuperación en el Kubernetes desplegado."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_monitoring import query

NAMESPACE = "gmcomponents"
REPORT = Path("reports/kubernetes/runtime-verification.json")


def get_json(url):
    with urllib.request.urlopen(url, timeout=5) as response:
        return json.load(response)


def wait_for(name, check, timeout=120):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            result = check()
            if result:
                return result
        except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError):
            pass
        time.sleep(2)
    raise RuntimeError(f"No se verificó {name} dentro de {timeout} segundos")


def kubectl(*args):
    return subprocess.check_output(["kubectl", "-n", NAMESPACE, *args], text=True)


def ready_pods():
    pods = json.loads(kubectl("get", "pods", "-l", "app=gmcomponents", "-o", "json"))["items"]
    return [p for p in pods if not p["metadata"].get("deletionTimestamp")
            and any(c["type"] == "Ready" and c["status"] == "True" for c in p["status"].get("conditions", []))]


def log_evidence():
    params = urllib.parse.urlencode({
        "query": '{app="gmcomponents"} | json | event="agent_run" | operation="observability_self_test"',
        "start": str(time.time_ns() - 600 * 1_000_000_000), "limit": "1000",
    })
    response = get_json("http://127.0.0.1:3100/loki/api/v1/query_range?" + params)
    if response["status"] != "success":
        return None
    by_pod = {}
    for stream in response["data"]["result"]:
        for _, line in stream["values"]:
            record = json.loads(line)
            if record.get("event") == "agent_run" and record.get("trace_id"):
                by_pod.setdefault(stream["stream"]["pod"], {})[record["trace_id"]] = record
    complete = {pod: list(records.values()) for pod, records in by_pod.items()
                if {r["ok"] for r in records.values()} == {True, False}}
    return complete if len(complete) >= 2 else None


def check_telemetry():
    prometheus = "http://127.0.0.1:9090"
    expressions = {
        "successes": 'sum(gm_agent_runs_total{status="success",source="self_test"})',
        "errors": 'sum(gm_agent_runs_total{status="error",source="self_test"})',
        "observations": 'sum(gm_agent_duration_seconds_count{source="self_test"})',
        "cpu_processes": 'count(process_cpu_seconds_total{job="gmcomponents"})',
        "memory_processes": 'count(process_resident_memory_bytes{job="gmcomponents"} > 0)',
    }
    values = {name: query(prometheus, expression) for name, expression in expressions.items()}
    return values if (values["successes"] == [2] and values["errors"] == [2]
                      and values["observations"] == [4] and values["cpu_processes"] == [2]
                      and values["memory_processes"] == [2]) else None


def check_dashboard():
    grafana = "http://127.0.0.1:3000"
    dashboard = get_json(grafana + "/api/dashboards/uid/gmcomponents-kubernetes")["dashboard"]
    datasources = get_json(grafana + "/api/datasources")
    if not {"prometheus", "loki"}.issubset({d["uid"] for d in datasources}):
        return None
    if not any(panel["type"] == "logs" for panel in dashboard["panels"]):
        return None
    return {"uid": dashboard["uid"], "panels": len(dashboard["panels"]), "datasources": [d["uid"] for d in datasources]}


def outage_test():
    started = time.monotonic()
    result = {}
    try:
        kubectl("scale", "deployment/gateway", "--replicas=0")
        wait_for("sonda caída", lambda: query("http://127.0.0.1:9090", 'probe_success{job="gateway-health"}') == [0])
        wait_for("alerta crítica", lambda: query("http://127.0.0.1:9090", 'ALERTS{alertname="GatewayUnavailable",alertstate="firing"}') == [1])
        result["alertmanager"] = wait_for("recepción en Alertmanager", lambda: [
            {"labels": alert["labels"], "status": alert["status"]}
            for alert in get_json("http://127.0.0.1:9093/api/v2/alerts")
            if alert["labels"].get("alertname") == "GatewayUnavailable"
        ])
        result["detected_seconds"] = round(time.monotonic() - started, 2)
    finally:
        kubectl("scale", "deployment/gateway", "--replicas=1")
        kubectl("rollout", "status", "deployment/gateway", "--timeout=180s")
        wait_for("sonda recuperada", lambda: query("http://127.0.0.1:9090", 'probe_success{job="gateway-health"}') == [1])
    result["recovered"] = True
    return result


def healing_test():
    before = ready_pods()
    if len(before) != 2:
        raise RuntimeError("Se requieren dos pods listos antes de probar recuperación")
    removed = before[0]["metadata"]
    started = time.monotonic()
    kubectl("delete", "pod", removed["name"], "--wait=false")

    def recovered():
        pods = ready_pods()
        return pods if len(pods) == 2 and all(p["metadata"]["uid"] != removed["uid"] for p in pods) else None

    after = wait_for("reposición automática del pod", recovered, timeout=180)
    wait_for("scrape de las dos réplicas recuperadas", lambda: query("http://127.0.0.1:9090", 'up{job="gmcomponents"}') == [1, 1])
    return {"removed_pod": removed["name"], "ready_pods": [p["metadata"]["name"] for p in after],
            "recovered_seconds": round(time.monotonic() - started, 2)}


def main():
    result = {
        "synthetic_load": True,
        "environment": {
            "github_actions": os.getenv("GITHUB_ACTIONS") == "true",
            "runner_os": os.getenv("RUNNER_OS", "local"),
            "commit": os.getenv("GITHUB_SHA", "local"),
            "run_id": os.getenv("GITHUB_RUN_ID", "local"),
            "orchestrator": "Kubernetes kind, efímero",
        },
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    try:
        result["telemetry"] = wait_for("contadores, histograma y recursos reales", check_telemetry)
        result["centralized_logs"] = wait_for("logs correlacionados de ambos pods en Loki", log_evidence)
        result["dashboard"] = wait_for("dashboard y fuentes de datos", check_dashboard)
        result["outage"] = outage_test()
        result["self_healing"] = healing_test()
        result["passed"] = True
        print("Kubernetes verificado: métricas, logs, dashboard, alerta crítica y recuperación")
    finally:
        REPORT.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
