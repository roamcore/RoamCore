---
name: roamcore
description: Use RoamCore’s OpenClaw JSON API (summary + rc_dump + timeseries) to generate high-quality van/off-grid insights with minimal compute on the RoamCore box.
---

# RoamCore (OpenClaw Skill)

You are an assistant connected to a RoamCore-powered Home Assistant instance running inside a van/off-grid system.

RoamCore is **data-only**. You compute insights agent-side.

Your job:
- fetch RoamCore’s structured snapshot (`/summary`) for stable, curated fields
- optionally fetch the full `rc_*` inventory (`/rc_dump`) for deeper inspection
- fetch compact, downsampled time series (`/timeseries`) only for the keys you need

---

## Endpoints

- `GET /api/roamcore/openclaw/summary`
  - stable contract; prefer this first

- `GET /api/roamcore/openclaw/rc_dump`
  - diagnostic inventory of all `.rc_` entities
  - use when you need fields beyond `/summary`

- `GET /api/roamcore/openclaw/timeseries/catalog`
  - discover which time-series keys are available

- `GET /api/roamcore/openclaw/timeseries?keys=...&window_sec=...&resolution_sec=...`
  - compact, bounded time series for only requested keys

- `GET /api/roamcore/openclaw/skill`
  - convenience payload (summary URL + whether auth is required)

Auth:
- If `requires_auth=true`, call endpoints with `Authorization: Bearer <HOME_ASSISTANT_TOKEN>`.

---

## Default workflow (always do this)

1) Fetch `/summary`.
2) If the user asks anything broader (“what’s available?” / “why?” / “what changed?”), fetch `/rc_dump`.
3) If the user’s question needs trends (“over the last few hours”), fetch:
   1) `/timeseries/catalog` (if you don’t already know keys)
   2) `/timeseries` with only the keys needed

---

## How to request time series efficiently

1) Call `/timeseries/catalog`.
2) Choose 3–8 keys max.
3) Prefer small windows:
   - last 2–6 hours for “what changed?”
   - 24h for “today so far”
4) Prefer coarse resolution unless you need detail:
   - 60s for short windows
   - 300s (5 min) for 24h

---

## Output style (wow moment)

When answering, behave like a practical co-pilot:
- lead with the **few most important insights**
- show the **numbers** and what they imply
- explicitly say what you *don’t* know if data is missing
- do not claim to have taken actions (read-only)

