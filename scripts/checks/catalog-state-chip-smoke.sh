#!/usr/bin/env bash
# RoamCore catalog-state-chip smoke check (Wave 9 #118).
#
# Validates that the connection-state chip primitive + Connect button
# helper are wired together correctly. Three checks:
#
#   1. Every `.rc-state-<kebab-case>` CSS class referenced by the
#      helper exists in docs/styles/rc.css. Drift (helper emits a
#      new state but the CSS isn't extended) would render an
#      unstyled chip on the catalog — the user sees a default gray
#      blob with no semantic meaning.
#   2. The pytest suite for the helper exits 0. The pytest file
#      already asserts the kebab-class emission + tier vocabulary +
#      Connect-button href; running it here keeps the smoke check
#      chain self-contained.
#   3. All known `state:` values in
#      `connections/*/connection.yml` have a matching CSS class.
#      Today only "Ready to connect" / "Connected" / "Available"
#      are present in the manifests; the other 7 states are reserved
#      for future connections but the CSS MUST be ready for them.
#
# Idempotent: safe to run repeatedly. No live HA / Proxmox / network.
#
# Wired into scripts/check.sh as part of the Wave 9 #118 smoke chain.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

fail() { echo "ERROR: $*" >&2; exit 1; }
banner() { printf '\033[1;36m▶ %s\033[0m\n' "$1"; }

# --- Check 1: every kebab-case CSS class is present in rc.css -------
banner "Catalog state chip: 10 kebab-case CSS classes present in docs/styles/rc.css"
CSS_FILE="$ROOT_DIR/docs/styles/rc.css"
[ -f "$CSS_FILE" ] || fail "missing $CSS_FILE"

REQUIRED_CLASSES=(
  ".rc-state-chip"
  ".rc-state-chip.available"
  ".rc-state-chip.detected"
  ".rc-state-chip.ready-to-connect"
  ".rc-state-chip.connecting"
  ".rc-state-chip.connected"
  ".rc-state-chip.needs-information"
  ".rc-state-chip.needs-attention"
  ".rc-state-chip.unsupported"
  ".rc-state-chip.offline"
  ".rc-state-chip.update-available"
  ".rc-state-chip-reason"
  ".rc-connect-button"
)
for cls in "${REQUIRED_CLASSES[@]}"; do
  if ! grep -qF "$cls" "$CSS_FILE"; then
    fail "docs/styles/rc.css is missing required chip CSS class: $cls"
  fi
done
echo "OK: all 13 required chip CSS classes present in rc.css"

# --- Check 2: pytest suite for the helper exits 0 --------------------
banner "Catalog state chip: pytest test_connection_card.py exits 0"
python3 -m pytest homeassistant/packages/tests/test_connection_card.py -v \
  || fail "pytest homeassistant/packages/tests/test_connection_card.py failed"

# --- Check 3: every state in connection.yml has a matching CSS class --
banner "Catalog state chip: every connection.yml state has a matching chip CSS class"
python3 - <<'PYEOF' || fail "state->CSS class mapping drift check failed"
from __future__ import annotations
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
import importlib.util
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import connection_card  # noqa: E402

css_path = REPO_ROOT / "docs" / "styles" / "rc.css"
css_text = css_path.read_text(encoding="utf-8")

# Build the set of valid kebab-case CSS class fragments we expect to
# see in rc.css for each of the 10 standard states.
state_kebab = list(connection_card._STATE_KEBAB.values())  # type: ignore[attr-defined]
missing_css = []
for kebab in state_kebab:
    expected_class = f".rc-state-chip.{kebab}"
    if expected_class not in css_text:
        missing_css.append(expected_class)
if missing_css:
    print(f"FAIL: rc.css missing kebab classes for states: {missing_css!r}",
          file=sys.stderr)
    sys.exit(1)

# Now scan every connection manifest for its declared `state:` value
# and assert each one is in the 10 standard set.
connections_dir = REPO_ROOT / "connections"
import yaml  # type: ignore
state_pattern = re.compile(r"^state:\s*(.*?)\s*$", re.MULTILINE)

unrecognized = []
for manifest_path in sorted(connections_dir.glob("*/connection.yml")):
    if manifest_path.parent.name.startswith("_"):
        continue
    text = manifest_path.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        print(f"FAIL: YAML parse error in {manifest_path}: {exc}",
              file=sys.stderr)
        sys.exit(1)
    if not isinstance(data, dict):
        continue
    state = data.get("state")
    if state is None:
        # Surfaced by the sister test_connection_state.py test;
        # we skip here to keep the focus on chip-class mapping.
        continue
    if state not in connection_card.STANDARD_STATES:
        unrecognized.append((manifest_path.parent.name, state))

if unrecognized:
    print(
        f"FAIL: {len(unrecognized)} connection manifests declare an "
        f"unrecognized state: {unrecognized!r}. The 10 standard "
        f"states are: {list(connection_card.STANDARD_STATES)!r}.",
        file=sys.stderr,
    )
    sys.exit(1)

print(
    f"OK: all {len(state_kebab)} standard-state kebab classes "
    f"present in rc.css; all connection manifests use one of the "
    f"10 standard states"
)
PYEOF

echo "OK: catalog-state-chip smoke check passed"