#!/usr/bin/env bash
# Trip tracking privacy smoke check (slice #20).
#
# Scans the RoamCore trip pipeline for outbound HTTP/HTTPS references,
# classifies each host as:
#   - loopback     (127.0.0.0/8, ::1)                       -> allow
#   - local-cidr   (RC_ADDON_CIDR, default 192.168.1.0/24
#                                  + 10.0.0.0/8)           -> allow
#   - external                                         -> require
#                                                              explicit
#                                                              opt-in
#
# An external host is "opt-in" if ANY of:
#   - It appears as a token in `input_text.rc_trip_opt_in_domains`'s
#     declared `initial:` value in `roamcore_trip_privacy.yaml`.
#   - It appears in `homeassistant/tools/trip_wrapped/privacy_allowlist.json`
#     under the top-level `allowlist` array.
#   - The literal URL line has a `# PRIVACY-OPTIN:` annotation.
#
# On any unannotated external host the script exits 1. On success it
# prints a summary table of every outbound URL found.
#
# Scope (per slice #20 write-scope):
#   - homeassistant/packages/roamcore_trip_local.yaml
#   - homeassistant/packages/roamcore_trip_wrapped.yaml
#   - homeassistant/packages/roamcore_trip_privacy.yaml
#   - homeassistant/packages/roamcore_location.yaml
#   - homeassistant/tools/trip_wrapped/   (recursive, excl. tests/)
#   - homeassistant/tools/trip_wrapped/privacy_allowlist.json
#
# Tests (under tests/) are intentionally excluded — they mock network
# behaviour and are not shipped to the device.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

# Optional override; default to the contract CIDRs from the privacy doc.
RC_ADDON_CIDR="${RC_ADDON_CIDR:-192.168.1.0/24 10.0.0.0/8}"

PYTHON_BIN="${PYTHON_BIN:-python3}"

fail() { echo "ERROR: $*" >&2; exit 1; }

# --- Required pipeline files exist ---
[ -f homeassistant/packages/roamcore_trip_privacy.yaml ] \
  || fail "missing homeassistant/packages/roamcore_trip_privacy.yaml"
[ -f homeassistant/packages/roamcore_trip_local.yaml ] \
  || fail "missing homeassistant/packages/roamcore_trip_local.yaml"
[ -f homeassistant/packages/roamcore_trip_wrapped.yaml ] \
  || fail "missing homeassistant/packages/roamcore_trip_wrapped.yaml"
[ -f homeassistant/packages/roamcore_location.yaml ] \
  || fail "missing homeassistant/packages/roamcore_location.yaml"
[ -d homeassistant/tools/trip_wrapped ] \
  || fail "missing homeassistant/tools/trip_wrapped/"
[ -f homeassistant/tools/trip_wrapped/privacy_allowlist.json ] \
  || fail "missing homeassistant/tools/trip_wrapped/privacy_allowlist.json"

# --- Quick YAML/JSON parse check (so a typo here surfaces as a clear
#     error rather than silently allowing a misconfigured privacy toggle).
"$PYTHON_BIN" - <<'PY' >/dev/null
import sys, yaml, json
for p in [
    "homeassistant/packages/roamcore_trip_privacy.yaml",
    "homeassistant/packages/roamcore_trip_local.yaml",
    "homeassistant/packages/roamcore_trip_wrapped.yaml",
    "homeassistant/packages/roamcore_location.yaml",
]:
    yaml.safe_load(open(p, "r", encoding="utf-8"))
json.load(open("homeassistant/tools/trip_wrapped/privacy_allowlist.json", "r", encoding="utf-8"))
PY

# --- Run the actual classification + reporting ---
"$PYTHON_BIN" - <<PY
import ipaddress, json, os, re, sys
from pathlib import Path

ROOT = Path("$ROOT_DIR")
CIDRS = [ipaddress.ip_network(c, strict=False) for c in """$RC_ADDON_CIDR""".split()]
PIPELINE = [
    ROOT / "homeassistant/packages/roamcore_trip_local.yaml",
    ROOT / "homeassistant/packages/roamcore_trip_wrapped.yaml",
    ROOT / "homeassistant/packages/roamcore_trip_privacy.yaml",
    ROOT / "homeassistant/packages/roamcore_location.yaml",
]
TRIP_DIR = ROOT / "homeassistant/tools/trip_wrapped"
for p in sorted(TRIP_DIR.rglob("*")):
    if not p.is_file():
        continue
    rel = p.relative_to(TRIP_DIR)
    if "tests" in rel.parts:
        continue
    if "__pycache__" in rel.parts:
        continue
    if p.suffix == ".pyc":
        continue
    if p.name == "privacy_allowlist.json":
        continue
    PIPELINE.append(p)

URL_RE = re.compile(r"https?://[^\s\"'<>]+")

