# RoamCore — Automated Acceptance Tests for Gate E (remote access)

## §1 What this is

An automated test that proves you can reach your dashboard from your
phone when you are away from your van — and that your local WiFi
connection keeps working even if the remote one drops — so you never
lose access to your van.

## §2 What you see

When RoamCore is healthy, you see a green check mark called
"Acceptance — Gate E (remote access)" in the GitHub Actions tab.
When something is wrong, that check is red and you can click into
the failed run to see exactly which step broke.

There are 13 steps in this test, and each one prints a short
plain-English message when it runs. If a step fails, the message
tells you what went wrong in words a normal person can understand
("local WiFi fallback did not respond within 5 seconds, check that
your van advertises itself on your home network") instead of showing
you a wall of code.

## §3 What you do

1. Push your change to the `main` branch (or open a pull request).
2. Open the **Actions** tab at the top of the GitHub repository.
3. Click on the run called "Acceptance — Gate E (remote access)".
4. If the run is green, you are done. If the run is red, click
   into the failed step to see which one broke and what it says.

## §4 What to do if it goes wrong

When the test fails, the failed step's plain-English message tells
you what is wrong and what to check first. The most common
reasons a step fails are:

- **Your phone cannot reach your van right now.** This usually
  means the remote-access setup wizard did not finish. Open the
  wizard on your dashboard and complete the pairing steps again.
- **The QR code on your phone did not pair within 5 minutes.**
  This means the pairing code expired. Open the wizard again and
  scan the new QR code with your phone.
- **Your dashboard looks different at home versus away.** This
  means the dashboard is serving a different version on the
  remote URL. Restart your van so it picks up the same version
  on both URLs.
- **Your local WiFi dashboard did not appear after the remote
  access dropped.** This means your van is not advertising itself
  on your home network. Check that your van is plugged in and
  connected to your home WiFi.
- **Your phone got a message that says "your phone can't reach
  your van right now".** This is the plain-English recovery
  message that fires when the remote connection is down. Try
  again on your home WiFi while the system reconnects.

If the plain-English message does not help, scroll down in the
run log to find the step-by-step output — every step in the test
quotes the specific contract element it was checking.

## §5 Useful links

- The full Phase 7 directive (all 6 release gates):
  `memory/roamcore/2026-08-03-directive.md` — section "6 release
  gates", Gate E.
- The other Gate runbooks for the rest of the release gates:
  `docs/runbooks/automated-acceptance-tests.md`.
- The bash test (the canonical contract) lives at
  `scripts/tests/acceptance/gate_e_remote_access.sh`.
- The pytest rig (the fast, always-on coverage) lives at
  `scripts/tests/acceptance/test_gate_e_remote_access.py`.
- The GitHub Actions workflow lives at
  `.github/workflows/acceptance-gate-e.yml`.

---

**Operator → vanlifer translation**

| If you see this in the test log | It means this for you |
| -------------------------------- | --------------------- |
| "remote-access setup wizard"     | "the guided remote-access setup" |
| "secure pairing code"            | "the code your phone needs to connect securely" |
| "your van's name on your home WiFi" | "roamcore.local" |
| "your van's local dashboard address" | "192.168.1.66:8123" |
| "the address your phone uses when you are away" | "your remote-access URL" |
| "your home WiFi still works when remote is down" | "local survives tunnel failure" |
| "the secure connection to your van" | "VPN daemon / tunnel handshake" |
| "a message on your dashboard that stays until you read it" | "persistent_notification" |