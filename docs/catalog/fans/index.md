<!-- SUPERSEDED: This legacy stub is superseded by the tier-b recipe connection at `connections/fans/`. The legacy 14-line stub originally listed "Fans are a simple upgrade that massively improves comfort: airflow, condensation control, cooking smells, and keeping the van livable in warm weather. This section covers fan controllers, vent fans, and easy automations like 'run when humidity is high'" with no recipe + no contract + no vendor-neutral coverage — just a placeholder. The tier-b recipe connection promotes the legacy concept into a vendor-neutral fan-controller umbrella covering FOUR operator-pickable paths (Path A Z-Wave / Zigbee / MQTT fan controllers + Path B Wi-Fi / BLE smart fans via Bond Home + Hunter SIMPLEconnect + Tuya + Path C generic 12 V / 24 V fan + relay + Path D all-in-one smart fan like MaxxAir / Fan-Tastic / MAXXAIR Deluxe rooftop vent fan) + adds the 8 `rc_fan_*` contract tiles (1 fan main + 1 sensor speed_percent + 1 select mode + 1 binary_sensor active + 1 sensor runtime_minutes_today + 1 sensor last_trigger_reason + 1 button run_now_15min + 1 binary_sensor rain_sensor_active) + the FIVE §8 automations (auto-fan on humidity high + auto-fan on temperature high + manual override via button + rain-sensor hard-block + Sleep mode suppression via `select.rc_mode`). The umbrella publishes the resulting data via the upstream HA core `fan` integration + the HA core `template:` fan wrapper + the HA core `zwave_js` integration + the HA core `zha` integration + the HA core `mqtt` integration + the HA core Shelly integration + the HACS `bond` integration + the HACS `tuya` integration + the HACS `hunterdouglas_simplify` integration (RoamCore does NOT own a custom fan integration; the upstream integrations handle 95%+ of operator-facing fan operators). See `connections/fans/README.md` for the new connection overview + `connections/fans/docs/recipe.md` for the full howto. See `Cron-handoff/2026-08-02-fans-connection.md` for the slice handoff. -->

# Fans

This folder is the **Fans** tag in the RoamCore catalog.

## Overview
Fans are a simple upgrade that massively improves comfort: airflow, condensation control, cooking smells, and keeping the van livable in warm weather. This section covers fan controllers, vent fans, and easy automations like “run when humidity is high”.

<!-- RC_FEATURE_LIST_START -->

## Features

Nothing listed here yet.

<!-- RC_FEATURE_LIST_END -->