# HA add-on hostnames that resolve to local-network containers
# (supervisor/hassio are DNS aliases inside the HA Core container).
HA_LOCAL_HOSTS = {"supervisor", "hassio", "homeassistant", "ha", "core"}

def is_loopback(host: str) -> bool:
    h = host.strip("[]")  # IPv6 bracket literal
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

# --- Parse opt-in allowlists ---
import yaml
privacy_yaml = yaml.safe_load(
    open(ROOT / "homeassistant/packages/roamcore_trip_privacy.yaml", "r", encoding="utf-8")
)
opt_in_initial = ""
try:
    opt_in_initial = str(
        privacy_yaml.get("input_text", {})
        .get("rc_trip_opt_in_domains", {})
        .get("initial", "")
        or ""
    )
except Exception:
    opt_in_initial = ""

def opt_in_tokens(s: str) -> set:
    return {t.strip().lower() for t in re.split(r"[,\s]+", s or "") if t.strip()}

opt_in_initial_set = opt_in_tokens(opt_in_initial)

try:
    allowlist_json = json.load(
        open(ROOT / "homeassistant/tools/trip_wrapped/privacy_allowlist.json", "r", encoding="utf-8")
    )
except Exception as e:
    print(f"ERROR: could not parse privacy_allowlist.json: {e}", file=sys.stderr)
    sys.exit(2)
allowlist_json_set = {
    str(x).strip().lower()
    for x in (allowlist_json.get("allowlist") or [])
    if str(x).strip()
}

# --- Scan ---
rows = []  # (file, line_no, url, host, classification, status, annotation)
fail_count = 0

for path in PIPELINE:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue
    # Need the line text for PRIVACY-OPTIN detection.
    for lineno, line in enumerate(text.splitlines(), start=1):
        # Skip XML namespace declarations (xmlns="http://www.w3.org/...")
        # and other non-fetch references such as SVG xmlns attributes; these
        # are NEVER fetched at runtime — they are just identifier strings.
        if re.search(r"xmlns\s*[:=]?\s*[\"']?", line):
            # Only skip the line if the xmlns declaration matches an http URL;
            # otherwise let the URL_RE loop inspect the line normally.
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
                # Opt-in: line annotation OR config allowlist
                if "# PRIVACY-OPTIN" in line:
                    annotation = "line:# PRIVACY-OPTIN"
                    status = "ok (opt-in: line annotation)"
                elif host_lc in allowlist_json_set:
                    annotation = f"json:privacy_allowlist.json ({host_lc})"
                    status = "ok (opt-in: privacy_allowlist.json)"
                elif host_lc in opt_in_initial_set:
                    annotation = f"yaml:rc_trip_opt_in_domains ({host_lc})"
                    status = "ok (opt-in: rc_trip_opt_in_domains initial)"
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

# --- Pretty-print summary ---
def _trunc(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1] + "\u2026"

w_file, w_line, w_url, w_host, w_cls, w_status, w_anno = 14, 5, 70, 28, 12, 32, 60

print()
print("Trip tracking privacy smoke check (slice #20)")
print(f"  RC_ADDON_CIDR = {os.environ.get('RC_ADDON_CIDR', '192.168.1.0/24 10.0.0.0/8')}")
print(f"  opt-in (initial rc_trip_opt_in_domains): {sorted(opt_in_initial_set) or '<empty>'}")
print(f"  opt-in (privacy_allowlist.json)        : {sorted(allowlist_json_set) or '<empty>'}")
print()
print(
    f"{'file':<{w_file}} {'line':<{w_line}} "
    f"{'url':<{w_url}} {'host':<{w_host}} "
    f"{'class':<{w_cls}} {'status':<{w_status}} {'annotation':<{w_anno}}"
)
print("-" * (w_file + w_line + w_url + w_host + w_cls + w_status + w_anno + 6))

if not rows:
    print("(no outbound http/https references found in trip pipeline \u2014 fully local)")
else:
    for r in rows:
        print(
            f"{_trunc(r[0], w_file):<{w_file}} {r[1]:<{w_line}} "
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
    f"Summary: total={total}  loopback={loopback_ok}  "
    f"local-cidr={local_cidr_ok}  opt-in={opt_in_ok}  "
    f"FAIL={external_fail}"
)

if external_fail:
    print()
    print("Unannotated external hosts detected. To fix, do ONE of:")
    print("  1) Switch the call to a loopback/local-CIDR target (preferred),")
    print("  2) Add the host to homeassistant/tools/trip_wrapped/privacy_allowlist.json,")
    print("  3) Add the host to rc_trip_opt_in_domains in roamcore_trip_privacy.yaml,")
    print("  4) Annotate the URL line with `# PRIVACY-OPTIN: <reason>`.")
    sys.exit(1)

sys.exit(0)
PY
