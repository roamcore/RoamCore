"""Frigate (NVR with on-device object detection) — tier-b recipe connection.

This module is a marker-only stub. Tier-b connections don't ship native
HA integration code; they publish a recipe (docs/recipe.md) that walks
the user through setting up the upstream HA core `frigate` integration
against their own Frigate container (HA add-on or external Docker) and
tells the wizard how to publish the RoamCore security-camera contract
entities on top.

The audit + boundary CI can detect a `frigate/` folder that claims to be
a connection via the `DOMAIN` constant exported here. The wizard reads
the manifest + recipe at runtime.

The real detection/recording path is:
    RTSP/ONVIF IP cameras
        -> Frigate container (object detection + go2rtc restream)
        -> Frigate HTTP API + MQTT events (frigate/events, frigate/available)
        -> HA core `frigate` integration (auto-creates camera entities)
        -> RoamCore contract layer (`rc_security_*` entities + tiles)
        -> dashboard tiles + OpenClaw queries

See docs/recipe.md for the full howto (HA add-on + external Docker paths,
go2rtc config, MQTT discovery mapping, storage + retention, troubleshooting,
tier-a promotion outline).
"""

DOMAIN = "frigate"