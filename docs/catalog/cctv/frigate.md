# CCTV with Frigate (spec + setup ideas)

**Support tier:** C (custom/manual)

## What this is
A single-page spec for a low-CPU CCTV system using Frigate + go2rtc, designed for predictable storage and practical van use.

## Why it’s useful in a van
- Security when you’re away
- Quick outside check at night
- Record incidents without relying on cloud subscriptions

## Extra hardware required
- IP cameras (RTSP/ONVIF) and networking (PoE switch recommended)
- Storage for recordings (SSD/NVMe)

## Install / best next step
- See: `homeassistant/HAOS/CCTV/FrigateOverview.md`

## Links
- Frigate: https://frigate.video/
- go2rtc: https://github.com/AlexxIT/go2rtc

---

## SUPERSEDED — 2026-08-03

This tier-c claim stub has been superseded by the **tier-b recipe connection** at
[`connections/frigate/`](../../../connections/frigate/) (Wave 3 #35, PR #<NEW>).

The new connection ships:
- The 12-tile vendor-neutral contract layer (4 cameras `rc_security_camera_*` + 4 detection `rc_security_detection_*` + 4 recording/storage `rc_storage_recording_*`).
- The FIVE-step operator-pickable NVR flow (Pick the NVR path + Mount the camera URLs + Confirm the cameras are online + Enable + start recording + Audit + revert).
- The FIVE §8 MANDATORY automations (per-camera offline guard + cameras-online guard + per-camera motion-mask guard + storage-full guard + records-on-motion guard).
- The 14-§section recipe howto (incl. the §10 Privacy section + the §14 Storage rotation policy section).
- The 7 manifest-honesty checks at `connections/frigate/tests/test_connection_yml.py`.

The legacy tier-c claim was honest-upstream-truth: RoamCore ships **no** native NVR engine in the repo today. The picker is honest and ships the contract layer + the recipe + the §8 automations + the operator-side NVR wire-up as tier-b. The legacy doc is preserved verbatim above for historical reference; the new connection is the canonical source-of-truth going forward.
