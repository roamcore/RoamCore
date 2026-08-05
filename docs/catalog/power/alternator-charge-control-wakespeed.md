# Alternator charge control (Wakespeed / smart regulator)

If your build uses a smart alternator regulator (e.g. Wakespeed), you can automate when alternator charging is allowed and how aggressively it charges — based on ignition state, battery SOC, temperature, and “quiet” modes.

## How to install
- A smart alternator regulator (e.g. Wakespeed) and a way to control/observe it (CAN, serial, GPIO/relay, or a bridge device)
- An ignition / engine-running signal

## How it works
- Provide safe, mode-aware enable/disable of alternator charging
- Surface key signals (charging enabled, target voltage/current, faults)

## Common automations (ideas)
- When ignition turns on and charging is allowed, enable alternator charging
- Reduce alternator charge targets when batteries are cold/hot
- Disable alternator charging in “Stealth” or “Protect battery” situations

## What it does

What this feature gives you and what it shows in the van.

## Useful links

Upstream docs and related references.
