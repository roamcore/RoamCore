# Approach + underbody lights (welcome home)

**Support tier:** C

Turn on exterior/underbody lights automatically when you approach the van after dark, so you can see where you’re stepping and feel like the van is “welcoming you home”.

## What you need
- Any controllable exterior/underbody lights (relay, smart switch, or lighting controller)
- A presence signal (see: Presence detection feature)
- Optional: an “after sunset” signal (time or light sensor)

## What RoamCore would do
- Detect a **first arrival** event (nobody → someone home)
- If it’s dark, run a short “approach” lighting scene:
  - Underbody ON for N minutes
  - Porch/entry light ON
  - Optional: soft interior entry lighting

## Common automations (ideas)
- Only trigger when arriving (not when already home)
- Disable in “Stealth” mode
- Flash/brighten only if a camera sees a person at night

