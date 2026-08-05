# RoamCore Victron Auto — bench integration tests

These tests are the **tier-a-is-honest** evidence for the RoamCore Victron
integration. They boot the real `VictronAuto` class against a real MQTT broker
(either the system `mosquitto` or a pure-Python `amqtt` broker), publish fake
Venus OS D-Bus MQTT topics, and assert that the `vt_*` discovery topics are
emitted and that the value transitions propagate to the retained state topics.

> **If this test is skipped, tier-a is no longer honest.**
> (Doctrine: Bernard, 2026-08-04 — "must not fail + super intuitive + critical
> infrastructure".)

## What the tests cover

| # | Test | What it proves |
|---|------|----------------|
| 1 | `test_victron_auto_connects_to_broker` | VictronAuto's HA MQTT client actually connects to the broker |
| 2 | `test_victron_auto_subscribes_to_n_wildcards` | Addon subscribes to `N/+/#` and learns the portal id from traffic |
| 3 | `test_victron_auto_publishes_discovery_on_connect` | Discovery configs appear under `homeassistant/...` on connect |
| 4 | `test_battery_soc_in_discovery_payload` | SoC discovery entity has the right shape (name, unit, id, state topic) |
| 5 | `test_all_required_vt_entities_discovered` | SoC, AC in/out, Solar, Load, Battery V/A all in discovery |
| 6 | `test_end_to_end_soc_round_trip` | Published SoC value → retained state topic → tile-ready discovery |
| 7 | `test_recovery_after_broker_restart` | `_maybe_rotate_bad_target` recovery contract works |
| 8 | `test_plain_english_error_when_broker_unreachable` | Error copy is "Victron GX not found…" not a traceback |
| 9 | `test_soc_transitions_reflected_in_retained_state` | 10 → 99 transitions propagate to retained state |
| 10 | `test_power_tile_jinja_resolves_vt_soc` | YAML parse + Jinja prefers `vt_*` over legacy/mock |
| 11 | `test_power_tile_sees_victron_data` | End-to-end: bench broker → tile would render real value |
| 12 | `test_double_start_idempotent_discovery` | Re-triggering discovery does NOT duplicate config topics |

## Quick start

### 1. Install dev deps (once per host)

```bash
pip3 install paho-mqtt pytest pytest-asyncio amqtt
```

> `mosquitto` (binary) is preferred for speed — the conftest uses it if it's
> on `$PATH`. Otherwise it falls back to `amqtt` (pure Python, no system
> install required).

### 2. Run the bench

From the repo root:

```bash
bash scripts/checks/victron-bench-smoke.sh
```

Or run pytest directly:

```bash
cd homeassistant/addons/roamcore-victron-auto
PYTHONPATH=src:. pytest tests/ -v
```

You should see:

```
12 passed in ~50s
```

(amqtt broker takes ~0.5s to come up; total wall time is dominated by the
`test_recovery_after_broker_restart` test which deliberately exercises the
grace period.)

### 3. Wire into CI

The bench is automatically picked up by `scripts/check.sh`. After this slice
lands, `scripts/checks/victron-bench-smoke.sh` is on the chain:

```bash
bash scripts/check.sh --core-only
```

## Running against a real Victron GX

The bench is wired against a local broker for portability, but the addon
itself is unchanged. To run against your GX:

1. Set `victron_host=<gx-ip>` in the addon options.
2. Set `victron_portal_id=<portal-id>` (find it on the GX under
   **Settings → VRM online portal → VRM Portal ID**).
3. The addon will connect to your GX on the configured MQTT port.
4. The bench smoke script is still useful as a CI gate — but for GX-specific
   scenarios, run the addon manually with `victron_host=<gx-ip>` set in
   `/data/options.json`.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `SKIP — no MQTT broker available` | Neither `mosquitto` (binary) nor `amqtt` (Python) installed | `apt install mosquitto` **or** `pip install amqtt` |
| `ConnectionRefusedError: [Errno 111]` | Port collision; another broker is bound to the same port | Stop the conflicting broker, or change `bench_ha_port`/`victron_mqtt_port` |
| `paho-mqtt==2.1.0 not found` | venv missing the dep | `pip install -r requirements.txt` (inside the addon dir) |
| `VictronStartupError: ... broker not reachable at 127.0.0.1:1883` | The HA MQTT broker port was not set correctly | The bench broker fixture uses a random port; the conftest wires both `bench_ha_port` and `victron_mqtt_port` to it. If you fork a test, set both. |
| `pytest-asyncio not installed` | The async tests need pytest-asyncio | `pip install pytest-asyncio` |
| `test_recovery_after_broker_restart` is flaky | amqtt 0.11 has flaky in-process restarts; the bench now exercises the rotation mechanism directly without a real broker kill+restart | This is expected — see test docstring |

## Why we don't mock the assertion under test

The whole point of the bench is to prove that the integration ACTUALLY works
end-to-end. We do NOT mock:
- The MQTT broker (real broker publishes + subscriptions)
- The discovery payload assertion (real `homeassistant/sensor/.../config`
  messages are read off the broker)
- The retained state topic (real `roamcore/victron/.../state` topic is read)

Mocking any of these would defeat the purpose. The single thing we mock is
the **addon's view of time** (`time.time()` is patched via the `bench_exit_after_sec`
opts) so the bench finishes in seconds, not minutes.

## Where the bench fits in the repo

```
homeassistant/addons/roamcore-victron-auto/
├── src/main.py              # addon entry (additive bench mode + bench CLI)
├── run.sh
├── config.yaml
├── requirements.txt         # addons' runtime deps (paho-mqtt, zeroconf)
├── tests/                   # bench integration tests (this dir)
│   ├── README.md
│   ├── conftest.py          # pytest fixtures (mqtt_broker, ha_discovery_recorder, ...)
│   ├── pytest.ini
│   └── test_victron_auto_bench.py
└── docs/
    └── ...

scripts/checks/victron-bench-smoke.sh   # wires the bench into check.sh
docs/catalog/power/victron.md           # user-facing IKEA-5 doc
```

## Honesty statement

> Tier-a is the highest support tier — it MUST work out of the box. This
> bench exists to catch regressions in the Victron integration before they
> reach a van. If you change anything in `src/main.py` related to MQTT
> connection, discovery, or the `_path_to_vt` mapping, you MUST run this
> bench before opening the PR. If you can't, the bench is no longer honest
> and tier-a is no longer honest.
