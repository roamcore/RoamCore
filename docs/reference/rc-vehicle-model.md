# RoamCore canonical vehicle model

> **One sentence:** When you connect a device to RoamCore, RoamCore automatically knows where it goes on your dashboard — battery, solar, water, position, lighting — no matter which brand it is.

This page is for anyone who wants to understand *what* the canonical vehicle model is, *why* it exists, and *what happens behind the scenes* when a device gets added to RoamCore.

If you only want to install a device and see it on your dashboard, the connection wizard does this for you — you don't need to read this page. If you're curious, or you want to know why a Victron SmartShunt and a Renogy battery monitor both show up in the same `Battery` tile, keep reading.

---

## §1 What is the canonical vehicle model?

The canonical vehicle model is RoamCore's **shared vocabulary** for "things in a van." Every device — Victron, Renogy, a generic USB temperature sensor, anything — gets translated into one of a small, fixed set of slots (battery state of charge, solar power, fresh water level, GPS position, …). The dashboard, the AI assistant, your automations, and the Trip Wrapped report all read from those slots, never from the raw device data.

| Concept | What it means in RoamCore | Vanlifer-friendly version |
|---|---|---|
| **Capability** | A single measurable thing in the van (battery percentage, solar watts, GPS location, …). | "One thing you can ask about the van." |
| **Category** | The area the capability belongs to: power, lighting, climate, water, position, network. | "Which part of the van this thing is about." |
| **Tile id** | The stable name RoamCore uses on the dashboard, always starting with `rc_` (e.g. `rc_power_battery_soc`). | "The label on the box on the screen." |
| **Vendor-neutral** | The tile id never mentions a brand. A Victron battery and a Renogy battery both become `rc_power_battery_soc`. | "It doesn't matter who made it — it ends up in the same box." |

The contract is simple: **downstream consumers (dashboard, AI, automations) only see `rc_*` tile ids.** Raw device entity IDs (like `sensor.vt_battery_soc_percent`) stay in the wiring layer and never leak to the user.

The full canonical list lives in a single JSON file at `connections/_schema/canonical_capabilities.json`. The Python validator at `homeassistant/custom_components/roamcore/vehicle_model.py` enforces the naming rules so the schema can't drift.

---

## §2 The 6 categories

RoamCore groups every capability into one of six categories. Each category has at least one example capability so you can see the shape.

| Category | What it covers | Example capability (vanlifer English) |
|---|---|---|
| **power** | Batteries, solar, shore, inverter | `rc_power_battery_soc` — "How full is the leisure battery, in percent." |
| **lighting** | Interior + exterior lights | `rc_lighting_interior_state` — "Are the cabin lights on or off." |
| **climate** | Indoor temperature, HVAC on/off | `rc_climate_indoor_temperature` — "How warm or cold it is inside the van right now." |
| **water** | Fresh / waste tank levels, water pump | `rc_water_fresh_level` — "How full the fresh water tank is, in percent." |
| **position** | GPS latitude + longitude | `rc_position_lat` — "Where the van is, north/south." |
| **network** | Internet reachability, WAN IP | `rc_network_internet_reachable` — "Does the van have any working internet right now (LTE, Starlink, Wi-Fi)." |

If you connect a device that doesn't fit any of these six, RoamCore won't drop it on the floor — it goes into an *Advanced mode* panel — but for the novice dashboard, these six are everything that matters.

---

## §3 Step-by-step: how a Victron device becomes a `rc_power_battery_soc` tile

You connect a Victron SmartShunt. Here is what happens, end to end, with zero YAML from you.

