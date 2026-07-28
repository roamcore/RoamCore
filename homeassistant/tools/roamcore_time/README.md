# RoamCore — Time primitives (tools)

This folder is the **test + utility** layer for the RoamCore time
contract. It mirrors the pattern used by
`homeassistant/tools/roamcore_weather/`.

## Layout

```
homeassistant/
├── roamcore_time_primitives.py     # Pure-Python helpers (no HA imports)
└── tools/
    └── roamcore_time/
        └── tests/
            └── test_time_primitives.py
```

## Why is the module outside `custom_components/`?

`homeassistant/custom_components/roamcore/__init__.py` imports
`homeassistant.config_entries` at module load. That makes pytest import
the whole HA stack just to run a unit test.

By placing `roamcore_time_primitives.py` at the top of `homeassistant/`,
the module is:

- Importable as a normal Python module in tests (no HA runtime needed).
- Still packaged inside the RoamCore custom component at runtime via
  the fallback import in
  `homeassistant/custom_components/roamcore/openclaw_view.py`.

## Run the tests

```sh
python -m pytest homeassistant/tools/roamcore_time/tests/ -v
```
