# NFC tags (vendor-neutral NFC-triggered scenes mapped via `tag_id → scene` mapping)

**Tier:** C (recipe)
**Category:** access_control
**Status:** recipe_published

## What this connection is

NFC tags (vendor-neutral NFC-triggered scenes mapped via `tag_id → scene` mapping) — the umbrella for "cheap + simple NFC tags make the van feel magical: tap your phone to run a scene (Lights off, Bedtime, Leave camp)" — is the access-control-category complement to the broader RoamCore scene + automation affordances. The single "what scene did the last NFC tag trigger?" tile aggregates the most recent `tag_scanned` event into one dashboard indicator; the "is the last-tag-triggered scene still active?" tile is the scratchpad state (TRUE while the triggered scene is still in its active state); the "how many NFC tags are registered?" tile surfaces the operator's coverage; the "tag-id of the last scanned tag" sensor surfaces the most recent scanned tag ID; the "last-tag ID scanned minutes ago" sensor is the freshness gate (helpful for "when did the operator last interact with the van?"); the "tag-unknown warning" binary sensor surfaces whether the last scanned tag was unknown (the operator's on-ramp for adding new tags); the "Stealth-mode suppression" binary sensor surfaces whether the mode/automation-builder recipe is currently suppressing NFC-triggered scenes; the "trigger-scene-now" button surfaces the manual override (operator can trigger the last-tag-triggered scene without re-scanning the tag — useful for the "I just want the lights off" affordance).

RoamCore ships **no** native NFC integration. We RECIPE the well-understood upstream HA core `tag` integration (since 2022.x — exposes scanned NFC tag IDs as `tag.last_scanned` + persistence via the core `tag` registry + a `tag_scanned` event fired on every scan) + a thin RoamCore automation wrapper that maps each `tag_id` to a RoamCore scene (the umbrella for "Lights off" + "Bedtime" + "Leave camp" + operator-defined scenes). The 8 `rc_nfc_*` contract tiles are the vendor-neutral layer the dashboard + OpenClaw queries use; the actual NFC tag scan event is fired by the upstream HA core `tag` integration + the HA Companion app + the HACS `nfcpy` integration (RoamCore does NOT fork any of these).

## Setup recipe (one-paragraph)

1. Source NFC tags (any NTAG215 / NTAG216 / Mifare Classic 1K / Mifare Ultralight NFC sticker tags work — they are cheap + widely available + the HA Companion app + the HACS `nfcpy` integration both support them out of the box).
2. Pick a NFC reader path (one or more of):
   - **Path A — Phone-as-NFC-reader via the HA Companion app.** Install the HA Companion app on the operator's Android phone + enable NFC scans on the phone (Settings → Companion app → Sensors → NFC tag sensor). The HA Companion app exposes a `tag_scanned` event in HA core since 2022.x when the operator taps an NFC tag to the phone. Path A is the default for any van operator who has a modern Android phone with NFC built in (most Android phones since 2018 support NFC).
   - **Path B — USB NFC reader via the HACS `nfcpy` integration.** Plug a USB NFC reader (ACR122U / PN532 / SonMicro / Identiv) into the HA server + install the HACS `nfcpy` integration. The HACS `nfcpy` integration forwards the NFC tag ID to HA as a `tag_scanned` event. Path B is the default for vans where the operator does NOT have an Android phone with NFC (e.g. the operator uses an iPhone, which does NOT expose an NFC scan event to HA directly) OR for vans where the operator wants a SINGLE shared NFC reader that everyone in the van can use (no per-phone pairing required).
   - **Path C — Implicit Path A via the HA Companion app's `tag` trigger.** The HA Companion app's `tag` trigger (since 2022.x) fires a `tag_scanned` event in HA when the operator scans an NFC tag with the phone. Path C is functionally identical to Path A (the HA Companion app is the phone-side NFC reader); the recipe treats Path C as an "implicit" Path A (the operator does NOT need to install a separate NFC reader; the phone IS the NFC reader).
3. Register each NFC tag in HA's tag registry (Settings → Devices & Services → Tags → Add tag — paste the tag's unique ID + give it a friendly name).
4. Create the operator's scenes in HA's scene registry (Settings → Devices & Services → Scenes → Add scene — choose the entities + their states for each scene).
5. Wire the §7.1 last-tag-triggered scene automation (the `tag_id → scene` mapping table) — the operator's single source of truth for which tag fires which scene.
6. Wire the §7.2 tag-unknown warning automation (so the operator gets a notification when an unregistered tag is scanned).
7. Wire the §7.3 Stealth-mode suppression automation (so the mode/automation-builder recipe's `select.rc_mode` tile can suppress NFC-triggered scenes in campgrounds with quiet hours).
8. Verify: scan a known NFC tag → check `sensor.rc_nfc_last_triggered_scene` reflects the mapped scene; scan an unknown NFC tag → check `binary_sensor.rc_nfc_tag_unknown_warning` is TRUE.

Full howto: see [`docs/recipe.md`](docs/recipe.md).

## Why tier-c, not tier-b

Tier-b would require a RoamCore-owned NFC integration + integration code + integration tests against a real NFC bench (a controlled NFC tag reader + canned fixture responses for `tag_scanned` events + the upstream HA core `tag` integration installed + the HACS `nfcpy` integration installed). We have no operator-side NFC bench on the CI to integration-test against (the bench requires a physical NFC reader + canned fixture responses for `tag_scanned` events + the HA Companion app's `tag` trigger installed + the HACS `nfcpy` integration installed + the upstream HA core `tag` integration installed — all wired together in a controlled environment). Tier-c is the honest tier: HA's core `tag` integration is upstream HA core code (not RoamCore-owned); the RoamCore wrapper is a thin `tag_id → scene` mapping table + a contract layer. The recipe is sound but we cannot claim one-tap automation.

The legacy catalog page (`docs/catalog/nfc-tags/index.md` — 14-line stub, originally listed as "Support tier: C" with no recipe + no contract + no automations — just a placeholder about "easy NFC-based automations and practical places to put tags in a van" + "Lights off", "Bedtime", "Leave camp" as example scene names) is now superseded by this tier-c recipe connection.

## Files

- `connection.yml` — the source-of-truth manifest.
- `__init__.py` — `DOMAIN = "nfc_tags"` marker for the audit.
- `docs/recipe.md` — the full howto.
- `tests/test_connection_yml.py` — manifest honesty checks.

## See also

- Legacy catalog page (now superseded by this slice): [`docs/catalog/nfc-tags/index.md`](../../docs/catalog/nfc-tags/index.md)
- HA core `tag` integration: https://www.home-assistant.io/integrations/tag/
- HA core `scene` integration: https://www.home-assistant.io/integrations/scene/
- HA Companion app NFC sensor docs: https://companion.home-assistant.io/docs/core/sensors
- HACS `nfcpy` integration (USB NFC reader): https://hacs.xyz/docs/integrations/active
- Mode/automation-builder (the `select.rc_mode` tile source of truth for the §7.3 Stealth-mode suppression): `connections/smart-automations/` (Wave 2 #23)
- Deadbolts (the optional "tag-unlock-the-door" affordance that uses the same `tag_id → scene` mapping pattern): `connections/deadbolts/` (Wave 3 #48)
- Approach lights (the canonical "Lights off" / "Welcome home" scene entities): `connections/approach-lights/` (Wave 3 #52)
- HVAC basics (the canonical "Bedtime" / "Climate" scene entities): `connections/hvac-basics/` (Wave 3 #49)
- RoamCore entity naming: `docs/reference/rc-entity-naming.md`
