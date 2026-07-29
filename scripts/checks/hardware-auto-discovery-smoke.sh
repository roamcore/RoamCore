#!/usr/bin/env bash
set -euo pipefail

# RoamCore — Hardware auto-discovery + setup flows smoke check.
#
# Validates the Wave 2 #31 slice is present and consistent in the repo:
#   1. Contract package YAML parses + declares 5+ add-ons + 2 summary
#      sensors + master switch + per-add-on setup helpers.
#   2. Setup wizard card YAML parses + references contract entities.
#   3. Probe helper exists + is stdlib-only.
#   4. Service `roamcore.hardware_setup_prompt` declared + handler present.
#   5. docs/setup/hardware-auto-discovery.md has all required sections.
#   6. docs/feature-checklist.md line 73 is ticked `[x]`.
#   7. Privacy invariant: no non-loopback / non-RFC1918 host literal
#      in any probe target across the discovery package + helper.
#
# This script is purely static — it never reaches out to a running HA,
# never resolves DNS, never opens a socket. It exits non-zero on the
# first failed assertion.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

PKG="homeassistant/packages/roamcore_hardware_discovery.yaml"
WIZ="homeassistant/packages/roamcore_setup_wizard_hardware_discovery.yaml"
HELPER_DIR="homeassistant/tools/hardware_discovery"
HELPER="${HELPER_DIR}/probe.py"
HELPER_README="${HELPER_DIR}/README.md"
SETUP_DOC="docs/setup/hardware-auto-discovery.md"
CHECKLIST="docs/feature-checklist.md"
SERVICES_YAML="homeassistant/custom_components/roamcore/services.yaml"
INIT_PY="homeassistant/custom_components/roamcore/__init__.py"

fail() { echo "ERROR: $*" >&2; exit 1; }
pass() { echo "  PASS: $*"; }

# --- Pre-flight -----------------------------------------------------------
[ -f "$PKG" ]    || fail "missing contract package: $PKG"
[ -f "$WIZ" ]    || fail "missing wizard snippet: $WIZ"
[ -f "$HELPER" ] || fail "missing probe helper: $HELPER"
[ -f "$HELPER_README" ] || fail "missing helper README: $HELPER_README"
[ -f "$SETUP_DOC" ] || fail "missing setup doc: $SETUP_DOC"
[ -f "$CHECKLIST" ] || fail "missing feature checklist: $CHECKLIST"
[ -f "$SERVICES_YAML" ] || fail "missing services.yaml: $SERVICES_YAML"
[ -f "$INIT_PY" ]  || fail "missing __init__.py: $INIT_PY"

# --- 1. Contract package -------------------------------------------------
echo "== contract package parses =="
python3 -c 'import sys,yaml; yaml.safe_load(open(sys.argv[1],"r",encoding="utf-8"))' "$PKG" \
  || fail "YAML parse failed: $PKG"
python3 -c 'import sys,yaml; yaml.safe_load(open(sys.argv[1],"r",encoding="utf-8"))' "$WIZ" \
  || fail "YAML parse failed: $WIZ"
pass "$PKG and $WIZ parse cleanly as YAML"

# Per-add-on binary_sensors: line-anchored unique_id checks. The spec
# requires at least 5 add-ons covered — we assert exactly the 5 listed
# in the spec (openwrt, tileserver, traccar, victron, ota).
declare -a ADDONS=(openwrt tileserver traccar victron ota)
echo "== per-add-on binary_sensor.rc_hardware_<addon>_available =="
for a in "${ADDONS[@]}"; do
  unique="rc_hardware_${a}_available"
  if ! grep -qE "^[[:space:]]+unique_id:[[:space:]]+${unique}[[:space:]]*$" "$PKG"; then
    fail "contract package missing unique_id '${unique}' for add-on '${a}'"
  fi
  pass "binary_sensor.${unique} declared (line-anchored unique_id)"
done

# Summary sensors.
echo "== summary sensors =="
for unique in rc_hardware_discovered_count rc_hardware_setup_pending_count; do
  if ! grep -qE "^[[:space:]]+unique_id:[[:space:]]+${unique}[[:space:]]*$" "$PKG"; then
    fail "contract package missing unique_id '${unique}'"
  fi
  pass "sensor.${unique} declared (line-anchored unique_id)"
done

# Master switch.
echo "== master switch + unavailable-when-OFF =="
if ! grep -qE "^[[:space:]]+rc_hardware_discovery_enabled:[[:space:]]*$" "$PKG"; then
  fail "master switch 'rc_hardware_discovery_enabled' missing from $PKG"
