# Connections

A **connection** is one thing a RoamCore user can plug into their van —
Victron, Wicann Pro, Starlink, Traccar, etc. Each one lives in its own
folder here with a `connection.yml` as the **single source of truth**.

## Why this folder exists

Before this folder existed, integrations lived in
`homeassistant/custom_components/`, docs lived in `docs/catalog/`,
and the install path knew about them through no single contract.
Adding a new connection meant touching three or four places and
hoping they stayed in sync.

Now:

- The `connection.yml` declares the integration's identity, tier,
  wizard config, install contract, dashboard tiles, OpenClaw API
  surface, and tests — all in one file.
- `scripts/audit_connections.py` validates every yml against the
  JSON Schema (`_schema/connection.schema.json`) and against the
  actual files on disk. The audit is the gate.
- `scripts/build_catalog.py` regenerates `docs/connections/<id>.md`
  and `connections/registry.json` from the yml — so docs + wizard
  never drift from the source of truth.
- `.github/workflows/connection-boundary.yml` refuses to merge a
  connection PR that touches anything outside its own folder.

The result: the wizard on a user's HA install renders from the same
file as the docs site, and you can ship a new connection in one PR.

## Layout

```
connections/
├── README.md                            # this file
├── registry.json                        # GENERATED. Wizard reads this.
├── _schema/
│   └── connection.schema.json           # The contract. Don't hand-edit.
├── victron-mqtt/                        # one connection = one folder
│   ├── connection.yml                   # source of truth
│   ├── __init__.py                      # HA integration entry point
│   ├── config_flow.py                   # one-tap wizard flow
│   ├── tests/
│   │   ├── test_config_flow.py
│   │   └── test_integration.py
│   └── README.md                        # optional, auto-generated if absent
└── ...
```

## Tier doctrine

| Tier | Means                                                              | Wizard button          |
|------|--------------------------------------------------------------------|------------------------|
| A    | Native, auto-discovery, working config_flow, integration tests pass | "Connect" (one tap)    |
| B    | Recipe / workaround published in docs/howto/                       | "Setup guide"          |
| C    | External link only — community / not officially supported           | "View docs"            |

The audit script enforces this. A connection claiming `tier: a`
without `tests`, `config_flow: true`, `wizard.one_tap: true`, and
`tier_requirements: [working_config_flow, integration_test_passes, no_manual_yaml_required]`
will fail the audit and the PR will be blocked.

## How to add a new connection

1. Create a branch: `feat/connections/<id>-<short-slug>`
2. Create `connections/<id>/connection.yml` — start by copying the
   Victron example (added on Day 2) and editing it.
3. Add the integration code: `__init__.py`, `config_flow.py`, etc.
4. Add tests under `connections/<id>/tests/`.
5. Open the PR. CI runs the audit + boundary check + tests.
6. On green: merge. The catalog robot regenerates docs + registry.

See `docs/engineering/connections-pipeline/` for the full design
(scheduled for Day 2).

## How the cron ships connections

The cron reads `connections/_backlog.yml`, picks the highest-priority
item, creates the branch, implements, commits, pushes, opens a PR.
The boundary CI + connection CI run on the branch. On green, the
cron surfaces the PR URL for tier-a merges (Bernard approves), or
auto-merges tier-b/c after 24h with no objections.

See `Cron-handoff/connection-shipper.md` (scheduled for Day 3).
