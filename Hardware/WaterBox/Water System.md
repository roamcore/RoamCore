# RoamCore Water System — Step-by-Step (All Water Via Fresh Tank)

[SYSTEM DESIGN FIGMA LINK](https://www.figma.com/design/mpZcB5gHA9DwzJfKYSvjSF/Plumbing-System-Design?node-id=0-1&t=gbbskgiSEq6t5rgG-1)

> Assumptions: No city-water bypass. Every drop first enters the **fresh tank**, then the pump supplies the system. Grey-water handling is outside this scope.

## 1) Fill the Fresh Tank
1. **External Fill Port** → (optional **Pressure Regulator** if using city water) → **Sediment Filter (coarse)** → **Fresh Tank**.
2. **Fresh Tank Vent/Overflow** → route safely to exterior (free-breathing during fill/use).

## 2) Draw From the Tank (Inside the RoamCore Water Hub)
3. **Tank Outlet** → **Isolation Valve** (service shut-off) → **Strainer** (pre-pump).
4. **Strainer** → **12 V Diaphragm Pump** (creates system pressure/flow).
5. **Pump** → **Accumulator** (smooths flow, reduces cycling).
6. **Accumulator** → *(optional)* **Check Valve** (prevents backflow toward tank).
7. → **Cold Manifold (valved, labeled branches)**.

## 3) Distribute Cold + Feed Heater
8. **Cold Manifold** → **Cold Fixtures** (sink, toilet, etc.).
9. **Cold Manifold** → **Heater IN** via **Check Valve on Heater Feed** (prevents hot back-feed).
10. **Heater IN** → **Water Heater** → **Heater OUT** returns to hub.
11. **Cold Manifold** → **TMV Cold Inlet** (C).

## 4) Make Safe Hot Water
12. **Heater OUT** → **TMV Hot Inlet** (H).
13. **TMV (Thermostatic Mixing Valve)** blends H + C to a **safe setpoint ~42–45 °C**.
14. **TMV Mixed Outlet** → **Hot Manifold (valved)** → **Hot Fixtures** (shower, sink hot).

## 5) Service & Safety (Plumbing Only)
15. Fit **Isolation Valves** at: tank feed, pump/accumulator, cold manifold main, **Heater IN/OUT**, **TMV H/C/M ports**, and hot manifold main (fast service with minimal draining).
16. If the heater is **tank/boiler type**: install the **manufacturer’s TPR (Temperature & Pressure Relief) valve in the heater’s dedicated TPR port** and pipe the discharge line to a safe drain. *(Do not install TPRs inline.)*
17. If the heater is **tankless/on-demand**: no external TPR; TMV after the heater provides anti-scald.
18. Optional **Low-Point Drains** after the pump (cold) and after the TMV (hot mixed) for winterizing.

## Notes
- Keep whole-system carbon filtration **off** the main line; use a **separate drinking-water branch** if desired.
- Choose a shower head that meets the heater’s **minimum flow** (important for on-demand units).
