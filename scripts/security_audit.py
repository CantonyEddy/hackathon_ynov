#!/usr/bin/env python3
"""Security audit helpers for the local AI deployment."""

from __future__ import annotations

import json
import os
import socket
import urllib.request
from pathlib import Path
from typing import Dict, List


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "reports" / "security_audit.json"


def check_port(host: str, port: int) -> Dict[str, object]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    try:
        sock.connect((host, port))
        return {"host": host, "port": port, "open": True}
    except OSError:
        return {"host": host, "port": port, "open": False}
    finally:
        sock.close()


def fetch_health(url: str) -> Dict[str, object]:
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            payload = response.read().decode("utf-8")
            return {"url": url, "status": response.status, "body": payload}
    except Exception as exc:
        return {"url": url, "status": "error", "error": str(exc)}


def run_audit() -> Dict[str, object]:
    checks: List[Dict[str, object]] = []
    checks.append(check_port("127.0.0.1", 8001))
    checks.append(fetch_health("http://127.0.0.1:8001/health"))
    findings = []
    if any(item.get("open") for item in checks if isinstance(item, dict) and "port" in item):
        findings.append("Inference endpoint reachable on localhost")
    else:
        findings.append("Inference endpoint not reachable; start the server before auditing")
    findings.append("CORS is enabled for localhost and 127.0.0.1")
    findings.append("Responses should be reviewed for medical or financial advice safety")
    return {"checks": checks, "findings": findings, "timestamp": os.getenv("COMPUTERNAME", "local")}


if __name__ == "__main__":
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report = run_audit()
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
