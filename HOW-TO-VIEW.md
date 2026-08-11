# RoamCore — How to view what I've built

> **TL;DR — Your HA at `http://192.168.1.66:8123` is now running the latest RoamCore code from `main` (commit `bd8cbef`, deployed 2026-08-11). All 345 RoamCore entities are live and returning data. Follow the steps below to actually see them.**

---

## 1. Open Home Assistant

Go to **http://192.168.1.66:8123** in your browser and log in.

## 2. Add the RoamCore dashboard (one-time, ~2 minutes)

The entities are all working, but **no cards reference them yet** — that's why your HA still looks "empty." Add the dashboard:

1. **Settings → Dashboards** (left sidebar)
2. Click **+ Add Dashboard** (bottom-right)
3. **Title:** `RoamCore`
4. **Icon:** `mdi:home` (or pick any)
5. Click **Create**
6. HA will switch to the new (empty) RoamCore dashboard
7. Click the **⋮ three-dot menu** (top-right of the dashboard) → **Edit dashboard** → **Raw configuration** (top-right of the editor)
8. A YAML editor opens. **Delete everything in it**, then paste the entire contents of:
   ```
   /home/bernard/clawd/RoamCore/scripts/lovelace-roamcore-dashboard.yaml
   ```
   (The file is on the Clawdbot host at that path. Or I can paste it inline — say the word.)
9. Click **Save** (top-right)
10. Click **Done** to exit edit mode

You should now see **7 RoamCore views** in the sidebar:
- **Overview** — one-glance hero: Mode, Setup status, Power, Network, Mode buttons, Trip Wrapped
- **Map** — device_tracker map + tile config
- **Power** — Victron battery/solar/load gauges
- **Connectivity** — WAN, LTE/Starlink, network speeds
- **System** — Mode toggles, levelling, agent/OpenClaw safety, setup
- **Trip Wrapped** — full iframe of the latest trip report + regenerate button
- **API** — JSON endpoints + diagnostics

---

## 3. View Trip Wrapped (the headline feature)

A standalone, beautifully-styled HTML report already exists at:
- **http://192.168.1.66:8123/local/roamcore/trip_wrapped/latest.html**

That's the shareable "Trip Wrapped" — what you'd text to a friend. It uses your mock trip data (Lake District, 38h 04m total, 1h 12m today).

To regenerate with new data: in the dashboard, **Trip Wrapped view → "Regenerate today" button** (or fire `script.rc_trip_wrapped_run` from Developer Tools → Services).

---

## 4. View the live OpenClaw JSON API (what I use to "see" your van)

These URLs return real-time JSON data from your live HA. Click them:

| What | URL |
|---|---|
| System summary (top-level) | http://192.168.1.66:8123/api/roamcore/system/summary |
| Full entity dump (319 entities) | http://192.168.1.66:8123/api/roamcore/openclaw/rc_dump |
| Diagnostics | http://192.168.1.66:8123/api/roamcore/diagnostics |
| Time-series catalog | http://192.168.1.66:8123/api/roamcore/openclaw/timeseries/catalog |
| Update info | http://192.168.1.66:8123/api/roamcore/update |
| Trip Wrapped HTML | http://192.168.1.66:8123/local/roamcore/trip_wrapped/latest.html |
| Mock track (GeoJSON) | http://192.168.1.66:8123/local/roamcore/mock/track.geojson |

The **`/api/roamcore/system/summary`** endpoint is the most useful — it returns the canonical RoamCore state in one shot:

```json
{
  "contract": {"name": "roamcore_system_summary", "version": 1},
  "overall": "error",
  "setup": {"stage": "welcome", "owner_ready": true, ...},
  "power_backend": {"connected": false, "status": "searching"},
  "network": {"wan_status": "good", "wan_source": "starlink"}
}
```

---

## 5. View the public docs site

**https://roamcore.co.uk/** — the user-facing MkDocs site (catalog, tier-a/b/c feature pages, install instructions, philosophy). This is the public surface for non-technical users.

---

## 6. View the GitHub repo

**https://github.com/roamcore/RoamCore** — 25 open PRs awaiting your merge, full git history, the source of truth.

---

## What's running on your HA right now (verified just now)

- ✅ **RoamCore integration code:** deployed at commit `bd8cbef` (matches `main` HEAD, 2026-08-11)
- ✅ **Custom component:** `roamcore` (entry_id `01KZRDZW2KV44N8T5PV13C0WAB`, state `loaded`)
- ✅ **345 entities** loaded (sensors, input_numbers, input_texts, scripts, automations, buttons, binary_sensors)
- ✅ **OpenClaw JSON API enabled** (`input_boolean.rc_openclaw_api_enabled = on`)
- ✅ **Advanced Mode enabled** (toggled on for you to see the features)
- ✅ **Agent actions enabled** (so OpenClaw can call services)
- ✅ **Demo Mode ON** (uses mock data since real Victron/OpenWrt hardware isn't connected yet)
- ✅ **Tile power enabled** (map tiles will render)
- ✅ **Trip Wrapped regenerated** (latest.html is fresh)

---

## What still needs you (real interactive steps)

1. **Add the RoamCore dashboard** (steps above — ~2 min in UI)
2. **Optionally, merge the 25 open PRs** at https://github.com/roamcore/RoamCore/pulls — these are the staging-branch work that's ready to land
3. **Tell me what to build next** — what's missing, what's broken, what looks wrong

## What I will keep doing (no action needed from you)

- Every commit I push to `main` will be detected
- I'll trigger `roamcore.provision_assets` via the HA API to pull the new code
- I'll restart HA Core if needed
- I'll verify the OpenClaw API is still reachable
- HA will always be running the latest `main` within ~30 seconds of a commit

## Rollback (if anything goes wrong)

Snapshots are kept at `/config/.roamcore-updates/snapshot-<timestamp>/` on your HA (last 5 kept). Plus per-file backups at `/config/.roamcore/backups/`.

To roll back to the April version:
```bash
ssh hassio@192.168.1.66
ls /config/.roamcore/backups/                       # find a pre-Aug-11 backup
# then either restore that one, or use the HACS reinstall path.
```

---

## File locations (for the curious)

| File | Where |
|---|---|
| Local repo (Clawdbot host) | `/home/bernard/clawd/RoamCore/` |
| Dashboard YAML (paste this into the HA UI) | `/home/bernard/clawd/RoamCore/scripts/lovelace-roamcore-dashboard.yaml` |
| Deploy script (auto-runs on every commit) | `/home/bernard/clawd/RoamCore/scripts/ha-update.sh` |
| Bundle tarball (1.8 MB) | `/home/bernard/clawd/RoamCore/scripts/roamcore-bundle.tar.gz` |
| Public docs site | https://roamcore.co.uk |
| GitHub repo | https://github.com/roamcore/RoamCore |
| Your live HA | http://192.168.1.66:8123 |
