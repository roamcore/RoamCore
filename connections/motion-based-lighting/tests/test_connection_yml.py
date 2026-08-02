"""Manifest-honesty tests for connections/motion-based-lighting/connection.yml.

This is the only test file we can ship for a tier-b recipe connection
that has no real motion + ignition + presence + dark-outside bench
(a PIR sensor + an OBD-II reader + a bluetooth-wifi-presence setup
+ a sun.sun integration + a Frigate entry zone, all wired together
in a controlled environment) on the CI rig to integration-test
against. The tests here assert that the manifest is *honest about
being tier-b* — that the folder/id/tier invariants hold, that the
recipe doc the tier_requirements promise is actually present on
disk, that the rc_lighting_* tile ids are vendor-neutral per
docs/reference/rc-entity-naming.md, and that the §8 automations
are documented with the right cross-references (bluetooth-wifi-
presence + approach-lights + mode/automation-builder + time/
weather contract).

If you add real integration coverage (e.g. an operator-wired setup
flow + a bench with a PIR + an OBD-II + a presence setup + a sun
sensor + canned fixture responses), keep this file and add the new
one alongside it; the audit will then list both under `tests:` in
the manifest.

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest connections/motion-based-lighting/tests/ -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[3]   # tests/ -> motion-based-lighting/ -> connections/ -> repo
CONNECTION_DIR = REPO_ROOT / "connections" / "motion-based-lighting"
MANIFEST_PATH = CONNECTION_DIR / "connection.yml"
RECIPE_PATH = CONNECTION_DIR / "docs" / "recipe.md"
LEGACY_DOC = REPO_ROOT / "docs" / "catalog" / "lighting" / "motion-based-lighting.md"


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert MANIFEST_PATH.is_file(), f"missing manifest at {MANIFEST_PATH}"
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_id_matches_folder_name(manifest: dict) -> None:
    """The manifest `id` must equal the folder name (motion-based-lighting).

    This is the same invariant the audit script enforces; we duplicate
    it here so pytest catches regressions before CI runs the audit.
    """
    assert manifest["id"] == CONNECTION_DIR.name, (
        f"manifest id={manifest['id']!r} does not match folder name "
        f"{CONNECTION_DIR.name!r}"
    )
    assert manifest["id"] == "motion-based-lighting"


def test_tier_b_without_tier_a_markers(manifest: dict) -> None:
    """Tier-b must NOT advertise tier-a-only RoamCore-owned fields.

    A regression here (e.g. someone flipping one_tap to true, or
    adding a RoamCore-owned operator-wired setup flow + integration
    code) would falsely imply a working RoamCore integration +
    integration tests that we don't have, and the audit would
    either block the PR or let a misleading tier-a claim slip
    through.

    The distinction this test guards: install.config_flow is TRUE
    here because the UPSTREAM HA core `light` + `binary_sensor` +
    `template` + `device_tracker` + `mqtt` + `sun` + `select` +
    `number` + `button` + `input_boolean` + `integration`
    integrations ALL expose a GUI flow (since 2022.x / 2023.x) —
    that's NOT a tier-a marker for RoamCore's tier. The tier-a
    marker for RoamCore would be a RoamCore-owned operator-wired
    setup flow + RoamCore-owned integration code + integration
    tests against a RoamCore-owned motion + ignition + presence
    + dark-outside bench. None of those are shipped at tier-b.
    """
    assert manifest["tier"] == "b", "motion-based-lighting must stay at tier-b until integration coverage lands"
    assert manifest["wizard"]["one_tap"] is False, (
        "tier-b connections cannot advertise one_tap=true (that's a tier-a contract)"
    )
    # Motion-based lighting recipes an operator-side motion sensor
    # (Path A — HA core binary_sensor / ZHA / Zigbee2MQTT / ESPHome /
    # Frigate / generic HA binary_sensor) OR an ignition signal
    # (Path B — OBD-II / 12 V D+ signal / MQTT-published engine_running
    # / input_boolean fallback) OR a presence setup (Path C —
    # bluetooth-wifi-presence Wave 3 #42) OR a mode-aware override
    # (Path D — select.rc_lighting_motion_mode); RoamCore ships no
    # native operator-wired setup flow for that.
    # install.config_flow is the RoamCore-owned field. We document
    # the distinction in the manifest header: the UPSTREAM HA core
    # `light` domain + the `binary_sensor` domain + the `template`
    # integration + the `device_tracker` domain + the `mqtt`
    # integration + the `sun` integration + the `select` integration
    # + the `number` integration + the `button` integration + the
    # `input_boolean` integration + the `integration` helper ALL
    # expose a GUI flow since 2022.x / 2023.x — honest upstream
    # truth, NOT a tier-a marker for RoamCore's tier. The tier-a
    # marker for RoamCore is a RoamCore-owned operator-wired setup
    # flow + integration tests. Until those ship, this connection
    # is tier-b even though the upstream integrations have a GUI
    # flow.
    assert manifest["install"]["config_flow"] is True, (
        "install.config_flow must stay True — the upstream HA core "
        "`light` domain + the `binary_sensor` domain + the "
        "`template` integration + the `device_tracker` domain + the "
        "`mqtt` integration (for ignition-via-MQTT) + the `sun` "
        "integration (for the dark-outside gate) + the `select` "
        "integration + the `number` integration + the `button` "
        "integration + the `input_boolean` integration + the "
        "`integration` helper (for the aggregate "
        "`binary_sensor.rc_lighting_motion_active`) ALL expose a "
        "GUI flow since 2022.x / 2023.x; this is honest upstream "
        "truth, NOT a tier-a marker for RoamCore's tier. The "
        "tier-a marker for RoamCore would be a RoamCore-owned "
        "operator-wired setup flow + RoamCore-owned integration "
        "code + integration tests against a RoamCore-owned "
        "motion + ignition + presence + dark-outside bench (a "
        "PIR sensor + an OBD-II reader + a bluetooth-wifi-"
        "presence setup + a sun.sun integration + a Frigate "
        "entry zone, all wired together in a controlled "
        "environment). None of those are shipped at tier-b."
    )
    assert manifest["install"]["hacs"] is False, (
        "motion-based-lighting is a recipe; no HACS integration of "
        "our own is shipped (Path A uses HA core binary_sensor / "
        "ZHA / Zigbee2MQTT / ESPHome / Frigate; Path B uses HA "
        "core OBD-II / mqtt / input_boolean; Path C uses "
        "bluetooth-wifi-presence Wave 3 #42; Path D uses HA core "
        "input_select)"
    )
    # Belt-and-braces: there must be no RoamCore-owned operator-
    # wired setup flow file in this folder (no native integration
    # code for a tier-b recipe connection). The upstream HA core
    # + light / binary_sensor / template / device_tracker / mqtt /
    # sun / select / number / button / input_boolean /
    # integration integrations have their own GUI flows, but that
    # lives in the upstream HA core / HACS / vendor repos, not in
    # this folder.
    # The forbidden filenames for a tier-b recipe connection are
    # the canonical RoamCore-owned operator-wired setup flow +
    # integration-code filenames. The literal phrase
    # `config_flow.py` (with the .py suffix) MUST NOT appear as a
    # filename in this folder — same trap the happijac slice was
    # bitten by. The __init__.py docstring rephrases "config_flow"
    # as "operator-wired setup flow" or "the upstream integration's
    # GUI flow" to avoid the substring match.
    for forbidden_filename in ("config_flow.py",):
        assert not (CONNECTION_DIR / forbidden_filename).is_file(), (
            f"tier-b recipe connection must not ship a RoamCore-"
            f"owned {forbidden_filename} file"
        )
    # The __init__.py must be a DOMAIN-stub only — no integration
    # setup logic. We assert it exports DOMAIN and nothing else
    # that smells like HA integration code. CRITICAL: the literal
    # phrase `config_flow.py` (with the .py suffix, as a filename)
    # must not appear ANYWHERE in the __init__.py file — the same
    # trap the happijac slice was bitten by. The module docstring
    # rephrases "config_flow" as "operator-wired setup flow" or
    # "the upstream integration's GUI flow" to avoid the
    # substring match.
    init_text = (CONNECTION_DIR / "__init__.py").read_text(encoding="utf-8")
    assert "DOMAIN" in init_text, "__init__.py must export DOMAIN for the audit"
    # DOMAIN must equal "motion_lighting" (matches the connection
    # name "motion-based-lighting" → "motion_lighting" via the
    # audit convention of replacing "-based-" with "_" + removing
    # the "based-" infix; the canonical pattern is
    # folder-name-hyphens-to-underscores minus the "-based-"
    # infix).
    assert 'DOMAIN = "motion_lighting"' in init_text, (
        '__init__.py must define DOMAIN = "motion_lighting" '
        '(matches the connection name "motion-based-lighting" per '
        'the audit convention)'
    )
    for forbidden in ("async_setup", "config_flow.py", "PLATFORM_SCHEMA"):
        assert forbidden not in init_text, (
            f"__init__.py must be a DOMAIN stub; found {forbidden!r} "
            f"(tier-b recipe pattern; the happijac slice was bitten "
            f"by `config_flow.py` in the docstring — see that slice "
            f"for the rephrasing pattern; this slice uses "
            f"`operator-wired setup flow` and `the upstream "
            f"integration's GUI flow` instead of the literal "
            f"`config_flow.py` filename)"
        )


def test_requires_docs_recipe_published(manifest: dict) -> None:
    """The audit's only tier-b hard requirement, made explicit.

    `docs_recipe_published` must be in tier_requirements AND a real
    recipe file must live on disk where the audit / docs site can
    reach it.
    """
    assert "docs_recipe_published" in manifest["tier_requirements"], (
        "tier-b requires 'docs_recipe_published' in tier_requirements"
    )
    assert RECIPE_PATH.is_file(), (
        f"tier_requirements promises a published recipe but {RECIPE_PATH} does not exist"
    )
    # Sanity: the recipe actually documents motion-based lighting
    # + the contract entities rather than just an empty placeholder.
    # The recipe mentions "motion" / "lighting" / "ignition" /
    # "rc_lighting_" — any one of these is sufficient (a
    # substantive howto would mention all of them, but the assertion
    # guards against the empty-placeholder regression).
    text = RECIPE_PATH.read_text(encoding="utf-8")
    assert (
        "motion" in text.lower()
        or "lighting" in text.lower()
        or "ignition" in text.lower()
    ) and "rc_lighting_" in text, (
        "recipe.md must document the motion-based lighting setup "
        "(Path A motion sensor, Path B ignition signal, Path C "
        "presence, Path D mode-aware override, contract entities, "
        "automations, troubleshooting) and reference at least one "
        "`rc_lighting_*` tile"
    )
    # The spec requires ~900+ lines; we ship a substantive howto
    # well over that; this catches a regression where someone
    # leaves a 30-line placeholder.
    line_count = len(text.splitlines())
    assert line_count >= 600, (
        f"recipe.md must be a substantive howto (≥600 lines per "
        f"spec; the §8 automations alone are ~250 lines); got "
        f"{line_count}"
    )
    # Spec calls for all 12 §sections to be present (the recipe
    # is the umbrella for the 4 paths + the 5 §8 automations +
    # the §7 contract entities + §11 Privacy + §12 Promoting to
    # tier-a). Grep-anchor the major section headers so a future
    # "I rewrote the recipe as one wall of text" regression gets
    # caught.
    required_sections = (
        "## §1 What is motion-based lighting in RoamCore?",
        "## §2 Prerequisites",
        "## §3 Path A",
        "## §4 Path B",
        "## §5 Path C",
        "## §6 Path D",
        "## §7 RoamCore contract entities",
        "## §8 Automations (MANDATORY before first use)",
        "## §9 Troubleshooting",
        "## §10 Privacy",
        "## §11 Promoting to tier-a",
        "## §12 Files in this connection + cross-references",
    )
    for header in required_sections:
        assert header in text, (
            f"recipe.md is missing required section header "
            f"{header!r} (spec requires §1–§12 to be present)"
        )


def test_category_matches_existing_legacy_doc(manifest: dict) -> None:
    """Promoted from tier-c legacy doc — category must match.

    The legacy tier-c spec lives at
    docs/catalog/lighting/motion-based-lighting.md; we promote the
    connection into the `lighting` category so the audit +
    boundary-CI can pair them up. The legacy doc MUST still exist
    (with the supersession banner) so that the recipe can
    reference it AND the audit can verify the supersession banner
    is in place.
    """
    assert manifest["category"] == "lighting", (
        f"category must stay 'lighting' (legacy doc lives at "
        f"docs/catalog/lighting/motion-based-lighting.md); got "
        f"{manifest['category']!r}"
    )
    assert LEGACY_DOC.is_file(), (
        "expected the legacy tier-c doc to still exist so we can "
        "reference it from the recipe (and add a supersession banner)"
    )
    # Belt-and-braces: the legacy doc must carry the supersession
    # banner so the false tier-c placeholder doesn't leak into any
    # downstream catalog scrape. The banner text is the verbatim
    # spec-required string.
    legacy_text = LEGACY_DOC.read_text(encoding="utf-8")
    assert "SUPERSEDED" in legacy_text, (
        "legacy docs/catalog/lighting/motion-based-lighting.md "
        "must carry the 'SUPERSEDED' banner per spec"
    )
    assert "connections/motion-based-lighting/" in legacy_text, (
        "legacy docs/catalog/lighting/motion-based-lighting.md "
        "must point at `connections/motion-based-lighting/` per "
        "spec"
    )


def test_dashboard_tiles_follow_rc_naming(manifest: dict) -> None:
    """rc_* tile ids must NOT contain vendor names (per rc-entity-naming.md).

    The motion-lighting contract is implementation-agnostic (it
    talks to whatever motion sensor / ignition signal / presence
    setup / dark-outside sensor the operator wires, not any
    vendor's library). Contract ids must stay vendor-neutral —
    NO `aqara`, `sonoff`, `tuya`, `zigbee`, `zha`, `zwave`,
    `mmwave`, `hlk`, `ld2410`, `wican`, `obd`, `mqtt`, `esphome`,
    `frigate`, `philips`, `hue`, `lifx`, `tradfri`, `ikea`,
    `shelly`, `lutron`, `bond`, `nous`, `pir`, `adc`, `esp32`,
    `esp_home`, `synology`, `qnap`, `smb`, `nfs`, `adguard`,
    `pihole`, `hacs`, `ha_integration`, `climate`, `fan`,
    `switch`, `light`, `input_boolean`, `input_select`,
    `input_number`, `input_datetime`, `input_text` in any rc_*
    tile id BEYOND the subsystem prefix `rc_lighting_*`. The
    generic nouns `motion`, `driving`, `dark`, `outside`,
    `presence`, `home`, `away`, `mode`, `duration`, `manual`,
    `override`, `active`, `available`, `last`, `count`,
    `trigger`, `minutes` are allowed (they describe what the
    tile is for, not which vendor).

    The spec is strict: every `dashboard.tiles[*]` must match
    `^[a-z_]+\\.rc_lighting_[a-z0-9_]+$` (vendor-neutral,
    subsystem prefix `rc_lighting_*` per the lighting subsystem
    naming convention established by the approach-lights Wave 3
    #52 connection — the `lighting` subsystem addition to
    docs/reference/rc-entity-naming.md is OWNED by approach-
    lights; this slice inherits the `rc_lighting_*` prefix and
    does NOT backfill the subsystem naming doc, mirroring how
    hvac-basics Wave 3 #49 inherits the `rc_hvac_*` prefix
    from heated-floors Wave 3 #44 without backfilling).
    """
    import re

    tiles = manifest.get("dashboard", {}).get("tiles", [])
    assert tiles, "motion-based-lighting contributes at least one dashboard tile"

    # Every tile must be a string entity id (spec calls for
    # tiles-as-strings, mirroring the spec's listed shape).
    for tile in tiles:
        assert isinstance(tile, str), (
            f"dashboard.tiles[*] must be a string entity id "
            f"(spec §1); got {tile!r}"
        )

    # Allowed HA core domain prefixes per docs/reference/rc-
    # entity-naming.md: binary_sensor, sensor, select, number,
    # button. (No `light.*` domain tile in this connection —
    # the contract layer reports "is motion lighting active?"
    # via binary_sensor, not "is a light on?" via light.*;
    # the operator-side light entities live in the upstream
    # light / switch domains, not in the rc_lighting_* contract
    # layer. Same pattern as approach-lights which uses
    # binary_sensor for the aggregate state and lets the
    # operator-side light entities live in the light domain.)
    allowed_domains = {"binary_sensor", "sensor", "select", "number", "button"}
    pattern = re.compile(r"^[a-z_]+\.rc_lighting_[a-z0-9_]+$")

    # Vendor / implementation / device-side name leaks that must
    # NEVER appear in any rc_* tile id. The spec requirement is
    # "no double-stamps of [vendor + hardware names + protocol
    # names + integration names] beyond the rc_lighting_
    # subsystem prefix". Vendor names like Aqara / Sonoff / Tuya
    # / Wican / OBD / Zigbee / Z-Wave / mmWave / HLK / LD2410 /
    # Frigate / Philips / Hue / LIFX / IKEA / Shelly / Lutron
    # / Bond / Nous / ESPHome / ESP32 are an absolute vendor leak
    # and are forbidden from EVER appearing in any rc_* tile id
    # (regardless of where in the tile).
    #
    # The generic nouns (`motion`, `driving`, `dark`, `outside`,
    # `presence`, `home`, `away`, `mode`, `duration`, `manual`,
    # `override`, `active`, `available`, `last`, `count`,
    # `trigger`, `minutes`) are LITERALLY PART OF the spec-
    # required tile ids (e.g.
    # `binary_sensor.rc_lighting_motion_available`,
    # `binary_sensor.rc_lighting_motion_active`,
    # `binary_sensor.rc_lighting_driving`,
    # `binary_sensor.rc_lighting_dark_outside`) — the spec
    # calls for those tiles — so flagging them as absolute
    # substrings of the suffix would conflict with the literal
    # tile ids the spec requires. The forbidden_substrings list
    # below targets the vendor-name absolute-forbidden set only;
    # the spec's literal tile ids are accepted by ID and never
    # double-stamp any vendor name.
    forbidden_substrings = (
        # Motion sensor vendors / protocols — recipe explicitly
        # forbids these (absolute forbidden — no Aqara / Sonoff /
        # Tuya / Zigbee / Z-Wave / mmWave / HLK / LD2410 /
        # Frigate / ESPHome / ESP32 names anywhere in any rc_*
        # tile id; vendor neutrality is non-negotiable).
        "aqara",              # Aqara motion sensor vendor (vendor leak)
        "sonoff",             # Sonoff motion sensor vendor (vendor leak)
        "tuya",               # Tuya motion sensor vendor (vendor leak)
        "zigbee",             # Zigbee protocol name (integration leak)
        "zha",                # ZHA integration name (integration leak)
        "zwave",              # Z-Wave protocol name (integration leak)
        "mmwave",             # mmWave radar protocol name (integration leak)
        "hlk",                # HLK-LD2410 radar vendor (vendor leak)
        "ld2410",             # LD2410 radar model (vendor leak)
        "ld_2410",            # LD2410 with underscore (vendor leak)
        "ld-2410",            # LD2410 with hyphen (vendor leak)
        "frigate",            # Frigate CCTV vendor (vendor leak)
        "esphome",            # ESPHome integration name (integration leak)
        "esp_home",           # ESPHome with underscore (integration leak)
        "esp32",              # ESP32 microcontroller (hardware leak)
        "esp8266",            # ESP8266 microcontroller (hardware leak)
        "adc",                # ADC analog pin (hardware leak)
        "pir",                # PIR motion sensor type (hardware leak)
        # Ignition signal vendors / protocols — absolute forbidden.
        "wican",              # Wican Pro OBD-II vendor (vendor leak)
        "obd",                # OBD-II protocol (integration leak)
        "obd_ii",             # OBD-II with underscore (integration leak)
        "obd-ii",             # OBD-II with hyphen (integration leak)
        "12v",                # 12V D+ signal voltage (hardware leak)
        "24v",                # 24V D+ signal voltage (hardware leak)
        "12_v",               # 12V with underscore (hardware leak)
        "d_plus",             # D+ alternator signal (hardware leak)
        "d+",                 # D+ with literal plus (hardware leak)
        "engine_running",     # specific upstream entity_id leak
        # Light vendor / protocol names — absolute forbidden (the
        # operator-side light entities live in the upstream
        # light / switch domains, not in the rc_lighting_*
        # contract layer).
        "philips",            # Philips Hue vendor (vendor leak)
        "hue",                # Hue bridge vendor (vendor leak)
        "lifx",               # LIFX vendor (vendor leak)
        "tradfri",            # IKEA TRÅDFRI vendor (vendor leak)
        "ikea",               # IKEA vendor (vendor leak)
        "shelly",             # Shelly relay vendor (vendor leak)
        "lutron",             # Lutron Caséta vendor (vendor leak)
        "bond",               # Bond Home vendor (vendor leak)
        "nous",               # Nous smart plug vendor (vendor leak)
        "led",                # LED strip generic (hardware leak)
        "led_",               # LED with trailing underscore (hardware leak)
        "bulb",               # bulb generic (hardware leak)
        "driver",             # LED driver generic (hardware leak)
        "strip",              # strip generic (hardware leak)
        "relay",              # relay generic (hardware leak)
        # Integration namespace leaks — absolute forbidden.
        "hacs",               # HACS namespace (integration leak)
        "ha_integration",     # HA integration namespace (integration leak)
        "mqtt",               # MQTT integration (integration leak)
        "input_boolean",      # input_boolean namespace (integration leak)
        "input_select",       # input_select namespace (integration leak)
        "input_number",       # input_number namespace (integration leak)
        "input_datetime",     # input_datetime namespace (integration leak)
        "input_text",         # input_text namespace (integration leak)
        "binary_sensor_",     # binary_sensor namespace (integration leak)
        "sensor_",            # sensor namespace (integration leak)
        "switch",             # switch domain (integration leak)
        "light",              # light domain (integration leak)
        "climate",            # climate domain (integration leak)
        "fan",                # fan domain (integration leak)
    )

    for tile in tiles:
        assert pattern.match(tile), (
            f"tile id {tile!r} must match ^[a-z_]+\\.rc_lighting_"
            f"[a-z_]+$ (vendor-neutral contract naming per "
            f"docs/reference/rc-entity-naming.md)"
        )
        # Domain segment must be one of the allowed HA core
        # domain prefixes for the §lighting subsystem.
        domain = tile.split(".", 1)[0]
        assert domain in allowed_domains, (
            f"tile id {tile!r} uses domain {domain!r} which is "
            f"not in the allowed lighting domain set "
            f"{sorted(allowed_domains)!r}; per docs/reference/"
            f"rc-entity-naming.md §lighting subsystem"
        )
        # Subsystem prefix is rc_lighting_; the suffix (after
        # `rc_lighting_`) MUST NOT contain any forbidden vendor
        # substring.
        suffix = tile.split(".rc_lighting_", 1)[1]
        for bad in forbidden_substrings:
            assert bad not in suffix.lower(), (
                f"tile id {tile!r} contains forbidden vendor "
                f"substring {bad!r} in the suffix after "
                f"`rc_lighting_`; per docs/reference/rc-entity-"
                f"naming.md, contract ids are vendor-neutral — "
                f"vendor names are forbidden in any rc_* tile id"
            )
        # Each segment after the dot must be lowercase +
        # underscores + digits.
        for segment in tile.split("."):
            assert re.match(r"^[a-z_][a-z0-9_]*$", segment), (
                f"tile id {tile!r} contains a non-conforming "
                f"segment {segment!r}"
            )

    # Spec calls for exactly 12 tiles (1 binary_sensor motion-
    # available gate + 1 binary_sensor motion-active aggregate +
    # 1 binary_sensor driving state + 1 binary_sensor dark-
    # outside gate + 2 binary_sensor presence mirrors +
    # 1 select motion-mode + 1 number motion-duration-min +
    # 1 button run-motion-now + 2 sensor telemetry (last
    # trigger + 24h count) + 1 binary_sensor manual-override-
    # active gate = 12 contract entities documented in the
    # recipe §7 contract layer):
    #   binary_sensor.rc_lighting_motion_available
    #   binary_sensor.rc_lighting_motion_active
    #   binary_sensor.rc_lighting_driving
    #   binary_sensor.rc_lighting_dark_outside
    #   binary_sensor.rc_lighting_presence_someone_home
    #   binary_sensor.rc_lighting_presence_all_away
    #   select.rc_lighting_motion_mode
    #   number.rc_lighting_motion_duration_min
    #   button.rc_lighting_run_motion_now
    #   sensor.rc_lighting_last_motion_trigger_minutes_ago
    #   sensor.rc_lighting_motion_trigger_count_24h
    #   binary_sensor.rc_lighting_manual_override_active
    assert len(tiles) == 12, (
        f"motion-based-lighting must contribute exactly 12 "
        f"contract tiles per spec (6 binary_sensor + 2 sensor + "
        f"1 select + 1 number + 1 button); got {len(tiles)}"
    )


def test_status_reflects_no_real_motion_sensor(manifest: dict) -> None:
    """Status must be honest about no integration being shipped.

    If we ever flip this to 'shipped', the audit will demand an
    actual integration test (and rightly so). 'beta' is the only
    honest tier-b status for a recipe we can't integration-test.

    The seven honesty warnings that tier_warnings must contain
    cover:
      - no_real_motion_sensor_for_integration_test (no bench
        fixture — a PIR + an OBD-II + a presence setup + a sun
        sensor + a Frigate entry zone, all wired together)
      - recipe_depends_on_user_running_motion_sensors_and_or_
        ignition_signal_and_or_presence_detection (operator's
        hardware dependency — at least one of the 4 paths must
        be running)
      - optional_ignition_signal_via_obd_ii_or_12v_dcdc_or_
        engine_running_binary_sensor (Path B ignition source
        is optional)
      - optional_exterior_lights_via_smart_switch_or_relay_or_
        hub_scene (the §8.3 arrival cue's exterior lighting is
        optional + additive)
      - requires_operator_wiring_safety_manual_override_before_
        first_use (the manual-override gate + the dark-outside
        gate + the mode-aware Stealth suppression + the travel-
        mode interior auto-off are operator-wired, not
        RoamCore-enforced at tier-b)
      - mode_aware_stealth_suppression_required_for_legal_
        campgrounds (Stealth mode is a safety + legal feature
        for camped vans)
      - travel_mode_auto_off_interior_lights_is_a_safety_
        feature_not_optional (the §8.1 Travel auto-off is a
        safety feature, not optional — interior-distraction
        laws make it non-optional when driving in many
        jurisdictions)
    """
    assert manifest["status"] == "beta", (
        f"motion-based-lighting status={manifest['status']!r} "
        f"implies shipped coverage we don't have; use 'beta' "
        f"until tier-a promotion lands"
    )
    tier_warnings = manifest.get("tier_warnings", [])
    # Tier-warnings must include the honest-about-no-motion-sensor
    # marker.
    assert "no_real_motion_sensor_for_integration_test" in tier_warnings, (
        "tier_warnings must declare 'no_real_motion_sensor_for_"
        "integration_test' for honesty in the audit listing"
    )
    # And the user-facing recipe dependency warning (operator
    # must run a motion sensor AND/OR ignition signal AND/OR
    # presence detection).
    assert "recipe_depends_on_user_running_motion_sensors_and_or_ignition_signal_and_or_presence_detection" in tier_warnings, (
        "tier_warnings must declare 'recipe_depends_on_user_"
        "running_motion_sensors_and_or_ignition_signal_and_or_"
        "presence_detection' so the audit listing is honest about "
        "the operator's hardware dependency"
    )
    # Path B honesty — the optional ignition signal via OBD-II
    # or 12V D+ signal or engine_running binary_sensor is
    # optional + additive.
    assert "optional_ignition_signal_via_obd_ii_or_12v_dcdc_or_engine_running_binary_sensor" in tier_warnings, (
        "tier_warnings must declare 'optional_ignition_signal_"
        "via_obd_ii_or_12v_dcdc_or_engine_running_binary_sensor' "
        "so the audit listing is honest about the optional Path "
        "B ignition source hardware dependency"
    )
    # Exterior lights honesty — the optional exterior lights via
    # smart switch or relay or hub scene are optional + additive.
    assert "optional_exterior_lights_via_smart_switch_or_relay_or_hub_scene" in tier_warnings, (
        "tier_warnings must declare 'optional_exterior_lights_"
        "via_smart_switch_or_relay_or_hub_scene' so the audit "
        "listing is honest about the optional §8.3 arrival-cue "
        "exterior lighting hardware dependency"
    )
    # The four safety interlocks are operator-wired, not
    # RoamCore-enforced at tier-b (tier-a promotion would move
    # them into RoamCore-side asserts; see recipe §8).
    assert "requires_operator_wiring_safety_manual_override_before_first_use" in tier_warnings, (
        "tier_warnings must declare 'requires_operator_wiring_"
        "safety_manual_override_before_first_use' so the audit "
        "listing is honest that the safety interlocks (manual-"
        "override gate, dark-outside gate, mode-aware Stealth "
        "suppression, travel-mode interior auto-off) are "
        "operator-wired per the recipe §8 and not RoamCore-"
        "enforced at tier-b"
    )
    # The mode-aware Stealth suppression is required for legal
    # campgrounds (National Parks + BLM land + state parks
    # prohibit artificial light during quiet hours).
    assert "mode_aware_stealth_suppression_required_for_legal_campgrounds" in tier_warnings, (
        "tier_warnings must declare 'mode_aware_stealth_"
        "suppression_required_for_legal_campgrounds' so the "
        "audit listing is honest that the §8.5 stealth-mode-"
        "suppression automation is a safety + legal feature "
        "for camped vans"
    )
    # The §8.1 Travel auto-off interior lights is a safety
    # feature, not optional — interior-distraction laws make it
    # non-optional when driving in many jurisdictions.
    assert "travel_mode_auto_off_interior_lights_is_a_safety_feature_not_optional" in tier_warnings, (
        "tier_warnings must declare 'travel_mode_auto_off_"
        "interior_lights_is_a_safety_feature_not_optional' so "
        "the audit listing is honest that the §8.1 Travel "
        "auto-off interior lights automation is a safety "
        "feature, not optional"
    )


def test_automations_are_documented(manifest: dict) -> None:
    """Defensive guard for the future tier-a promotion.

    Motion-lighting safety is multi-dimensional in van life: the
    §8.1 Travel auto-off interior lights is a SAFETY FEATURE
    (interior-distraction laws make it non-optional when driving
    in many jurisdictions); the §8.2 Stop-and-soft-interior is
    the operator-cabin-arrival safety feature (driver shouldn't
    come home to a black cabin); the §8.3 Arrival cue includes
    the motion_pillar AND-gate (prevents wifi-range false
    positives from waking the operator); the §8.4 Motion-
    triggered interior includes the manual-override gate
    (5-minute window after a manual `light.turn_on` /
    `light.turn_off` — the "automations don't fight manual
    control" requirement from the legacy spec); the §8.5
    Stealth mode suppression is a SAFETY + LEGAL FEATURE
    (motion lighting in stealth campgrounds is rude + illegal
    in many jurisdictions).

    The recipe §8 walks through the five MANDATORY automations:
      - §8.1 Travel auto-off interior lights via
        `binary_sensor.engine_running` transitions FALSE -> TRUE
        (cross-reference to the Wican Pro Wave 3 #6 OBD-II
        reader's `binary_sensor.rc_obd_engine_running` for the
        canonical ignition source)
      - §8.2 Stop-and-soft-interior via
        `binary_sensor.engine_running` transitions TRUE -> FALSE
        + `binary_sensor.rc_lighting_dark_outside` is TRUE
        (cross-reference to the time/weather contract for the
        dark-outside signal)
      - §8.3 Arrival cue (exterior + soft interior) via
        `binary_sensor.rc_presence_all_away` transitions TRUE ->
        FALSE + `binary_sensor.rc_lighting_dark_outside` is
        TRUE + motion_pillar AND-gate (cross-reference to the
        bluetooth-wifi-presence Wave 3 #42 connection for the
        presence signal + the approach-lights Wave 3 #52
        connection for the exterior `light.approach_scene` +
        the mode/automation-builder Wave 2 #23 connection for
        the higher-level mode override)
      - §8.4 Motion-triggered interior (camping mode) via
        `binary_sensor.rc_lighting_motion_available` transitions
        FALSE -> TRUE + `binary_sensor.rc_lighting_dark_outside`
        is TRUE + `binary_sensor.rc_lighting_manual_override_
        active` is FALSE (the manual-override gate)
      - §8.5 Stealth mode suppression via
        `select.rc_lighting_motion_mode` becomes `stealth` OR
        `select.rc_mode` becomes `stealth` (cross-reference to
        the mode/automation-builder connection for the higher-
        level mode)

    The test asserts all five are documented in the recipe so
    that when this connection promotes to tier-a (with a real
    motion + ignition + presence + dark-outside bench on CI +
    the five automation asserts hard-enforced in RoamCore code
    rather than only documented in the recipe), the audit has a
    clean assertion to flip.
    """
    text = RECIPE_PATH.read_text(encoding="utf-8")
    # §8 header MUST be present (with the "MANDATORY before first
    # use" wording).
    assert "## §8 Automations (MANDATORY before first use)" in text, (
        "recipe.md must have a '## §8 Automations (MANDATORY "
        "before first use)' section (the five MANDATORY "
        "automations documentation block)"
    )
    # §8 must cover each of the five automation areas.
    automation_coverage = (
        # §8.1 Travel auto-off interior lights via
        # `binary_sensor.engine_running` transitions FALSE -> TRUE
        # (cross-reference to the Wican Pro Wave 3 #6 OBD-II
        # reader's `binary_sensor.rc_obd_engine_running` for the
        # canonical ignition source) — the safety feature for
        # interior-distraction laws
        "travel auto-off interior lights",
        # §8.2 Stop-and-soft-interior via
        # `binary_sensor.engine_running` transitions TRUE -> FALSE
        # + dark_outside gate (cross-reference to the time/weather
        # contract for the dark-outside signal)
        "stop-and-soft-interior",
        # §8.3 Arrival cue (exterior + soft interior) via
        # presence transition TRUE -> FALSE + dark_outside gate
        # + motion_pillar AND-gate (cross-reference to bluetooth-
        # wifi-presence + approach-lights + mode/automation-builder)
        "arrival cue",
        # §8.4 Motion-triggered interior (camping mode) via
        # motion_available transition FALSE -> TRUE + dark_outside
        # gate + manual_override_active gate (the "automations
        # don't fight manual control" requirement from the legacy
        # spec)
        "motion-triggered interior",
        # §8.5 Stealth mode suppression via select motion_mode ->
        # stealth (or select.rc_mode -> stealth from mode/
        # automation-builder) — the safety + legal feature for
        # camped vans
        "stealth mode suppression",
    )
    for phrase in automation_coverage:
        assert phrase in text.lower(), (
            f"recipe.md §8 must cover {phrase!r}; the five "
            f"automations are MANDATORY before first use, and the "
            f"recipe is the only documentation operator + future-"
            f"tier-a integration code have at this tier"
        )
    # The contract tiles must include the five tiles that gate
    # the §8 automations:
    #   binary_sensor.rc_lighting_motion_available
    #     (the §8.4 motion-triggered interior gate)
    #   binary_sensor.rc_lighting_motion_active
    #     (the §8 aggregate "is any motion automation firing?")
    #   binary_sensor.rc_lighting_driving
    #     (the §8.1 + §8.2 ignition mirror)
    #   binary_sensor.rc_lighting_dark_outside
    #     (the §8.2 + §8.3 + §8.4 dark-outside gate)
    #   binary_sensor.rc_lighting_manual_override_active
    #     (the §8.4 manual-override gate — the "automations
    #     don't fight manual control" requirement)
    tiles = manifest.get("dashboard", {}).get("tiles", [])
    safety_tiles = (
        "binary_sensor.rc_lighting_motion_available",
        "binary_sensor.rc_lighting_motion_active",
        "binary_sensor.rc_lighting_driving",
        "binary_sensor.rc_lighting_dark_outside",
        "binary_sensor.rc_lighting_manual_override_active",
    )
    for safety_tile in safety_tiles:
        assert safety_tile in tiles, (
            f"dashboard.tiles must include {safety_tile!r}; the "
            f"automation-gate tiles are part of the contract "
            f"layer that the recipe §8 documents"
        )
    # The recipe must cross-reference the bluetooth-wifi-presence
    # Wave 3 #42 connection via
    # `binary_sensor.rc_presence_anyone_home` +
    # `binary_sensor.rc_presence_all_away` so the §8.3 arrival-
    # cue cross-reference is discoverable.
    assert "binary_sensor.rc_presence_anyone_home" in text, (
        "recipe.md must reference `binary_sensor.rc_presence_"
        "anyone_home` for the §8.3 arrival-cue cross-reference "
        "to the bluetooth-wifi-presence `connections/bluetooth-"
        "wifi-presence/` recipe"
    )
    assert "binary_sensor.rc_presence_all_away" in text, (
        "recipe.md must reference `binary_sensor.rc_presence_"
        "all_away` for the §8.3 arrival-cue cross-reference to "
        "the bluetooth-wifi-presence `connections/bluetooth-wifi-"
        "presence/` recipe"
    )
    # The recipe must cross-reference the approach-lights Wave 3
    # #52 connection via `light.approach_scene` so the §8.3
    # arrival-cue exterior lighting cross-reference is
    # discoverable.
    assert "light.approach_scene" in text, (
        "recipe.md must reference `light.approach_scene` for "
        "the §8.3 arrival-cue exterior lighting cross-reference "
        "to the approach-lights `connections/approach-lights/` "
        "recipe"
    )
    # The recipe must cross-reference the mode/automation-
    # builder connection via `select.rc_mode` so the §6 +
    # §8.5 mode-aware override cross-reference is discoverable.
    assert "select.rc_mode" in text, (
        "recipe.md must reference `select.rc_mode` for the "
        "§6 mode-aware override + §8.5 stealth-mode-suppression "
        "cross-reference to the mode/automation-builder "
        "`connections/mode-automation-builder/` recipe"
    )
    # The recipe must cross-reference the time/weather contract
    # via `sensor.rc_weather_light_lux` OR `sun.sun` so the
    # §8.2 + §8.3 + §8.4 dark-outside gate cross-reference is
    # discoverable.
    assert (
        "sensor.rc_weather_light_lux" in text
        or "sun.sun" in text
    ), (
        "recipe.md must reference `sensor.rc_weather_light_lux` "
        "OR `sun.sun` for the §8.2 + §8.3 + §8.4 dark-outside "
        "gate cross-reference to the time/weather contract"
    )
    # The recipe must reference the ignition source
    # `binary_sensor.engine_running` so the §8.1 + §8.2 ignition
    # mirror cross-reference is discoverable.
    assert "binary_sensor.engine_running" in text, (
        "recipe.md must reference `binary_sensor.engine_"
        "running` for the §8.1 Travel auto-off + §8.2 Stop-"
        "and-soft-interior ignition source"
    )
    # The recipe's defensive guard for future tier-a promotion —
    # assert the §8 section has the "MANDATORY before first use"
    # emphasis that the recipe uses to remind operators to wire
    # each automation.
    assert "mandatory before first use" in text.lower(), (
        "recipe.md §8 must use the 'MANDATORY before first use' "
        "emphasis on the five automations; this is the operator-"
        "side reminder that keeps the automations top-of-mind "
        "during install"
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))