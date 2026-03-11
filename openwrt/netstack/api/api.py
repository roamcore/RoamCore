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
import re
import subprocess
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any


def sh(cmd: list[str], timeout: int = 5) -> tuple[int, str, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"


def sh_json(cmd: list[str], timeout: int = 5) -> Any:
    rc, out, _ = sh(cmd, timeout=timeout)
    if rc != 0:
        raise RuntimeError("command_failed")
    return json.loads(out)


def sh_best_effort(cmd: list[str], timeout: int = 5) -> str:
    """Run a command and return stdout on success, else empty string."""

    try:
        rc, out, _ = sh(cmd, timeout=timeout)
        return out if rc == 0 else ""
    except Exception:
        return ""


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
    rc, out, _ = sh(["sh", "-c", "ip route show default | awk '{print $5}' | head -1"], timeout=3)
    if rc != 0:
        return "unknown"
    return (out or "").strip() or "unknown"


def fw4_check() -> dict[str, Any]:
    """Best-effort firewall4 (fw4) health.

    On some OpenWrt x86 VM images we've observed fw4 failing with:
    `Chain of type "filter" is not supported`.

    We expose this so HA/RoamCore can display the real state without SSH.
    """

    obj: dict[str, Any] = {
        "firewall_backend": "unknown",
        "fw4_ok": None,
        "fw4_error": "",
        "iptables_mvp_detected": False,
        "roamcore_fw_running": None,
        "iptables_nat_table_ok": None,
    }

    # Detect whether firewall4 is present.
    rc, _, _ = sh(["sh", "-lc", "command -v fw4 >/dev/null 2>&1"], timeout=2)
    if rc == 0:
        obj["firewall_backend"] = "fw4"
        rc2, _out2, err2 = sh(["fw4", "check"], timeout=4)
        obj["fw4_ok"] = rc2 == 0
        obj["fw4_error"] = (err2 or "").strip()

    # Detect our MVP iptables workaround by looking for a MASQUERADE rule.
    # This is intentionally fuzzy; we just want a signal for dashboards.
    # Note: OpenWrt may be configured for legacy iptables; check both.
    rc3, out3, err3 = sh(["sh", "-lc", "iptables -t nat -S"], timeout=3)
    # iptables may be configured for legacy; keep this best-effort.
    rc4, out4, err4 = sh(["sh", "-lc", "iptables-legacy -t nat -S"], timeout=3)

    nat_ok = (rc3 == 0) or (rc4 == 0)
    obj["iptables_nat_table_ok"] = nat_ok

    rules = (out3 or "") + "\n" + (out4 or "")
    errs = (err3 or "") + "\n" + (err4 or "")
    if "Table does not exist" in errs:
        # Helpful hint in dashboards.
        obj["iptables_nat_table_ok"] = False
    if nat_ok and "MASQUERADE" in rules:
        obj["iptables_mvp_detected"] = True

    # Is our RoamCore firewall workaround service running?
    rc5, out5, _err5 = sh(["sh", "-lc", "/etc/init.d/roamcore-fw status 2>/dev/null || true"], timeout=2)
    if rc5 == 0:
        obj["roamcore_fw_running"] = "running" in (out5 or "")

    return obj


# CPU percent without sleeping: compute delta since last call.
# This avoids blocking Home Assistant REST polls.
_CPU_LAST: tuple[int, int] | None = None


def cpu_percent_nonblocking() -> float:
    global _CPU_LAST

    line = read_first("/proc/stat", "").splitlines()[0:1]
    if not line:
        return 0.0
    parts = line[0].split()
    if len(parts) < 5 or parts[0] != "cpu":
        return 0.0

    try:
        nums = [int(x) for x in parts[1:]]
    except Exception:
        return 0.0

    idle = nums[3] + (nums[4] if len(nums) > 4 else 0)
    total = sum(nums)

    if _CPU_LAST is None:
        _CPU_LAST = (idle, total)
        return 0.0

    i1, t1 = _CPU_LAST
    _CPU_LAST = (idle, total)

    idle_d = max(idle - i1, 0)
    total_d = max(total - t1, 1)
    used_d = max(total_d - idle_d, 0)
    return used_d / total_d * 100.0


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

    def _env(self, key: str, default: str) -> str:
        v = os.environ.get(key)
        return v if v else default

    def _want_devnames(self) -> dict[str, str]:
        # Allow overriding device names for dev/test environments.
        return {
            "starlink": self._env("RC_DEV_WAN_STARLINK", "eth1"),
            "lte": self._env("RC_DEV_WAN_LTE_WWAN", "wwan0"),
            "qmi": self._env("RC_DEV_LTE_QMI", "/dev/cdc-wdm0"),
            "mbim": self._env("RC_DEV_LTE_MBIM", "/dev/cdc-wdm0"),
            "lan": self._env("RC_DEV_LAN", "eth0"),
        }

    def _parse_iwinfo_assoclist(self, dev: str) -> list[dict[str, Any]]:
        # Parses `iwinfo <dev> assoclist` output (best-effort).
        rc, out, _ = sh(["sh", "-lc", f"iwinfo {dev} assoclist 2>/dev/null || true"], timeout=3)
        if rc != 0 or not out.strip():
            return []
        clients: list[dict[str, Any]] = []
        cur: dict[str, Any] | None = None
        for line in out.splitlines():
            if re.match(r"^[0-9A-Fa-f:]{17}\s", line):
                if cur:
                    clients.append(cur)
                mac = line.strip().split()[0]
                cur = {"mac": mac, "signal_dbm": None, "rx_rate_mbps": None, "tx_rate_mbps": None}
                continue
            if not cur:
                continue
            m = re.search(r"Signal:\s*(-?\d+)\s*dBm", line)
            if m:
                cur["signal_dbm"] = int(m.group(1))
            m = re.search(r"RX:\s*([0-9.]+)\s*MBit/s", line)
            if m:
                cur["rx_rate_mbps"] = float(m.group(1))
            m = re.search(r"TX:\s*([0-9.]+)\s*MBit/s", line)
            if m:
                cur["tx_rate_mbps"] = float(m.group(1))
        if cur:
            clients.append(cur)
        return clients

    def _dhcp_leases(self) -> dict[str, dict[str, str]]:
        # Map MAC-> {ip, hostname}
        out = read_first("/tmp/dhcp.leases", "")
        m: dict[str, dict[str, str]] = {}
        for line in out.splitlines():
            parts = line.split()
            if len(parts) < 4:
                continue
            _ts, mac, ip, host = parts[:4]
            m[mac.lower()] = {"ip": ip, "hostname": host}
        return m

    def _vnstat_json(self, dev: str, period: str) -> Any:
        # period: d|m
        return sh_json(["vnstat", "-i", dev, "--json", period], timeout=6)

    def _vnstat_pick_mb(self, obj: Any, kind: str) -> int:
        # kind: today_rx_mb, today_tx_mb, month_rx_mb, month_tx_mb
        # Best-effort for vnstat2 JSON structure.
        try:
            iface = obj["interfaces"][0]
        except Exception:
            return 0

        def to_mb(v: Any) -> int:
            try:
                # vnstat reports in KiB.
                return int(round(float(v) / 1024.0))
            except Exception:
                return 0

        if kind.startswith("today_"):
            try:
                day = iface["traffic"]["day"][-1]
                return to_mb(day["rx"] if kind.endswith("rx_mb") else day["tx"])
            except Exception:
                return 0

        if kind.startswith("month_"):
            try:
                month = iface["traffic"]["month"][-1]
                return to_mb(month["rx"] if kind.endswith("rx_mb") else month["tx"])
            except Exception:
                return 0

        return 0

    def _uqmi_signal(self, qmi_dev: str) -> dict[str, Any]:
        # uqmi returns JSON.
        try:
            sig = sh_json(["uqmi", "-d", qmi_dev, "--get-signal-info"], timeout=5)
            sys = sh_json(["uqmi", "-d", qmi_dev, "--get-serving-system"], timeout=5)
        except Exception:
            return {}

        out: dict[str, Any] = {}
        # Common fields: rssi, rsrp, rsrq, snr
        for k in ("rssi", "rsrp", "rsrq", "snr"):
            if k in sig:
                out[f"signal_{k}"] = sig.get(k)
        # Operator
        if isinstance(sys, dict):
            op = sys.get("plmn_description") or sys.get("plmn") or ""
            if op:
                out["carrier"] = op
            reg = sys.get("registration")
            if reg:
                out["registration"] = reg
            tech = sys.get("radio_interface") or sys.get("radio_interfaces")
            if tech:
                out["technology"] = tech
        return out

    def _mbim_status(self, mbim_ctl: str) -> dict[str, Any]:
        """Best-effort LTE modem status via mbimcli.

        Useful for carrier-agnostic diagnostics (SIM missing vs deregistered vs low signal).
        """

        if not mbim_ctl or not os.path.exists(mbim_ctl):
            return {}

        # IMPORTANT: mbimcli can hang if the modem is in a bad state. Keep timeouts tight.
        sub = sh_best_effort(["mbimcli", "-d", mbim_ctl, "--query-subscriber-ready-status"], timeout=2)
        reg = sh_best_effort(["mbimcli", "-d", mbim_ctl, "--query-registration-state"], timeout=2)
        sig = sh_best_effort(["mbimcli", "-d", mbim_ctl, "--query-signal-state"], timeout=2)

        def pick(label: str, text: str) -> str:
            for line in (text or "").splitlines():
                if label in line:
                    return line.split(":", 1)[-1].strip().strip("'")
            return ""

        out: dict[str, Any] = {}
        if not sub and not reg and not sig:
            return {"mbim": "timeout"}

        ready = pick("Ready state", sub)
        if ready:
            out["sim_ready_state"] = ready
        iccid = pick("SIM ICCID", sub)
        if iccid and iccid != "unknown":
            out["sim_iccid"] = iccid

        reg_state = pick("Register state", reg)
        if reg_state:
            out["registration_state"] = reg_state
        provider = pick("Provider name", reg)
        if provider and provider != "unknown":
            out["provider_name"] = provider

        # Signal state (when available)
        rssi = pick("RSSI", sig)
        if rssi:
            out["signal_rssi"] = rssi
        rsrp = pick("RSRP", sig)
        if rsrp:
            out["signal_rsrp"] = rsrp
        rsrq = pick("RSRQ", sig)
        if rsrq:
            out["signal_rsrq"] = rsrq
        sinr = pick("SNR", sig) or pick("SINR", sig)
        if sinr:
            out["signal_sinr"] = sinr

        return out

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
            devs = self._want_devnames()
            st = self._ubus_status("wan_starlink")
            lte = self._ubus_status("wan_lte")

            def ipv4_addr(x: dict[str, Any]) -> str:
                try:
                    return x["ipv4-address"][0]["address"]
                except Exception:
                    return ""

            def gateway(x: dict[str, Any]) -> str:
                try:
                    for r in x.get("route", []) or []:
                        if r.get("target") == "0.0.0.0" and r.get("mask") == 0:
                            return str(r.get("nexthop") or "")
                except Exception:
                    pass
                return ""

            obj = {
                "starlink": {
                    "state": "online" if st.get("up") else "offline",
                    "ipv4": ipv4_addr(st),
                    "gateway": gateway(st),
                    "rx_bytes": self._sysfs_counter(devs["starlink"], "rx_bytes"),
                    "tx_bytes": self._sysfs_counter(devs["starlink"], "tx_bytes"),
                },
                "lte": {
                    "state": "online" if lte.get("up") else "offline",
                    "ipv4": ipv4_addr(lte),
                    "gateway": gateway(lte),
                    "rx_bytes": self._sysfs_counter(devs["lte"], "rx_bytes"),
                    "tx_bytes": self._sysfs_counter(devs["lte"], "tx_bytes"),
                },
                "preferred": "starlink",
            }

            # Keep /wan fast and robust for HA polling.
            # LTE/SIM diagnostics are available under /api/v1/lte.

            # Preferred WAN (best-effort via mwan3 metrics)
            try:
                # Lower metric is preferred.
                rc, out, _ = sh(
                    [
                        "sh",
                        "-c",
                        "uci -q get mwan3.starlink_primary.metric; uci -q get mwan3.lte_backup.metric",
                    ],
                    timeout=2,
                )
                if rc == 0:
                    lines = [x.strip() for x in out.splitlines() if x.strip()]
                    if len(lines) >= 2:
                        sm = int(lines[0])
                        lm = int(lines[1])
                        obj["preferred"] = "starlink" if sm <= lm else "lte"
            except Exception:
                pass
            return json_response(self, 200, obj)

        if self.path == "/api/v1/lte":
            devs = self._want_devnames()
            obj = {"success": True}
            obj.update(self._mbim_status(devs.get("mbim", "")))
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
                "cpu_percent": round(cpu_percent_nonblocking(), 1),
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

            # Best-effort thermal.
            t = read_first("/sys/class/thermal/thermal_zone0/temp", "")
            try:
                obj["temperature_celsius"] = float(t) / 1000.0
            except Exception:
                pass
            return json_response(self, 200, obj)

        if self.path == "/api/v1/firewall":
            obj = {"success": True}
            obj.update(fw4_check())
            return json_response(self, 200, obj)

        if self.path == "/api/v1/wifi":
            # Report SSID + clients (best-effort).
            rc, ssid, _ = sh(["sh", "-c", "uci -q get wireless.default_radio0.ssid"], timeout=2)

            leases = self._dhcp_leases()
            # Try common interface names.
            clients = []
            for dev in ("wlan0", "wlan1"):
                for c in self._parse_iwinfo_assoclist(dev):
                    mac = str(c.get("mac") or "").lower()
                    if mac in leases:
                        c.update(leases[mac])
                    clients.append(c)
            obj = {
                "enabled": True,
                "ssid": (ssid or "").strip() if rc == 0 else "",
                "client_count": len(clients),
                "clients": clients,
            }
            return json_response(self, 200, obj)

        if self.path == "/api/v1/data_usage":
            devs = self._want_devnames()

            out: dict[str, Any] = {
                "starlink": {
                    "today_rx_mb": 0,
                    "today_tx_mb": 0,
                    "month_rx_mb": 0,
                    "month_tx_mb": 0,
                },
                "lte": {
                    "today_rx_mb": 0,
                    "today_tx_mb": 0,
                    "month_rx_mb": 0,
                    "month_tx_mb": 0,
                },
            }

            try:
                d = self._vnstat_json(devs["starlink"], "d")
                m = self._vnstat_json(devs["starlink"], "m")
                out["starlink"]["today_rx_mb"] = self._vnstat_pick_mb(d, "today_rx_mb")
                out["starlink"]["today_tx_mb"] = self._vnstat_pick_mb(d, "today_tx_mb")
                out["starlink"]["month_rx_mb"] = self._vnstat_pick_mb(m, "month_rx_mb")
                out["starlink"]["month_tx_mb"] = self._vnstat_pick_mb(m, "month_tx_mb")
            except Exception:
                pass

            try:
                d = self._vnstat_json(devs["lte"], "d")
                m = self._vnstat_json(devs["lte"], "m")
                out["lte"]["today_rx_mb"] = self._vnstat_pick_mb(d, "today_rx_mb")
                out["lte"]["today_tx_mb"] = self._vnstat_pick_mb(d, "today_tx_mb")
                out["lte"]["month_rx_mb"] = self._vnstat_pick_mb(m, "month_rx_mb")
                out["lte"]["month_tx_mb"] = self._vnstat_pick_mb(m, "month_tx_mb")
            except Exception:
                pass

            obj = out
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
            rc, _, err = sh(["sh", "-c", script + "; uci commit mwan3; /etc/init.d/mwan3 restart"], timeout=10)
            if rc != 0:
                return json_response(self, 500, {"success": False, "error": "apply_failed", "detail": err[-200:]})
            return json_response(self, 200, {"success": True, "preferred": pref})

        if self.path == "/api/v1/restart":
            # Return response first then restart in background.
            json_response(self, 200, {"success": True, "message": "Network restart initiated"})
            sh(["sh", "-c", "(sleep 1; /etc/init.d/network restart; /etc/init.d/mwan3 restart) >/dev/null 2>&1 &"], timeout=2)
            return

        return json_response(self, 404, {"success": False, "error": "not_found"})


def main() -> None:
    host = os.environ.get("RC_API_BIND", "0.0.0.0")
    port = int(os.environ.get("RC_API_PORT", "8080"))
    httpd = HTTPServer((host, port), Handler)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
def cpu_percent_sample(sample_s: float = 0.2) -> float:
    def read_cpu() -> tuple[int, int]:
        line = read_first("/proc/stat", "").splitlines()[0]
        parts = line.split()
        if len(parts) < 5:
            return (0, 0)
        nums = [int(x) for x in parts[1:]]
        idle = nums[3] + (nums[4] if len(nums) > 4 else 0)
        total = sum(nums)
        return (idle, total)

    i1, t1 = read_cpu()
    time.sleep(sample_s)
    i2, t2 = read_cpu()
    idle = max(i2 - i1, 0)
    total = max(t2 - t1, 1)
    used = max(total - idle, 0)
    return used / total * 100.0
