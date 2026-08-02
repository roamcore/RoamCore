> **SUPERSEDED** by `connections/motion-based-lighting/` (Wave 3 #53, shipped 2026-08-02).
> This page is kept for historical context only. The canonical spec now lives in
> `connections/motion-based-lighting/connection.yml` + `connections/motion-based-lighting/docs/recipe.md`.

# Motion‑based lighting (driving + arrival)

**Support tier:** C

Make lighting feel “automatic”:
- turn off interior house lights when the vehicle starts moving
- turn on soft interior lights when ignition turns off after dark
- turn on exterior lights when the first person returns home after sunset

## What you need
- Ignition / engine running signal (or motion/speed)
- Controllable lighting circuits
- Optional: presence detection

## What RoamCore would do
- Provide clean, mode-aware lighting scenes (Travel / Camp / Stealth)
- Ensure automations don’t fight manual control

