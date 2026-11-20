"""Regresiones de concurrencia, carga sintética y políticas de Kubernetes."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

from prometheus_client import REGISTRY
import yaml

from observability import ObservabilityRecorder, load_traces
from scripts.gate_fixture import create_fixture
from scripts.compliance_gate import evaluate

ROOT = Path(__file__).resolve().parents[1]


def test_concurrent_recorders_keep_complete_json_and_summary(tmp_path):
    traces = str(tmp_path / "traces.jsonl")
    summary = tmp_path / "summary.json"
    recorders = [ObservabilityRecorder(traces, str(summary)) for _ in range(2)]

    def write(index):
        recorder = recorders[index % 2]
        recorder.start_trace("concurrent").finish(ok=True)

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(write, range(40)))
    saved = load_traces(traces)
    assert len(saved) == 40
    assert len({r["trace_id"] for r in saved}) == 40
    assert json.loads(summary.read_text())["total_traces"] == 40
    assert not (tmp_path / "summary.json.tmp").exists()


def test_self_test_metrics_do_not_mix_with_application(tmp_path, monkeypatch):
    from scripts.run_app import telemetry_self_test
    import observability
    recorder = ObservabilityRecorder(str(tmp_path / "traces.jsonl"), str(tmp_path / "summary.json"))
    monkeypatch.setattr(observability, "ObservabilityRecorder", lambda: recorder)
    labels = {"status": "error", "source": "app"}
    before = REGISTRY.get_sample_value("gm_agent_runs_total", labels)
    test_labels = {"status": "error", "source": "self_test"}
    before_test = REGISTRY.get_sample_value("gm_agent_runs_total", test_labels) or 0
    telemetry_self_test()
    assert REGISTRY.get_sample_value("gm_agent_runs_total", labels) == before
    assert REGISTRY.get_sample_value("gm_agent_runs_total", test_labels) == before_test + 1
    assert {r["ok"] for r in load_traces(recorder.traces_file)} == {True, False}


def test_kubernetes_containers_follow_restricted_policy():
    documents = list(yaml.safe_load_all((ROOT / "deploy/kubernetes/resources.yaml").read_text()))
    deployments = {d["metadata"]["name"]: d for d in documents if d["kind"] == "Deployment"}
    assert deployments["gmcomponents"]["spec"]["replicas"] == 2
    for deployment in deployments.values():
        pod = deployment["spec"]["template"]["spec"]
        assert pod["securityContext"]["runAsNonRoot"] is True
        assert pod["securityContext"]["seccompProfile"]["type"] == "RuntimeDefault"
        for container in pod["containers"]:
            security = container["securityContext"]
            assert security["allowPrivilegeEscalation"] is False
            assert security["readOnlyRootFilesystem"] is True
            assert security["capabilities"]["drop"] == ["ALL"]
            assert container["resources"]["limits"]["memory"]
            assert container["readinessProbe"]
            assert container["livenessProbe"]
    assert deployments["alloy"]["spec"]["template"]["spec"]["automountServiceAccountToken"] is True
    assert deployments["gmcomponents"]["spec"]["template"]["spec"]["automountServiceAccountToken"] is False
    assert not any(d["kind"] in ("ClusterRole", "ClusterRoleBinding") for d in documents)


def test_all_demo_failures_are_rejected_by_real_policy(tmp_path):
    for scenario in ("vulnerability", "coverage", "sonar"):
        directory = tmp_path / scenario
        create_fixture(directory, scenario)
        checks = evaluate(directory / "coverage.xml", directory / "dependency-audit.json", directory / "sonarqube.json")
        assert not all(checks.values())
        assert json.loads((directory / "fixture-metadata.json").read_text())["synthetic_fixture"]
