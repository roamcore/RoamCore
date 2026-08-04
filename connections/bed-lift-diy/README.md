# DIY bed lift (actuators / winch + motor + strap)

**Tier:** C (recipe)
**Category:** Bed lift
**Status:** beta

## What this connection is

Bed lift control — van bed up / down — is the **foundation** of every sleep-cycle automation in a van with a DIY bed lift (operator-built linear actuators OR winch + motor + strap OR any 2-relay + 2-limit-switch bed lift assembled by the operator): lower the bed automatically at 23:00 local time when mode is `Sleep`, lift the bed at 07:00 local when mode is `Travel` + presence says anyone is home, stop the bed instantly on obstruction detection, refuse to lower the bed when inverter SOC < 20 % + shore is disconnected (the bed motor draws enough current to brown out a low SOC battery bank), alert when both limit microswitches report TRUE simultaneously (wiring fault — mechanically impossible). The signal that drives all of those is a vendor-neutral "what's the bed doing right now?" layer that the rest of RoamCore can rely on — and that layer is what this connection provides.

RoamCore ships **no** native DIY bed lift controller. We RECIPE the well-understood combination of one of two upstream operator-side paths and a translation layer that maps each upstream `cover.bed_lift` (Path A) or upstream `switch.shelly_*_relay` entities (Path B) + upstream limit binary_sensors into a vendor-neutral `rc_bed_lift_*` contract layer. The two paths:

- **Path A — ESPHome custom cover** (recommended for ESPHome-friendly installs). ESPHome handles the device-side: 2× outputs (one for UP relay coil, one for DOWN relay coil; both relay coils must be isolated from ESPHome GPIO via a 5 V logic-level translator + flyback diode; a fuse per relay per the recipe §2 prerequisites), 2× binary_sensor inputs (one for UP limit microswitch, one for DOWN limit microswitch; both with `delayed_off: 100ms` filter to debounce mechanical bounce), and an optional CT-clamp current sensor wired into an ADC pin for obstruction detection. ESPHome exposes a `config_flow` since 2023.x and the resulting device registers `cover.bed_lift` upstream; we wrap that into the `rc_bed_lift_*` contract tiles via a `template:` cover.

- **Path B — Dry-contact relay + HA core `template` cover** (no ESPHome required; recommended when the operator is relay-friendly + wants the upstream HA core integrations to do the IO). Two Shelly 1 / Shelly Plus 1 / Zooz ZEN17 / Aeotec Nano Switch units are wired to the DIY actuator / motor driver's up/down inputs (5 V signal, common, up, down). HA auto-discovers the Shelly units via mDNS (`shelly` integration has a config_flow since 2019.x). The recipe documents both the Shelly-side wiring (5 V signal + common + up + down per device) and the upstream `switch.shelly_*_relay` entities that result, plus the upstream `binary_sensor.shelly_*_dry_contact` entities for the limit microswitches. We wrap those into a `cover.template:` that synthesizes `cover.bed_lift` with up/down/stop + the position binary_sensor logic + an optional `current_based_obstruction_detection` block.

Both paths land on the same vendor-neutral contract layer via `rc_bed_lift_*` dashboard tiles:

- `cover.rc_bed_lift_position` — vendor-neutral cover entity (open/close/stop semantics with position reporting).
- `binary_sensor.rc_bed_lift_up_limit` / `..._down_limit` — operator limit microswitch binary_sensors wrapped to vendor-neutral names.
- `binary_sensor.rc_bed_lift_moving` — derived from `cover.rc_bed_lift_position` state ∈ {opening, closing}.
- `sensor.rc_bed_lift_position_pct` — `cover.rc_bed_lift_position.current_position` (0 / 100 / interpolated when the cover has implicit position feedback).
- `binary_sensor.rc_bed_lift_safety_ok` — limit-sanity aggregate (NOR of `up_limit` AND `down_limit`; FALSE if both limits report TRUE simultaneously — a wiring fault that must be acknowledged before the next motion command).
- `button.rc_bed_lift_lift` / `..._lower` / `..._stop` — explicit button affordances for agent-driven requests (OpenClaw queries bind to these) + automations.
- `binary_sensor.rc_bed_lift_obstruction_detected` — TRUE when the CT-clamp current sensor (Path A) OR the motor-stall heuristic (Path B) detects a stalled motor against an obstruction (sustained >5 A for >2 s with no limit-switch change in the expected direction).
- `binary_sensor.rc_bed_lift_low_voltage_lockout` — TRUE when inverter SOC < 20 % (cross-references `sensor.rc_power_battery_soc` from the Victron `connections/victron/` recipe) OR shore disconnected AND battery low. The `low_voltage_lockout` tile gates the `lift` / `lower` button commands (any motion request is rejected while the tile is TRUE; the operator can acknowledge the lockout via the `stop` button + a mode override).
- `select.rc_bed_lift_mode` — `auto` (RoamCore modes drive the bed — auto-lower at 23:00 when Sleep, auto-lift at 07:00 when Travel, etc.), `manual_only` (only the OpenClaw `lift_bed` / `lower_bed` / `stop_bed` queries + the buttons work; RoamCore modes do NOT auto-schedule), `disabled` (no motion at all — service mode).