1. **Home Assistant discovers the Victron device.** RoamCore's Victron add-on (`homeassistant/addons/roamcore-victron-auto`) talks to your Cerbo GX / SmartShunt over MQTT Discovery and publishes vendor-layer entities like `sensor.vt_battery_soc_percent`. You don't touch any YAML — discovery is automatic.
2. **RoamCore maps the vendor entity to the canonical tile.** RoamCore's translation layer (a thin set of Home Assistant template entities in `homeassistant/packages/`) reads `sensor.vt_battery_soc_percent` and exposes a canonical tile: `sensor.rc_power_battery_soc`. The mapping is one-way — the vendor entity stays in the wiring layer, the canonical tile goes to the dashboard.
3. **The tile appears on your dashboard.** The RoamCore dashboard (`docs/catalog/power/index.md` and friends) renders the `rc_power_battery_soc` tile as a battery percentage with a clear icon. You see "Battery: 87%" without ever knowing that under the hood, Victron's MQTT topic just published a number.
4. **OpenClaw can read it via the API.** OpenClaw — your AI assistant that "chats with the van" — uses RoamCore's OpenClaw JSON API (`connections/openclaw-api`) to ask "what's the battery?" and gets back `rc_power_battery_soc`. It never sees the raw Victron entity. This is the abstraction working for the AI layer too.
5. **You never touch a YAML.** The whole chain — discovery → mapping → dashboard tile → API surface — is configured by RoamCore. If you switch your Victron for a Renogy later, only the mapping table changes; your dashboard, your automations, and your OpenClaw skills all keep working unchanged.

That's the foundational value of RoamCore: **one canonical vocabulary, many possible vendors behind it.**

---

## §4 For developers

The canonical vehicle model is **schema-as-data** plus a **pure-Python validator**.

- **The schema** lives at `connections/_schema/canonical_capabilities.json`. It's a JSON document with a `capability_categories` list (the 6 categories) and a `capabilities` array. Each entry carries an `id`, `category`, `kind` (`telemetry` or `control`), `type` (the Home Assistant domain: `sensor`, `binary_sensor`, `switch`, …), an optional `device_class` and `unit`, a plain-English `description`, and an `example_sources` list of vendor entities that should map into it.
- **The validator** lives at `homeassistant/custom_components/roamcore/vehicle_model.py`. It's pure stdlib + json (no Home Assistant imports) and exposes four functions: `load_capabilities(path)`, `validate_capabilities(caps) -> list[str]` (empty list = valid), `get_capabilities_by_category(caps, category)`, and `find_capability(caps, capability_id)`. The validator enforces: the `rc_` prefix, the `<subsystem>_<object>_<metric>` token pattern, no vendor names in any contract id, no duplicate ids, every category declared in the top-level allowlist, every `kind` in `{telemetry, control}`, every `type` in the HA domain allowlist, and at least 12 capabilities total.
- **Adding a new capability.** Edit the JSON file: add a new entry to the `capabilities` array, add the new `category` (if needed) to the `capability_categories` list, run `bash scripts/checks/canonical-capabilities-smoke.sh` to confirm the validator is happy, and the change is live for downstream consumers. The pytest suite at `homeassistant/custom_components/roamcore/tests/test_vehicle_model.py` guards against regressions in the validator rules.

Naming follows `docs/reference/rc-entity-naming.md` exactly: `<domain>.rc_<subsystem>_<object>_<metric>`, lowercase, underscore-separated, no vendor names. If your new id doesn't pass the validator, the smoke script and the pytest will both fail loudly.

---

## §5 Troubleshooting

**My device doesn't map to a canonical tile.**
First, check the device list in the RoamCore catalogue — if it's not listed there yet, RoamCore won't have a mapping for it. Second, open the device's raw entity IDs in Home Assistant's Developer Tools → States and look for `sensor.vt_*`, `sensor.unifi_*`, etc. If you see those, the vendor layer is working but the mapping isn't in place yet. File an issue against `connections/_schema/canonical_capabilities.json` with the vendor entity and the canonical tile you think it should map into.

**I see a raw Victron sensor (e.g. `sensor.vt_battery_soc_percent`) on my dashboard.**
You probably have an "Advanced mode" toggle on, or an old Lovelace card that's still referencing the vendor entity. The fix is to update the card to reference the canonical tile (`sensor.rc_power_battery_soc`). The canonical tiles are the only thing RoamCore's generated dashboard uses; vendor tiles are an advanced-only escape hatch.

**The canonical schema file is missing (`connections/_schema/canonical_capabilities.json`).**
That's a repo-level bug — the file is part of RoamCore itself. Re-clone the repo or run `git pull`. The smoke script `scripts/checks/canonical-capabilities-smoke.sh` will fail loudly if the file is missing on a CI run, so this should never reach a release.
