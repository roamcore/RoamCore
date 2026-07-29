#!/usr/bin/env bash
# Amenities overlay privacy smoke check (slice #22).
#
# Scans the RoamCore amenities overlay surface for outbound HTTP/HTTPS
# references and classifies each host as:
#   - loopback     (127.0.0.0/8, ::1)                       -> allow
#   - local-cidr   (RC_ADDON_CIDR, default 192.168.1.0/24
#                                  + 10.0.0.0/8)           -> allow
#   - external                                         -> require
#                                                              explicit
#                                                              opt-in
#
# An external host is "opt-in" if ANY of:
#   - The literal URL line has a `# PRIVACY-OPTIN:` annotation.
#   - It appears as a token in `input_text.rc_amenities_overpass_url`'s
#     declared `initial:` value AND the line is annotated
#     `# PRIVACY-OPTIN:`.
#
# The check also enforces two slice-specific invariants:
#   1) `input_boolean.rc_amenities_overlay_enabled` must default to OFF.
#   2) `input_text.rc_amenities_overpass_url` default host must be the
#      canonical Overpass instance AND be annotated `# PRIVACY-OPTIN:`.
#
# On any unannotated external host (or invariant violation) the script
# exits 1. On success it prints a summary table of every outbound URL.
#
# Scope (per slice #22 write-scope):
#   - homeassistant/packages/roamcore_amenities.yaml
#   - homeassistant/tools/amenities/overpass_query.py
#   - homeassistant/tools/amenities/__init__.py (if present)
#
# Wired into scripts/check.sh --core-only after the Trip Wrapped smoke
# check and before the amenities-overlay smoke check.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

# Optional override; default to the contract CIDRs from the privacy doc.
RC_ADDON_CIDR="${RC_ADDON_CIDR:-192.168.1.0/24 10.0.0.0/8}"

PYTHON_BIN="${PYTHON_BIN:-python3}"

fail() { echo "ERROR: $*" >&2; exit 1; }

# --- Required slice files exist ---
[ -f homeassistant/packages/roamcore_amenities.yaml ] \
  || fail "missing homeassistant/packages/roamcore_amenities.yaml"
[ -f homeassistant/tools/amenities/overpass_query.py ] \
  || fail "missing homeassistant/tools/amenities/overpass_query.py"

# --- Quick YAML parse check (so a typo here surfaces as a clear
#     error rather than silently allowing a misconfigured privacy toggle).
"$PYTHON_BIN" - <<'PY' >/dev/null
import sys, yaml
yaml.safe_load(open("homeassistant/packages/roamcore_amenities.yaml", "r", encoding="utf-8"))
PY

# --- Run the actual classification + reporting ---
"$PYTHON_BIN" - <<PY
import ipaddress, os, re, sys
from pathlib import Path

ROOT = Path("$ROOT_DIR")
CIDRS = [ipaddress.ip_network(c, strict=False) for c in """$RC_ADDON_CIDR""".split()]

AMENITIES_PKG = ROOT / "homeassistant/packages/roamcore_amenities.yaml"
AMENITIES_TOOLS = ROOT / "homeassistant/tools/amenities"

