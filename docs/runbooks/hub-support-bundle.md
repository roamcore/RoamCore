# How to send a support bundle from your Hub

This guide shows how to send a single file to support when something's wrong with your van setup, so you don't have to explain your whole setup over chat.

## §1 — What it does

When something stops working on the Hub, you can press one button and get a single file that captures what's going on inside the system, so you can send that file to the people who are helping you.

## §2 — What you see on screen

On the Hub dashboard you will see three things, all in the same panel:

- Two buttons stacked on top of each other:
  - **Send support bundle** (with zip) — makes one file you can email.
  - **Send support bundle (no zip)** — makes a folder you can copy, for systems that can't open zip files.
- Three readings underneath:
  - **Last export path** — where the file or folder was saved on the Hub.
  - **Last export at** — when you sent it (date and time).
  - **Status** — one of Idle, Export-Running, Exported, or Failed.

## §3 — What you do

1. Press the **Send support bundle** button (the one with the zip, unless your helper told you otherwise).
2. Wait a few seconds. The status will move through Export-Running and then settle on Exported.
3. When the status reads Exported, copy the file path shown under "Last export path" and send that file to the person helping you.

## §4 — What to do if it goes wrong

If the status reads Failed, tap the button again — and if it keeps failing, send a message in our community with the last error text shown on screen.

---

## §5 — For operators and developers (only)

This section is for the person maintaining the Hub itself, not for someone using it on the road.

### Where the wiring lives

The Hub-level wiring is a Home Assistant package file. The buttons, the three readings, and the three behind-the-scenes rules that move data between them are all declared in one file:

`homeassistant/packages/roamcore_support_bundle_hub.yaml`

### What the three rules do

The package declares three Home Assistant automations:

- `rc_support_bundle_hub_export_button_guard` — fires when either button is pressed. Sets the status reading to Export-Running, then calls the existing `roamcore.export_support_bundle` service with `zip: true` or `zip: false` depending on which button was pressed.
- `rc_support_bundle_hub_export_success` — fires when the service returns successfully. Writes the bundle path + the current timestamp into the two readings and sets the status to Exported.
- `rc_support_bundle_hub_export_failure` — fires when the service returns an error. Writes the error message into the last-error field and sets the status to Failed.

### How the buttons call the exporter

Both buttons use the standard Home Assistant input-button → automation → service-call pattern. The buttons themselves do not call the service directly — the automation does, after the button press is registered. This is the same pattern used elsewhere in the system.

### What calls the exporter underneath

The exporter that does the actual work is owned by RoamCore and ships as a Home Assistant custom component. It registers a service named `roamcore.export_support_bundle` that accepts a `zip:` data field. The Hub-level wiring calls that service; it does not implement the export itself.

### Tests and smoke check

- The pytest rig at `homeassistant/packages/tests/test_support_bundle_hub.py` (11 tests) checks the package file exists, parses cleanly, declares the right entities with the right names, wires the buttons to the service call, populates the success and failure readings correctly, and re-applies idempotently.
- The bash smoke at `scripts/checks/support-bundle-hub-smoke.sh` runs the pytest plus a YAML pre-check plus an rc-naming check. It is wired into `scripts/check.sh` so the full chain stays green.

### Adding the smoke to the chain

The new smoke is added to `scripts/check.sh` as a single `run_if_present` line between the existing agent-actions-allowlist entry and the connection-state-smoke entry.
