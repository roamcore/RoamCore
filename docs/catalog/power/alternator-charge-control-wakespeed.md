# Alternator charge control (Wakespeed / smart regulator)

**Support tier:** C

If your build uses a smart alternator regulator (e.g. Wakespeed), you can automate when alternator charging is allowed and how aggressively it charges — based on ignition state, battery SOC, temperature, and “quiet” modes.

## What you need
- A smart alternator regulator (e.g. Wakespeed) and a way to control/observe it (CAN, serial, GPIO/relay, or a bridge device)
- An ignition / engine-running signal

## What RoamCore would do
- Provide safe, mode-aware enable/disable of alternator charging
- Surface key signals (charging enabled, target voltage/current, faults)

## Common automations (ideas)
- When ignition turns on and charging is allowed, enable alternator charging
- Reduce alternator charge targets when batteries are cold/hot
- Disable alternator charging in “Stealth” or “Protect battery” situations

