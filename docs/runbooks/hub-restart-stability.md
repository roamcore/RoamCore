# Hub restart-stability

When your Hub reboots after a power blip, all the screens in your van come back automatically — this runbook shows how to verify that.

## §1 What this checks

Every RoamCore Hub runs five small services in the background: Victron (your batteries), Traccar (your location), the offline map, the Traccar proxy that keeps the map embed working, and a one-shot secret-bootstrap that only runs the first time. This runbook makes sure each one comes back to life after a reboot, and that none of them step on each other's toes.

The verification is automatic. If you run the smoke check on the Hub (or on any machine with the RoamCore source code checked out), it tells you — in plain English — whether every service came back cleanly.

## §2 How to run the check

If you are the operator of a Hub, the simplest path is: nothing. The Hub runs the check itself whenever it boots, and surfaces any problem on the dashboard. You only need to read this runbook if the dashboard shows a "service didn't come back up" notice.

If you want to run it by hand, open the Hub's terminal app (or SSH in) and run the smoke check. The script prints a clear "OK" line if everything is fine, or a plain-English explanation of what went wrong if it isn't. The exact command lives in the developer section at the bottom of this runbook — §5 has it alongside the rest of the technical details.

## §3 What each service does

These are the five services that live on your Hub. Each one is small and does one job. If a service is missing from this list, something is wrong — every Hub should have all five.

- **Victron (your batteries)** — Reads your Victron battery, solar and shore power and shows them on your dashboard.
- **Victron mock (pretend readings)** — Publishes pretend Victron readings so you can try the app before plugging in real hardware.
- **Traccar first-boot helper** — Creates the Traccar admin account the first time your Hub powers on, then steps out of the way.
- **Traccar proxy** — Lets the live map embed in your dashboard without breaking on phones that block cross-network pages.
- **Offline tile server** — Serves the offline map tiles so the live map still works when you are out of phone signal.

The full list, including each service's restart behaviour and the order they come back in, lives in the canonical manifest (`scripts/build/hub-services.yml` on the GitHub repo). The manifest is the source of truth — this runbook is the short version.

## §4 What to do if a service doesn't come back

The dashboard will tell you which service is stuck. Most of the time the fix is the same: open Home Assistant → Settings → Add-ons → find the stuck service → click **Restart**. Wait ten seconds, then check the dashboard again.

If the service still will not start, the smoke check (above) prints the exact reason in plain English — for example, "Victron didn't come back up — check the Traccar proxy log" tells you which log to open. That is the only log you need to look at first.

If you have tried the restart twice and the smoke check is still failing, send the support bundle from the Hub's Settings page to support. The bundle includes the full output of the smoke check, so the support team can see exactly which service is stuck and why.

## §5 Adding a new service to the rig (developer-facing)

To run the smoke check by hand:

```bash
bash scripts/checks/hub-restart-stability-smoke.sh
```

If you are adding a new RoamCore service (a new addon) that should come back automatically after a reboot, you need to update three things:

1. The canonical manifest at `scripts/build/hub-services.yml` — add a new entry under `services:` with the addon's slug, where the addon folder lives, the restart policy (`always`, `on-failure`, or `no`), the services it depends on (empty list if none), how to check it has reached ready state, and one short sentence in plain English that explains what the addon does.
2. The pytest rig at `homeassistant/addons/tests/test_hub_restart_stability.py` — the rig reads the manifest, so it will pick up the new service automatically; no test changes are required. If the new addon has a port, make sure no other addon uses the same port.
3. The smoke wrapper at `scripts/checks/hub-restart-stability-smoke.sh` — add the new addon folder name to the pre-check loop so a missing `config.yaml` fails fast with a clear message.

After you have made all three changes, run `bash scripts/check.sh --core-only` from the repo root. If the chain is GREEN, the rig will catch the new service on the next reboot automatically.