PIPELINE: list[Path] = [AMENITIES_PKG]
if AMENITIES_TOOLS.exists():
    for p in sorted(AMENITIES_TOOLS.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(AMENITIES_TOOLS)
        if "__pycache__" in rel.parts:
            continue
        if p.suffix == ".pyc":
            continue
        if p.suffix not in (".py", ".yaml", ".yml", ".json"):
            continue
        PIPELINE.append(p)

URL_RE = re.compile(r"https?://[^\s\"'<>]+")

# HA add-on hostnames that resolve to local-network containers
HA_LOCAL_HOSTS = {"supervisor", "hassio", "homeassistant", "ha", "core"}

def is_loopback(host: str) -> bool:
    h = host.strip("[]")
    if h in ("localhost", "::1", "0.0.0.0") or h in HA_LOCAL_HOSTS:
        return True
    try:
        ip = ipaddress.ip_address(h)
        if ip.is_loopback:
            return True
        if ip.version == 4 and ip.is_private and ip in ipaddress.ip_network("127.0.0.0/8"):
            return True
    except ValueError:
        pass
    return False

def is_local_cidr(host: str) -> bool:
    h = host.strip("[]")
    try:
        ip = ipaddress.ip_address(h)
        for cidr in CIDRS:
            if ip in cidr:
                return True
    except ValueError:
        return False
    return False

# --- Slice invariants ---
print()
print("Amenities overlay privacy smoke check (slice #22)")

import yaml
amenities_yaml = yaml.safe_load(open(AMENITIES_PKG, "r", encoding="utf-8"))
errors: list[str] = []

ib = (amenities_yaml.get("input_boolean") or {}).get("rc_amenities_overlay_enabled") or {}
if not isinstance(ib, dict):
    errors.append("input_boolean.rc_amenities_overlay_enabled missing or malformed")
elif ib.get("initial") is not False:
    errors.append(
        f"input_boolean.rc_amenities_overlay_enabled initial must be false (got {ib.get('initial')!r})"
    )
else:
    print("  ✓ input_boolean.rc_amenities_overlay_enabled defaults to OFF (opt-in)")

it = (amenities_yaml.get("input_text") or {}).get("rc_amenities_overpass_url") or {}
if not isinstance(it, dict):
    errors.append("input_text.rc_amenities_overpass_url missing or malformed")
else:
    initial_url = str(it.get("initial") or "").strip()
    m = re.match(r"https?://([^/\s:]+)", initial_url)
    if not m:
        errors.append("input_text.rc_amenities_overpass_url initial must be a URL")
    else:
        host = m.group(1).strip("[]").lower()
        if host != "overpass-api.de":
            errors.append(
                f"input_text.rc_amenities_overpass_url default host must be overpass-api.de (got {host!r})"
            )
        else:
            # Annotation check is enforced by the URL scan below; this just
            # gives a nicer message when both invariants hold.
            print("  ✓ input_text.rc_amenities_overpass_url default points at overpass-api.de")

# --- Scan ---
rows = []
fail_count = 0

for path in PIPELINE:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue
    for lineno, line in enumerate(text.splitlines(), start=1):
        if re.search(r"xmlns\s*[:=]?\s*[\"']?", line):
            stripped = line.lstrip()
            if stripped.startswith("<") or "xmlns" in line.split("//", 1)[0]:
                continue
        for m in URL_RE.finditer(line):
            url = m.group(0).rstrip(".,;:)\"'>]")
            host_match = re.match(r"https?://([^/\s:]+)", url)
            if not host_match:
                continue
            host = host_match.group(1).strip("[]")
            host_lc = host.lower()

            cls = "external"
            if is_loopback(host):
                cls = "loopback"
            elif is_local_cidr(host):
                cls = "local-cidr"

            status = "ok"
            annotation = ""
            if cls == "external":
                if "# PRIVACY-OPTIN" in line:
                    annotation = "line:# PRIVACY-OPTIN"
                    status = "ok (opt-in: line annotation)"
                else:
                    annotation = "UNANNOTATED"
                    status = "FAIL"
                    fail_count += 1

            rows.append((
                str(path.relative_to(ROOT)),
                lineno,
                url,
                host,
                cls,
                status,
                annotation,
            ))

def _trunc(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1] + "\u2026"

w_file, w_line, w_url, w_host, w_cls, w_status, w_anno = 14, 5, 70, 28, 12, 32, 60

print()
print(f"  RC_ADDON_CIDR = {os.environ.get('RC_ADDON_CIDR', '192.168.1.0/24 10.0.0.0/8')}")
print()
print(
    f"  {'file':<{w_file}} {'line':<{w_line}} "
    f"{'url':<{w_url}} {'host':<{w_host}} "
    f"{'class':<{w_cls}} {'status':<{w_status}} {'annotation':<{w_anno}}"
)
print("  " + "-" * (w_file + w_line + w_url + w_host + w_cls + w_status + w_anno + 6))

if not rows:
    print("  (no outbound http/https references found in amenities overlay \u2014 fully local)")
else:
    for r in rows:
        print(
            f"  {_trunc(r[0], w_file):<{w_file}} {r[1]:<{w_line}} "
            f"{_trunc(r[2], w_url):<{w_url}} {_trunc(r[3], w_host):<{w_host}} "
            f"{r[4]:<{w_cls}} {_trunc(r[5], w_status):<{w_status}} "
            f"{_trunc(r[6], w_anno):<{w_anno}}"
        )

print()
total = len(rows)
external_fail = sum(1 for r in rows if r[5] == "FAIL")
loopback_ok = sum(1 for r in rows if r[4] == "loopback")
local_cidr_ok = sum(1 for r in rows if r[4] == "local-cidr")
opt_in_ok = sum(1 for r in rows if "opt-in" in r[5])

print(
    f"  Summary: total={total}  loopback={loopback_ok}  "
    f"local-cidr={local_cidr_ok}  opt-in={opt_in_ok}  "
    f"FAIL={external_fail}"
)

if errors:
    print()
    print("  Slice invariant violations:")
    for e in errors:
        print(f"    - {e}")
    sys.exit(1)

if external_fail:
    print()
    print("  Unannotated external hosts detected. To fix, do ONE of:")
    print("    1) Switch the call to a loopback/local-CIDR target (preferred),")
    print("    2) Annotate the URL line with `# PRIVACY-OPTIN: <reason>`,")
    print("    3) Add the host to homeassistant/tools/amenities/privacy_allowlist.json (follow-up).")
    sys.exit(1)

print()
print("\u2713 Amenities overlay privacy smoke check passed (slice #22)")
sys.exit(0)
PY