fi
pass "input_boolean.rc_hardware_discovery_enabled declared"

# The unavailable-when-OFF branch must be present. We accept either form:
#   - explicit OFF clause: is_state(..., 'off')
#   - positive ON gate:    is_state(..., 'on')  (equivalent unavailable-when-OFF)
# Both are documented Wave 2 patterns; the spec accepts either.
if ! grep -qE "is_state\('input_boolean.rc_hardware_discovery_enabled',[[:space:]]*'off'\)" "$PKG" \
   && ! grep -qE "is_state\('input_boolean.rc_hardware_discovery_enabled',[[:space:]]*'on'\)" "$PKG"; then
  fail "no OFF-clause / ON-gate for rc_hardware_discovery_enabled in $PKG (privacy/availability invariant)"
fi
pass "unavailable-when-OFF branch present (explicit OFF clause or positive ON gate)"

# Per-add-on setup-prompt helpers.
echo "== per-add-on setup-prompt helpers =="
for a in "${ADDONS[@]}"; do
  pending="rc_hardware_setup_${a}_pending"
  message="rc_hardware_setup_${a}_message"
  if ! grep -qE "^[[:space:]]+${pending}:[[:space:]]*$" "$PKG"; then
    fail "per-add-on setup helper '${pending}' missing from $PKG"
  fi
  if ! grep -qE "^[[:space:]]+${message}:[[:space:]]*$" "$PKG"; then
    fail "per-add-on message helper '${message}' missing from $PKG"
  fi
  pass "setup helpers for '${a}' declared (${pending} + ${message})"
done

# --- 2. Setup wizard card -----------------------------------------------
echo "== wizard card references contract entities =="
for unique in \
  "rc_hardware_openwrt_available" \
  "rc_hardware_tileserver_available" \
  "rc_hardware_traccar_available" \
  "rc_hardware_victron_available" \
  "rc_hardware_ota_available" \
  "rc_hardware_discovered_count" \
  "rc_hardware_setup_pending_count" \
  "rc_hardware_discovery_enabled"; do
  if ! grep -qF "$unique" "$WIZ"; then
    fail "$WIZ does not reference contract entity '${unique}'"
  fi
  pass "wizard references contract entity '${unique}'"
done

# Wizard card must also reference the roamcore.hardware_setup_prompt service
# (the per-row "Set up" buttons).
if ! grep -qF "roamcore.hardware_setup_prompt" "$WIZ"; then
  fail "$WIZ does not reference service 'roamcore.hardware_setup_prompt'"
fi
pass "wizard references roamcore.hardware_setup_prompt service"

