#!/usr/bin/env python3

"""RoamCore Networking API (OpenWrt)

MVP goals:
- LAN-only HTTP API (firewall restricts to LAN).
- No auth required for MVP.
- Keep implementation minimal (stdlib only).

Auth (future-ready):
- If `RC_API_TOKEN` is set, requests must include header `X-RoamCore-Token: <token>`.
- If unset, no auth is required.
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


def sh_json(cmd: list[str], timeout: int = 5) -> Any:
    rc, out, _ = sh(cmd, timeout=timeout)
    if rc != 0:
        raise RuntimeError("command_failed")
    return json.loads(out)


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

    def _require_auth(self) -> bool:
        token = os.environ.get("RC_API_TOKEN")
        if not token:
            return True
        got = self.headers.get("X-RoamCore-Token")
        return got == token

    def _read_json(self) -> Any:
        ln = int(self.headers.get("Content-Length") or "0")
        raw = self.rfile.read(ln) if ln > 0 else b"{}"
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            raise ValueError("invalid_json")

    def _active_wan_label(self) -> str:
        dev = active_wan_device()
        if dev in ("eth1", "wan", "wan_starlink"):
            return "starlink"
        if dev.startswith("wwan") or dev in ("usb0", "wan_lte"):
            return "lte"
        return dev

    def _ubus_status(self, iface: str) -> dict[str, Any]:
        try:
            return sh_json(["ubus", "call", f"network.interface.{iface}", "status"], timeout=3)
        except Exception:
            return {}

    def _sysfs_counter(self, dev: str, name: str) -> int:
        p = f"/sys/class/net/{dev}/statistics/{name}"
        v = read_first(p, "0")
        try:
            return int(v)
        except Exception:
            return 0

    def do_GET(self) -> None:
        if not self._require_auth():
            return json_response(self, 401, {"success": False, "error": "unauthorized"})

        if self.path == "/api/v1/status":
            obj = {
                "internet": "online" if ping_ok() else "offline",
                "active_wan": self._active_wan_label(),
                "uptime_seconds": get_uptime_seconds(),
                "hostname": read_first("/proc/sys/kernel/hostname", "roamcore"),
            }
            return json_response(self, 200, obj)

        if self.path == "/api/v1/wan":
            st = self._ubus_status("wan_starlink")
            lte = self._ubus_status("wan_lte")

            def ipv4_addr(x: dict[str, Any]) -> str:
                try:
                    return x["ipv4-address"][0]["address"]
                except Exception:
                    return ""

            obj = {
                "starlink": {
                    "state": "online" if st.get("up") else "offline",
                    "ipv4": ipv4_addr(st),
                    "rx_bytes": self._sysfs_counter("eth1", "rx_bytes"),
                    "tx_bytes": self._sysfs_counter("eth1", "tx_bytes"),
                },
                "lte": {
                    "state": "online" if lte.get("up") else "offline",
                    "ipv4": ipv4_addr(lte),
                    "rx_bytes": self._sysfs_counter("wwan0", "rx_bytes"),
                    "tx_bytes": self._sysfs_counter("wwan0", "tx_bytes"),
                },
                "preferred": "starlink",
            }
            return json_response(self, 200, obj)

        if self.path == "/api/v1/system":
            load = read_first("/proc/loadavg", "0 0 0").split()
            meminfo = read_first("/proc/meminfo", "")
            mt = ma = 0
            for line in meminfo.splitlines():
                if line.startswith("MemTotal"):
                    mt = int(line.split()[1])
                if line.startswith("MemAvailable"):
                    ma = int(line.split()[1])
            used = max(mt - ma, 0)
            obj = {
                "load_1m": float(load[0]) if load else 0.0,
                "load_5m": float(load[1]) if len(load) > 1 else 0.0,
                "load_15m": float(load[2]) if len(load) > 2 else 0.0,
                "memory_total_mb": int(mt / 1024) if mt else 0,
                "memory_used_mb": int(used / 1024) if used else 0,
                "memory_percent": (used / mt * 100.0) if mt else 0.0,
                "uptime_seconds": get_uptime_seconds(),
                "openwrt_version": read_first("/etc/openwrt_version", ""),
                "temperature_celsius": 0.0,
            }
            return json_response(self, 200, obj)

        if self.path == "/api/v1/wifi":
            # Minimal: report SSID + enabled. Client listing can be added later.
            rc, ssid, _ = sh(["sh", "-lc", "uci -q get wireless.default_radio0.ssid"], timeout=2)
            obj = {
                "enabled": True,
                "ssid": (ssid or "").strip() if rc == 0 else "",
                "client_count": 0,
                "clients": [],
            }
            return json_response(self, 200, obj)

        if self.path == "/api/v1/data_usage":
            # Minimal placeholder; vnstat parsing can be added once vnstat is installed.
            obj = {"starlink": {}, "lte": {}}
            return json_response(self, 200, obj)

        return json_response(self, 404, {"success": False, "error": "not_found"})

    def do_POST(self) -> None:
        if not self._require_auth():
            return json_response(self, 401, {"success": False, "error": "unauthorized"})

        try:
            body = self._read_json()
        except ValueError:
            return json_response(self, 400, {"success": False, "error": "invalid_json"})

        if self.path == "/api/v1/wifi":
            ssid = str(body.get("ssid") or "").strip()
            key = str(body.get("key") or "")
            if not (1 <= len(ssid) <= 32):
                return json_response(self, 400, {"success": False, "error": "ssid_invalid"})
            if not (8 <= len(key) <= 63):
                return json_response(self, 400, {"success": False, "error": "key_invalid"})
            cmds = [
                f"uci set wireless.default_radio0.ssid='{ssid}'",
                f"uci set wireless.default_radio0.key='{key}'",
                f"uci set wireless.default_radio1.ssid='{ssid}'",
                f"uci set wireless.default_radio1.key='{key}'",
                "uci commit wireless",
                "wifi reload",
            ]
            rc, _, err = sh(["sh", "-lc", " && ".join(cmds)], timeout=10)
            if rc != 0:
                return json_response(self, 500, {"success": False, "error": "apply_failed", "detail": err[-200:]})
            return json_response(self, 200, {"success": True, "message": "WiFi updated"})

        if self.path == "/api/v1/wan/preference":
            pref = str(body.get("preferred") or "").strip().lower()
            if pref not in ("starlink", "lte"):
                return json_response(self, 400, {"success": False, "error": "preferred_invalid"})
            # Minimal: set mwan3 metrics as per spec.
            if pref == "lte":
                script = "uci set mwan3.lte_backup.metric='1'; uci set mwan3.starlink_primary.metric='2'"
            else:
                script = "uci set mwan3.lte_backup.metric='2'; uci set mwan3.starlink_primary.metric='1'"
            rc, _, err = sh(["sh", "-lc", script + "; uci commit mwan3; /etc/init.d/mwan3 restart"], timeout=10)
            if rc != 0:
                return json_response(self, 500, {"success": False, "error": "apply_failed", "detail": err[-200:]})
            return json_response(self, 200, {"success": True, "preferred": pref})

        if self.path == "/api/v1/restart":
            # Return response first then restart in background.
            json_response(self, 200, {"success": True, "message": "Network restart initiated"})
            sh(["sh", "-lc", "(sleep 1; /etc/init.d/network restart; /etc/init.d/mwan3 restart) >/dev/null 2>&1 &"], timeout=2)
            return

        return json_response(self, 404, {"success": False, "error": "not_found"})


def main() -> None:
    host = os.environ.get("RC_API_BIND", "0.0.0.0")
    port = int(os.environ.get("RC_API_PORT", "8080"))
    httpd = HTTPServer((host, port), Handler)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
