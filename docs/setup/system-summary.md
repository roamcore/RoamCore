# RoamCore System Summary (deterministic, local)

The RoamCore System Summary is a small, deterministic JSON contract that
exposes the *current* state of the most important RoamCore signals in one
place. It is the boring, consistent source of truth that both the RoamCore
UI and any local agent (OpenClaw, future MCP bridges, …) rely on.

## Endpoint

```
GET /api/roamcore/system/summary
```

- Auth: required (standard Home Assistant bearer token / cookie).
- Method: `GET` only.
- Size: ≤ 2 KB (intentional — no huge debug dumps).
- Rate: friendly to polling (UI polls every 30 s; agents should not exceed
  that).

## Response shape

The response is a single JSON object. **Top-level keys are sorted
alphabetically** for stable diffs and cacheable clients. Nested objects
keep their natural order.

```json
{
  "contract": {
    "name": "roamcore_system_summary",
    "version": 2
  },
  "diagnostics": {
    "signals_total": 9,
    "signals_unknown": 1,
    "signals_ok": 8
  },
  "generated_at": "2026-07-29T14:03:11.123456+00:00",
  "network": {
    "wan_source": "cellular",
    "wan_status": "good"
  },
  "overall": "ok",
  "power_backend": {
    "connected": true,
    "status": "ok"
  },
  "roamcore": {
    "component_version": "0.1.0-beta.1"
  },
  "schema": {
    "required": [
      "contract",
      "generated_at",
      "overall",
      "roamcore",
      "setup",
      "power_backend",
      "network",
      "diagnostics"
    ],
    "type": "object"
  },
  "setup": {
    "map_ready": true,
    "owner_ready": true,
    "ready": true,
    "stage": "complete",
    "trip_wrapped_ready": true,
    "victron_ready": true
  }
}
```

## Status semantics (`overall`)

The `overall` field is computed deterministically from the four `*_ready`
sensors:

| Result   | Meaning                                                                |
| -------- | ---------------------------------------------------------------------- |
| `ok`     | All four `*_ready` sensors are explicitly `true`.                      |
| `warn`   | At least one `*_ready` sensor is `unknown`/`unavailable` (transient).  |
| `error`  | At least one `*_ready` sensor is explicitly `false` (setup incomplete).|

This rule is intentionally simple: agents and UI do not need to know which
sensor is at fault to render a useful pill. Drill into the `setup` block
for per-sensor detail.

## How the UI consumes it

The bundled web component
[`homeassistant/www/roamcore/roamcore-system-summary.js`](https://github.com/roamcore/RoamCore/blob/main/homeassistant/www/roamcore/roamcore-system-summary.js)
is a self-contained custom element (`<roamcore-system-summary>`) that:

- Polls the endpoint every 30 s.
- Renders an overall status pill (`ok` / `warn` / `error`).
- Renders three collapsible rows (Setup, Power backend, Network).
- Shows a **trust indicator** chip using `diagnostics.signals_ok` /
  `diagnostics.signals_total` (e.g. "8/9 signals OK").
- Shows a "last refreshed HH:MM UTC" timestamp from `generated_at`.
- Falls back to *"Status unknown — connect to Home Assistant"* on auth or
  network errors.

Use it from a Lovelace dashboard with:

```yaml
type: custom:roamcore-system-summary
title: System summary
```

It is also embedded automatically on the RoamCore Settings page so the
summary stays visible even if the standalone file is not registered as a
Lovelace resource.

## How local agents consume it

From any language that can hit an HTTP endpoint:

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" \
     http://homeassistant.local:8123/api/roamcore/system/summary \
   | jq '.overall, .diagnostics'
```

Agents should:

1. Always check `contract.name == "roamcore_system_summary"` before
   parsing — protects against future routing changes.
2. Treat any non-2xx response as **transient** (the endpoint is best-effort
   by design — missing entities never crash it).
3. Treat `warn` as "try again in a few seconds"; treat `error` as
   "ask the user to finish setup".
4. Surface `diagnostics.signals_unknown` to the user when it is non-zero —
   it's the simplest honesty signal we have.

## Privacy

**All data stays on the local network.** Nothing is sent off-device. The
endpoint is served by Home Assistant on your LAN (or VPN) only; there is
no cloud relay, no telemetry, no third-party API calls.

## What's deterministic about it?

Three things, by design:

1. **Stable top-level key order.** The response is serialized with sorted
   top-level keys (alphabetic), so request-to-request bytes are byte-for-byte
   identical when nothing has changed.
2. **Stable contract name + version.** The string `"roamcore_system_summary"`
   and the integer `contract.version` only change on **breaking** schema
   changes. New optional fields do *not* bump the version.
3. **Bounded payload size.** Even with every signal `unknown`, the response
   stays well under 2 KB — no debug dumps, no per-entity chatter.

## Where it's wired

- View: `homeassistant/custom_components/roamcore/system_summary_view.py`
  (registered in `homeassistant/custom_components/roamcore/__init__.py`).
- UI card: `homeassistant/www/roamcore/roamcore-system-summary.js`.
- Page embed: `homeassistant/www/roamcore/roamcore-pages.js` (Settings
  page auto-mounts the card).
- Smoke check: `scripts/checks/system-summary-smoke.sh`.
- Wired into: `scripts/check.sh` (immediately after the Advanced mode
  smoke check).

<!-- RC_FEATURE_LIST_START -->
<!-- RC_FEATURE_LIST_END -->