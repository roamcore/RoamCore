"""Music Assistant (multi-room van audio) — tier-b recipe connection.

This module is a marker-only stub. Tier-b connections don't ship native
HA integration code; they publish a recipe (docs/recipe.md) that walks
the user through setting up Music Assistant on the van (Path A — HA
add-on, recommended for HAOS installs; OR Path B — external MA
server, recommended for fleet installs + non-HAOS hosts), exposing
the resulting data via the upstream HACS `music_assistant`
integration (canonical HACS-only MA integration, fetched from
`music-assistant/hass-music-assistant` on GitHub via HACS →
Repositories → Add), and publishing the RoamCore media contract
tiles on top (`rc_media_*` tiles: per-zone media_player entities,
an `any_player_playing` binary sensor, an `active_zone` sensor, a
now-playing title/artist/album trio, three library-count sensors,
a `pause_all` button, a `resume_last` button, and a `default_zone`
select).

The audit + boundary CI can detect a `music-assistant/` folder that
claims to be a connection via the `DOMAIN` constant exported here.
The wizard reads the manifest + recipe at runtime.

The real per-zone control + pause_all / resume_last affordance path
is:

    Operator-side Music Assistant server (Path A HA add-on OR
        Path B external container)
        -> HACS `music_assistant` integration (HA core does NOT
           include Music Assistant; MA is HACS-only — fetched
           from `music-assistant/hass-music-assistant`)
        -> auto-discover via zeroconf on the LAN (Path A) OR
           pointed at via URL like `http://ma.lan:8095` (Path B)
        -> HA media_player entities (per-zone; provider-agnostic
           — Spotify, Apple Music, TuneIn, local files,
           Chromecast / AirPlay / Sonos receivers)
        -> RoamCore contract layer
           (media_player.rc_media_zone_living,
            media_player.rc_media_zone_bed,
            media_player.rc_media_zone_outdoor,
            binary_sensor.rc_media_any_player_playing,
            sensor.rc_media_active_zone,
            sensor.rc_media_now_playing_title,
            sensor.rc_media_now_playing_artist,
            sensor.rc_media_now_playing_album,
            sensor.rc_media_library_artists_count,
            sensor.rc_media_library_albums_count,
            sensor.rc_media_library_tracks_count,
            button.rc_media_pause_all,
            button.rc_media_resume_last,
            select.rc_media_default_zone)
        -> dashboard tiles + OpenClaw queries
            ("what's playing?", "what zone is on?",
             "pause all music", "resume last playlist",
             "switch to outdoor zone", "set volume 30 on bedroom",
             "play <artist/album/playlist>",
             "how many artists in library?")

    Pause-all / resume-last affordance (operator's choice of path):
        -> button.rc_media_pause_all calls
           `media_player.turn_off` on every `rc_media_zone_*`
           media_player (Path A or Path B; provider-agnostic —
           the upstream HACS MA integration abstracts the player
           types, so Chromecast / AirPlay / Sonos / DLNA / UPnP
           receivers all respond to the same `turn_off` call)
        -> button.rc_media_resume_last resumes the last-known
           playlist on `rc_media_default_zone`

See docs/recipe.md for the full howto (HACS install, provider
configuration, Path A HA add-on wiring, Path B external server
wiring, HA helpers, mode-aware media automations that respect
Stealth silent hours + Travel motion + Boost zone volumes +
inverter-SOC power-aware pausing + TTS-zone-pinning, provider
setup notes for Spotify / Apple Music / TuneIn / local files /
Chromecast / AirPlay / Sonos, troubleshooting, tier-a promotion
outline).
"""

DOMAIN = "music-assistant"
