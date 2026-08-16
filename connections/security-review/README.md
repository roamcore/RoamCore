# Security Review — proactive plain-English audit of SSH + firewall + access codes

**Tier:** A (native integration; real RoamCore-owned Python service handler at `homeassistant/custom_components/roamcore/security.py` + ~20 pytest tests at `homeassistant/packages/tests/test_security_review.py` + ~10 bash assertions at `scripts/checks/security-review-smoke.sh`)

**Category:** security
**Status:** Available

## What this connection is

Security Review tells you in plain English whether your van is locked down — SSH keys only, firewall tight, access codes fresh — so you can fix small problems before they become lockouts. The daily audit reads `/etc/ssh/sshd_config` + `/etc/nftables.conf` + `iptables-save` and surfaces the warnings on a single dashboard tile using sentences like "Your SSH config allows password login — switch to keys" or "Port 22 (SSH) is open to the whole internet — restrict to your IP range". The 3-step IKEA flow is the operator-facing affordance surface (Rotate access codes → Audit SSH → Audit firewall). The full howto lives at [`docs/recipe.md`](docs/recipe.md).

This is the **third true tier-a connection** in the RoamCore connection pipeline. The prior tier-a connections (`connections/openclaw-api/` Wave 3 #64 + `connections/hub-backup/` Wave 9 #123.a) wrap existing custom components or ship new RoamCore-owned service handlers. This slice SHIPS the tier-a connection manifest + the data-layer package + the pytest rig + the bash smoke + the IKEA runbook on top of the foundation service handler at `homeassistant/custom_components/roamcore/security.py` (already shipped at #123.c.i). The tier-a claim is provable via `pytest homeassistant/packages/tests/test_security_review.py` (~20/20 PASS) + `bash scripts/checks/security-review-smoke.sh` (~10/10 PASS).

## The 3-step operator flow

- **Step 1 — Rotate access codes.** Tap the `button.rc_security_review_rotate_token_now` button to rotate the access code (the rotation writes a backup BEFORE updating .storage/ — backup-before-mutate discipline).
- **Step 2 — Audit SSH.** The automated §8.2 audit-ssh automation runs daily at 02:30 AND on operator demand via `button.rc_security_review_audit_ssh_now` — checks `/etc/ssh/sshd_config` for hardening and surfaces plain-English warnings.
- **Step 3 — Audit firewall.** The automated §8.3 audit-firewall automation runs daily at 02:45 AND on operator demand via `button.rc_security_review_audit_firewall_now` — checks `/etc/nftables.conf` + `iptables-save` for risky rules and surfaces plain-English warnings.

## Files

- `connection.yml` — the source-of-truth tier-a manifest.
- `__init__.py` — `DOMAIN = "security_review"` marker + tile-name constants for the audit.
- `docs/recipe.md` — the full howto.
- `tests/test_connection_yml.py` — manifest honesty checks.

## See also

- RoamCore-owned service handler: `homeassistant/custom_components/roamcore/security.py` (883 LOC — stdlib-only Python — 3 stdlib-only classes + the plain-English status mapper + the 3 RoamCore service registrations).
- Helper package: `homeassistant/packages/roamcore_security_review.yaml` (declares the 12 contract entities + the 4 §8 MANDATORY automations).
- Pytest rig: `homeassistant/packages/tests/test_security_review.py` (~20 tests).
- Bash smoke check: `scripts/checks/security-review-smoke.sh` (~10 assertions).
- User-facing IKEA-style runbook: `docs/runbooks/security-review.md` (5 steps + 3-line troubleshooting + useful links).
- RoamCore entity naming: `docs/reference/rc-entity-naming.md` (the `security_review` subsystem was added by this slice).
