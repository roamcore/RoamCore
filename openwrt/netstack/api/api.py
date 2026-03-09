#!/usr/bin/env python3

"""RoamCore Networking API (OpenWrt)

MVP goals:
- LAN-only HTTP API (firewall restricts to LAN).
- No auth required for MVP.
- Keep implementation minimal (stdlib only), designed so we can add optional token auth later.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any


def sh(cmd: list[str], timeout: int = 5) -> tuple[int, str, str]:
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout, p.stderr


def read_first(path: str, default: str = "") -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return default


def json_response(handler: BaseHTTPRequestHandler, code: int, obj: Any) -> None:
    raw = json.dumps(obj).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()
    handler.wfile.write(raw)


def get_uptime_seconds() -> int:
    up = read_first("/proc/uptime", "0 0").split(" ")[0]
    try:
        return int(float(up))
    except Exception:
        return 0


def ping_ok() -> bool:
    rc, _, _ = sh(["ping", "-c", "1", "-W", "2", "1.1.1.1"], timeout=4)
    return rc == 0


def active_wan_device() -> str:
    rc, out, _ = sh(["sh", "-lc", "ip route show default | awk '{print $5}' | head -1"], timeout=3)
    if rc != 0:
        return "unknown"
    return (out or "").strip() or "unknown"


class Handler(BaseHTTPRequestHandler):
    server_version = "RoamCoreNetAPI/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        # quiet by default
        return

    def do_GET(self) -> None:
        if self.path == "/api/v1/status":
            obj = {
                "internet": "online" if ping_ok() else "offline",
                "active_wan": active_wan_device(),
                "uptime_seconds": get_uptime_seconds(),
                "hostname": read_first("/proc/sys/kernel/hostname", "roamcore"),
            }
            return json_response(self, 200, obj)

        return json_response(self, 404, {"success": False, "error": "not_found"})


def main() -> None:
    host = os.environ.get("RC_API_BIND", "0.0.0.0")
    port = int(os.environ.get("RC_API_PORT", "8080"))
    httpd = HTTPServer((host, port), Handler)
    httpd.serve_forever()


if __name__ == "__main__":
    main()

