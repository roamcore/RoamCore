# DIY bed lift (actuators / motor + strap)

**Support tier:** C (custom/manual)

## What this is
A DIY bed lift is usually either linear actuators or a winch/motor + strap system, controlled by a relay/driver and protected with limit switches.

## Why it’s useful in a van
- Space efficiency (garage vs living mode)
- One-tap lift/lower from the dashboard
- Safer operation with interlocks and limits

## Extra hardware required
Typically:
- Linear actuators OR winch/motor + strap
- Limit switches (top/bottom) (strongly recommended)
- A controller (ESPHome device + relays/motor driver)

## Install / best next step
- Model it in HA as a **Cover** (open/close/stop)
- Use ESPHome to control relays/outputs and read limit switches

## Links
- ESPHome Cover: https://esphome.io/components/cover/index.html
- ESPHome: https://esphome.io/
