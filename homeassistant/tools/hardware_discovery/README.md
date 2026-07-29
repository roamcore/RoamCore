# RoamCore — Hardware auto-discovery helper

Stdlib-only Python helper that backs the Wave 2 #31 hardware
auto-discovery slice.

## What it does

For each RoamCore-shipped add-on, runs a single, fast probe and emits
a one-line JSON result on stdout:

```
$ python3 probe.py --addon openwrt
{"addon": "openwrt", "available": true, "latency_ms": 4, "error": ""}
```

| Add-on      | Probe target                                  | Mechanism                     |
|-------------|-----------------------------------------------|-------------------------------|
| `openwrt`   | `192.168.1.1:80` (override via env)            | TCP connect                   |
| `tileserver`| `127.0.0.1:8000`                              | TCP connect                   |
| `traccar`   | `127.0.0.1:8082`                              | TCP connect                   |
| `victron`   | `192.168.1.100:1883` (override via env)       | TCP connect                   |
| `ota`       | `/share/roamcore/state.json`                  | Filesystem freshness          |

## Privacy

**All probing is local. The helper never resolves DNS, never opens a UDP
socket, and never reaches the public internet.** Every target is either:

- loopback (`127.0.0.1`, `::1`), OR
- link-local (`169.254/16`, `fe80::/10`), OR
- RFC1918 private (`10/8`, `172.16/12`, `192.168/16`), OR
- RFC4193 unique-local IPv6 (`fc00::/7`), OR
- the local filesystem (`/share/roamcore/state.json`).

The `_validate_target()` helper enforces this before every connect.
The smoke check (`scripts/checks/hardware-auto-discovery-smoke.sh`) greps
the helper + the discovery package to assert no non-loopback/non-RFC1918
host literal ever appears in a probe target. If you add a new probe,
either keep the target loopback/RFC1918 or update the smoke check in the
same commit — the privacy invariant is load-bearing for tier-b.

## Why stdlib?

- **Deterministic** — no third-party deps, no surprise upgrades.
- **Testable** — every probe is a pure function that returns a dict.
- **Fast** — short timeouts (1.5 s default) keep the contract layer
  responsive.
- **Matches the Wave 2 precedent** — same shape as
  `homeassistant/tools/trip_wrapped/traccar_trip_stats.py` and
  `homeassistant/tools/trip_local/trip_today.py`.

## Where it's wired

- `homeassistant/packages/roamcore_hardware_discovery.yaml` exposes
  one `binary_sensor.rc_hardware_<addon>_available` per add-on via
  `command_line` sensors reading this helper's stdout.
- `homeassistant/packages/roamcore_setup_wizard_hardware_discovery.yaml`
  renders the wizard card that surfaces those entities + a "Set up"
  CTA per row.
- `docs/setup/hardware-auto-discovery.md` walks the operator through
  enable/disable + per-add-on overrides.

## Adding a new add-on probe

1. Add the new add-on name to `SUPPORTED_ADDONS`.
2. Write `_probe_<addon>()` and register it in `PROBES`.
3. Use only loopback / RFC1918 / filesystem targets. Validate via
   `_validate_target()` for any host literal.
4. Add `binary_sensor.rc_hardware_<addon>_available` to the package.
5. Update the smoke check (`scripts/checks/hardware-auto-discovery-smoke.sh`)
   to expect the new probe + contract entity.
6. Update `docs/setup/hardware-auto-discovery.md` §Supported add-ons.

## Exit codes

| Code | Meaning                                                  |
|------|----------------------------------------------------------|
| 0    | Probe completed (availability is in stdout, not the code)|
| 1    | Unexpected runtime error                                 |
| 2    | Argument / configuration error (invalid `--addon`)       |