"""Analiza con SonarQube temporal y bloquea errores de seguridad/calidad graves."""
import base64
import json
import os
from pathlib import Path
import secrets
import subprocess
import time
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
URL = "http://127.0.0.1:9000"
PROJECT = "ia-components-devops"
SERVER_IMAGE = "sonarqube:lts-community"
SCANNER_IMAGE = "sonarsource/sonar-scanner-cli:11"


def api(path, password=None, data=None):
    headers = {}
    if password is not None:
        encoded = base64.b64encode(f"admin:{password}".encode()).decode()
        headers["Authorization"] = f"Basic {encoded}"
    body = urllib.parse.urlencode(data).encode() if data is not None else None
    request = urllib.request.Request(URL + path, data=body, headers=headers)
    # El servidor es local; nunca enviar su autenticación a un proxy externo.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=15) as response:
        payload = response.read()
        return json.loads(payload) if payload else {}


def run():
    name = f"gmcomponents-sonar-{secrets.token_hex(4)}"
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    subprocess.run([
        "docker", "run", "-d", "--name", name,
        "-p", "127.0.0.1:9000:9000", "--memory=3g",
        "-e", "SONAR_ES_BOOTSTRAP_CHECKS_DISABLE=true", SERVER_IMAGE,
    ], check=True)
    try:
        deadline = time.monotonic() + 240
        while time.monotonic() < deadline:
            try:
                if api("/api/system/status").get("status") == "UP":
                    break
            except (OSError, ValueError):
                pass
            time.sleep(3)
        else:
            raise RuntimeError("SonarQube no inició dentro del plazo")

        # Credenciales aleatorias y efímeras; no usar secretos del usuario.
        password = secrets.token_urlsafe(32)
        api("/api/users/change_password", "admin", {
            "login": "admin", "previousPassword": "admin", "password": password,
        })
        token = api("/api/user_tokens/generate", password, {"name": "ci-scan"})["token"]
        api("/api/projects/create", password, {"project": PROJECT, "name": "GM Components"})
        gate = api("/api/qualitygates/create", password, {"name": "GM Components Security"})
        for metric in ("vulnerabilities", "blocker_violations", "critical_violations"):
            api("/api/qualitygates/create_condition", password, {
                "gateId": gate["id"], "metric": metric, "op": "GT", "error": "0",
            })
        api("/api/qualitygates/select", password, {"projectKey": PROJECT, "gateId": gate["id"]})

        env = os.environ.copy()
        env["SONAR_TOKEN"] = token
        env["SONAR_HOST_URL"] = URL
        # Sonar escribe .scannerwork; permitir la escritura al UID del checkout.
        result = subprocess.run([
            "docker", "run", "--rm", "--network=host",
            "--tmpfs", "/tmp:rw,nosuid,nodev,size=512m",
            "--user", f"{os.getuid()}:{os.getgid()}",
            "-e", "SONAR_TOKEN", "-e", "SONAR_HOST_URL",
            "-e", "SONAR_USER_HOME=/tmp/.sonar",
            "-v", f"{ROOT}:/usr/src", SCANNER_IMAGE,
            "-Dsonar.scanner.skipJreProvisioning=true",
            f"-Dsonar.projectVersion={os.getenv('GITHUB_SHA', 'local')}",
        ], env=env)
        status = api(f"/api/qualitygates/project_status?projectKey={PROJECT}", password)
        (reports / "sonarqube.json").write_text(json.dumps(status, indent=2) + "\n")
        issues = api(f"/api/issues/search?componentKeys={PROJECT}&severities=BLOCKER,CRITICAL&ps=100", password)
        (reports / "sonarqube-issues.json").write_text(json.dumps(issues, indent=2) + "\n")
        if result.returncode or status.get("projectStatus", {}).get("status") != "OK":
            raise RuntimeError("El análisis o Quality Gate de SonarQube falló")
        print("SonarQube Quality Gate aprobado")
    finally:
        with (reports / "sonarqube-server.log").open("w") as log:
            subprocess.run(["docker", "logs", name], stdout=log, stderr=subprocess.STDOUT)
        subprocess.run(["docker", "rm", "-f", "-v", name], check=True)


if __name__ == "__main__":
    run()
