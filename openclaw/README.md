# OpenClaw + RoamCore

RoamCore exposes a small set of **agent-friendly JSON endpoints** from Home Assistant so an OpenClaw agent can “talk to your van” with deep context.

Design goals:
- **Data-first**: RoamCore provides deterministic, typed-ish snapshots.
- **Agent-side compute**: insights are computed by the agent (keeps the van box low-power and simple).
- **Stable contract**: the curated `/summary` endpoint stays consistent as underlying hardware/vendors change.

---

## What’s included

### 1) RoamCore OpenClaw API (Home Assistant)

Endpoints (relative to your Home Assistant base URL):

- `GET /api/roamcore/openclaw/summary`
  - curated, stable snapshot (power/map/level)

- `GET /api/roamcore/openclaw/rc_dump`
  - full inventory of all `.rc_` entities with best-effort `num`/`bool` parses

- `GET /api/roamcore/openclaw/timeseries/catalog`
  - discover which compact time-series keys are available

- `GET /api/roamcore/openclaw/timeseries?keys=...&window_sec=...&resolution_sec=...`
  - bounded, downsampled time series for only the keys requested

- `GET /api/roamcore/openclaw/skill`
  - convenience payload that returns the full absolute URL to `/summary` and whether auth is required

Primary documentation:
- `docs/reference/openclaw-json-api.md`

Code:
- `homeassistant/custom_components/roamcore/openclaw_view.py`
- View registration: `homeassistant/custom_components/roamcore/__init__.py`

---

### 2) RoamCore OpenClaw Skill (agent-side)

RoamCore ships an OpenClaw skill folder that teaches an agent how to:
- fetch `/summary` first
- fetch `/rc_dump` when it needs more breadth
- fetch `/timeseries` only when it needs trends
- compute insights locally (agent-side)

Skill folder:
- `skills/roamcore/SKILL.md`

Install/how-to:
- `docs/howto/openclaw-roamcore-skill.md`

---

## Recommended OpenClaw runtime in Home Assistant (upstream)

For running OpenClaw inside HAOS, RoamCore recommends the techartdev OpenClaw add-on + integration:

- `docs/howto/openclaw-techartdev.md`

Upstream:
- https://github.com/techartdev/OpenClawHomeAssistant
- https://github.com/techartdev/OpenClawHomeAssistantIntegration

---

## Roadmap: safe action-taking

Beta is intentionally **read-only**.

The roadmap approach for safe writes is a RoamCore-controlled **default-deny allowlist** + audit log:

- `docs/design/agent-actions-allowlist.md`

