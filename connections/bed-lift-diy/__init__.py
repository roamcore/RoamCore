"""DIY bed lift (actuators / winch + motor + strap) — tier-c recipe connection.

This module is a marker-only stub. Tier-c connections don't ship native HA
integration code; they publish a recipe (docs/recipe.md) that walks the
user through setting up a DIY bed lift (Path A — ESPHome custom cover:
for ESPHome-friendly installs, OR Path B — Shelly 1 / Shelly Plus 1 /
Zooz ZEN17 / Aeotec Nano Switch pair + HA core template: cover for
relay-friendly installs), and exposes the resulting data via the
upstream ESPHome or HA core integrations, then publishes the RoamCore
bed-lift contract tiles on the dashboard + the OpenClaw API surface.
"""

DOMAIN = "bed-lift-diy"