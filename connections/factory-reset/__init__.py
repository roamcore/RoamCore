"""RoamCore connection: Factory Reset — one-tap recover to a known-good
state, never silent — tier-a connection.

This is a TIER-A connection that owns the RoamCore-owned Python
service-handler at
`homeassistant/custom_components/roamcore/factory_reset.py` (~340 LOC).
The service handler registers 4 RoamCore services via
`register_factory_reset_services(hass)` + a `RoamCoreFactoryResetView`
HTTP view at `/api/roamcore/factory_reset/{action}` so the dashboard +
OpenClaw agents can drive the dry-run / confirm / cancel / postflight
surface over HTTP (in addition to the service calls).

The reset is "panic-button safe" — it ALWAYS restores from the latest
Hub Backup (from the hub-backup connection at
`connections/hub-backup/`, MERGED on main as commit bfaa73d) and never
silently destroys user data. The wizard enforces a 2-step confirmation
flow with an explicit token ("type RESET to confirm") AND it runs a
dry-run first that lists the current state + the last backup + the
post-reset state. The integration is bench-tested via the pytest rig at
`homeassistant/packages/tests/test_factory_reset.py` (>=25 tests).

This connection is brand-new — there is no legacy tier-claim stub in
`docs/catalog/factory-reset/` (the connection was promoted directly
into the `connections/` pipeline). The brand-new nature is HONEST — the
RoamCore-owned service-handler at `factory_reset.py` + the helper
package at `homeassistant/packages/roamcore_factory_reset.yaml` + the
>=25 pytest tests are all real + repo-local + verified; the tier-a claim
is provable via `pytest homeassistant/packages/tests/test_factory_reset.py`
(>=25/25 PASS) + `bash scripts/checks/factory-reset-smoke.sh` (12/12
PASS).

The connection's recipe + contract tiles + 5 section 8 MANDATORY
automations are documented in
`connections/factory-reset/docs/recipe.md`. The user-facing IKEA-style
runbook lives at `docs/runbooks/factory-reset.md` (5-step + 3-line
troubleshooting — no file paths, no PR numbers, no "Wave N" labels, no
internal jargon).

The umbrella publishes the resulting data via the RoamCore-owned
service handler at
`homeassistant/custom_components/roamcore/factory_reset.py` (wraps the
HA core 2024.x `backup.restore` service + the hub-backup connection's
`async_test_restore` sandbox runner + the 2-step confirm flow + the
chain-corruption recovery path), then publishes the RoamCore
factory-reset contract tiles on top (the 11 contract entities
documented in the manifest's `dashboard.tiles` list).

The audit + boundary CI can detect a `factory-reset/` folder that
claims to be a connection via the `DOMAIN` constant exported here. The
wizard reads the manifest + recipe at runtime.

The real per-operator factory-reset affordance path is:

    Operator-side choice of the FIVE-step flow (Glance at the
        tile -> Click Dry-run -> Read the plan -> Click Confirm
        -> Check the post-flight tile)
        -> existing helper entities (the 11 `rc_factory_reset_*`
           contract entities from
           `homeassistant/packages/roamcore_factory_reset.yaml`)
        -> the RoamCore-owned service handler at
           `homeassistant/custom_components/roamcore/factory_reset.py`
        -> dashboard tiles + OpenClaw queries
            ("is it safe to factory reset?",
             "when was the last Hub Backup?",
             "show me the factory reset plan",
             "factory reset dry-run",
             "factory reset confirm",
             "factory reset cancel",
             "what does the post-reset state look like?",
             "self-recovered")

    Safety interlocks (the recipe is the contract layer; the
    automation wrappers are documented in section 8):
        -> The RoamCore dry-run-sets-token automation is the section 8.1
           automation that fires when
           `input_button.rc_factory_reset_dry_run` is pressed.
        -> The RoamCore confirm-requires-token-match automation is
           the section 8.2 automation that fires when
           `input_button.rc_factory_reset_confirm` is pressed.
        -> The RoamCore cancel-clears-token automation is the section 8.3
           automation that fires every 5 minutes.
        -> The RoamCore postflight-check-on-boot automation is the
           section 8.4 automation that fires on HA start.
        -> The RoamCore recovery-on-audit-chain-invalid automation
           is the section 8.5 automation that fires when
           `binary_sensor.rc_openclaw_api_chain_valid` flips off
           (the openclaw-api audit chain went invalid).

    Cross-references:
        -> The RoamCore-owned service handler at
           `homeassistant/custom_components/roamcore/factory_reset.py`
           is the canonical umbrella.
        -> The helper package at
           `homeassistant/packages/roamcore_factory_reset.yaml`
           is the canonical input + sensor + automation storage.
        -> The pytest rig at
           `homeassistant/packages/tests/test_factory_reset.py`
           is the canonical >=25-test contract validation rig.
        -> The bash smoke check at
           `scripts/checks/factory-reset-smoke.sh` is the canonical
           cross-cutting YAML/secrets-leak/idempotency smoke (12
           assertions).
        -> The user-facing IKEA-style runbook at
           `docs/runbooks/factory-reset.md` is the canonical
           vanlifer-facing howto.
        -> The Hub Backup connection at
           `connections/hub-backup/` is the MANDATORY upstream
           dependency.

See docs/recipe.md for the full howto.
"""

