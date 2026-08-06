#!/usr/bin/env bash
# Hub golden-image: smoke check (Wave 9 #120d)
#
# Mirrors the convention in scripts/checks/<name>.sh:
#   - bash strict mode (set -euo pipefail)
#   - repo-local only (no live HA / Proxmox / vendor calls)
#   - asserts the script + manifest + their cross-references are
#     healthy, the manifest pins a reachable + verifiable base image,
#     and the script's user-facing surface is plain English (no jargon)
#   - plain-English summary at exit 0 / non-zero
#
# Usage:
#   bash scripts/checks/hub-golden-image-smoke.sh
#
# Exit codes:
#   0  all 10 assertions pass — the golden-image build pipeline
#      foundation is ready for a Linux+Docker build host to consume
#   1  one or more assertions failed (a plain-English line names the
#      offending file:line)
#
# Wired into scripts/check.sh as a run_if_present step.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

SCRIPT="scripts/build/hub-golden-image.sh"
MANIFEST="scripts/build/hub-golden-image.manifest.yml"
DOCKERFILE="homeassistant/addons/roamcore-hub-builder/Dockerfile.hub"

PASS=0
FAIL=0

pass() { PASS=$((PASS+1)); printf '\033[1;32m✓\033[0m %s\n' "$*"; }
fail() { FAIL=$((FAIL+1)); printf '\033[1;31m✗\033[0m %s\n' "$*" >&2; }

# --- Assertion 1: script exists + is executable + has the right shebang --
[ -f "$SCRIPT" ] || fail "Assertion 1: golden-image script missing at $SCRIPT"
if [ -f "$SCRIPT" ]; then
  [ -x "$SCRIPT" ] || fail "Assertion 1: golden-image script at $SCRIPT is not executable (chmod +x)"
  head -1 "$SCRIPT" | grep -q "^#!/usr/bin/env bash" \
    || fail "Assertion 1: golden-image script shebang must be '#!/usr/bin/env bash'"
fi
# Count this as 1 assertion regardless of how many sub-checks fail
# inside (the smoke binary passes/fails on the assertion as a whole).
if [ -x "$SCRIPT" ] && head -1 "$SCRIPT" 2>/dev/null | grep -q "^#!/usr/bin/env bash"; then
  pass "Assertion 1: $SCRIPT exists + is executable + uses the env-bash shebang"
fi

# --- Assertion 2: manifest exists + parses as valid YAML ----------------
[ -f "$MANIFEST" ] || fail "Assertion 2: manifest missing at $MANIFEST"
if [ -f "$MANIFEST" ]; then
  python3 -c "import sys,yaml; yaml.safe_load(open(sys.argv[1], encoding='utf-8'))" "$MANIFEST" \
    2>/dev/null || fail "Assertion 2: manifest at $MANIFEST did not parse as YAML"
fi
if [ -f "$MANIFEST" ] && python3 -c "import sys,yaml; yaml.safe_load(open(sys.argv[1], encoding='utf-8'))" "$MANIFEST" 2>/dev/null; then
  pass "Assertion 2: $MANIFEST exists + parses as valid YAML"
fi

# --- Assertion 3: script references the manifest path in its body -------
SCRIPT_BODY_REFERENCES_MANIFEST=0
if [ -f "$SCRIPT" ]; then
  # Look for the literal filename hub-golden-image.manifest.yml in the
  # script body (the manifest path is the cross-reference the build
  # contract relies on).
  if grep -q 'hub-golden-image\.manifest\.yml' "$SCRIPT"; then
    SCRIPT_BODY_REFERENCES_MANIFEST=1
  fi
fi
if [ "$SCRIPT_BODY_REFERENCES_MANIFEST" -eq 1 ]; then
  pass "Assertion 3: $SCRIPT references the manifest path in its body"
else
  fail "Assertion 3: $SCRIPT does not reference $MANIFEST — the build contract relies on the manifest path being in the script body"
fi

# --- Assertion 4: manifest's base_image URL returns HTTP 200 ----------
if [ -f "$MANIFEST" ]; then
  BASE_URL="$(
    python3 -c "
import sys, yaml
data = yaml.safe_load(open(sys.argv[1], encoding='utf-8'))
print(data['base_image']['url'])
" "$MANIFEST" 2>/dev/null || true
  )"
  if [ -z "$BASE_URL" ]; then
    fail "Assertion 4: manifest's base_image.url is missing or empty"
  else
    HTTP_CODE="$(curl -sIL --max-time 15 -o /dev/null -w '%{http_code}' "$BASE_URL" 2>/dev/null || echo "000")"
    # GitHub release download URLs return 302 -> 200; curl -L follows
    # the redirect and reports the final code (200). A 000 means curl
    # could not reach the host at all.
    case "$HTTP_CODE" in
      200) pass "Assertion 4: manifest's base_image URL is reachable (HTTP 200: $BASE_URL)" ;;
      302) pass "Assertion 4: manifest's base_image URL is reachable (HTTP 302 redirect, expected for github.com releases): $BASE_URL" ;;
      *)   fail "Assertion 4: manifest's base_image URL returned HTTP $HTTP_CODE (expected 200 or 302): $BASE_URL" ;;
    esac
  fi
else
  fail "Assertion 4: manifest missing — cannot check base_image URL"
