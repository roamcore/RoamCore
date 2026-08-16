# Security Review

Tells you in plain English whether your van is locked down — SSH keys only, firewall tight, access codes fresh — so you can fix small problems before they become lockouts, without having to read technical jargon.

## What this is

Security Review is a daily check that tells you whether your van is locked down in plain English. Every night, it reads your SSH settings and your firewall rules, and surfaces any problems as sentences on a single dashboard tile — like "Your SSH config allows password login — switch to keys" or "Port 22 (SSH) is open to the whole internet — restrict to your IP range". If anything looks off, you can fix it before it becomes a lockout.

## What you see

- **A single status tile.** It reads "Your van is locked down — access codes fresh, SSH key-only, firewall tight." or one of the plain-English warnings.
- **A red/green healthy indicator.** Green means everything is fine; red means one of the checks found a problem.
- **Warnings list.** A short plain-English list of the issues the audit found (e.g. "Your SSH allows password login — switch to keys for safety" or "Port 22 (SSH) is open to the whole internet — restrict to your IP range").
- **Three buttons.** One to rotate the access code (the password OpenClaw agents use to ask your Hub questions), one to re-run the SSH check, and one to re-run the firewall check.

## What you do

1. **Open the Security Review screen.** The tile is on the dashboard by default. The master switch at the top is **ON** (the audit runs automatically every night — you don't have to do anything).
2. **Rotate the access code if it's old.** Tap the **Rotate access code** button. The new code is written down before the old one is replaced, so you can always undo the change. Tap this once now to start fresh, then check back every 90 days (the audit will tell you when to rotate next).
3. **Check the SSH settings.** Tap the **Audit SSH now** button. The audit reads your SSH settings and tells you in plain English whether keys-only login is on, whether root login is allowed, and whether the port is the default. If a warning shows up, follow the suggested fix (typically: switch to keys, disable root login, change the port).
4. **Check the firewall.** Tap the **Audit firewall now** button. The audit reads your firewall rules and tells you in plain English whether any sensitive ports (SSH, SMB, RDP, etc.) are open to the whole internet. If a warning shows up, restrict the port to your IP range (or your VPN range) — the runbook for the firewall setup has the safe defaults.
5. **Check back tomorrow.** The audit runs automatically every night at 02:30 (SSH) and 02:45 (firewall). The tile updates to the latest status. If a problem appears, the tile goes red and you can re-run the audit on demand.

## What to do if it goes wrong

- **"Security review hasn't run yet — check back tomorrow."** Your Hub was just provisioned and the audit hasn't fired yet. Wait until 02:30 the next morning, or tap the **Audit SSH now** button to run it on demand.
- **"Your access codes are N days old — rotate soon."** The access code is approaching the 90-day rotation window. Tap the **Rotate access code** button to rotate it now (the audit takes a backup before writing the new code, so you can always undo).
- **"Your SSH is locked down — keys only, no password login."** All clear. The tile is green and the audit found no SSH warnings. No action needed.
- **"Your SSH needs attention: ..."** The audit found SSH settings that aren't locked down. The plain-English warning tells you what to fix (e.g. "switch to keys", "disable root login", "change the port"). Make the fix in the SSH config and re-run the audit by tapping the **Audit SSH now** button.
- **"Your firewall is locked down — no wide-open ports."** All clear. The tile is green and the audit found no firewall warnings. No action needed.
- **"Your firewall needs attention: ..."** The audit found firewall rules that open sensitive ports to the whole internet. The plain-English warning tells you which port is open and which service it belongs to (e.g. SSH, SMB, RDP). Restrict the port to your IP range (or your VPN range) and re-run the audit by tapping the **Audit firewall now** button.

## Useful links

- The full step-by-step recipe is in the **Security Review** section of the RoamCore catalog.
- The GitHub issue tracker: open an issue at <https://github.com/roamcore/RoamCore/issues> with the label `security-review`.
- For the broader RoamCore catalog, browse to <https://roamcore.github.io/RoamCore/>.
