# RoamCore Gamification — headless CLI helpers

Local-only. Stdlib-only. No HTTP. No third-party imports.

This directory ships the headless CLI mirrors of the
`roamcore.gamification_*` custom-component service surface. The CLI is
used by `scripts/checks/gamification-smoke.sh` to validate the
trophy-state model without a running Home Assistant instance.

## Contents

- `trophy_state.py` — render a snapshot JSON describing the 7 relevant
  RoamCore entities into a `{enabled, count, last_award_at, last_award_trophy, trophies[]}`
  report. Pure stdlib (`argparse`, `json`, `sys`). No HTTP, no third-party
  imports, no telemetry.

## Usage

```bash
# Print help.
python3 homeassistant/tools/gamification/trophy_state.py --help

# Emit a default snapshot where the kill-switch is OFF and every trophy
# is untriggered + unseen. Used by the smoke check.
python3 homeassistant/tools/gamification/trophy_state.py --dry-run

# Render a JSON snapshot from a file.
python3 homeassistant/tools/gamification/trophy_state.py --input /tmp/snap.json

# Render a JSON snapshot from stdin.
echo '{"enabled": true, "trophies": {"first_trip_wrapped": {"triggered": true, "seen": false}}}' \
  | python3 homeassistant/tools/gamification/trophy_state.py
```

## Privacy

- Stdlib only. No `requests`, no `urllib.request.urlopen`, no `httpx`, no
  `aiohttp`, no third-party imports.
- No outbound network calls.
- No telemetry. No external CDN.

The privacy invariant is enforced in CI by
`scripts/checks/gamification-smoke.sh`.

## Trophy taxonomy

The 7 starter trophies are deliberately boring — each one composes over
an already-shipping RoamCore signal. See
`docs/setup/gamification.md#trophy-taxonomy` for the full list.