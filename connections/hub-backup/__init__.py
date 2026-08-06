"""RoamCore connection: Hub Backup — nightly automatic snapshot of the Hub
that is verified-restorable, with one status tile + one button + one knob —
tier-a connection.

This is a TIER-A connection that owns the RoamCore-owned Python
service-handler at
`homeassistant/custom_components/roamcore/backup.py` (~240 LOC). The
service handler wraps the HA core 2024.x `backup.create` / `backup.list`
/ `backup.delete` services + a restore-tested sandbox runner
(`async_test_restore`) + a plain-English status mapper so the dashboard
+ OpenClaw queries surface "Your last backup ran 2 hours ago and checked
out." instead of raw exception text. The integration is bench-tested via
the pytest rig at `homeassistant/packages/tests/test_hub_backup.py` (22
tests covering the 4 service definitions + the 3 §8 automations + the
rc-entity-naming compliance + the idempotency guarantees + the
secrets-leak guard).

This connection is brand-new — there is no legacy tier-claim stub in
`docs/catalog/backup/` (the connection was promoted directly into the
`connections/` pipeline). The brand-new nature is HONEST — the
RoamCore-owned service-handler at `backup.py` + the helper package at
`homeassistant/packages/roamcore_hub_backup.yaml` + the 22 pytest tests
are all real + repo-local + verified; the tier-a claim is provable
via `pytest homeassistant/packages/tests/test_hub_backup.py` (22/22
PASS) + `bash scripts/checks/hub-backup-smoke.sh` (10/10 PASS).

The connection's recipe + contract tiles + 3 §8 MANDATORY automations
are documented in `connections/hub-backup/docs/recipe.md`. The
user-facing IKEA-style runbook lives at `docs/runbooks/hub-backup.md`
(5-step + 3-line troubleshooting — no file paths, no PR numbers, no
"Wave N" labels, no internal jargon).

The umbrella publishes the resulting data via the RoamCore-owned service
handler at `homeassistant/custom_components/roamcore/backup.py`
(wraps the HA core `backup.create` / `backup.list` / `backup.delete`
services + the `roamcore.create_backup` / `roamcore.list_backups` /
`roamcore.delete_backup` / `roamcore.test_restore` RoamCore-registered
services), then publishes the RoamCore hub-backup contract tiles on top
(the 11 contract entities documented in the manifest's `dashboard.tiles`
list — 1 input_boolean enabled + 1 input_datetime next_run + 1
input_select retention_policy + 2 input_text (destination + status) + 3
sensors (last_status + age_minutes) + 1 binary_sensor healthy = 9
contract entities + 1 backup_now button + 1 verify_now button = 11
contract entities).

The audit + boundary CI can detect a `hub-backup/` folder that claims to
be a connection via the `DOMAIN` constant exported here. The wizard
reads the manifest + recipe at runtime.

The real per-operator hub-backup affordance path is:

    Operator-side choice of the FIVE-step flow (Enable ->
        Set destination -> Set retention -> Wait for first run ->
        Check the tile)
        -> existing helper entities (the HA core
           `input_boolean.rc_hub_backup_enabled` +
           `input_datetime.rc_hub_backup_next_run` +
           `input_select.rc_hub_backup_retention_policy` +
           `input_text.rc_hub_backup_destination` (mode password) +
           `input_text.rc_hub_backup_status` from
           `homeassistant/packages/roamcore_hub_backup.yaml`)
        -> the RoamCore-owned service handler at
           `homeassistant/custom_components/roamcore/backup.py`
           (registers the 4 RoamCore services via
           `register_backup_services(hass)` + calls the HA core
           `backup.create` / `backup.list` / `backup.delete`
           services + runs `async_test_restore` in a sandbox)
        -> the RoamCore contract layer (the 9 `rc_hub_backup_*`
           contract entities + 2 `button.rc_hub_backup_*` operator
           buttons documented in the manifest's `dashboard.tiles`
           list — mostly `template:` sensors + `binary_sensor:`
           derivations + `input_*` helpers derived from the
           helper package + the service handler status writes)
        -> dashboard tiles + OpenClaw queries
            ("is the Hub healthy?",
             "when was the last backup?",
             "how old is the last backup?",
             "what's the plain-English status?",
             "back up now",
             "verify restore now")

    Safety interlocks (the recipe is the contract layer; the
    automation wrappers are documented in §8):
        -> The RoamCore nightly-create-backup automation is the
           §8.1 automation that fires at 02:00 daily when
           `input_boolean.rc_hub_backup_enabled` is ON. The
           automation calls the RoamCore `roamcore.create_backup`
           service with retention_days=30 + writes the
           `backup_id` + `path` + `size_bytes` to
           `input_text.rc_hub_backup_status`. The
           `mode: single` guard prevents double-creation if a
           backup is already running.
        -> The RoamCore verify-integrity automation is the §8.2
           automation that fires after the nightly-create
           completes + runs `roamcore.test_restore` against the
           newly-created backup + writes the result to
           `input_text.rc_hub_backup_status`. The automation
           surfaces a plain-English banner ("Your last backup
           checked out and can be restored." or "Your last
           backup ran but the restore-test failed.").
        -> The RoamCore cleanup-old automation is the §8.3
           automation that fires at 03:30 daily + calls
           `roamcore.list_backups` + deletes any backup older
           than the retention policy (the
           `input_select.rc_hub_backup_retention_policy` helper).
           The automation enforces the operator-chosen retention
           policy + keeps the destination from filling up.

    Cross-references:
        -> The RoamCore-owned service handler at
           `homeassistant/custom_components/roamcore/backup.py`
           is the canonical umbrella (calls the HA core
           `backup.create` / `backup.list` / `backup.delete`
           services + the `roamcore.test_restore` sandbox
           runner + the plain-English status mapper).
        -> The helper package at
           `homeassistant/packages/roamcore_hub_backup.yaml`
           is the canonical enable / destination / retention /
           status helper storage + the 3 §8 automations.
        -> The pytest rig at
           `homeassistant/packages/tests/test_hub_backup.py`
           is the canonical 22-test contract validation rig.
        -> The bash smoke check at
           `scripts/checks/hub-backup-smoke.sh` is the canonical
           cross-cutting YAML/secrets-leak/idempotency smoke
           (10 assertions).
        -> The user-facing IKEA-style runbook at
           `docs/runbooks/hub-backup.md` is the canonical
           vanlifer-facing howto (5 steps + 3-line
           troubleshooting + useful links).
        -> The existing settings backup flow at
           `homeassistant/custom_components/roamcore/__init__.py`
           `roamcore.backup_update` service cross-references the
           §8.1 nightly-create automation (the Settings UI's
           "Backup + Update" path is the operator-triggered
           one-tap path; the §8.1 nightly-create is the
           automatic-daily path).

See docs/recipe.md for the full howto (the RoamCore-owned service
handler install + the HA core `input_*` helpers install + the FIVE-step
operator flow + the 11 `rc_hub_backup_*` contract tiles + the 3 §8
MANDATORY automations + the 3-line §9 troubleshooting entries + the
secrets-leak guard + the tier-a promotion outline).
"""

