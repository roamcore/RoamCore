# NAS (Network Attached Storage)

**Support tier:** B (Home Assistant supported)

> ⚠️ SUPERSEDED: This legacy tier-b spec has been promoted to a tier-b connection at [`connections/nas/`](../../../connections/nas/). This page is retained for historical context only. The current recipe (Synology DSM Path A + QNAP Path B + generic SMB/NFS Path C + NAS contract wiring + 4 automations + 8 troubleshooting entries + tier-a promotion outline) lives at [`connections/nas/docs/recipe.md`](../../../connections/nas/docs/recipe.md).

## What this is
A NAS gives you reliable local storage for media, camera footage, backups, and logs—especially useful when you don’t want to depend on cloud services.

## Why it’s useful in a van
- Local backups (even offline)
- Store CCTV recordings and Trip Wrapped exports
- Central place for media libraries

## Extra hardware required
- A NAS (or a mini-PC with storage)

## Install / best next step
Common HA paths:
- Use SMB/NFS shares for storage
- Use Synology/QNAP integrations if you have those devices

## Links
- Home Assistant Synology DSM: https://www.home-assistant.io/integrations/synology_dsm/
- Home Assistant SMB share (storage): https://www.home-assistant.io/common-tasks/os/#network-storage
- Home Assistant backups overview: https://www.home-assistant.io/common-tasks/general/#backups
