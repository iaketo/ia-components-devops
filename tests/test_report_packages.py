"""El empaquetado debe conservar la cobertura descargable y delimitar evidencias."""
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import unquote

from scripts.package_reports import build_bundle


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.links.extend(value for key, value in attrs if key == "href")


def test_quality_bundle_keeps_download_contract_and_excludes_secrets(tmp_path):
    source = tmp_path / "reports"
    source.mkdir()
    (source / "compliance.json").write_text('{"passed": true}')
    (source / ".env").write_text("GROQ_API_KEY=do-not-copy")
    (source / "unrelated.json").write_text('{"secret":"do-not-copy"}')
    coverage = tmp_path / "coverage.xml"
    coverage.write_text('<coverage line-rate="0.9467"/>')
    summary = tmp_path / "summary.md"
    output = build_bundle("quality", source, tmp_path / "package", coverage, {
        "GITHUB_SHA": "example-commit", "GITHUB_RUN_ID": "123", "GITHUB_REF_NAME": "main",
        "GITHUB_STEP_SUMMARY": str(summary), "GROQ_API_KEY": "do-not-copy",
    })
    # download-artifact debe seguir entregando coverage.xml directamente en su raíz.
    assert (output / "coverage.xml").read_bytes() == coverage.read_bytes()
    assert not (output / ".env").exists()
    assert not (output / "unrelated.json").exists()
    html = (output / "ABRIR-RESUMEN.html").read_text()
    assert "94.67%" in html
    assert "do-not-copy" not in html + (output / "REVISION.json").read_text()
    assert "01-Pruebas-y-seguridad" in summary.read_text()
    assert json.loads((output / "REVISION.json").read_text())["commit"] == "example-commit"
    parser = LinkParser()
    parser.feed(html)
    for link in parser.links:
        if "://" not in link:
            assert (output / unquote(link)).is_file()


def test_kubernetes_bundle_describes_real_measurements_and_escapes_metadata(tmp_path):
    source = tmp_path / "runtime"
    source.mkdir()
    (source / "monitoring.json").write_text(json.dumps({
        "coverage_percent": [94.67], "deployment_seconds": [81], "replicas_up": [1, 1],
    }))
    (source / "runtime-verification.json").write_text(json.dumps({
        "synthetic_load": True, "outage": {"detected_seconds": 34.14},
        "self_healing": {"recovered_seconds": 6.32}, "passed": True,
    }))
    output = build_bundle("kubernetes", source, tmp_path / "package", environment={"GITHUB_SHA": "<script>unsafe</script>"})
    html = (output / "ABRIR-RESUMEN.html").read_text()
    for measurement in ("94.67%", "81 s", "34.14 s", "6.32 s"):
        assert measurement in html
    assert "Sintética" in html
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_missing_reports_are_visible_and_do_not_look_approved(tmp_path):
    output = build_bundle("quality", tmp_path / "missing", tmp_path / "package", environment={})
    html = (output / "ABRIR-RESUMEN.html").read_text()
    assert "Sin reporte disponible" in html
    assert ">Aprobado<" not in html
    assert (output / "REVISION.json").exists()
