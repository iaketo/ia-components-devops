"""Genera solo evidencia sintética para demostrar el bloqueo del gate real."""
import argparse
import json
from pathlib import Path


def create_fixture(directory, scenario):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    rate = "0.79" if scenario == "coverage" else "0.85"
    (directory / "coverage.xml").write_text(f'<coverage line-rate="{rate}"/>\n')
    vulnerabilities = [{"id": "EP3-DEMO-CRITICAL", "description": "Fixture sintética, no vulnerabilidad real"}] if scenario == "vulnerability" else []
    audit = {"dependencies": [{"name": "synthetic-fixture", "version": "1.0", "vulns": vulnerabilities}]}
    (directory / "dependency-audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    (directory / "sonarqube.json").write_text(json.dumps({"projectStatus": {"status": "ERROR" if scenario == "sonar" else "OK"}}) + "\n")
    (directory / "fixture-metadata.json").write_text(json.dumps({"synthetic_fixture": True, "scenario": scenario}) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=["vulnerability", "coverage", "sonar"], default="vulnerability")
    parser.add_argument("--directory", default="reports/blocking-demo")
    args = parser.parse_args()
    create_fixture(args.directory, args.scenario)


if __name__ == "__main__":
    main()
