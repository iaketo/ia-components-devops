"""Pruebas del exporter real y demostración negativa de la política usada en CI."""
import json
import logging
from pathlib import Path
import subprocess
import sys
import urllib.request

import pytest
from prometheus_client.parser import text_string_to_metric_families

from observability import ObservabilityRecorder
from observability.metrics import start_metrics_server
from scripts.ci_metrics import render

ROOT = Path(__file__).resolve().parents[1]


def test_exporter_observes_real_success_and_error(tmp_path, caplog):
    caplog.set_level(logging.INFO, logger="gmcomponents.traces")
    server, thread = start_metrics_server(port=0, addr="127.0.0.1")
    url = f"http://127.0.0.1:{server.server_port}/metrics"

    def samples():
        with urllib.request.urlopen(url, timeout=3) as response:
            return {s.name + str(sorted(s.labels.items())): s.value
                    for family in text_string_to_metric_families(response.read().decode())
                    for s in family.samples}

    try:
        before = samples()
        recorder = ObservabilityRecorder(str(tmp_path / "traces.jsonl"), str(tmp_path / "summary.json"))
        for ok in (True, False):
            run = recorder.start_trace("test", {"secret": "DO_NOT_LOG"})
            record = run.finish(ok=ok, error=None if ok else "DO_NOT_LOG")
            assert record["trace_id"] in caplog.text
        after = samples()
        for status in ("success", "error"):
            key = "gm_agent_runs_total" + str([("status", status)])
            assert after[key] - before.get(key, 0) == 1
        assert after["gm_agent_duration_seconds_count[]"] - before.get("gm_agent_duration_seconds_count[]", 0) == 2
        assert after["process_resident_memory_bytes[]"] > 0
        assert "DO_NOT_LOG" not in caplog.text
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


@pytest.mark.parametrize("scenario", ["pass", "coverage", "vulnerability", "sonar", "skipped", "missing", "corrupt"])
def test_gate_blocks_critical_failures(tmp_path, scenario):
    coverage = tmp_path / "coverage.xml"
    audit = tmp_path / "audit.json"
    sonar = tmp_path / "sonar.json"
    coverage.write_text('<coverage line-rate="0.85"/>')
    dependency = {"name": "fixture-only", "version": "1.0", "vulns": []}
    if scenario == "coverage":
        coverage.write_text('<coverage line-rate="0.79"/>')
    if scenario == "vulnerability":
        dependency["vulns"] = [{"id": "EP3-CRITICAL-FIXTURE", "description": "Synthetic negative test"}]
    if scenario == "skipped":
        dependency["skip_reason"] = "No advisory data"
    audit.write_text(json.dumps({"dependencies": [dependency]}))
    sonar.write_text(json.dumps({"projectStatus": {"status": "ERROR" if scenario == "sonar" else "OK"}}))
    if scenario == "missing":
        sonar.unlink()
    if scenario == "corrupt":
        audit.write_text("invalid json")
    output = tmp_path / "result.json"
    result = subprocess.run([
        sys.executable, str(ROOT / "scripts/compliance_gate.py"),
        "--coverage", str(coverage), "--audit", str(audit), "--sonar", str(sonar), "--output", str(output),
    ], capture_output=True, text=True)
    expected = 0 if scenario == "pass" else 1
    assert result.returncode == expected, result.stdout + result.stderr
    report = json.loads(output.read_text())
    assert report["passed"] == (scenario == "pass")
    # Evidencias separadas de los reportes reales de SonarQube/pip-audit.
    evidence = ROOT / "reports" / "negative-gate-tests"
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / f"{scenario}.json").write_text(json.dumps({
        "synthetic_fixture": True, "scenario": scenario,
        "exit_code": result.returncode, "gate_result": report,
    }, indent=2) + "\n")


def test_ci_metrics_use_coverage_report(tmp_path):
    coverage = tmp_path / "coverage.xml"
    coverage.write_text('<coverage line-rate="0.873"/>')
    metrics = render(coverage, 42)
    assert "gm_ci_test_coverage_percent 87.3\n" in metrics
    assert "gm_ci_deployment_duration_seconds 42\n" in metrics
    with pytest.raises(ValueError):
        render(coverage, -1)
    coverage.write_text('<coverage line-rate="nan"/>')
    with pytest.raises(ValueError):
        render(coverage, 42)
