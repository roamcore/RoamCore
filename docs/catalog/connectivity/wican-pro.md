# WiCAN Pro

RoamCore auto-discovers it on the same network, polls it for engine RPM, speed, coolant temperature, throttle position, fuel level, battery voltage and a dozen other generic OBD2 readings, and saves them to a local time-series database. The dashboard populates automatically the moment the device is discovered — no…

## What you need

- Nothing extra — uses what's already in the van.

## Install

- Click **Add to my van** in the RoamCore dashboard, **or** run `bash <(curl -sL https://raw.githubusercontent.com/roamcore/RoamCore/main/install.sh) --feature wican-pro`.
- Restart Home Assistant.
- Done — the tiles appear under the relevant section in the dashboard.

## What it shows on your dashboard

- Engine load
- Coolant temp
- Stft bank1
- Ltft bank1
- Rpm
- Speed
- Timing advance
- Intake air temp
- Maf
- Throttle pct
- Run time
- Fuel rail pressure
- Fuel level pct
- Distance since dtc clear
- Control module voltage
- Ambient air temp
- Fuel rate
- Session readings
- Connected
- Dtc active
