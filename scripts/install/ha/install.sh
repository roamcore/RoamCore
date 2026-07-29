#!/usr/bin/env bash
set -euo pipefail

# Back-compat wrapper.
#
# The canonical HAOS installer lives at:
#   https://raw.githubusercontent.com/roamcore/RoamCore/main/homeassistant/install.sh
#
# This wrapper keeps older docs/links working.

# When invoked as a CLI (no stdin from a pipe), accept flags so we can
# optionally configure the Traccar integration alongside the base install.
#
# Flags (all optional, matching the existing pattern of opt-in tooling):
#   --with-traccar   Print the Traccar Server integration setup steps after
#                    the base install + soft-verify the integration is
#                    present (best-effort, no failure if `ha` is missing
#                    or the integration is not yet added).
#   -h, --help       Show usage.
#
# Default behaviour (no flags) is unchanged — the canonical install runs
# and this wrapper exits. This preserves back-compat with any doc that
# pipes us in via curl | sh.

usage() {
    cat <<'USAGE'
Usage: install.sh [--with-traccar]

  --with-traccar   After the canonical install, print the HA Traccar
                   Server integration setup steps and best-effort check
                   that the integration is registered. See
                   docs/setup/traccar.md §"Step 1: Configure the Home
                   Assistant Traccar integration".

No flags (default): runs the canonical RoamCore installer and exits.
Back-compat with curl ... | sh is preserved.

Environment variables honoured by the canonical installer:
  ROAMCORE_REF, ROAMCORE_REPO, CONFIG_DIR  (see homeassistant/install.sh)
USAGE
}

WITH_TRACCAR=0
for arg in "$@"; do
    case "$arg" in
        --with-traccar) WITH_TRACCAR=1 ;;
        -h|--help) usage; exit 0 ;;
        --) shift; break ;;
        *) ;; # ignore unknown flags (defensive — curl|sh path)
    esac
done

# 1. Always run the canonical installer (unchanged behaviour).
if command -v curl >/dev/null 2>&1; then
  curl -fsSL https://raw.githubusercontent.com/roamcore/RoamCore/main/homeassistant/install.sh | sh
elif command -v wget >/dev/null 2>&1; then
  wget -qO- https://raw.githubusercontent.com/roamcore/RoamCore/main/homeassistant/install.sh | sh
else
  echo "ERROR: need curl or wget" >&2
  exit 1
fi

# 2. Optional Traccar Server integration setup (off by default).
install_traccar_integration() {
    echo
    echo "== RoamCore: Traccar Server integration =="
    echo
    echo "The HA Traccar Server integration is added via the UI. The"
    echo "RoamCore packages ship the auto-fill automation that wires"
    echo "input_text.rc_location_tracker_entity to the first"
    echo "device_tracker.traccar_* entity on first boot."
    echo
    echo "Manual steps (also in docs/setup/traccar.md §Step 1):"
    echo "  1. Home Assistant \u2192 Settings \u2192 Devices & services"
    echo "  2. Add Integration \u2192 Traccar Server"
    echo "  3. Base URL  : http://homeassistant.local:8082 (official add-on)"
    echo "              : or the RoamCore proxy add-on ingress URL"
    echo "  4. Username  : a Traccar user (admin works for fresh installs)"
    echo "  5. Password  : from /config/secrets.yaml:"
    echo "                 roamcore_traccar_admin_password"
    echo "  6. After submit, expect device_tracker.traccar_<name> entities"
    echo "  7. input_text.rc_location_tracker_entity is auto-filled."
    echo
    echo "== Verifying integration status =="
    # Best-effort check: print whether the integration appears in HA's
    # integration list. This is soft: many HAOS installs do not have the
    # `ha` CLI available locally (the install script runs on a generic
    # host), so a missing/unknown command is a warning, not a failure.
    if command -v ha >/dev/null 2>&1; then
        if ha integrations list 2>/dev/null | grep -qi 'traccar'; then
            echo "  \u2713 traccar server integration detected"
        else
            echo "  ! traccar server integration NOT detected yet"
            echo "    (expected on a fresh install — complete the UI steps above)"
        fi
    else
        echo "  - 'ha' CLI not on PATH; skipping live check"
        echo "    (re-run with --with-traccar on the HAOS host to verify)"
    fi
    echo
    echo "Next: open \u2192  http://<home-assistant>:8123/config/integrations"
    echo
}

if [ "$WITH_TRACCAR" = "1" ]; then
    install_traccar_integration
fi