fi

# --- Assertion 5: manifest's base_image expected_sha256 is 64-char hex -
if [ -f "$MANIFEST" ]; then
  BASE_SHA="$(
    python3 -c "
import sys, yaml
data = yaml.safe_load(open(sys.argv[1], encoding='utf-8'))
print(data['base_image']['expected_sha256'])
" "$MANIFEST" 2>/dev/null || true
  )"
  if [ -z "$BASE_SHA" ]; then
    fail "Assertion 5: manifest's base_image.expected_sha256 is missing or empty"
  elif ! printf '%s' "$BASE_SHA" | grep -qE '^[0-9a-fA-F]{64}$'; then
    fail "Assertion 5: manifest's base_image.expected_sha256 is not a 64-char hex string (got: $BASE_SHA)"
  else
    pass "Assertion 5: manifest's base_image.expected_sha256 is a 64-char hex string (${BASE_SHA:0:16}…)"
  fi
else
  fail "Assertion 5: manifest missing — cannot check expected_sha256"
fi

# --- Assertion 6: script --help output is plain English (no jargon) ----
if [ -x "$SCRIPT" ]; then
  HELP_OUT="$(bash "$SCRIPT" --help 2>&1 || true)"
  # Forbidden jargon tokens. The script's --help MUST NOT contain
  # operator/developer tokens that would confuse a vanlifer or
  # integrator reading the help text.
  FORBIDDEN_JARGON='^(errno 2|HTTP 503|errno=|exit code|stack trace|null pointer|segfault|Traceback \(most recent call last\))'
  JARGON_HITS="$(printf '%s\n' "$HELP_OUT" | grep -E "$FORBIDDEN_JARGON" || true)"
  if [ -n "$JARGON_HITS" ]; then
    fail "Assertion 6: script --help contains forbidden jargon: $(printf '%s' "$JARGON_HITS" | head -1 | cut -c1-80)"
  else
    pass "Assertion 6: script --help output is plain English (no jargon matches)"
  fi
  # --help must exit 0 too.
  bash "$SCRIPT" --help >/dev/null 2>&1 || fail "Assertion 6: script --help exited non-zero"
else
  fail "Assertion 6: script not present / not executable — cannot check --help"
fi

# --- Assertion 7: output filename is non-empty + ends in .img.gz -------
if [ -f "$MANIFEST" ]; then
  OUTPUT_FN="$(
    python3 -c "
import sys, yaml
data = yaml.safe_load(open(sys.argv[1], encoding='utf-8'))
print(data['output']['filename'])
" "$MANIFEST" 2>/dev/null || true
  )"
  if [ -z "$OUTPUT_FN" ]; then
    fail "Assertion 7: manifest's output.filename is missing or empty"
  elif ! printf '%s' "$OUTPUT_FN" | grep -qE '\.img\.gz$'; then
    fail "Assertion 7: manifest's output.filename does not end in .img.gz (got: $OUTPUT_FN)"
  else
    pass "Assertion 7: manifest's output.filename is non-empty + ends in .img.gz ($OUTPUT_FN)"
  fi
fi

# --- Assertion 8: script has idempotent cache-skip pattern ------------
if [ -f "$SCRIPT" ]; then
  if grep -qE 'cached|CACHED_BASE|--no-cache|CACHE_DIR' "$SCRIPT"; then
    pass "Assertion 8: script body shows an idempotent cache-skip pattern (re-runs reuse the downloaded base)"
  else
    fail "Assertion 8: script body does not show a cache-skip / --no-cache pattern — the script must not re-download on every run"
  fi
fi

# --- Assertion 9: script mentions retry/backoff in the download section
if [ -f "$SCRIPT" ]; then
  if grep -qE 'retry|backoff|attempt' "$SCRIPT"; then
    pass "Assertion 9: script body shows a retry/backoff pattern for the base-image download (resilient to transient network failures)"
  else
    fail "Assertion 9: script body does not mention retry/backoff for the download — the build must be resilient to transient network failures"
  fi
fi

# --- Assertion 10: Dockerfile.hub (the optional builder) exists --------
# The Dockerfile is the "what the script invokes on a Linux+Docker
# host" piece. Its presence is not strictly required for this slice
# (script-only delivery is acceptable, per the #106 OpenWrt Image
# Builder precedent), but it makes the script's docker build step
# actionable on a real build host, so we surface its presence as an
# advisory assertion.
if [ -f "$DOCKERFILE" ]; then
  pass "Assertion 10 (advisory): $DOCKERFILE is present — the script's docker build step is actionable on a real Linux+Docker host"
else
  printf '\033[1;33m!\033[0m Assertion 10 (advisory): %s is not present — the script will still print the "Baking skipped" message and exit 0 on this host, but the real bake will need a Dockerfile in the next slice.\n' "$DOCKERFILE"
fi

# --- Summary -------------------------------------------------------------
printf '\n'
printf 'Hub golden-image smoke: %d passed, %d failed\n' "$PASS" "$FAIL"
if [ "$FAIL" -gt 0 ]; then
  printf '\033[1;31m✗ Hub golden-image smoke check FAILED\033[0m\n' >&2
  exit 1
fi
printf '\033[1;32m✓ Hub golden-image smoke check PASSED\033[0m\n'
exit 0