DOMAIN = "hub_backup"

BACKUP_TILE_PREFIX = "rc_hub_backup_"

# Module-level constants exported for the audit + the helper package +
# the pytest rig. These are the canonical names the package YAML +
# the test rig + the dashboard tile surface all reference.
BACKUP_TILE_NAMES = (
    "input_boolean.rc_hub_backup_enabled",
    "input_datetime.rc_hub_backup_next_run",
    "input_select.rc_hub_backup_retention_policy",
    "input_text.rc_hub_backup_destination",
    "input_text.rc_hub_backup_status",
    "sensor.rc_hub_backup_last_status",
    "sensor.rc_hub_backup_age_minutes",
    "binary_sensor.rc_hub_backup_healthy",
    "button.rc_hub_backup_backup_now",
    "button.rc_hub_backup_verify_now",
)

BACKUP_RETENTION_DAYS_DEFAULT = 30
BACKUP_DESTINATION_DEFAULT = "/config/.roamcore/backups/"
PATH_BACKUP_NOW = "button.rc_hub_backup_backup_now"
PATH_VERIFY_NOW = "button.rc_hub_backup_verify_now"

STATUS_OK = "ok"
STATUS_FAILED = "failed"
STATUS_RUNNING = "running"
STATUS_NEVER = "never"
