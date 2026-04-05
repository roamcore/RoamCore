# OpenClaw in Home Assistant (techartdev) — Recommended with RoamCore

RoamCore’s OpenClaw JSON endpoints provide a stable, machine-readable snapshot of your van.

To *run an agent* inside Home Assistant OS (HAOS) with a good UX, RoamCore recommends the techartdev OpenClaw stack:

- Add-on (runs OpenClaw in HAOS): https://github.com/techartdev/OpenClawHomeAssistant
- HA integration (chat card + Assist agent + service execution): https://github.com/techartdev/OpenClawHomeAssistantIntegration

RoamCore does **not** fork these projects. Install/update them via HACS/Add-on Store.

---

## 1) Install OpenClaw Assistant (Add-on)

Home Assistant → Settings → Add-ons → Add-on store

1) ⋮ → **Repositories**
2) Add:

```
https://github.com/techartdev/OpenClawHomeAssistant
```

3) Install **OpenClaw Assistant**
4) Start it

Then open the add-on page and run onboarding in its terminal:

```sh
openclaw onboard
```

Follow the prompts to connect your AI provider(s).

---

## 2) Install the OpenClaw Home Assistant Integration

This adds the chat card + Assist agent + HA services/events.

Install via HACS (Custom repository):

1) HACS → Integrations → ⋮ → Custom repositories
2) Add:
   - URL: `https://github.com/techartdev/OpenClawHomeAssistantIntegration`
   - Category: **Integration**
3) Install **OpenClaw**
4) Restart Home Assistant

Then add it:

Settings → Devices & Services → Add Integration → **OpenClaw**

If the add-on is installed on the same HA instance, the integration can auto-discover it.

---

## 3) Connect OpenClaw to RoamCore data

RoamCore exposes an OpenClaw-oriented JSON endpoint:

- Summary: `/api/roamcore/openclaw/summary`
- Convenience payload: `/api/roamcore/openclaw/skill`

Recommended pattern:
- In OpenClaw, create a skill/tool that fetches the RoamCore summary URL.
- Use that as “ground truth” context for chat and what-if questions.

Docs:
- `docs/reference/openclaw-json-api.md`

---

## 4) Action-taking (later, safety-first)

The techartdev integration supports tool calls that can execute HA services.

RoamCore’s recommendation for safety:
- keep read-only RoamCore APIs simple
- gate any action-taking behind:
  - authentication
  - allowlists
  - audit logs
  - optional confirmation flows

This is planned for a later RoamCore version.

