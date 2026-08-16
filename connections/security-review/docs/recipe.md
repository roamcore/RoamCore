# Security Review — recipe

This is the operator-facing recipe for the **Security Review** connection. It walks you through the 5-step IKEA flow + the "How it works" section + the "How to recover" section + the contract layer + the cross-references.

For the broader vanlifer-facing howto (no file paths, no internal jargon, no "Wave N" labels), see the IKEA-style runbook at the project docs site.

## §1 What this is

Security Review is a proactive plain-English audit of your SSH + firewall + access-code rotation, so small problems (password SSH, open ports, expiring tokens) get caught and fixed before they become lockouts. RoamCore runs the audit daily at 02:30 (SSH) + 02:45 (firewall), and surfaces the warnings on a single dashboard tile using sentences like "Your access codes are 95 days old — rotate soon" or "Port 22 (SSH) is open to the whole internet — restrict to your IP range".

## §2 Prerequisites

- RoamCore is installed (HACS or one-line command — RoamCore bundles the service handler at `homeassistant/custom_components/roamcore/security.py` as part of the standard install).
- The Hub is on a network where `/etc/ssh/sshd_config` + `/etc/nftables.conf` + `iptables-save` are reachable (the audit is file-based; the operator-owned files are read-only).

## §3 Step 1 — Rotate access codes

1. Open the RoamCore dashboard.
2. Find the **Security Review** tile.
3. Tap the `button.rc_security_review_rotate_token_now` button.
4. The rotation writes a backup BEFORE updating `.storage/` (backup-before-mutate discipline) — the backup is at `/config/.storage/.roamcore_security_backup.jsonl` (append-only JSONL).
5. The new token is written to `/config/.storage/roamcore_security.json` atomically (`.tmp + os.replace`).
6. The result surfaces on `input_text.rc_security_review_status` as plain English ("Access codes rotated successfully.").

## §4 Step 2 — Audit SSH

1. The automated §8.2 audit-ssh automation fires at **02:30 daily** when `input_boolean.rc_security_review_enabled` is ON.
2. The automation calls `roamcore.audit_ssh` (the RoamCore-owned service at `homeassistant/custom_components/roamcore/security.py`).
3. The audit reads `/etc/ssh/sshd_config` (read-only by design) + surfaces plain-English warnings via `find_risky_settings()` ("Your SSH allows password login — switch to keys for safety" / "Your SSH allows root login — disable or restrict to 'prohibit-password'").
4. The automation writes the result to `input_text.rc_security_review_warnings` + writes the timestamp to `input_datetime.rc_security_review_last_audit`.
5. The operator can also trigger the audit on demand via `button.rc_security_review_audit_ssh_now`.

## §5 Step 3 — Audit firewall

1. The automated §8.3 audit-firewall automation fires at **02:45 daily** when `input_boolean.rc_security_review_enabled` is ON.
2. The automation calls `roamcore.audit_firewall` (the RoamCore-owned service at `homeassistant/custom_components/roamcore/security.py`).
3. The audit reads `/etc/nftables.conf` + `iptables-save` (read-only by design) + surfaces plain-English warnings via `find_risky_rules()` ("Port 22 (SSH) is open to the whole internet — restrict to your IP range" / "Port 445 (SMB) is open to the whole internet — restrict to your IP range").
4. The automation writes the result to `input_text.rc_security_review_warnings` + writes the timestamp to `input_datetime.rc_security_review_last_audit`.
5. The operator can also trigger the audit on demand via `button.rc_security_review_audit_firewall_now`.

## §6 The 4 §8 MANDATORY automations

### §8.1 Rotate-token

- **Trigger.** Cron at 02:00 every 90 days (`0 2 */90 * *`).
- **Condition.** `input_boolean.rc_security_review_enabled` is ON.
- **Action.** Calls the RoamCore `roamcore.rotate_api_token` service with `reason: "scheduled_90_day"`. Writes the result (`rotated_at` + `reason` + `rotation_count`) to `input_text.rc_security_review_status` as plain English.
- **Idempotency.** `mode: single` — re-firing the cron while a rotation is already running returns gracefully (no double-rotation).

### §8.2 Audit-ssh

- **Trigger.** Cron at 02:30 daily (`30 2 * * *`).
- **Condition.** `input_boolean.rc_security_review_enabled` is ON.
- **Action.** Calls the RoamCore `roamcore.audit_ssh` service. Writes the warnings list to `input_text.rc_security_review_warnings` + writes the timestamp to `input_datetime.rc_security_review_last_audit` + writes the plain-English status to `input_text.rc_security_review_status`.
- **Outcome.** Surfaces "Your SSH is locked down — keys only, no password login." OR "Your SSH needs attention: <plain-English warnings>".

### §8.3 Audit-firewall

- **Trigger.** Cron at 02:45 daily (`45 2 * * *`).
- **Condition.** `input_boolean.rc_security_review_enabled` is ON.
- **Action.** Calls the RoamCore `roamcore.audit_firewall` service. Writes the warnings list to `input_text.rc_security_review_warnings` + writes the timestamp to `input_datetime.rc_security_review_last_audit` + writes the plain-English status to `input_text.rc_security_review_status`.
- **Outcome.** Surfaces "Your firewall is locked down — no wide-open ports." OR "Your firewall needs attention: <plain-English warnings>".