This fills the `bed_lift` subsystem slot in `docs/reference/rc-entity-naming.md` — a forward-compatible addition that mirrors how `media` was added by the Music Assistant slice + how `presence` was backfilled alongside this slice (Wave 3 #42 promised the addition in the manifest header code comment but it never landed in the doc).

**Sibling connection:** [`connections/happijac/`](../happijac/) (Wave 3 #43) is the tier-b Happijac-specific connection for the LCI Happijac controller flow. The DIY sibling shares the §5 contract tile ids (the `rc_bed_lift_*` namespace is vendor-neutral), shares the §6 safety interlocks, shares the §7 automations, and shares the §8 OpenClaw queries — only the hardware stack differs (operator-built DIY actuators / winch + motor + strap vs LCI Happijac controller).

RoamCore does **not** ship a DIY bed lift, an ESPHome device, a Shelly relay, a Zooz / Aeotec relay, or any vendor-specific controller. The ESPHome + HA core integrations are the upstream truth; RoamCore layers a contract on top: the `rc_bed_lift_*` dashboard tiles + the OpenClaw queries that bind to those contract entities ("lift the bed", "lower the bed", "stop the bed", "what's the bed position?", "is the bed safe?", "is the bed moving?", "is the bed obstructed?", "is the bed low-voltage locked?", "set bed mode").

## Setup recipe (one-paragraph)

1. Decide which path fits your van: **Path A** — ESPHome custom cover (ESPHome-friendly; needs an ESP32 / ESP8266 wired to the two relay coils + two limit microswitches + optional CT-clamp current sensor); OR **Path B** — Dry-contact relay + HA core `template` cover (relay-friendly; needs two Shelly 1 / Shelly Plus 1 / Zooz ZEN17 / Aeotec Nano Switch units, no ESPHome required).
2. Wire the safety prerequisites FIRST (the recipe §2 walks through these — a fuse per relay + a 5 V logic-level translator per relay coil + a flyback diode per relay coil + the two limit microswitches wired into either ESPHome binary_sensor inputs (Path A) or Shelly dry-contact inputs / separate GPIO-to-WiFi sensors (Path B)). The operator MUST not skip the safety prerequisites — the cover template refuses motion commands until all four interlocks are wired (the `rc_bed_lift_safety_ok` tile is the gate).
3. Wire the upstream device. Path A: flash the ESPHome YAML from recipe §3 onto the ESP device; ESPHome handles the device-side I/O + exposes `cover.bed_lift` upstream via the ESPHome config_flow. Path B: wire the two Shelly / Shelly Plus / Zooz / Aeotec units to the DIY actuator / motor driver; HA auto-discovers the Shelly units via mDNS (config_flow since 2019.x); the upstream `switch.shelly_*_relay` entities appear + the `binary_sensor.shelly_*_dry_contact` entities for the limits.
4. Wire the HA core `template:` cover that synthesizes `cover.bed_lift` (Path A) or maps the Shelly + limit binary_sensors into the same `cover.bed_lift` (Path B) — recipe §3 / §4 walk through the template YAML for each path.
5. Create the `rc_bed_lift_*` contract tiles (or import the recipe's `template:` cover + `template:` binary_sensor + `template:` sensor + `button:` + `select:` helpers from the recipe §5 helper YAML). The recipe walks through synthesizing each `rc_bed_lift_*` tile from the upstream `cover.bed_lift` + limit binary_sensors + the inverter SOC tile from the Victron recipe.
6. Verify the four safety interlocks (recipe §6 walks through each): limit-switch sanity (`rc_bed_lift_safety_ok`), low-voltage lockout (`rc_bed_lift_low_voltage_lockout`), obstruction detection (`rc_bed_lift_obstruction_detected`), mode-aware lockouts (the `select.rc_bed_lift_mode` operator-tunable overrides; RoamCore modes drive the `auto` lane).
7. Enable the recipe §7 automations (Stealth auto-stop at the start of silent hours, Sleep 23:00 auto-lower + 07:00 auto-lift when mode is `auto`, Boost disable-mode-aware-lockouts for service, low-voltage lockout when SOC < 20 %, obstruction detected → stop + alert via Music Assistant TTS, mode-aware scheduling per the operator's choice).
8. Reload the RoamCore dashboard; the `rc_bed_lift_*` contract tiles appear under the Bed lift section.

Full howto with copy-pasteable YAML for the helpers, automations, Path A / Path B wiring, ESPHome current-sensor wiring, Shelly auto-discovery, the four safety interlocks in full, mode-aware exceptions, and the tier-a promotion outline: see [`docs/recipe.md`](docs/recipe.md).

## Why tier-c, not tier-b (or tier-a)

Tier-b requires a RoamCore-owned upstream pattern + a documented operator-bench, but no canonical RoamCore-owned integration code (recipe). Tier-a requires a working RoamCore-owned `config_flow.py`, integration tests against a real DIY bed lift + ESPHome + 2× dry-contact relays + 2× limit microswitches + optional CT-clamp current sensor on CI, and `wizard.one_tap: true`. We have no operator pin choice on the CI bench to integration-test against (no DIY bed lift, no ESPHome device, no relay pair, no limit microswitches, no CT clamp). The operator's exact Path A vs Path B choice + the relay pin / limit pin / current-sensor pin choice is a wiring decision that requires the operator's physical install context, and there's no canonical RoamCore-owned upstream HA integration that does what this connection recipes. The Happijac sibling (`connections/happijac/`, Wave 3 #43) is the canonical tier-b pattern; the DIY sibling is tier-c because the operator-side hardware variability is greater (DIY actuators have a wider current-draw range, motor-driver choice varies — H-bridge vs two-relay-pair vs single-relay direction-control — and the operator owns the assembly rather than buying an off-the-shelf controller). So this connection is honestly beta-tier-c: the recipe is sound but we cannot claim one-tap automation and we cannot claim a documented operator-bench upstream pattern. The [`tests/test_connection_yml.py`](tests/test_connection_yml.py) file asserts the manifest is honest about its tier — including the defensive `test_safety_interlocks_are_documented` assertion that guards the future tier-a promotion's hard-enforced safety interlock asserts — that's the only test we can ship today.

When a real DIY bed lift + ESPHome + relay bench lands (a bench with at least one ESP32 flashed with the recipe §3 ESPHome YAML + two Shelly / Zooz / Aeotec units wired into the bench's no-load DIY bed lift simulator + a CT-clamp current sensor wired into an ADC pin + the four safety interlock sources that the §10 promotion outline describes), this connection is the candidate to promote to tier-a: add a native `config_flow.py` that walks the operator through Path A vs Path B + relay pin / limit pin / current-sensor pin declaration, add an integration test that asserts the four safety interlocks (`rc_bed_lift_safety_ok`, `rc_bed_lift_low_voltage_lockout`, `rc_bed_lift_obstruction_detected`, mode-aware lockouts) all flip to the expected state when wired to canned fixture responses, add a second integration test that asserts a 0→100% `cover.rc_bed_lift_position` change triggers the right tile updates, and flip `tier_requirements` to include `working_config_flow` + `integration_test_passes` + `no_manual_yaml_required` + `safety_interlocks_hard_enforced_in_roamcore_code`.

## Files

- `connection.yml` — the source-of-truth manifest.
- `__init__.py` — `DOMAIN = "bed-lift-diy"` marker for the audit.
- `docs/recipe.md` — the full howto (Path A ESPHome YAML wiring for outputs + binary_sensors + cover + the HA-side `template:` cover that synthesizes the contract layer, Path B Shelly / Shelly Plus / Zooz ZEN17 / Aeotec Nano Switch + HA `template:` cover wiring + limit binary_sensor + the `current_based_obstruction_detection` block, the four safety interlocks in full, six §7 automations, eight §8 troubleshooting entries, privacy, tier-a promotion outline).
- `tests/test_connection_yml.py` — manifest honesty checks (including the `test_safety_interlocks_are_documented` defensive guard for the future tier-a promotion).

## See also

- Legacy catalog page (now superseded by the connection manifest):
  [`docs/catalog/bed-lift/diy-bedlift.md`](../../docs/catalog/bed-lift/diy-bedlift.md)
- Catalog category index: `docs/catalog/bed-lift/index.md`
- Sibling Happijac connection (tier-b; canonical pattern for the LCI Happijac controller flow that this tier-c DIY connection mirrors):
  [`connections/happijac/`](../happijac/)
- Victron connection (companion for the §6 low-voltage lockout cross-reference to `sensor.rc_power_battery_soc` + `binary_sensor.rc_power_shore_connected`):
  `connections/victron/`
- Music Assistant connection (companion for the §7 "obstruction detected → stop + alert" TTS automation — the TTS target is `media_player.rc_media_zone_living`):
  `connections/music-assistant/`
- Bluetooth / Wi-Fi presence connection (companion for the §7 "if bed is in the up position AND presence says only-driver-home for >15 min AND mode is Sleep → gentle reminder to lower bed before sleeping" — uses the `rc_presence_*` contract tiles for the presence signal):
  `connections/bluetooth-wifi-presence/`
- RoamCore entity naming: `docs/reference/rc-entity-naming.md`
- OpenClaw JSON API (the contract `summary_keys` land here): `docs/reference/openclaw-json-api.md`