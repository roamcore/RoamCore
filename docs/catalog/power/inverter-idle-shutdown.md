# Inverter idle shutdown (automatic power safety)

**Support tier:** C

Automatically turn off (or reduce) inverter usage when it’s been idle for a while, or when nobody is home — to prevent silent battery drain.

## What you need
- Inverter telemetry (on/off state, load watts) and a safe way to control it
- Optional: presence detection (nobody home)

## What RoamCore would do
- Show inverter status + load
- Provide a safe “inverter allowed” toggle
- Optionally automate inverter OFF when:
  - load is below a threshold for N minutes
  - nobody is home
  - battery SOC is low

## Common automations (ideas)
- Don’t shut off if a critical load is active (fridge/medical/etc.)
- Disable in “Travel” if you rely on it while driving

