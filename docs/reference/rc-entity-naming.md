# RoamCore Entity Naming Convention ("rc" Contract)

## Purpose
RoamCore integrates many different subsystems (power, networking, location, weather, etc.) and may support multiple vendors per subsystem over time.

To keep the UI stable and avoid dashboards/automations breaking when the underlying vendor changes, RoamCore defines a small set of **contract entities** with predictable names.

- The **frontend** (dashboards, cards, automations, scripts) should reference **only** these contract entities.
- Vendor- or device-specific entities are mapped into the contract layer by translation logic (templates/helpers/custom integrations).

This document defines **how RoamCore names contract entities**. It intentionally does **not** prescribe the full list of entities.  
This full list can be found elsewhere in the repo. 

---

## Key concept: the `rc_*` contract
A RoamCore contract entity is any Home Assistant entity whose `entity_id` begins with:

- `sensor.rc_…`
- `binary_sensor.rc_…`
- `number.rc_…`
- `select.rc_…`
- `switch.rc_…`
- `button.rc_…`
- `text.rc_…`
- `device_tracker.rc_…` (rare; only if explicitly needed)

### Hard rules
1. **Contract-only naming**: `rc_*` entity IDs are reserved for RoamCore’s stable interface.
2. **No vendor names in contract IDs**: do not put `victron`, `unifi`, `starlink`, etc. into any `rc_*` entity_id.
3. **UI only depends on contract IDs**: dashboards should not depend on vendor entity IDs.
4. **Small and curated**: add new `rc_*` entities only when the UI/automations truly require them.
5. **One meaning per entity**: never overload an entity to sometimes represent different metrics.

---

## Naming format
### Canonical pattern

```
<domain>.rc_<subsystem>_<object>_<metric>
```

Where:
- `<domain>` is the Home Assistant domain (`sensor`, `binary_sensor`, `switch`, …)
- `<subsystem>` is the broad system area (examples below)
- `<object>` is the thing being measured/controlled (battery, wan, gps, time, …)
- `<metric>` is the specific measurement or state (soc, w, connected, status, …)

**Examples (illustrative):**
- `sensor.rc_power_battery_soc`
- `sensor.rc_net_wan_ip`
- `binary_sensor.rc_net_internet_reachable`
- `sensor.rc_location_lat`

### Allowed subsystems (recommended set)
Keep this list short. Start with these and extend deliberately:
- `power` — electrical/power system
- `net` — networking / connectivity
- `location` — GPS / positioning
- `weather` — weather inputs used by UI
- `time` — time/date inputs used by UI
- `system` — RoamCore system health (CPU, disk, updates), only if needed

---

## Metric naming rules
### Prefer explicit units in the entity, not in the ID
- Use `device_class` and `unit_of_measurement` to communicate units.
- Keep the ID readable and stable.

**Good:**
- `sensor.rc_power_solar_power` with unit `W`

**Acceptable when ambiguity exists:**
- `sensor.rc_power_solar_w` (if you want the ID itself to encode unit)

Pick one style and stay consistent. RoamCore recommendation:
- Prefer **semantic metric names** (`power`, `voltage`, `current`, `energy_today`)
- Use short unit suffixes (`_w`, `_v`, `_a`, `_wh`, `_kwh`) only when it prevents confusion.

### Common metric tokens
Use consistent tokens across subsystems:
- Status/state: `status`, `state`, `mode`
- Connectivity: `connected`, `reachable`, `link`, `ssid`
- Power system: `soc`, `power`, `voltage`, `current`, `temperature`
- Location: `lat`, `lon`, `accuracy_m`, `speed`, `heading`

---

## Controls vs telemetry
Contract entities can be telemetry or controls, but controls should be introduced cautiously.

- Telemetry: `sensor.*`, `binary_sensor.*`
- Simple toggles: `switch.*`
- Discrete modes: `select.*`
- Numeric settings: `number.*`

Naming:
- `switch.rc_power_inverter_enabled`
- `select.rc_power_inverter_mode`
- `number.rc_power_charger_current_limit_a`

---

## Multi-source and multi-device considerations
### One active source at a time (MVP recommendation)
For MVP, define each `rc_*` entity as **the single “active” value** RoamCore uses.

Internally, RoamCore can decide which backend is active (Victron, etc.), but the UI should not care.

### If you must support multiple instances
Only when necessary, use an instance suffix:

- `sensor.rc_power_battery_soc_1`
- `sensor.rc_power_battery_soc_2`

Do **not** invent instance identifiers prematurely.

---

## Availability semantics
Contract entities must behave predictably when the source is missing.

- Sensors should become `unknown`/`unavailable` when upstream is missing.
- Binary sensors should be `unknown` when upstream is missing (not silently `off`).

---

## Documentation requirements when adding a new contract entity
When introducing a new `rc_*` entity, the PR/commit must include:
1. A short reason why the UI/automation needs it.
2. The intended unit/device_class (if applicable).
3. The upstream mapping plan (which vendor entity/entities it will map from).

---

## Implementation note (non-normative)
RoamCore may implement the mapping layer using:
- Home Assistant template entities in a `packages/` translation layer, and/or
- a dedicated RoamCore custom integration.

The naming convention above remains valid regardless of implementation.
