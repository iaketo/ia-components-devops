import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class TestComplianceLimits(unittest.TestCase):

    def run_gate(self, rate, dependencies, sonar_status, expected):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)

            coverage = base / "coverage.xml"
            audit = base / "audit.json"
            sonar = base / "sonar.json"
            output = base / "result.json"

            coverage.write_text(
                f'<coverage line-rate="{rate}"/>'
            )

            audit.write_text(json.dumps({
                "dependencies": dependencies
            }))

            sonar.write_text(json.dumps({
                "projectStatus": {"status": sonar_status}
            }))

            result = subprocess.run([
                sys.executable,
                str(ROOT / "scripts/compliance_gate.py"),
                "--coverage", str(coverage),
                "--audit", str(audit),
                "--sonar", str(sonar),
                "--output", str(output)
            ], capture_output=True, text=True)

            self.assertEqual(
                result.returncode,
                expected,
                result.stdout + result.stderr
            )

            report = json.loads(output.read_text())
            self.assertEqual(report["passed"], expected == 0)

    def test_coverage_limits(self):
        dependencies = [
            {"name": "fixture", "version": "1.0", "vulns": []}
        ]

        cases = [
            ("0.80", 0),
            ("0.7999", 1),
            ("1.0", 0),
            ("1.01", 1),
            ("-0.1", 1),
            ("nan", 1),
            ("inf", 1)
        ]

        for rate, expected in cases:
            with self.subTest(rate=rate):
                self.run_gate(
                    rate, dependencies, "OK", expected
                )

    def test_empty_dependency_report(self):
        self.run_gate("0.85", [], "OK", 1)

    def test_dependency_without_vulnerability_data(self):
        dependencies = [
            {"name": "fixture", "version": "1.0"}
        ]
        self.run_gate("0.85", dependencies, "OK", 1)

    def test_dependency_without_version(self):
        dependencies = [
            {"name": "fixture", "vulns": []}
        ]
        self.run_gate("0.85", dependencies, "OK", 1)

    def test_unknown_sonar_status(self):
        dependencies = [
            {"name": "fixture", "version": "1.0", "vulns": []}
        ]
        self.run_gate("0.85", dependencies, "UNKNOWN", 1)


if __name__ == "__main__":
    unittest.main()
