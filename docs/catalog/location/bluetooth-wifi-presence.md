# Bluetooth / Wi-Fi presence

Presence detection — who is currently home in the van — is the foundation of every occupied/away automation in RoamCore: shut down inverter + pump when nobody is home, turn on approach lighting when the first person returns after dark, suppress Stealth-silent-hours actions when only the driver is present, alert…

## What you need

- Nothing extra — uses what's already in the van.

## Install

- Click **Add to my van** in the RoamCore dashboard, **or** run `bash <(curl -sL https://raw.githubusercontent.com/roamcore/RoamCore/main/install.sh) --feature bluetooth-wifi-presence`.
- Restart Home Assistant.
- Done — the tiles appear under the relevant section in the dashboard.

## What it shows on your dashboard

- A Bluetooth / Wi-Fi presence tile that updates automatically.
