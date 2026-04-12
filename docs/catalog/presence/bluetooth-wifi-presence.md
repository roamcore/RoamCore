# Bluetooth / Wi‑Fi presence detection (who’s home?)

**Support tier:** C

Detect whether people are home (and who) using Bluetooth and/or Wi‑Fi signals from phones, watches, key fobs, or other devices — then use that to drive automations.

## What you need
- A presence method (examples):
  - Bluetooth tracking (phone/watch/fob)
  - Wi‑Fi tracking (device on LAN)
  - Vehicle ignition/motion as a coarse “occupied” signal

## What RoamCore would do
- Provide a stable “occupied / away” signal and (optionally) per-person presence
- Use presence to power-safe the van:
  - shut down inverter/pump when nobody is home
  - turn on approach lighting when the first person returns after dark

## Common automations (ideas)
- Only consider “home” when both Bluetooth *and* Wi‑Fi agree (reduce false positives)
- Disable presence-based actions in Stealth mode

