"""Verifica réplicas, sonda del gateway y métricas del CI consultando Prometheus."""
import argparse
import json
import time
import urllib.parse
import urllib.request


def query(base, expression):
    url = base + "/api/v1/query?" + urllib.parse.urlencode({"query": expression})
    with urllib.request.urlopen(url, timeout=5) as response:
        payload = json.load(response)
    if payload["status"] != "success":
        raise ValueError("Prometheus rechazó la consulta")
    return [float(item["value"][1]) for item in payload["data"]["result"]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:9090")
    parser.add_argument("--replicas", type=int, default=2)
    parser.add_argument("--output", default="reports/monitoring.json")
    args = parser.parse_args()
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        try:
            replicas = query(args.url, 'up{job="gmcomponents"}')
            probe = query(args.url, 'probe_success{job="gateway-health"}')
            coverage = query(args.url, 'gm_ci_test_coverage_percent')
            duration = query(args.url, 'gm_ci_deployment_duration_seconds')
            if (len(replicas) == args.replicas and all(v == 1 for v in replicas)
                    and probe == [1] and len(coverage) == 1 and coverage[0] >= 80
                    and len(duration) == 1 and duration[0] >= 0):
                from pathlib import Path
                output = Path(args.output)
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(json.dumps({
                    "replicas_up": replicas, "gateway_probe_success": probe,
                    "coverage_percent": coverage, "deployment_seconds": duration,
                }, indent=2) + "\n")
                print("Monitoreo verificado en Prometheus")
                return
        except (OSError, ValueError, KeyError):
            pass
        time.sleep(3)
    raise RuntimeError("Monitoreo incompleto tras 90 segundos")


if __name__ == "__main__":
    main()
