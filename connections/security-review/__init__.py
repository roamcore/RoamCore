"""RoamCore connection: Security Review — proactive plain-English audit
of SSH + firewall + access-code rotation, with one status tile + 3
buttons + the 4 §8 MANDATORY automations + 12 helper entities — tier-a
connection.

This is a TIER-A connection that owns the RoamCore-owned Python
service-handler at
`homeassistant/custom_components/roamcore/security.py` (883 LOC of
stdlib-only Python — 3 stdlib-only classes + the plain-English status
mapper + the 3 RoamCore service registrations). The service handler
exposes 3 RoamCore services for OpenClaw to call through the existing
`agent-actions-allowlist` connection:

  - `roamcore.rotate_api_token` — rotates the RC_API_TOKEN
    (the OpenClaw agent interface token) with backup-before-mutate
    discipline (writes a backup to
    `/config/.storage/.roamcore_security_backup.jsonl` BEFORE
    rotating the token, then updates
    `/config/.storage/roamcore_security.json` with
    `{last_rotation_at, last_rotation_reason, rotation_count}`).
  - `roamcore.audit_ssh` — runs the SSH audit (read-only;
    returns plain-English warnings via `find_risky_settings`).
  - `roamcore.audit_firewall` — runs the firewall audit
    (read-only; returns plain-English warnings via
    `find_risky_rules`).

The service handler is bench-tested via the pytest rig at
`homeassistant/packages/tests/test_security_review.py` (~20 tests
covering the 3 service definitions + the 4 helper entities + the 4
template sensors + the 4 §8 MANDATORY automations + the
rc-entity-naming compliance + the idempotency guarantees + the
secrets-leak guard).

This connection is the canonical prevention for the "lockout" worst-
case (the §connection from the directive §"Phase 7 delivery" / Gate F
— security review IS the canonical prevention for the §"Lockout"
worst-case). The dashboard tile surfaces plain-English status
("Your access codes are 95 days old — rotate soon" / "Your SSH config
allows password login — switch to keys" / "Port 22 (SSH) is open to
the whole internet — restrict to your IP range") so the operator can
fix small problems before they become lockouts.

The connection's recipe + contract tiles + 4 §8 MANDATORY automations
are documented in `connections/security-review/docs/recipe.md`. The
user-facing IKEA-style runbook lives at
`docs/runbooks/security-review.md` (5-step + 3-line troubleshooting —
no file paths, no PR numbers, no "Wave N" labels, no internal jargon).

The umbrella publishes the resulting data via the RoamCore-owned
service handler at
`homeassistant/custom_components/roamcore/security.py` (registers the
3 RoamCore services via `register_security_services(hass)` + calls
the `RCApiTokenManager.rotate_token` /
`SSHAuditReader.find_risky_settings` /
`FirewallAuditReader.find_risky_rules` APIs + the plain-English
status mapper), then publishes the RoamCore security-review contract
tiles on top (the 12 contract entities documented in the manifest's
`dashboard.tiles` list — 4 helpers + 4 template sensors + 1
binary_sensor + 3 buttons).

The audit + boundary CI can detect a `security-review/` folder that
claims to be a connection via the `DOMAIN` constant exported here.
The wizard reads the manifest + recipe at runtime.

The real per-operator security-review affordance path is:

    Operator-side choice of the THREE-step flow (Rotate access
        codes -> Audit SSH -> Audit firewall)
        -> existing helper entities (the HA core
           `input_boolean.rc_security_review_enabled` +
           `input_datetime.rc_security_review_last_audit` +
           `input_text.rc_security_review_status` +
           `input_text.rc_security_review_warnings` from
           `homeassistant/packages/roamcore_security_review.yaml`)
        -> the RoamCore-owned service handler at
           `homeassistant/custom_components/roamcore/security.py`
           (registers the 3 RoamCore services via
           `register_security_services(hass)` + calls the
           `RCApiTokenManager.rotate_token` /
           `SSHAuditReader.find_risky_settings` /
           `FirewallAuditReader.find_risky_rules` APIs + the
           plain-English status mapper)
        -> the RoamCore contract layer (the 12
           `rc_security_review_*` contract entities + 3
           `button.rc_security_review_*` operator buttons
           documented in the manifest's `dashboard.tiles` list
           — mostly `template:` sensors + `binary_sensor:`
           derivations + `input_*` helpers derived from the
           helper package + the service handler status writes)
        -> dashboard tiles + OpenClaw queries
            ("is the security review healthy?",
             "how old is the access code?",
             "what are the SSH warnings?",
             "what are the firewall warnings?",
             "rotate the access code now",
             "audit SSH now",
             "audit firewall now")

    Safety interlocks (the recipe is the contract layer; the
    automation wrappers are documented in §8):
        -> The RoamCore rotate-token automation is the
           §8.1 automation that fires via cron every 90 days
           when `input_boolean.rc_security_review_enabled` is
           ON. The automation calls the RoamCore
           `roamcore.rotate_api_token` service with the
           operator-chosen reason + writes the result to
           `input_text.rc_security_review_status`. The
           `mode: single` guard prevents double-rotation if a
           rotation is already running.
        -> The RoamCore audit-ssh automation is the §8.2
           automation that fires at 02:30 daily +
           `input_boolean.rc_security_review_enabled` is ON +
           calls `roamcore.audit_ssh` + writes the result
           (warnings list) to `input_text.rc_security_review_warnings`
           + writes the timestamp to `input_datetime.rc_security_review_last_audit`.
           The automation surfaces a plain-English banner
           ("Your SSH is locked down — keys only, no password
           login." or "Your SSH needs attention: <plain-English
           warnings>").
        -> The RoamCore audit-firewall automation is the §8.3
           automation that fires at 02:45 daily +
           `input_boolean.rc_security_review_enabled` is ON +
           calls `roamcore.audit_firewall` + writes the result
           (warnings list) to `input_text.rc_security_review_warnings`
           + writes the timestamp to `input_datetime.rc_security_review_last_audit`.
           The automation surfaces a plain-English banner
           ("Your firewall is locked down — no wide-open ports."
           or "Your firewall needs attention: <plain-English
           warnings>").
        -> The RoamCore warn-rotation-age automation is the §8.4
           automation that fires at 09:00 daily + checks
           `sensor.rc_security_review_token_age_days` + when
           token age >= 75 days, writes a plain-English warning
           to `input_text.rc_security_review_status`
           ("Your access codes are N days old — rotate soon").
           The automation is idempotent (re-firing returns
           gracefully when the warning is already on the
           status helper).

    Cross-references:
        -> The RoamCore-owned service handler at
           `homeassistant/custom_components/roamcore/security.py`
           is the canonical umbrella (the 3 RoamCore services +
           the 3 stdlib-only class APIs + the plain-English
           status mapper).
        -> The helper package at
           `homeassistant/packages/roamcore_security_review.yaml`
           is the canonical enable / last-audit / status /
           warnings helper storage + the 4 §8 automations.
        -> The pytest rig at
           `homeassistant/packages/tests/test_security_review.py`
           is the canonical ~20-test contract validation rig.
        -> The bash smoke check at
           `scripts/checks/security-review-smoke.sh` is the
           canonical cross-cutting YAML / secrets-leak /
           idempotency smoke (~10 assertions).
        -> The user-facing IKEA-style runbook at
           `docs/runbooks/security-review.md` is the canonical
           vanlifer-facing howto (5 steps + 3-line
           troubleshooting + useful links).
        -> The existing agent-actions-allowlist connection at
           `connections/agent-actions-allowlist/` cross-references
           the §8.1 rotate-token automation (the OpenClaw
           agent can call `roamcore.rotate_api_token` /
           `roamcore.audit_ssh` / `roamcore.audit_firewall`
           through the allowlist gateway).

See docs/recipe.md for the full howto (the RoamCore-owned service
handler install + the HA core `input_*` helpers install + the
THREE-step operator flow + the 12 `rc_security_review_*` contract
tiles + the 4 §8 MANDATORY automations + the 3-line §9
troubleshooting entries + the secrets-leak guard + the tier-a
promotion outline).
"""

