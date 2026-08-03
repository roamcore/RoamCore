# HappiJac bed lift

**Support tier:** C (custom/manual)

> **Superseded by the tier-b connection:** this catalog page is retained for context. For the install + recipe + contract tiles, see [connections/happijac/](../../../connections/happijac/) and [docs/recipe.md](../../../connections/happijac/docs/recipe.md).

## What this is
HappiJac bed lifts are a popular off-the-shelf system. The HA integration is usually custom because the stock controller is not designed as a smart-home device.

## Why it’s useful in a van
- Reliable physical system with a clean “up/down” control goal
- Great candidate for safety interlocks (limits, obstruction checks)

## Extra hardware required
- HappiJac bed lift system
- A control interface you add (relay control + limit switch sensing)

## Install / best next step
Most setups:
- Tap into the controller’s up/down inputs with **dry-contact relays**
- Add limit switch sensing into ESPHome

## Links
- ESPHome: https://esphome.io/
- Home Assistant Cover: https://www.home-assistant.io/integrations/cover/
- HappiJac support (manuals/tech info): https://support.lci1.com/happijac-support-happijac-beds
