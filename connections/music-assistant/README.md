# Music Assistant (multi-room van audio)

**Tier:** B (recipe)
**Category:** Media
**Status:** beta

## What this connection is

Music Assistant (<https://www.music-assistant.io/>) is a provider-agnostic multi-room audio orchestrator very popular in Home Assistant installs — it unifies Spotify, Apple Music, TuneIn/radio, local files, Chromecast/AirPlay/Sonos receivers behind a single "play everywhere" surface with per-zone controls and a clean dashboard. For vans, MA delivers multi-zone audio (living, bed, outdoor) with HA-orchestrated player discovery + per-zone volume + provider-agnostic library access — perfect for "everyone listens together" and "I want silence in the bedroom now" use cases. RoamCore recipes the **provider + per-zone control + library summary** story — the per-zone `media_player` family + a now-playing trio + library counts + the `pause_all` / `resume_last` affordances — that powers the RoamCore `rc_media_*` contract tiles + OpenClaw media queries ("what's playing?", "what zone is on?", "pause all music", "resume last playlist", "switch to outdoor zone", "set volume 30 on bedroom", "play <artist/album/playlist>", "how many artists in library?").

- **Provider-agnostic audio** comes from the upstream HACS `music_assistant` integration (canonical HACS-only MA integration, fetched from `music-assistant/hass-music-assistant` on GitHub via HACS → Repositories → Add; HA core does NOT include Music Assistant — MA is HACS-only). At least one provider is required: Spotify OAuth, Apple Music developer token, local-files library mount, TuneIn radio, or a Chromecast/AirPlay/Sonos receiver.
- **MA server install path** is the operator's choice: **Path A** — MA HA add-on (recommended for HAOS installs; auto-discovered via zeroconf on the LAN; the upstream HA add-on runs the MA server inside the HA host), OR **Path B** — external MA server (recommended for fleet installs + non-HAOS hosts; runs the upstream `ghcr.io/music-assistant/server` container or `linuxserver/music-assistant` for LSI Docker hosts; pointed at by the same HACS `music_assistant` integration via URL like `http://ma.lan:8095`).
- **Mode-aware behavior** is built into the recipe: Stealth silent hours auto-pause all players unless the active zone is `bed`; Travel mode auto-resumes the last playlist on the outdoor zone when motion is detected (with a 60 % volume cap); Boost mode defaults the outdoor zone to 80 % volume and all other zones to 30 %; a power-aware automation pauses all media when the inverter SOC drops below 25 % AND shore power is disconnected; TTS announcements are pinned to the `media_player.rc_media_zone_living` only (never bleeding into the bedroom at night).

RoamCore does **not** ship a Music Assistant server or a RoamCore-owned native integration. The HACS `music_assistant` integration is the upstream truth; RoamCore layers a contract on top: the `rc_media_*` dashboard tiles + the OpenClaw queries that bind to those contract entities.

## Setup recipe (one-paragraph)

1. Make sure HACS is installed on your HA instance (HACS is the Home Assistant Community Store — install via <https://hacs.xyz/docs/setup/download>).
2. Add the HACS repository: HACS → **Frontend** → three-dot menu → **Custom repositories** → add `music-assistant/hass-music-assistant` as an **Integration**. Or directly: **HACS → Integrations → Explore & Add Repositories → search "Music Assistant"** (the integration IS in the HACS default store).
3. Pick a path: **Path A** — MA HA add-on (recommended for HAOS installs; the upstream HA add-on runs the MA server inside the HA host; HA auto-discovers MA via zeroconf on the LAN and the config_flow launches), OR **Path B** — external MA server (recommended for fleet installs + non-HAOS hosts; pull `ghcr.io/music-assistant/server` or `linuxserver/music-assistant` and run it on a separate host on the LAN; the HACS `music_assistant` integration walks you through pointing it at the MA server URL like `http://ma.lan:8095`).
4. Install the HACS `music_assistant` integration in HA.
5. Configure at least one provider (Spotify OAuth, Apple Music developer token, local-files library mount, TuneIn radio, or a Chromecast/AirPlay/Sonos receiver). The recipe §7 walks through each provider.
6. Create the `rc_media_*` contract tiles (or import the recipe's `input_select` + `template` + `media_player` + `button` + `select` helpers from the recipe §5 snippet block). The recipe walks through mapping the upstream MA `media_player.mass_*` entities into the `rc_media_zone_*` contract family (when the names naturally match, the translation is a 1:1 rename; when they don't, the recipe adds explicit `template` media_player entries).
7. (Optional) Wire a `default_zone` so the `resume_last` button knows where to resume — the recipe §5.1 helper YAML wires this up.
8. Enable the recipe §6 automations (mode-aware Stealth auto-pause, Travel motion-resume, Boost zone-default-volume, inverter-SOC power-aware pause, TTS-zone-pinning).
9. Reload the RoamCore dashboard; the `rc_media_*` contract tiles appear on the Media section.

Full howto with copy-pasteable YAML for the helpers, automations, HACS wiring, MA Path A + Path B wiring, provider setup, mode-aware exceptions, and the tier-a promotion outline: see [`docs/recipe.md`](docs/recipe.md).

## Why tier-b, not tier-a

Tier-a requires a working RoamCore-owned `config_flow.py`, integration tests against a real Music Assistant server on CI, and `wizard.one_tap: true`. We have no MA server on the CI bench to integration-test against, the operator's exact provider mix + Path A-vs-B choice varies (HAOS-vs-not + memory + fleet needs), and there's no canonical RoamCore-owned upstream HA integration that does what this connection recipes. So this connection is honestly beta-tier: the recipe is sound but we cannot claim one-tap automation. The [`tests/test_connection_yml.py`](tests/test_connection_yml.py) file asserts the manifest is honest about its tier — that's the only test we can ship today.

When a real Music Assistant server lands on the bench (likely via a RoamCore-owned MA container image with a default provider stub + a CI bench container that validates the provider handshake — exactly what the §10 promotion outline describes), this connection is the candidate to promote to tier-a: add a native `config_flow.py` that wraps the RoamCore-specific media contract (with provider pinning so the operator's provider mix is bounded), add an integration test that asserts the `rc_media_*` contract entities appear after a synthetic MA-server-poll with a canned provider response, and flip `tier_requirements` to include `working_config_flow` + `integration_test_passes` + `no_manual_yaml_required`.

## Files

- `connection.yml` — the source-of-truth manifest.
- `__init__.py` — `DOMAIN = "music-assistant"` marker for the audit.
- `docs/recipe.md` — the full howto (HACS wiring, Path A HA add-on, Path B external MA server, provider configuration, HA helpers, mode-aware media automations that respect Stealth silent hours + Travel motion + Boost zone volumes + inverter-SOC power-aware pausing + TTS-zone-pinning, troubleshooting, tier-a promotion outline).
- `tests/test_connection_yml.py` — manifest honesty checks.

## See also

- Legacy catalog page (now superseded by the connection manifest):
  [the legacy spec](../../the legacy spec)
- Catalog category index: the legacy spec
- Starlink connection (companion van-networking slice — long-range WAN that supports the cloud paths MA may use):
  `connections/starlink/`
- Teltonika connection (companion mobile-internet slice — cellular WAN):
  `connections/teltonika/`
- Peplink connection (companion multi-WAN slice):
  `connections/peplink/`
- MQTT broker (cross-reference — MA could ride MQTT if a community exporter is installed):
  `connections/mqtt/`
- RoamCore entity naming: `docs/reference/rc-entity-naming.md`