DOMAIN = "security_review"

SECURITY_TILE_PREFIX = "rc_security_review_"

# Module-level constants exported for the audit + the helper package +
# the pytest rig. These are the canonical names the package YAML +
# the test rig + the dashboard tile surface all reference.
SECURITY_TILE_NAMES = (
    "input_boolean.rc_security_review_enabled",
    "input_datetime.rc_security_review_last_audit",
    "input_text.rc_security_review_status",
    "input_text.rc_security_review_warnings",
    "sensor.rc_security_review_last_status",
    "sensor.rc_security_review_token_age_days",
    "sensor.rc_security_review_ssh_warnings",
    "sensor.rc_security_review_firewall_warnings",
    "binary_sensor.rc_security_review_healthy",
    "button.rc_security_review_rotate_token_now",
    "button.rc_security_review_audit_ssh_now",
    "button.rc_security_review_audit_firewall_now",
)

# Status codes (mapped to plain-English via the
# `plain_english_status` mapper in security.py).
STATUS_SECURE = "secure"
STATUS_NEEDS_ROTATION = "needs_rotation"
STATUS_SSH_RISK = "ssh_risk"
STATUS_FIREWALL_RISK = "firewall_risk"
STATUS_UNKNOWN = "unknown"

# Path aliases for the 3 operator buttons.
PATH_ROTATE_TOKEN_NOW = "button.rc_security_review_rotate_token_now"
PATH_AUDIT_SSH_NOW = "button.rc_security_review_audit_ssh_now"
PATH_AUDIT_FIREWALL_NOW = "button.rc_security_review_audit_firewall_now"
