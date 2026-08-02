"""NFC tags (vendor-neutral NFC-triggered scenes mapped via tag_id →
scene mapping) — tier-c recipe connection.

This module is a marker-only stub. Tier-c connections don't ship native
HA integration code; they publish a recipe (docs/recipe.md) that walks
the operator through installing the upstream HA core `tag` integration
(since 2022.x — exposes scanned NFC tag IDs as `tag.last_scanned` +
persistence via the core `tag` registry + a `tag_scanned` event fired
on every scan) + wiring ONE OR MORE NFC readers (Path A phone-as-NFC-
reader via the HA Companion app + Path B USB NFC reader via the HACS
`nfcpy` integration + Path C HA Companion app `tag` trigger as an
implicit Path A) + adding a thin RoamCore automation wrapper that
maintains the `tag_id → scene` mapping table + runs the THREE §7
automations (last-tag-triggered scene + tag-unknown warning + Stealth-
mode suppression). The recipe exposes the resulting data via the
upstream `tag` + `scene` + `automation` + `device_tracker` integrations
+ the HACS `nfcpy` integration, then publishes the RoamCore NFC-tags
contract tiles on top (the 8 contract entities documented in
connection.yml — 1 sensor last-triggered-scene + 1 binary_sensor
last-triggered-scene-active + 1 sensor registered-tags-count + 1
sensor last-scanned-tag-id + 1 sensor last-scan-minutes-ago + 1
binary_sensor tag-unknown-warning + 1 binary_sensor stealth-mode-
suppressed + 1 button trigger-scene-now).

The audit + boundary CI can detect a `nfc-tags/` folder that claims to
be a connection via the `DOMAIN` constant exported here. The wizard
reads the manifest + recipe at runtime.

The real per-operator NFC-tags affordance path is:

    Operator-side NFC reader (Path A — the HA Companion app on the
        operator's Android phone with NFC enabled; the app exposes
        a `tag_scanned` event in HA core since 2022.x when the
        operator taps an NFC tag to the phone; OR Path B — a USB
        NFC reader (ACR122U / PN532 / SonMicro / Identiv) plugged
        into the HA server + the HACS `nfcpy` integration which
        forwards the NFC tag ID to HA as a `tag_scanned` event; OR
        Path C — implicit Path A via the HA Companion app's
        `tag` automation trigger since 2022.x, which is the same
        underlying phone-side NFC scan event as Path A)
        -> upstream entity (`event.tag_scanned` from HA core
           `tag` integration + the `tag.last_scanned` entity
           + the `tag.list` service for the registered-tags
           listing + the operator's `scene.*` entities from the
           HA core `scene` integration)
        -> RoamCore contract layer (HA core `template:` sensor +
           binary_sensor + the operator's `input_text` for the
           `tag_id → scene` mapping table + the `button` /
           `input_boolean` / `input_select` integrations for the
           operator-facing affordance tiles)
        -> dashboard tiles + OpenClaw queries
            ("what scene did the last NFC tag trigger?",
             "is the last NFC-tag-triggered scene still active?",
             "how many NFC tags are registered?",
             "what was the last scanned NFC tag ID?",
             "when was the last NFC tag scanned?",
             "is the tag-unknown warning active?",
             "is the NFC scanner in stealth mode suppression?",
             "trigger the last NFC-tag-triggered scene now")

    Safety interlocks (the recipe is the contract layer; the
    automation wrappers are documented in §7):
        -> The RoamCore last-tag-triggered scene automation is
           the §7.1 automation that fires when a `tag_scanned`
           event is received AND matches a known `tag_id` in
           the RoamCore `tag_id → scene` mapping table AND then
           calls `scene.turn_on` on the mapped scene. The
           mapping is the operator's single source of truth for
           which tag fires which scene; the recipe §3.4 walks
           through wiring the mapping table.
        -> The RoamCore tag-unknown warning automation is the
           §7.2 automation that fires when a `tag_scanned`
           event is received AND the `tag_id` is NOT in the
           RoamCore `tag_id → scene` mapping table. The
           automation sends a notification to the operator's
           phone (via the HA Companion app) saying "Unknown NFC
           tag scanned: <tag_id> — register it in the RoamCore
           tag_id → scene mapping table". This is the
           operator's on-ramp for adding new tags without
           having to read the recipe cover-to-cover.
        -> The RoamCore Stealth-mode suppression automation is
           the §7.3 automation that SUPPRESSES the §7.1 last-
           tag-triggered scene automation when the
           `select.rc_mode` is in `stealth` mode (campgrounds
           with quiet hours + overnight stays where running a
           scene would disturb other campers). The recipe §11
           cross-references the mode/automation-builder recipe
           (Wave 2 #23) for the `select.rc_mode` tile.

    Cross-references:
        -> The HA Companion app is the canonical phone-side NFC
           reader (Path A + Path C implicit Path A).
        -> The HACS `nfcpy` integration is the canonical USB NFC
           reader (Path B; ACR122U / PN532 / SonMicro / Identiv).
        -> The HA core `scene` integration is the canonical
           scene registry (the operator's `scene.*` entities).
        -> The HA core `automation` UI editor is the canonical
           operator-wired setup flow for the `tag_id → scene`
           mapping automation.
        -> The mode/automation-builder recipe Wave 2 #23
           cross-references the `select.rc_mode` tile (the
           Stealth-mode suppression source of truth).
        -> The deadbolts Wave 3 #48 connection cross-references
           the NFC-tags tile for the optional "tag-unlock-the-
           door" affordance (the operator tags an NFC tag at
           the entry door + the recipe adds a deadbolts scene
           to the `tag_id → scene` mapping table).

See docs/recipe.md for the full howto (HA core `tag` integration
install + HA Companion app NFC scan setup + HACS `nfcpy` integration
setup + Path A phone-as-NFC-reader wiring + Path B USB NFC reader
wiring + Path C implicit Path A wiring + the `tag_id → scene`
mapping table + the THREE §7 automations + the 8 `rc_nfc_*` contract
tiles + the 6 §8 troubleshooting entries + privacy + tier-b
promotion outline).
"""

DOMAIN = "nfc_tags"