### §8.4 Warn-rotation-age

- **Trigger.** Cron at 09:00 daily (`0 9 * * *`).
- **Condition.** `input_boolean.rc_security_review_enabled` is ON.
- **Action.** Reads `sensor.rc_security_review_token_age_days`. When token age >= 75 days, writes a plain-English warning to `input_text.rc_security_review_status` ("Your access codes are N days old — rotate soon"). When token age < 75 days, the automation is a no-op.
- **Outcome.** The operator gets a plain-English nudge 2 weeks before the 90-day threshold.

## §7 How to recover from a lockout

1. If the operator is locked out via SSH (password login broken, key revoked, root login disabled), the recovery path is:
   - Use the Proxmox console (the Hub VM is at 192.168.1.66 on the home LAN — direct console access bypasses SSH).
   - Restore the previous `/etc/ssh/sshd_config` from the operator's pre-existing backup (the audit is read-only; RoamCore does NOT write a backup of sshd_config).
   - Restart the SSH service (`systemctl restart sshd`).
2. If the operator is locked out via firewall (the audit revealed an open port but the operator closed it and now can't reach the Hub):
   - Use the Proxmox console to inspect `/etc/nftables.conf` + `iptables-save`.
   - Restore the previous rules from the operator's pre-existing backup.
   - Reload the firewall (`nft -f /etc/nftables.conf`).
3. If the access code is revoked:
   - Use the Proxmox console + run the `roamcore.rotate_api_token` service manually with the `force: true` flag.
   - The new access code is written to `/config/.storage/roamcore_security.json` atomically + the audit log records the rotation.

> ⚠️ The recovery flow is intentionally NOT automated in this slice (the recipe's "How to recover" section cross-references the operator's pre-existing backup discipline — RoamCore's audit is read-only by design).

## §8 The 12 `rc_security_review_*` contract entities

| Domain | Tile id | Purpose |
|---|---|---|
| `input_boolean` | `rc_security_review_enabled` | Master enable toggle (pauses the daily security audit when OFF). |
| `input_datetime` | `rc_security_review_last_audit` | Date_time helper tracking the last audit run (set by §8.2 + §8.3). |
| `input_text` | `rc_security_review_status` | Operator-visible plain-English status. |
| `input_text` | `rc_security_review_warnings` | Operator-visible plain-English warnings list. |
| `sensor` | `rc_security_review_last_status` | Mirrors `input_text.rc_security_review_status` + adds a plain-English banner. |
| `sensor` | `rc_security_review_token_age_days` | Age of the current RC_API_TOKEN in whole days (99999 if never). |
| `sensor` | `rc_security_review_ssh_warnings` | Count of SSH warnings from the last audit (0 if no warnings). |
| `sensor` | `rc_security_review_firewall_warnings` | Count of firewall warnings from the last audit (0 if no warnings). |
| `binary_sensor` | `rc_security_review_healthy` | Resolved healthiness chip (true when no warnings AND token age < 75 days). |
| `button` | `rc_security_review_rotate_token_now` | Operator-triggered one-tap "rotate access code". |
| `button` | `rc_security_review_audit_ssh_now` | Operator-triggered one-tap "audit SSH now". |
| `button` | `rc_security_review_audit_firewall_now` | Operator-triggered one-tap "audit firewall now". |

## §9 Troubleshooting (3 entries)

- **"Security review hasn't run yet — check back tomorrow."** The Hub was just provisioned + the §8.2 audit-ssh automation hasn't fired yet. Wait until 02:30 the next morning, or tap the **audit SSH now** button to trigger it on demand.
- **"Your SSH config allows password login — switch to keys for safety."** The audit detected that `PasswordAuthentication yes` is set in `/etc/ssh/sshd_config`. Switch to keys (the runbook §3 "What you do" step 4 covers the key switch).
- **"Port 22 (SSH) is open to the whole internet — restrict to your IP range."** The audit detected that the firewall accepts SSH connections from `0.0.0.0/0`. Restrict to a specific IP range (the runbook §3 "What you do" step 5 covers the firewall restriction).

## §10 Files in this connection + cross-references

- `connections/security-review/connection.yml` — the source-of-truth tier-a manifest.
- `connections/security-review/__init__.py` — `DOMAIN = "security_review"` marker + tile-name constants for the audit.
- `connections/security-review/docs/recipe.md` — this recipe.
- `connections/security-review/tests/test_connection_yml.py` — manifest honesty checks.
- `homeassistant/custom_components/roamcore/security.py` — RoamCore-owned service handler (883 LOC — stdlib-only Python).
- `homeassistant/custom_components/roamcore/services.yaml` — service definitions (3 services).
- `homeassistant/custom_components/roamcore/__init__.py` — `register_security_services(hass)` wired into `async_setup_entry`.
- `homeassistant/packages/roamcore_security_review.yaml` — helper package + 4 §8 automations.
- `homeassistant/packages/tests/test_security_review.py` — ~20 pytest tests.
- `scripts/checks/security-review-smoke.sh` — ~10 bash assertions.
- `docs/runbooks/security-review.md` — IKEA-style user-facing runbook.
- `scripts/check.sh` — wired with the new smoke check.
