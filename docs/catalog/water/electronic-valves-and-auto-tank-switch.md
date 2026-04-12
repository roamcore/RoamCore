# Electronic valves + auto tank switching

**Support tier:** C

Use electronically controlled valves to automate water routing: switching between primary/aux tanks, closing a grey valve if it’s left open, and protecting the system in freezing conditions.

## What you need
- Electrically actuated valves (12V/24V) + safe drivers (relays/IO modules)
- Tank level sensors (primary + auxiliary)
- Optional: temperature sensors (freeze protection)

## What RoamCore would do
- Expose a clear state model:
  - active tank (primary/aux)
  - grey valve open/closed
  - freeze risk (yes/no)
- Provide one-tap actions (switch tanks, close grey valve)

## Common automations (ideas)
- Switch to auxiliary tank when primary reaches 0%
- Close the grey valve if it’s left open for N minutes
- When freeze risk is detected: close valves / run safe drain / enable tank heater (build dependent)

