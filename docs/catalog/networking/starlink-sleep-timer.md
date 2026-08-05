# Starlink sleep timer (night + battery saving)

>  SUPERSEDED: This legacy tier-c spec has been promoted to a tier-b connection at [`connections/starlink/`](../../connections/starlink/). This page is retained for historical context only. The current recipe (smart-plug wiring, HA helpers, optional signal-stats, sleep + wake + mode-aware automations, troubleshooting, tier-a promotion outline) lives at [`connections/starlink/docs/recipe.md`](../../connections/starlink/docs/recipe.md).

Automatically power down (or “sleep”) Starlink at night or when you don’t need it, to save battery and reduce idle consumption — without losing the ability to bring it back when needed.

## How to install
- Starlink power control (smart plug/relay/DC switch) **or** router/API support for Starlink control
- A schedule (quiet hours) or mode signal (Camp / Travel / Stealth)

## How it works
- Provide a simple toggle or schedule for “Starlink allowed”
- Optionally expose a one-tap “Wake Starlink for 30 minutes” action

## Common automations (ideas)
- Sleep Starlink when going to bed
- Wake Starlink periodically if nobody is home and no other internet is available (to preserve remote access)
- Disable sleep while driving (Travel mode)

## What it does

What this feature gives you and what it shows in the van.

## Useful links

Upstream docs and related references.