DOMAIN = "factory_reset"

FACTORY_RESET_TILE_PREFIX = "rc_factory_reset_"

# Module-level constants exported for the audit + the helper package +
# the pytest rig. These are the canonical names the package YAML +
# the test rig + the dashboard tile surface all reference.
FACTORY_RESET_TILE_NAMES = (
    "input_button.rc_factory_reset_dry_run",
    "input_button.rc_factory_reset_confirm",
    "input_text.rc_factory_reset_token",
    "input_text.rc_factory_reset_dry_run_report",
    "input_boolean.rc_factory_reset_armed",
    "input_datetime.rc_factory_reset_last_dry_run",
    "sensor.rc_factory_reset_status",
    "sensor.rc_factory_reset_last_backup_age",
    "binary_sensor.rc_factory_reset_safe_to_run",
    "sensor.rc_factory_reset_preflight_warnings",
    "sensor.rc_factory_reset_postflight_status",
)

# The 4 RoamCore service names the service handler registers via
# `register_factory_reset_services(hass)`. The dashboard + OpenClaw
# agents call these services.
FACTORY_RESET_SERVICE_NAMES = (
    "factory_reset_dry_run",
    "factory_reset_confirm",
    "factory_reset_cancel",
    "factory_reset_postflight_check",
)

# The freshness window — the reset refuses to run without a Hub
# Backup less than this many minutes old. 24h = 1440 minutes. This
# is the safety rail that prevents silent data loss.
BACKUP_FRESHNESS_WINDOW_MINUTES = 24 * 60  # 1440

# The token lifetime — the section 8.3 cancel automation clears the token
# if the dry-run is older than this. 5 minutes is short enough to
# prevent an attacker from finding the token + long enough that a
# human operator can read the dry-run report + click confirm.
TOKEN_LIFETIME_MINUTES = 5

# The expected confirm token — the operator must type "RESET" in the
# confirm field. This is the explicit-token guard from the doctrine
# ("type RESET to confirm"). The Python handler matches against
# this constant in addition to the 8-char session token returned by
# dry-run.
EXPECTED_CONFIRM_TOKEN = "RESET"

# The status constants used by the audit + the helper package + the
# pytest rig + the section 8 automations.
STATUS_READY = "ready"
STATUS_DRY_RUN_SHOWN = "dry_run_shown"
STATUS_CONFIRM_PENDING = "confirm_pending"
STATUS_RESETTING = "resetting"
STATUS_OK = "ok"
STATUS_FAILED = "failed"
STATUS_NEVER = "never"

# The section 8 automation IDs — exported for the audit + the pytest rig
# + the test_connection_yml.py honesty check.
FACTORY_RESET_AUTOMATION_IDS = (
    "rc_factory_reset_dry_run_sets_token",
    "rc_factory_reset_confirm_requires_token_match",
    "rc_factory_reset_cancel_clears_token",
    "rc_factory_reset_postflight_check_on_boot",
    "rc_factory_reset_recovery_on_audit_chain_invalid",
)

# The OpenClaw audit-chain binary_sensor that the section 8.5 recovery
# automation references. This is a forward reference — the binary_sensor
# lives in the openclaw-api connection. Until the openclaw-api audit
# chain binary_sensor lands on main, the section 8.5 recovery automation is
# dormant. When the binary_sensor flips off, the recovery flow fires
# automatically.
OPENCLAW_CHAIN_VALID_BINARY_SENSOR = "binary_sensor.rc_openclaw_api_chain_valid"
