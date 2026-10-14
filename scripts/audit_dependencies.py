"""Audita todas las versiones instaladas y falla si alguna no pudo auditarse."""
from importlib.metadata import distributions
import json
from pathlib import Path
import subprocess
import sys


def run():
    reports = Path(__file__).resolve().parents[1] / "reports"
    reports.mkdir(exist_ok=True)
    packages = {}
    for package in distributions():
        name = package.metadata["Name"]
        version = package.version
        # +cpu identifica el wheel oficial, no una versión distinta del código.
        # Solo normaliza la consulta de advisories; no instala ni altera el wheel.
        if name.lower() == "torch" and version.endswith("+cpu"):
            version = version.removesuffix("+cpu")
        packages[name] = version
    requirements = reports / "audit-requirements.txt"
    requirements.write_text("".join(f"{name}=={version}\n" for name, version in sorted(packages.items())))
    result = subprocess.run([
        sys.executable, "-m", "pip_audit", "-r", str(requirements),
        "--disable-pip", "--no-deps", "--format", "json",
        "--output", str(reports / "dependency-audit.json"), "--progress-spinner", "off",
    ])
    if result.returncode:
        return result.returncode
    report = json.loads((reports / "dependency-audit.json").read_text())
    skipped = [p["name"] for p in report["dependencies"] if p.get("skip_reason")]
    if skipped:
        print("Auditoría incompleta:", ", ".join(skipped), file=sys.stderr)
        return 1
    print(f"Auditoría completa: {len(report['dependencies'])} dependencias")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