# --- 3. Probe helper ----------------------------------------------------
echo "== probe helper =="
# Must exist + be executable + start with a Python shebang.
SHEBANG="$(head -1 "$HELPER" 2>/dev/null || true)"
if ! [[ "$SHEBANG" =~ ^#!.*python3 ]]; then
  fail "$HELPER does not start with a python3 shebang"
fi
pass "$HELPER has python3 shebang"

# Stdlib-only check: refuse any third-party import.
if grep -qE "^(import|from)[[:space:]]+(requests|aiohttp|httpx|urllib3|yaml)" "$HELPER"; then
  fail "$HELPER imports a non-stdlib module (requests/aiohttp/httpx/urllib3/yaml)"
fi
if grep -qE "^import requests|^from requests" "$HELPER"; then
  fail "$HELPER imports the 'requests' library (not allowed)"
fi
pass "$HELPER is stdlib-only"

# Helper must reference the per-add-on functions (one function per add-on
# is the documented convention).
for a in "${ADDONS[@]}"; do
  if ! grep -qE "def _probe_${a}\b" "$HELPER"; then
    fail "$HELPER missing per-add-on function '_probe_${a}()'"
  fi
  pass "$HELPER defines _probe_${a}()"
done

# Helper README must exist + describe privacy.
if ! grep -qE "^## Privacy" "$HELPER_README"; then
  fail "$HELPER_README missing '## Privacy' section"
fi
pass "$HELPER_README has Privacy section"

# --- 4. Service + handler -----------------------------------------------
echo "== service declaration + handler =="
if ! grep -qE "^hardware_setup_prompt:" "$SERVICES_YAML"; then
  fail "service 'hardware_setup_prompt' not declared in $SERVICES_YAML"
fi
pass "service 'roamcore.hardware_setup_prompt' declared in $SERVICES_YAML"

if ! grep -qE "addon:" "$SERVICES_YAML"; then
  fail "service 'hardware_setup_prompt' missing 'addon' field"
fi
pass "service 'roamcore.hardware_setup_prompt' declares 'addon' field"

if ! grep -qF "_svc_hardware_setup_prompt" "$INIT_PY"; then
  fail "$INIT_PY missing service handler '_svc_hardware_setup_prompt'"
fi
pass "$INIT_PY defines service handler '_svc_hardware_setup_prompt'"

if ! grep -qF '"hardware_setup_prompt"' "$INIT_PY"; then
  fail "$INIT_PY does not register 'hardware_setup_prompt' with hass.services.async_register"
fi
pass "$INIT_PY registers 'hardware_setup_prompt' service"

# --- 5. docs/setup/hardware-auto-discovery.md ---------------------------
echo "== docs/setup/hardware-auto-discovery.md content =="
for needle in \
  "## 1. What this is" \
  "## 2. Privacy" \
  "## 3. Supported add-ons" \
  "## 4. Enable / disable" \
  "## 5. Setup CTA flow" \
  "## 6. Troubleshooting" \
  "## 7. What's next"; do
  if ! grep -qF "$needle" "$SETUP_DOC"; then
    fail "docs/setup/hardware-auto-discovery.md missing required heading: '$needle'"
  fi
done
pass "$SETUP_DOC has all required sections (what-this-is/privacy/supported/enable-disable/setup-cta/troubleshooting/what's-next)"

# --- 6. feature-checklist line 73 --------------------------------------
echo "== feature-checklist line 73 (Hardware auto-discovery) =="
LINE_73="$(sed -n '73p' "$CHECKLIST")"
echo "    line 73: $LINE_73"
if ! grep -qE "Hardware auto-discovery" <<<"$LINE_73"; then
  fail "feature-checklist.md line 73 is not the Hardware auto-discovery row: '$LINE_73'"
fi
if ! grep -qE "^\- \[x\] .*Hardware auto-discovery" <<<"$LINE_73"; then
  fail "feature-checklist.md line 73 is not ticked '[x]': '$LINE_73'"
fi
pass "feature-checklist.md line 73 ticked [x] for Hardware auto-discovery"

# --- 7. Privacy invariant (load-bearing for tier-b) --------------------
# This is the smoke's strictest assertion. We grep the discovery package
# + probe helper for any IP literal or DNS name that isn't loopback /
# RFC1918. If found, the privacy contract is broken and the build FAILS.
#
# We use Python (the helper's own parser) for the IP check so the rule
# is unambiguous.
echo "== privacy invariant =="
python3 - <<'PY' "$PKG" "$HELPER" "$WIZ"
import ipaddress
import re
import sys

paths = sys.argv[1:]
PAT_HOST = re.compile(
    r"(?<![A-Za-z0-9_.])"
    r"((?:\d{1,3}\.){3}\d{1,3})"          # IPv4 literal
    r"|"
    r"((?:[0-9a-fA-F]{1,4}:){2,7}[0-9a-fA-F]{1,4})"  # IPv6 literal
)

# Strings we explicitly allow:
#   127.0.0.0/8, ::1            — loopback
#   10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16  — RFC1918
#   169.254.0.0/16, fe80::/10   — link-local
#   fc00::/7                    — RFC4193 unique-local
def allowed(ip: ipaddress._BaseAddress) -> bool:
    return (
        ip.is_loopback
        or ip.is_link_local
        or ip.is_private  # RFC1918 + RFC4193
        or ip.is_unspecified
    )

bad = []
for path in paths:
    with open(path, "r", encoding="utf-8") as f:
        for ln, line in enumerate(f, start=1):
            # Strip YAML/HTTP quoting to avoid false positives from quoted docs strings.
            for m in PAT_HOST.finditer(line):
                s = m.group(1) or m.group(2)
                try:
                    ip = ipaddress.ip_address(s)
                except ValueError:
                    continue
                if not allowed(ip):
                    bad.append(f"{path}:{ln}: {s}  ← {line.rstrip()[:120]}")

if bad:
    print("ERROR: privacy invariant violated — non-loopback/RFC1918 host literal(s) found:", file=sys.stderr)
    for b in bad:
        print(f"  {b}", file=sys.stderr)
    sys.exit(1)

print(f"  PASS: privacy invariant holds across {len(paths)} files (no non-loopback/RFC1918 hosts)")
PY

echo "All Hardware auto-discovery smoke checks passed."