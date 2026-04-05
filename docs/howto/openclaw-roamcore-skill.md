# Install the RoamCore OpenClaw Skill (agent-side insights)

RoamCore intentionally keeps the on-van compute minimal.

Instead of adding “analysis endpoints” on the RoamCore box, we provide **data-only** endpoints from Home Assistant and let your **OpenClaw agent** do the analysis.

This doc explains how to install the RoamCore skill into an OpenClaw instance.

---

## What the skill does

The `roamcore` OpenClaw skill teaches the agent to:
- fetch RoamCore’s structured snapshot: `/api/roamcore/openclaw/summary`
- optionally fetch full inventory: `/api/roamcore/openclaw/rc_dump`
- compute practical insights (power, leveling, readiness) **inside the agent**

---

## Install (copy the skill folder)

In this repo, the skill lives at:

`openclaw/skills/roamcore/SKILL.md`

Copy the entire `roamcore` folder into your OpenClaw workspace `skills/` directory.

Example:

```bash
# From a machine where you have this RoamCore repo checked out
cp -R openclaw/skills/roamcore /path/to/your/openclaw/workspace/skills/
```

Then restart OpenClaw (or start a new session) so it reloads skills.

---

## Configure the agent to reach RoamCore

From your Home Assistant instance (RoamCore):

- `GET /api/roamcore/openclaw/skill`

This returns:
- `openclaw_summary_url` (the absolute URL to use)
- `requires_auth` (whether you need a Bearer token)

If `requires_auth=true`, provide OpenClaw with a Home Assistant Long-Lived Access Token.

---

## Verify

From the agent machine:

```bash
curl http://HOME_ASSISTANT:8123/api/roamcore/openclaw/summary
curl http://HOME_ASSISTANT:8123/api/roamcore/openclaw/rc_dump
```

You should get JSON.

