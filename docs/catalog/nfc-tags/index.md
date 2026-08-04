# NFC Tags

> **SUPERSEDED — Wave 2 #23 (2026-08-02).** This legacy tier-c placeholder spec has been promoted to a tier-c recipe connection at [`connections/nfc-tags/`](../../../connections/nfc-tags/). The new connection ships a vendor-neutral `tag_id → scene` mapping recipe over the upstream HA core `tag` integration + the HA Companion app + the HACS `nfcpy` integration + the HA core `scene` integration + the HA core `automation` UI editor + the mode/automation-builder recipe. The legacy tier-c content below is preserved for historical context only — do NOT wire a new install from this doc; use the recipe in the connection folder.

**Replaced by:** [`connections/nfc-tags/`](../../../connections/nfc-tags/)

**Recipe:** [`connections/nfc-tags/docs/recipe.md`](../../../connections/nfc-tags/docs/recipe.md)

---

Cheap + simple NFC tags make the van feel magical: tap your phone to
run a scene (Lights off, Bedtime, Leave camp).

## What you need

- Nothing extra — uses what's already in the van.

## Install

- Add this repo as a **HACS custom repository** (Category: *Integration*), then install **nfc-tags**.
- Restart Home Assistant.
- Done — the tiles appear under the relevant section in the dashboard.

## What it shows on your dashboard

- A NFC tags tile that updates automatically.