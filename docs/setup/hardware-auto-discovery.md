# RoamCore — Hardware auto-discovery setup

This guide covers the Wave 2 #31 hardware auto-discovery slice: which
add-ons RoamCore probes, how to enable/disable discovery globally and
per add-on, and how to interpret what the Setup Wizard surfaces.

## 1. What this is

RoamCore ships a small stdlib-Python helper that surveys the local LAN
for each add-on RoamCore already has a connection for and exposes a
single `binary_sensor.rc_hardware_<addon>_available` per add-on. The
Setup Wizard renders a "Hardware" card that lists what's reachable and
offers a one-tap "Set up" CTA per row.

The slice is **tier-b** (community-supported): well-scoped, documented,
smoke-verified, but not the full polish of a tier-a feature.

## 2. Privacy

**All probing is local. RoamCore never leaves your device to look for
hardware.**

Every probe target is one of:

- Loopback: `127.0.0.1`, `::1`
- Link-local: `169.254/16`, `fe80::/10`
- RFC1918 private: `10/8`, `172.16/12`, `192.168/16`
- RFC4193 unique-local IPv6: `fc00::/7`
- The local filesystem (`/share/roamcore/state.json` for the OTA poller)

The helper (`homeassistant/tools/hardware_discovery/probe.py`) hard-validates
every host literal via `_validate_target()` before any connect attempt.
The smoke check (`scripts/checks/hardware-auto-discovery-smoke.sh`) greps
both the helper and the discovery package for non-loopback / non-RFC1918
literals and fails the build if it finds any.

If you add a new probe, either keep the target loopback / RFC1918 or
update the smoke check in the same commit.

## 3. Supported add-ons

The slice covers the five RoamCore-shipped add-ons / integrations that
have a discoverable local presence:

| Add-on      | Default probe target                  | Override helper                          |
|-------------|---------------------------------------|------------------------------------------|
| `openwrt`   | `192.168.1.1:80` (TCP)                | `input_text.rc_hardware_openwrt_host`    |
| `tileserver`| `127.0.0.1:8000` (TCP)                | (loopback only)                          |
| `traccar`   | `127.0.0.1:8082` (TCP)                | (loopback only)                          |
| `victron`   | `192.168.1.100:1883` (TCP)            | `input_text.rc_hardware_victron_host`    |
| `ota`       | `/share/roamcore/state.json` (file)   | (filesystem only)                        |

The `openwrt` and `victron` overrides are RFC1918-only — the helper
refuses any host that doesn't pass `_validate_target()`.

## 4. Enable / disable

### Master switch (kills all discovery)

```yaml
input_boolean.rc_hardware_discovery_enabled:
  initial: true  # default ON
```

When flipped **OFF**, all `binary_sensor.rc_hardware_*_available`
entities report `unavailable` (never `unknown`). The probe helper is
not invoked — no scanning happens at all.

### Per-add-on

The per-add-on `binary_sensor.rc_hardware_<addon>_available` is read-only.
If you don't want to discover a particular add-on:

1. Flip the master switch OFF (simplest), OR
2. Customize your Lovelace card to hide that row (the wizard card
   doesn't auto-hide anything).

The setup-prompt helpers (`input_boolean.rc_hardware_setup_<addon>_pending`)
can be cleared with `input_boolean.turn_off` once you're done with a
prompt — they're independent of discovery.

## 5. Setup CTA flow

1. The Setup Wizard renders the card from
   `homeassistant/packages/roamcore_setup_wizard_hardware_discovery.yaml`
   at the "Hardware" stage.
2. Each discovered add-on row has a "Set up" button that calls
   `roamcore.hardware_setup_prompt(addon=<name>)`.
3. The service handler in `homeassistant/custom_components/roamcore/__init__.py`
   flips `input_boolean.rc_hardware_setup_<addon>_pending` ON and writes
   the pill text to `input_text.rc_hardware_setup_<addon>_message`.
4. Open the corresponding setup guide (linked below) and follow it.

| Add-on      | Setup guide                              |
|-------------|------------------------------------------|
| `openwrt`   | (see Network page → OpenWrt)              |
| `tileserver`| (see Map → Tile Server)                  |
| `traccar`   | `docs/setup/traccar.md`                  |
| `victron`   | (see Power page → Victron Connect)       |
| `ota`       | `docs/setup/ota.md`                      |

## 6. Troubleshooting

### "All `rc_hardware_*_available` are `unavailable`"

- The master switch is OFF. Flip `input_boolean.rc_hardware_discovery_enabled` ON.
- HA hasn't polled the probes yet (the first poll takes ~30 s; the
  helper itself takes < 2 s per probe). Wait and reload the entity.
- The probe helper script is missing from `/config/tools/hardware_discovery/`.
  Re-run the installer.

### "An add-on shows `OFF` but it's running"

- Check the override helper (`input_text.rc_hardware_openwrt_host` or
  `input_text.rc_hardware_victron_host`). The default may not match
  your network.
- For `tileserver` / `traccar`, the helper only probes the loopback
  port — if you changed the add-on's port mapping, the helper will
  return `OFF` until you update it (see the helper README for the
  constants).
- The helper refuses to connect to any non-RFC1918 / non-loopback
  host. If your device is on a public IP or a non-standard private
  range, you'll need to file an issue — the privacy invariant is
  load-bearing.

### "Setup CTA does nothing"

- The service handler raises `ValueError` for unknown add-on names.
  Check the Wizard log for the exact add-on string sent.
- The `input_boolean.rc_hardware_setup_<addon>_pending` helper may
  not exist on a fresh install (the contract package hasn't been
  reloaded yet). Restart Home Assistant once after install.

### "I see `unavailable` even when the probe JSON says `available: true`"

- The contract layer's template `binary_sensor` flips to
  `unavailable` whenever the underlying `command_line` sensor is
  `unknown` / `unavailable`. This usually means the probe hasn't
  completed yet — wait one cycle (5 min) and reload.

## 7. What's next

This slice covers the **discovery + prompt** primitive only. The
following follow-ups are tracked in
`docs/feature-checklist.md` (Platform section, line 74):

- **Row #304 (Additional hardware support — OBD, lighting, etc.):**
  extends the contract layer to additional hardware tiers. The
  `SUPPORTED_ADDONS` list in `homeassistant/tools/hardware_discovery/probe.py`
  is the single place to register new probes; see its README for the
  recipe.
- **Setup wizard per-add-on guides:** the actual setup flows for
  each add-on (e.g. pairing OpenWrt, configuring a Venus OS broker).
  Those live in their respective `docs/setup/<addon>.md` and are
  independent of this slice.

## 8. Where the slice lives

| Concern               | Path                                                          |
|-----------------------|---------------------------------------------------------------|
| Contract package      | `homeassistant/packages/roamcore_hardware_discovery.yaml`     |
| Setup wizard card     | `homeassistant/packages/roamcore_setup_wizard_hardware_discovery.yaml` |
| Probe helper (Python) | `homeassistant/tools/hardware_discovery/probe.py`             |
| Probe helper README   | `homeassistant/tools/hardware_discovery/README.md`            |
| Service declaration   | `homeassistant/custom_components/roamcore/services.yaml`      |
| Service handler       | `homeassistant/custom_components/roamcore/__init__.py`        |
| Smoke check           | `scripts/checks/hardware-auto-discovery-smoke.sh`             |
| Wired into            | `scripts/check.sh --core-only`                                |
| Docs tick             | `docs/feature-checklist.md` line 73 → `[x]`                  |
| Build status          | `docs/mvp/features-build-status.md` (Shipped bullet)          |