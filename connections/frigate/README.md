# Frigate (NVR with on-device object detection)

**Tier:** B (recipe)
**Category:** CCTV
**Status:** beta

## What this connection is

Frigate is a self-hosted Network Video Recorder with **on-device ML
object detection** — it recognises people, cars, animals, packages,
license plates, etc. on the same box that runs Home Assistant, and
records to local storage. RoamCore uses Frigate as the CCTV backend:

- **Person/car/animal detection** runs on the Frigate container
  (CPU or Coral/Intel GPU accelerated) — no cloud round-trip.
- **Recording** lands on an SSD/NVMe volume you mount into the
  Frigate container, with retention policies per `record.events` and
  `record.alerts`.
- **Re-stream** uses `go2rtc` (bundled with Frigate) so the HA core
  `frigate` integration can pull a low-latency live stream for the
  dashboard.
- **MQTT events** (`frigate/events`, `frigate/available`) flow over
  the Mosquitto broker from `connections/mqtt/` — RoamCore's contract
  layer subscribes there to expose stable `rc_security_camera_*` and
  `rc_security_recording_*` entities to the dashboard and OpenClaw.

RoamCore does **not** ship a Frigate container of its own. We publish
the documented setup for the upstream HA core `frigate` integration
(https://www.home-assistant.io/integrations/frigate/, ships in HA core,
config_flow since 2022.4), then layer a small contract on top: the
camera-count / motion-active / recording-active / last-motion /
object-detection-summary / storage-usage tiles + the OpenClaw queries
that let you ask "is anyone at the door?" without wiring a custom
dashboard.

## Setup recipe (one-paragraph)

1. Mount an SSD/NVMe volume on the HA host (1 TB minimum; 2–4 TB
   recommended for 4+ cameras at 1080p + 14-day retention).
2. Install either the **Frigate add-on** (community repo, recommended)
   or run Frigate + go2rtc as external Docker containers — both paths
   are documented in [`docs/recipe.md`](docs/recipe.md).
3. In Frigate's `config.yaml`, declare your RTSP/ONVIF cameras, set
   the MQTT section to point at your Mosquitto broker (from
   `connections/mqtt/`), and set `record.events` + `record.alerts`
   retention.
4. In HA → **Settings → Devices & Services → Add Integration →
   Frigate**, enter your Frigate URL (`http://ccab4aaf-frigate:5000`
   for the add-on, or `http://<lan-ip>:5000` for external) and the
   MQTT credentials.
5. Reload the RoamCore dashboard; the `rc_security_*` contract tiles
   appear on the CCTV / Security section.

Full howto with copy-pasteable Frigate `config.yaml` snippets, an
external `docker-compose.yml`, and the RoamCore MQTT contract wiring:
see [`docs/recipe.md`](docs/recipe.md).

## Why tier-b, not tier-a

Tier-a requires a working RoamCore-owned `config_flow.py`, integration
tests against a real Frigate container on CI, and `wizard.one_tap:
true`. We have no Frigate NVR on the CI bench to integration-test
against (the CI bench is a container, not a video-recording box with
a Coral accelerator + RTSP cameras), so this connection is honestly
beta-tier: the recipe is sound (it leans on the well-tested core
`frigate` integration) but we cannot claim one-tap automation. The
[`tests/test_connection_yml.py`](tests/test_connection_yml.py) file
asserts the manifest is honest about its tier — that's the only test
we can ship today.

When a real Frigate container lands on the bench (likely via
`testcontainers/frigate` with a synthetic RTSP source or a recorded
fixture), this connection is the candidate to promote to tier-a: add a
native `config_flow.py` that wraps the RoamCore-specific security
contract, add an integration test that asserts the `rc_security_*`
contract entities appear after a synthetic `frigate/events` payload,
and flip `tier_requirements` to include `working_config_flow` +
`integration_test_passes` + `no_manual_yaml_required`.

## Files

- `connection.yml` — the source-of-truth manifest.
- `__init__.py` — `DOMAIN = "frigate"` marker for the audit.
- `docs/recipe.md` — the full howto (Frigate add-on + external Docker
  paths, go2rtc config, MQTT contract wiring, storage + retention,
  troubleshooting, tier-a promotion outline).
- `tests/test_connection_yml.py` — manifest honesty checks.

## See also

- Legacy catalog page (now superseded by the connection manifest):
  [`docs/catalog/cctv/frigate.md`](../../docs/catalog/cctv/frigate.md)
- Catalog category index: `docs/catalog/cctv/index.md`
- Auto-generated catalog page (built by `scripts/build_catalog.py`
  from this manifest): `docs/connections/frigate.md`
- MQTT broker (Frigate publishes events over MQTT — natural cross-ref):
  `connections/mqtt/`
- HA core `frigate` integration docs:
  <https://www.home-assistant.io/integrations/frigate/>
- Frigate project: <https://frigate.video/>
- Frigate docs: <https://docs.frigate.video/>
- RoamCore entity naming: `docs/reference/rc-entity-naming.md`