# DIY bed lift (actuators / motor + strap)

## What it does
A DIY bed lift is usually either linear actuators or a winch/motor + strap system, controlled by a relay/driver and protected with limit switches.

## Why it’s useful in a van
- Space efficiency (garage vs living mode)
- One-tap lift/lower from the dashboard
- Safer operation with interlocks and limits

## How to install
Typically:
- Linear actuators OR winch/motor + strap
- Limit switches (top/bottom) (strongly recommended)
- A controller (ESPHome device + relays/motor driver)

- Model it in HA as a **Cover** (open/close/stop)
- Use ESPHome to control relays/outputs and read limit switches

## Useful links
- ESPHome Cover: https://esphome.io/components/cover/index.html
- ESPHome: https://esphome.io/

## How it works

What RoamCore does behind the scenes.
