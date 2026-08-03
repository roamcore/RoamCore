# Music Assistant — tier-b recipe connection

**Tier:** B (recipe)
**Audience:** A RoamCore user who wants multi-room (multi-zone) audio in
their van — provider-agnostic (Spotify, Apple Music, TuneIn, local files,
Chromecast / AirPlay / Sonos receivers), orchestrated by Home Assistant
through the upstream HACS `music_assistant` integration, and surfaced on
the RoamCore dashboard as `rc_media_*` contract tiles + OpenClaw media
queries ("what's playing?", "what zone is on?", "pause all music",
"resume last playlist", "switch to outdoor zone", "set volume 30 on
bedroom", "play <artist/album/playlist>", "how many artists in
library?").

This howto is mirrored into `docs/connections/music-assistant.md` by the
catalog cron (`scripts/build_catalog.py`) so it shows up under the public
docs site's "Connections" section. Keep this recipe as the source of
truth.

## What is Music Assistant in RoamCore?

Music Assistant (<https://www.music-assistant.io/>) is a provider-
agnostic multi-room audio orchestrator. It ships a single "play
everywhere" surface that abstracts over Spotify, Apple Music, TuneIn,
local files, Chromecast / AirPlay / Sonos / DLNA / UPnP receivers, and
unifies them behind per-zone player controls (volume, play/pause,
queue, source) + a single shared library + a single now-playing
metadata stream. It exposes the upstream HACS `music_assistant`
integration (<https://github.com/music-assistant/hass-music-assistant>)
that registers `media_player.*` entities per zone in Home Assistant
(names look like `media_player.mass_living_room_speaker`,
`media_player.mass_bedroom`, `media_player.mass_outdoor_deck`,
etc.) and gives HA a clean service surface for `play_media`,
`turn_off`, `volume_set`, `media_next`, `media_previous`, etc.

In RoamCore, Music Assistant is the **multi-room van audio** slice:

- **Per-zone media_player entities** (`media_player.rc_media_zone_living`,
  `media_player.rc_media_zone_bed`, `media_player.rc_media_zone_outdoor`)
  — vendor-neutral aliases of the upstream MA players, surfaced on the
  RoamCore dashboard as the canonical media controls.
- **Now-playing metadata trio** (`sensor.rc_media_now_playing_title` /
  `_artist` / `_album`) — the RoamCore contract layer exposes the
  upstream MA "currently playing" metadata so OpenClaw can answer
  "what's playing?" without needing to read the upstream `media_player`
  attributes directly.
- **Library counts** (`sensor.rc_media_library_artists_count` /
  `_albums_count` / `_tracks_count`) — sourced from the upstream MA
  library endpoint; answers OpenClaw queries like "how many artists in
  library?".
- **`any_player_playing` binary sensor** (`binary_sensor.rc_media_any_player_playing`)
  — ON when any zone is actively playing; OFF when all zones are
  paused/idle.
- **`active_zone` sensor** (`sensor.rc_media_active_zone`) — the
  zone currently playing (or `none` when all zones are paused).
- **`pause_all` button** (`button.rc_media_pause_all`) — one-tap
  "pause every zone". Wires to `media_player.turn_off` on every
  `rc_media_zone_*` entity; provider-agnostic (the upstream HACS MA
  integration abstracts over Chromecast / AirPlay / Sonos / DLNA / UPnP
  receivers, so the same `turn_off` call reaches them all).
- **`resume_last` button** (`button.rc_media_resume_last`) — one-tap
  "resume the last playlist on the default zone". Wires to
  `media_player.play_media` on `rc_media_default_zone` with the
  operator's last-known playlist/album/artist URI.
- **`default_zone` select** (`select.rc_media_default_zone`) — the
  zone the `resume_last` button targets; operator-configurable.
- **Mode-aware behavior** is built into the recipe: Stealth silent
  hours auto-pause all players unless the active zone is `bed`;
  Travel mode auto-resumes the last playlist on outdoor motion with
  a 60 % volume cap; Boost mode defaults the outdoor zone to 80 %
  and all other zones to 30 %; a power-aware automation pauses all
  media when the inverter SOC drops below 25 % AND shore power is
  disconnected; TTS announcements are pinned to
  `media_player.rc_media_zone_living` only (never bleeding into the
  bedroom at night).
- **OpenClaw media queries** ("what's playing?", "what zone is on?",
  "pause all music", "resume last playlist", "switch to outdoor
  zone", "set volume 30 on bedroom", "play
  <artist/album/playlist>", "how many artists in library?") bind to
  the contract entities. The corresponding OpenClaw query keys
  (used by the agent wiring) are: `whats_playing`, `what_zone_is_on`,
  `pause_all_music`, `resume_last_playlist`, `switch_to_outdoor_zone`,
  `set_volume_30_on_bedroom`, `play_artist_album_playlist`,
  `how_many_artists_in_library` — the recipe exposes a
  `button.rc_media_pause_all` for the `pause_all_music` agent-action
  allowlist so the OpenClaw wiring has a known-good button to call.

RoamCore does **not** ship a Music Assistant server or a RoamCore-
owned native integration. There is no canonical RoamCore-owned
upstream HA integration for "talk to a Music Assistant server as a
multi-room van audio slice" — the operator's Path A-vs-B choice is
HAOS-vs-not + memory + fleet needs driven, and the underlying HACS
`music_assistant` integration is the upstream truth. So we publish a
recipe that walks you through the wiring, then layer a small
contract on top: the `rc_media_*` dashboard tiles + the OpenClaw
queries that bind to those contract entities.

**Why tier-b:** RoamCore has no real Music Assistant server on the
bench to integration-test against, no native HA integration to point
at, and the operator's Path A-vs-B choice + provider mix is HAOS-vs-
not + memory + fleet needs + personal-taste driven — so the audit-
recommended config_flow can't be canonical here. The recipe is sound
(it leans on the upstream HACS `music_assistant` integration + the
well-understood MA provider ecosystem + the auto-discover via
zeroconf), but we cannot claim one-tap automation. The promotion
outline at the bottom of this recipe describes exactly what needs
to happen to flip this to tier-a.

**Two install paths (operator picks based on host OS + memory +
fleet size):**

- **Path A — Music Assistant HA add-on (recommended for HAOS
  installs where the operator wants MA to ship with HA).** The
  operator adds the HACS repository
  `music-assistant/hass-music-assistant`, installs the HACS
  `music_assistant` integration, and the upstream HA add-on runs
  the MA server inside the HA host. HA auto-discovers the MA server
  via zeroconf on the LAN and the config_flow launches. No manual
  URL entry.
- **Path B — External Music Assistant server (recommended for fleet
  installs + non-HAOS hosts that need the MA server decoupled from
  HA — e.g. the HA box is on a memory-constrained VP2430 but the
  MA server lives on the NAS Docker host for memory reasons).**
  The operator pulls the upstream `ghcr.io/music-assistant/server`
  container (or `linuxserver/music-assistant` for LSI Docker hosts),
  runs it on a separate host on the LAN, installs the same HACS
  `music_assistant` integration in HA, and points the integration
  at the external MA server URL (default `http://ma.lan:8095`).
  HA imports the players; the contract tiles are identical.

Both paths land on the same `rc_media_*` contract tiles. The wizard
asks the operator which path they wired; the contract tiles are
identical either way.

## Prerequisites

Before starting the recipe, make sure you have:

- **Home Assistant 2023.8 or newer** (the upstream HACS
  `music_assistant` integration has a config_flow since 2023).
- **HACS installed** on your HA instance (Music Assistant is
  HACS-only — HA core does NOT include Music Assistant; MA is
  fetched from `music-assistant/hass-music-assistant` via HACS →
  Repositories → Add). Install HACS via
  <https://hacs.xyz/docs/setup/download>.
- **At least one media player reachable on the LAN** for Path A —
  typically a Chromecast Audio / Google Nest Audio / Sonos One /
  AirPlay receiver / DLNA / UPnP speaker. For Path B, the MA
  server itself runs as a separate container (the upstream
  `ghcr.io/music-assistant/server` image or
  `linuxserver/music-assistant` for LSI Docker hosts), reachable
  on `http://ma.lan:8095` from HA.
- **A network-reachable MA server** (Path A: the HA add-on
  inside the HA host; Path B: the external MA server URL —
  typically `http://ma.lan:8095`). For Path B, make sure HA can
  reach the MA server on the LAN and the MA server can reach
  the LAN media players (the MA server acts as the player
  controller).
- **At least one provider configured** — Spotify (OAuth), Apple
  Music (developer token), local-files library mount, TuneIn
  radio, or a Chromecast / AirPlay / Sonos receiver. The
  recipe §7 walks through each provider.
- **Hardware callouts (typical van install):** small amplifiers
  (e.g. TPA3116 / TPA3118 / Sure Electronics) behind passive
  speakers for the living + bed zones (MA streams to them via
  AirPlay or Chromecast Audio dongles), plus a Sonos-like Wi-Fi
  speaker for outdoor (e.g. Sonos Roam, JBL Charge Wi-Fi mode,
  or a Chromecast-Audio dongle + outdoor passive speakers). The
  outdoor zone needs at least one Wi-Fi speaker for MA to
  control. For kitchen (overlap with living), a Chromecast Audio
  is the simplest path. None of these are required for the
  recipe — the operator picks the player topology.

## Path A — Music Assistant HA add-on (recommended for HAOS installs)

The default install for RoamCore users on HAOS who want MA to ship
with HA.

### A.1 — Install HACS if you haven't already

1. Install HACS on your HA instance per
   <https://hacs.xyz/docs/setup/download>. HACS is the Home
   Assistant Community Store — required for Music Assistant
   (MA is HACS-only).

### A.2 — Add the HACS repository for Music Assistant

The upstream MA HACS integration IS in the HACS default store, so
you can find it via:

1. In HA → **HACS → Integrations → Explore & Add Repositories**,
   search for "Music Assistant" (the integration by
   `music-assistant`).
2. Install the `music_assistant` integration and restart HA.

If the integration isn't in the default store (e.g. you pinned
HACS to a strict allowlist), add the repository manually:

1. In HA → **HACS → Integrations → three-dot menu → Custom
   repositories**.
2. Add `https://github.com/music-assistant/hass-music-assistant`
   as an **Integration**.
3. Install the `music_assistant` integration and restart HA.

### A.3 — Add the MA integration in HA (config_flow)

In HA → **Settings → Devices & Services → Add Integration →
Music Assistant**, with:

- Discovery: **Auto-discover** (HA finds the local MA server via
  zeroconf on the LAN — this is the Path A add-on path).
- API key: leave blank for the local add-on (the integration
  negotiates the local auth token automatically).

For Path B (external MA server), use the manual entry:

- API base URL: `http://ma.lan:8095` (or whatever your external
  MA server URL is).
- API key: the operator-configured API key from the MA server's
  Settings → Security page.

HA will create a handful of base MA entities per zone (per
`media_player.mass_*` device the MA server reports).

### A.4 — Configure at least one provider

The recipe §7 walks through each provider (Spotify OAuth,
Apple Music developer token, local-files library mount, TuneIn,
Chromecast / AirPlay / Sonos receivers). At least one provider
is required for MA to play anything.

### A.5 — Verify MA is talking to HA

1. Open the RoamCore dashboard → **Media** section (or the MA
   integration's device page).
2. The `media_player.mass_*` entities should be visible. Tap
   one to play a test track.
3. If MA can't reach a player, check §8 (Troubleshooting).

## Path B — External Music Assistant server (recommended for fleet installs + non-HAOS hosts)

Identical contract + helpers as Path A; the only difference is
how the operator runs the MA server (separate container on the
LAN, decoupled from HA).

### B.1 — Run the upstream MA server container

Pick one:

- **Upstream OCI image:** `ghcr.io/music-assistant/server`
  (the official MA server image, recommended for Docker /
  Podman hosts).
- **LinuxServer.io image:** `linuxserver/music-assistant`
  (LSI-style image for Synology / QNAP / Unraid NAS hosts;
  recommended for NAS-Docker hosts).

Example `docker-compose.yml` for the upstream OCI image:

```yaml
version: "3.8"
services:
  music-assistant:
    image: ghcr.io/music-assistant/server
    container_name: music-assistant
    restart: unless-stopped
    ports:
      - "8095:8095"
    volumes:
      - ./data:/data
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
```

For the LSI image, follow the
<https://hub.docker.com/r/linuxserver/music-assistant> readme
(Synology / QNAP / Unraid paths).

### B.2 — Configure the MA server

1. Browse to `http://ma.lan:8095` (replace `ma.lan` with the
   container's LAN IP).
2. Walk through the MA server's first-run wizard — provider
   configuration, player discovery, library mount.
3. (Optional but recommended) Configure an API key in MA server
   Settings → Security for the HACS integration to authenticate.

### B.3 — Install HACS + add the MA repository (same as Path A)

Follow §A.1 + §A.2 above.

### B.4 — Add the MA integration in HA (manual entry)

In HA → **Settings → Devices & Services → Add Integration →
Music Assistant**, with:

- API base URL: `http://ma.lan:8095`.
- API key: the API key from §B.2.

HA will import the players from the MA server; the upstream
integration creates one `media_player.mass_*` entity per MA zone.

### B.5 — Map MA entities to the same contract helpers

Same as Path A — drop the recipe §5.1 helper YAML into the
same package, and replace the `media_player.mass_*` references
with the entity ids your MA integration exposes (per-zone entities
look like `media_player.mass_living_room_speaker`,
`media_player.mass_bedroom`, `media_player.mass_outdoor_deck`,
etc.). The contract tiles stay identical; only the upstream
sourcing changes.

### B.6 — Verify

Same as Path A §A.5 — the contract tiles + the pause_all /
resume_last buttons behave identically. The only difference is
the upstream sourcing (local HA add-on vs external MA container).

## §5 RoamCore contract entities

The full listing the wizard + dashboard + OpenClaw rely on:

| Entity | Type | States | Source |
|---|---|---|---|
| `media_player.rc_media_zone_living` | media_player | per upstream MA player (e.g. Sonos / Chromecast / AirPlay) | template media_player alias of upstream `media_player.mass_living_room_speaker` |
| `media_player.rc_media_zone_bed` | media_player | per upstream MA player | template media_player alias of upstream `media_player.mass_bedroom` |
| `media_player.rc_media_zone_outdoor` | media_player | per upstream MA player | template media_player alias of upstream `media_player.mass_outdoor_deck` |
| `binary_sensor.rc_media_any_player_playing` | binary_sensor | ON / OFF | template: any `rc_media_zone_*` state == `playing` |
| `sensor.rc_media_active_zone` | sensor | `living \| bed \| outdoor \| none` | template: which `rc_media_zone_*` is currently `playing` |
| `sensor.rc_media_now_playing_title` | sensor | string (title) | template: `media_player.rc_media_zone_*` attribute `media_title` |
| `sensor.rc_media_now_playing_artist` | sensor | string (artist) | template: `media_player.rc_media_zone_*` attribute `media_artist` |
| `sensor.rc_media_now_playing_album` | sensor | string (album) | template: `media_player.rc_media_zone_*` attribute `media_album_name` |
| `sensor.rc_media_library_artists_count` | sensor | int count | template: MA library endpoint, artists count |
| `sensor.rc_media_library_albums_count` | sensor | int count | template: MA library endpoint, albums count |
| `sensor.rc_media_library_tracks_count` | sensor | int count | template: MA library endpoint, tracks count |
| `button.rc_media_pause_all` | button | (press) | calls `media_player.turn_off` on every `rc_media_zone_*` |
| `button.rc_media_resume_last` | button | (press) | calls `media_player.play_media` on `rc_media_default_zone` with the last-known playlist URI |
| `select.rc_media_default_zone` | select | `living \| bed \| outdoor` | operator choice; `resume_last` targets this |

All grayed-out / `unknown` fallback when the upstream MA
integration is in error state (MA server unreachable, API key
wrong, provider auth expired, MA server crashed).

### §5.1 — Copy-pasteable helper YAML

Drop into `homeassistant/packages/roamcore_media.yaml`:

```yaml
# RoamCore Media contract helpers (recipe §5.1).
# All entities are vendor-neutral per docs/reference/rc-entity-naming.md.
# Replace `media_player.mass_*` references with the actual entity ids
# your MA integration exposes.

input_text:
  rc_media_last_played_uri:
    name: Music Assistant last-played URI (contract)
    icon: mdi:music-note

input_select:
  rc_media_default_zone_raw:
    name: Music Assistant default zone (contract)
    options:
      - living
      - bed
      - outdoor
    icon: mdi:speaker

template:
  - media_player:
      # Per-zone aliases — the upstream MA integration registers
      # `media_player.mass_<zone>` entities; the recipe aliases them
      # into the vendor-neutral `rc_media_zone_*` family. When the
      # upstream names don't naturally map (e.g.
      # `media_player.mass_outdoor_deck` vs `rc_media_zone_outdoor`),
      # the alias reads the upstream entity's state + attributes and
      # exposes them under the contract name.
      - name: Music Assistant zone living (contract)
        unique_id: rc_media_zone_living
        value_template: "{{ states('media_player.mass_living_room_speaker') }}"
        attributes:
          volume_level: "{{ state_attr('media_player.mass_living_room_speaker', 'volume_level') }}"
          media_title: "{{ state_attr('media_player.mass_living_room_speaker', 'media_title') }}"
          media_artist: "{{ state_attr('media_player.mass_living_room_speaker', 'media_artist') }}"
          media_album_name: "{{ state_attr('media_player.mass_living_room_speaker', 'media_album_name') }}"
          is_volume_muted: "{{ state_attr('media_player.mass_living_room_speaker', 'is_volume_muted') }}"
        turn_on:
          service: media_player.turn_on
          target:
            entity_id: media_player.mass_living_room_speaker
        turn_off:
          service: media_player.turn_off
          target:
            entity_id: media_player.mass_living_room_speaker
        volume_set:
          service: media_player.volume_set
          target:
            entity_id: media_player.mass_living_room_speaker
          data:
            volume_level: "{{ volume_level }}"
        volume_mute:
          service: media_player.volume_mute
          target:
            entity_id: media_player.mass_living_room_speaker
          data:
            is_volume_muted: "{{ is_volume_muted }}"
        media_play:
          service: media_player.media_play
          target:
            entity_id: media_player.mass_living_room_speaker
        media_pause:
          service: media_player.media_pause
          target:
            entity_id: media_player.mass_living_room_speaker
        media_next_track:
          service: media_player.media_next_track
          target:
            entity_id: media_player.mass_living_room_speaker
        media_previous_track:
          service: media_player.media_previous_track
          target:
            entity_id: media_player.mass_living_room_speaker
        play_media:
          service: media_player.play_media
          target:
            entity_id: media_player.mass_living_room_speaker
          data:
            media_content_type: "{{ media_content_type }}"
            media_content_id: "{{ media_content_id }}"
      - name: Music Assistant zone bed (contract)
        unique_id: rc_media_zone_bed
        value_template: "{{ states('media_player.mass_bedroom') }}"
        attributes:
          volume_level: "{{ state_attr('media_player.mass_bedroom', 'volume_level') }}"
          media_title: "{{ state_attr('media_player.mass_bedroom', 'media_title') }}"
          media_artist: "{{ state_attr('media_player.mass_bedroom', 'media_artist') }}"
          media_album_name: "{{ state_attr('media_player.mass_bedroom', 'media_album_name') }}"
          is_volume_muted: "{{ state_attr('media_player.mass_bedroom', 'is_volume_muted') }}"
        turn_on:
          service: media_player.turn_on
          target:
            entity_id: media_player.mass_bedroom
        turn_off:
          service: media_player.turn_off
          target:
            entity_id: media_player.mass_bedroom
        volume_set:
          service: media_player.volume_set
          target:
            entity_id: media_player.mass_bedroom
          data:
            volume_level: "{{ volume_level }}"
        volume_mute:
          service: media_player.volume_mute
          target:
            entity_id: media_player.mass_bedroom
          data:
            is_volume_muted: "{{ is_volume_muted }}"
        media_play:
          service: media_player.media_play
          target:
            entity_id: media_player.mass_bedroom
        media_pause:
          service: media_player.media_pause
          target:
            entity_id: media_player.mass_bedroom
        media_next_track:
          service: media_player.media_next_track
          target:
            entity_id: media_player.mass_bedroom
        media_previous_track:
          service: media_player.media_previous_track
          target:
            entity_id: media_player.mass_bedroom
        play_media:
          service: media_player.play_media
          target:
            entity_id: media_player.mass_bedroom
          data:
            media_content_type: "{{ media_content_type }}"
            media_content_id: "{{ media_content_id }}"
      - name: Music Assistant zone outdoor (contract)
        unique_id: rc_media_zone_outdoor
        value_template: "{{ states('media_player.mass_outdoor_deck') }}"
        attributes:
          volume_level: "{{ state_attr('media_player.mass_outdoor_deck', 'volume_level') }}"
          media_title: "{{ state_attr('media_player.mass_outdoor_deck', 'media_title') }}"
          media_artist: "{{ state_attr('media_player.mass_outdoor_deck', 'media_artist') }}"
          media_album_name: "{{ state_attr('media_player.mass_outdoor_deck', 'media_album_name') }}"
          is_volume_muted: "{{ state_attr('media_player.mass_outdoor_deck', 'is_volume_muted') }}"
        turn_on:
          service: media_player.turn_on
          target:
            entity_id: media_player.mass_outdoor_deck
        turn_off:
          service: media_player.turn_off
          target:
            entity_id: media_player.mass_outdoor_deck
        volume_set:
          service: media_player.volume_set
          target:
            entity_id: media_player.mass_outdoor_deck
          data:
            volume_level: "{{ volume_level }}"
        volume_mute:
          service: media_player.volume_mute
          target:
            entity_id: media_player.mass_outdoor_deck
          data:
            is_volume_muted: "{{ is_volume_muted }}"
        media_play:
          service: media_player.media_play
          target:
            entity_id: media_player.mass_outdoor_deck
        media_pause:
          service: media_player.media_pause
          target:
            entity_id: media_player.mass_outdoor_deck
        media_next_track:
          service: media_player.media_next_track
          target:
            entity_id: media_player.mass_outdoor_deck
        media_previous_track:
          service: media_player.media_previous_track
          target:
            entity_id: media_player.mass_outdoor_deck
        play_media:
          service: media_player.play_media
          target:
            entity_id: media_player.mass_outdoor_deck
          data:
            media_content_type: "{{ media_content_type }}"
            media_content_id: "{{ media_content_id }}"
  - binary_sensor:
      - name: Music Assistant any player playing (contract)
        unique_id: rc_media_any_player_playing
        state: >
          {{ is_state('media_player.rc_media_zone_living', 'playing')
             or is_state('media_player.rc_media_zone_bed', 'playing')
             or is_state('media_player.rc_media_zone_outdoor', 'playing') }}
        device_class: running
        icon: mdi:music
  - sensor:
      - name: Music Assistant active zone (contract)
        unique_id: rc_media_active_zone
        state: >
          {% if is_state('media_player.rc_media_zone_living', 'playing') %}
            living
          {% elif is_state('media_player.rc_media_zone_bed', 'playing') %}
            bed
          {% elif is_state('media_player.rc_media_zone_outdoor', 'playing') %}
            outdoor
          {% else %}
            none
          {% endif %}
        icon: mdi:speaker
      - name: Music Assistant now-playing title (contract)
        unique_id: rc_media_now_playing_title
        state: >
          {% if is_state('binary_sensor.rc_media_any_player_playing', 'on') %}
            {{ state_attr('media_player.rc_media_zone_' ~ states('sensor.rc_media_active_zone'), 'media_title') }}
          {% else %}
            unknown
          {% endif %}
        icon: mdi:music-note
      - name: Music Assistant now-playing artist (contract)
        unique_id: rc_media_now_playing_artist
        state: >
          {% if is_state('binary_sensor.rc_media_any_player_playing', 'on') %}
            {{ state_attr('media_player.rc_media_zone_' ~ states('sensor.rc_media_active_zone'), 'media_artist') }}
          {% else %}
            unknown
          {% endif %}
        icon: mdi:account-music
      - name: Music Assistant now-playing album (contract)
        unique_id: rc_media_now_playing_album
        state: >
          {% if is_state('binary_sensor.rc_media_any_player_playing', 'on') %}
            {{ state_attr('media_player.rc_media_zone_' ~ states('sensor.rc_media_active_zone'), 'media_album_name') }}
          {% else %}
            unknown
          {% endif %}
        icon: mdi:album
      - name: Music Assistant library artists count (contract)
        unique_id: rc_media_library_artists_count
        state: "{{ state_attr('media_player.mass_library', 'artists_count') | int(0) }}"
        icon: mdi:account-music-outline
      - name: Music Assistant library albums count (contract)
        unique_id: rc_media_library_albums_count
        state: "{{ state_attr('media_player.mass_library', 'albums_count') | int(0) }}"
        icon: mdi:album
      - name: Music Assistant library tracks count (contract)
        unique_id: rc_media_library_tracks_count
        state: "{{ state_attr('media_player.mass_library', 'tracks_count') | int(0) }}"
        icon: mdi:music-note

select:
  - name: Music Assistant default zone (contract)
    unique_id: rc_media_default_zone
    options:
      - living
      - bed
      - outdoor
    icon: mdi:speaker

button:
  - name: Music Assistant pause all (contract)
    unique_id: rc_media_pause_all
    icon: mdi:pause
    # The §6.1 Stealth automation listens for this press as a
    # no-op (the automation already paused everything); explicit
    # button presses bypass the Stealth check.
    # OpenClaw agent-action allowlist: this button is the target
    # of the `pause_all_music` query key.
    press:
      - service: media_player.media_pause
        target:
          entity_id:
            - media_player.rc_media_zone_living
            - media_player.rc_media_zone_bed
            - media_player.rc_media_zone_outdoor
  - name: Music Assistant resume last (contract)
    unique_id: rc_media_resume_last
    icon: mdi:play
    # Resume the last-known playlist/album/artist URI on the
    # default zone; the URI is captured by the §6.6
    # "remember-last-played" automation.
    # OpenClaw agent-action allowlist: this button is the target
    # of the `resume_last_playlist` query key.
    press:
      - service: media_player.play_media
        target:
          entity_id: >-
            media_player.rc_media_zone_{{ states('select.rc_media_default_zone') }}
        data:
          media_content_type: music
          media_content_id: "{{ states('input_text.rc_media_last_played_uri') }}"
```

## §6 Automations

Five sample automations, copy-pasteable into
`homeassistant/automations/roamcore_media_*.yaml`:

### §6.1 — Stealth: auto-pause all players unless zone is `bed`

```yaml
alias: Music Assistant — Stealth auto-pause (preserve bed zone only)
mode: single
trigger:
  - platform: state
    entity_id: input_select.rc_mode
    to: "stealth"
  - platform: time
    at: "22:00:00"
condition:
  # Don't double-pause if we're already paused.
  - condition: state
    entity_id: binary_sensor.rc_media_any_player_playing
    state: "on"
action:
  - choose:
      # Preserve the bedroom zone — Stealth = silent hours; bedroom
      # is the only tolerated zone.
      - conditions:
          - condition: state
            entity_id: sensor.rc_media_active_zone
            state: "bed"
        sequence:
          - service: persistent_notification.create
            data:
              title: RoamCore — Stealth media: bedroom zone preserved
              message: >-
                Stealth silent hours started; bedroom zone remains
                active. Outdoor + living zones paused.
      # Pause everything else.
      - conditions:
          - condition: template
            value_template: >
              {{ states('sensor.rc_media_active_zone') in ['living', 'outdoor', 'none'] }}
        sequence:
          - service: media_player.media_pause
            target:
              entity_id:
                - media_player.rc_media_zone_living
                - media_player.rc_media_zone_outdoor
          - service: persistent_notification.create
            data:
              title: RoamCore — Stealth media: paused all zones
              message: >-
                Stealth silent hours started; paused living + outdoor
                zones. Bedroom zone unaffected.
```

### §6.2 — Travel: auto-resume last playlist on outdoor motion (60 % volume cap)

```yaml
alias: Music Assistant — Travel motion: auto-resume outdoor (60% cap)
mode: single
trigger:
  - platform: state
    entity_id: binary_sensor.rc_motion_outdoor
    to: "on"
condition:
  - condition: state
    entity_id: input_select.rc_mode
    state: "travel"
  # Don't resume if a zone is already playing (avoid stomping).
  - condition: state
    entity_id: binary_sensor.rc_media_any_player_playing
    state: "off"
action:
  - service: media_player.volume_set
    target:
      entity_id: media_player.rc_media_zone_outdoor
    data:
      volume_level: 0.6   # 60% volume cap for Travel mode
  - service: media_player.play_media
    target:
      entity_id: media_player.rc_media_zone_outdoor
    data:
      media_content_type: music
      media_content_id: "{{ states('input_text.rc_media_last_played_uri') }}"
  - service: persistent_notification.create
    data:
      title: RoamCore — Travel media: outdoor zone resumed
      message: >-
        Travel mode + outdoor motion detected; resumed last playlist
        on the outdoor zone at 60 % volume.
```

### §6.3 — Boost: outdoor defaults 80 %, others default 30 %

```yaml
alias: Music Assistant — Boost mode: outdoor 80%, others 30%
mode: single
trigger:
  - platform: state
    entity_id: input_select.rc_mode
    to: "boost"
action:
  - service: media_player.volume_set
    target:
      entity_id: media_player.rc_media_zone_outdoor
    data:
      volume_level: 0.8
  - service: media_player.volume_set
    target:
      entity_id:
        - media_player.rc_media_zone_living
        - media_player.rc_media_zone_bed
    data:
      volume_level: 0.3
  - service: persistent_notification.create
    data:
      title: RoamCore — Boost media: zone volumes set
      message: >-
        Boost mode entered; outdoor zone set to 80 %, living + bed
        zones set to 30 %.
```

### §6.4 — Power-aware: pause all media when inverter SOC < 25 % AND shore disconnected

```yaml
alias: Music Assistant — Power-aware: pause all on low SOC + shore disconnected
mode: single
trigger:
  - platform: numeric_state
    entity_id: sensor.rc_power_battery_soc
    below: 25
condition:
  - condition: state
    entity_id: binary_sensor.rc_power_shore_connected
    state: "off"
  - condition: state
    entity_id: binary_sensor.rc_media_any_player_playing
    state: "on"
action:
  - service: media_player.media_pause
    target:
      entity_id:
        - media_player.rc_media_zone_living
        - media_player.rc_media_zone_bed
        - media_player.rc_media_zone_outdoor
  - service: persistent_notification.create
    data:
      title: RoamCore — Power-aware media: paused all zones
      message: >-
        Inverter SOC {{ states('sensor.rc_power_battery_soc') }} %
        (below 25 %) AND shore power disconnected; paused all media
        zones to preserve battery for mission-critical systems.
```

### §6.5 — TTS: pin announcements to the living-room zone only

```yaml
alias: Music Assistant — TTS pin to living zone only
mode: single
trigger:
  - platform: state
    entity_id: tts.google_translate_en_compatible
    attribute: is_streaming
    to: "true"
condition: []
action:
  # Override the default TTS target to ensure announcements never
  # bleed into the bedroom at night. If the operator wants TTS on
  # a different zone, they can override this automation.
  - choose:
      - conditions:
          - condition: template
            value_template: >
              {{ state_attr('tts.google_translate_en_compatible', 'media_player_entity_id') != 'media_player.rc_media_zone_living' }}
        sequence:
          - service: tts.clear_cache
            data:
              entity_id: tts.google_translate_en_compatible
          - service: persistent_notification.create
            data:
              title: RoamCore — TTS zone override
              message: >-
                Detected TTS playback targeting a non-living zone;
                please verify your TTS automation uses
                `media_player.rc_media_zone_living` as the
                `media_player_entity_id` to prevent bedroom bleed
                at night.
```

### §6.6 — Remember-last-played (drives the `resume_last` button)

```yaml
alias: Music Assistant — remember last played URI for resume_last button
mode: single
trigger:
  - platform: state
    entity_id:
      - media_player.rc_media_zone_living
      - media_player.rc_media_zone_bed
      - media_player.rc_media_zone_outdoor
    attribute: media_content_id
action:
  - service: input_text.set_value
    target:
      entity_id: input_text.rc_media_last_played_uri
    data:
      value: "{{ trigger.to_state.attributes.media_content_id }}"
```

## §7 Provider setup notes

Concise subsections for each provider. MA supports many more
(check <https://music-assistant.io/providers/> for the canonical
list), but these cover the most common van installs.

### §7.1 — Spotify

1. In MA web UI → **Settings → Providers → Add Provider →
   Spotify**.
2. MA will redirect you to Spotify's OAuth flow. Authorize MA.
3. MA auto-imports your Spotify playlists, albums, artists,
   tracks.
4. **Note:** Spotify requires a Premium account for full MA
   control (free accounts can play via Spotify Connect but MA
   cannot control playback).

### §7.2 — Apple Music

1. Generate an Apple Music developer token via the
   `MediaToken` generator (third-party tool, search "Apple
   Music MediaToken generator" — the token lasts ~6 months
   before you need to regenerate).
2. In MA web UI → **Settings → Providers → Add Provider →
   Apple Music**.
3. Paste the developer token. MA will index your Apple Music
   library.

### §7.3 — TuneIn / radio

1. In MA web UI → **Settings → Providers → Add Provider →
   TuneIn**.
2. No auth required — TuneIn is free.
3. Browse stations via MA's web UI; add favorites to your
   library.

### §7.4 — Local-files library mount

1. Mount a local files directory into the MA server container
   (Path B) or into the HA add-on (Path A). For Path B, add a
   bind mount in your `docker-compose.yml`:

```yaml
volumes:
  - /srv/roamcore/media:/media:ro   # read-only mount
```

2. In MA web UI → **Settings → Providers → Add Provider →
   Filesystem** (or "Local Files").
3. Point at the mount path. MA scans the directory on a
   schedule; tracks appear in the library.

### §7.5 — Chromecast / AirPlay / Sonos receivers

1. Make sure the receiver is on the LAN (Wi-Fi or wired).
2. For Chromecast: enable mDNS / multicast on the LAN
   (most routers do this by default; OpenWrt may need
   `igmpproxy` + `avahi` packages — see the OpenWrt recipe).
3. For AirPlay: same — mDNS / multicast.
4. For Sonos: Sonos uses its own discovery protocol; the
   MA server auto-discovers Sonos devices on the LAN.
5. In MA web UI → **Settings → Players**, the discovered
   receivers appear. Assign each to a zone (living / bed /
   outdoor).

## §8 Troubleshooting

- **MA server unreachable from HA.** The most common Path B
  runtime error — HA cannot reach the external MA server at
  `http://ma.lan:8095`. Check: is the MA container running
  (`docker ps` / Portainer / Synology Container Manager)?
  Is the LAN IP routable from HA (can HA reach
  `http://ma.lan:8095/` in a browser)? Is there a firewall
  blocking UDP/5353 (zeroconf / mDNS) on the LAN? Is there
  a TLS cert issue if you're using `https://ma.lan:8095`
  with a self-signed cert (HA may reject it)?
- **HACS integration can't find the MA server.** Verify the
  API key matches MA server Settings → Security (Path B).
  Verify the URL format is `http://ma.lan:8095` (no trailing
  slash, no `https://` if you didn't set up TLS). For Path
  A, the HACS integration should auto-discover the local
  add-on via zeroconf; if auto-discovery fails, restart the
  HA add-on + reload the integration.
- **Player discovery incomplete.** Chromecast / AirPlay
  receivers not showing up in MA. Usually multicast routing
  on the LAN is the culprit — the OpenWrt recipe may need
  `igmpproxy` + `avahi` packages, or the router's AP
  isolation is blocking multicast between the HA host and
  the players. Verify with `tcpdump` on the HA host that
  mDNS packets (`udp port 5353`) are arriving from the
  player IPs.
- **TTS degrades to group playback instead of single-zone.**
  When TTS targets `media_player.rc_media_zone_living` but
  the living zone is part of an MA group (e.g. grouped with
  outdoor), the TTS announcement plays on every zone in the
  group. Use the `speak` service with a specific
  `media_player_entity_id:` instead of grouping, or ungroup
  the living zone before TTS.
- **Library scan loop stuck.** MA's library database can
  corrupt under heavy provider churn (e.g. Spotify auth
  expiring + being re-granted repeatedly). Stop the MA
  server, delete the MA library DB (typically
  `/data/library.db` in the container), restart MA — MA
  will re-import the library from scratch. This is also the
  fix for "library counts never settle" issues.
- **Zone volume max-out not sticking across reboot.** When
  the operator maxes a zone's volume in MA's web UI
  (Settings → Players → `<zone>` → Volume Max), the setting
  can revert to the MA default after a container / HA
  restart. Set the `default_volume` per zone in MA
  Settings → Players → `<zone>` → Default Volume — this
  persists across restarts.
- **Provider auth expired mid-trip.** Spotify and Apple Music
  tokens expire; if a token expires mid-trip, MA will stop
  being able to control playback for that provider. Re-auth
  the provider in MA's web UI (Settings → Providers →
  `<provider>` → Re-authenticate). For Apple Music, this
  means regenerating the developer token (§7.2).
- **`active_zone` shows `none` but a zone is clearly playing.**
  This usually means the `media_player.mass_*` upstream entity
  has a state of `playing` but the alias template hasn't
  picked it up yet (HA template evaluation lags by a few
  seconds). Force a state refresh via the upstream
  `homeassistant.update_entity` service on the affected
  `mass_*` entity. If the issue persists, check that the
  upstream `media_player.mass_*` state attribute names
  match what the alias template reads (some MA versions
  expose `media_content_id` instead of `media_content_type`).
- **`button.rc_media_pause_all` doesn't pause the bedroom.**
  If the bedroom is grouped with another MA zone, pausing
  the bedroom alias might not propagate to the upstream
  MA player. Ungroup the bedroom first, then re-test.

## §9 Privacy

- **MA does NOT phone home by default.** The MA server is
  self-hosted (Path A HA add-on or Path B external
  container); no telemetry is sent to music-assistant.io
  by default. Provider auth tokens (Spotify, Apple Music)
  stay on the MA server.
- **Provider auth tokens stay local.** Spotify OAuth tokens
  and Apple Music developer tokens are stored on the MA
  server (Path A: the HA add-on's persistent volume; Path
  B: the external container's `/data` volume). They are
  not published to any external service beyond the
  provider's own API (which is required for MA to talk to
  Spotify / Apple Music at all).
- **Optional cloud-sync explicitly off.** MA has a "Sync
  Providers" setting that, if enabled, syncs the operator's
  library metadata to music-assistant.io for cross-device
  sync. The recipe ships with this OFF by default; the
  operator can opt in if they want it.
- **The one exception** — Spotify + Apple Music DO call
  their own APIs (this is unavoidable for those providers;
  they're cloud services by nature). The MA server only
  talks to Spotify's API and Apple Music's API; it does
  NOT talk to any other third-party service.
- **No MAC / serial / device-id captured.** The contract
  intentionally publishes only the high-level media
  metadata (per-zone state, now-playing title/artist/album,
  library counts). The raw MAC addresses / serial numbers
  / device IDs of the upstream MA players stay on the MA
  server and are not pulled into HA by the recipe.
- **No vendor double-stamping.** No `music_assistant`,
  `mass`, `spotify`, `airplay`, `chromecast`, `sonos`,
  `squeezebox`, `dlna`, `upnp`, or other provider/vendor
  name appears in any `rc_media_*` entity, OpenClaw
  summary key, or dashboard tile beyond the subsystem
  prefix `rc_media_*`. The contract is intentionally
  vendor-neutral per `docs/reference/rc-entity-naming.md`.

## §10 Promoting to tier-a

When a real Music Assistant server lands on the bench (likely
via a RoamCore-owned MA container image with a default provider
stub + a CI bench container that validates the provider
handshake), this connection is the candidate to promote to
tier-a:

1. Add a native `config_flow.py` (or a thin wrapper around the
   upstream HACS `music_assistant` integration) that walks the
   operator through adding the HACS repository + choosing Path
   A (HA add-on) vs Path B (external MA server URL) + entering
   the API key + selecting the provider set.
2. Add a RoamCore-owned MA container image with a default
   provider stub (so the CI bench has something to talk to
   without operator intervention).
3. Add an integration test that asserts the `rc_media_*`
   contract entities appear after a synthetic MA-server-poll
   with a canned provider response (Path A's add-on path AND
   Path B's external-server path).
4. Flip `tier_requirements` to include `working_config_flow` +
   `integration_test_passes` + `no_manual_yaml_required`.
5. Drop `tier_warnings` entries that mention
   `no_real_music_assistant_for_integration_test` /
   `recipe_depends_on_user_running_ma` /
   `optional_provider_choice_spotify_apple_music_local_files` /
   `hacs_required_for_integration`.
6. Flip `status` from `beta` to `shipped`.
7. Keep `wizard.one_tap: false` because the operator's
   provider mix + Path A-vs-B choice is personal — even at
   tier-a, one-tap install is misleading if the provider
   selection is a personal-taste choice. The wizard can
   pre-fill the upstream HACS install but the provider
   selection is operator-driven.

Until then, this stays at tier-b (beta, recipe) — the recipe
is sound, the contract is honest, and we don't claim one-tap
coverage we don't have.
