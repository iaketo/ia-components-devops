"""Política EP3: exige evidencia completa; nunca aprueba ante datos faltantes."""
import argparse
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


def evaluate(coverage, audit, sonar):
    rate = float(ET.parse(coverage).getroot().attrib["line-rate"])
    if not math.isfinite(rate) or not 0 <= rate <= 1:
        raise ValueError("Cobertura inválida")
    dependencies = json.loads(Path(audit).read_text())["dependencies"]
    if not isinstance(dependencies, list) or not dependencies:
        raise ValueError("Auditoría vacía o inválida")
    for package in dependencies:
        if not package.get("name") or not package.get("version") or not isinstance(package.get("vulns"), list):
            raise ValueError("Dependencia sin evidencia de auditoría")
    status = json.loads(Path(sonar).read_text())["projectStatus"]["status"]
    return {
        "coverage_at_least_80": rate >= 0.8,
        "dependencies_audited": all(not p.get("skip_reason") for p in dependencies),
        "no_known_vulnerabilities": all(not p["vulns"] for p in dependencies),
        "sonarqube_ok": status == "OK",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coverage", default="coverage.xml")
    parser.add_argument("--audit", default="reports/dependency-audit.json")
    parser.add_argument("--sonar", default="reports/sonarqube.json")
    parser.add_argument("--output", default="reports/compliance.json")
    args = parser.parse_args()
    try:
        checks = evaluate(args.coverage, args.audit, args.sonar)
        result = {"passed": all(checks.values()), "checks": checks}
    except (OSError, ValueError, KeyError, TypeError, AttributeError, ET.ParseError) as exc:
        result = {"passed": False, "error": f"Evidencia inválida o ausente: {exc}"}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
