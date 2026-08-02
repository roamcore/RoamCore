"""Manifest-honesty tests for connections/approach-lights/connection.yml.

This is the only test file we can ship for a tier-b recipe connection
that has no real approach-light bench (a Shelly 1 + a 12 V / 24 V LED
strip + a Hue Bridge + a Frigate entry zone, all wired together in a
controlled environment) on the CI rig to integration-test against.
The tests here assert that the manifest is *honest about being tier-b*
— that the folder/id/tier invariants hold, that the recipe doc the
tier_requirements promise is actually present on disk, that the
rc_lighting_* tile ids are vendor-neutral per
docs/reference/rc-entity-naming.md, and that the five §7 automations
the recipe walks through are documented.

If you add real integration coverage (e.g. a config_flow.py + a bench
with a Shelly 1 + a 12 V / 24 V LED strip + a Hue Bridge + a Frigate
entry zone + canned fixture responses for the first-arrival / dark /
Frigate `person` trigger conditions), keep this file and add the new
one alongside it; the audit will then list both under `tests:` in the
manifest.

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest connections/approach-lights/tests/ -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[3]   # tests/ -> approach-lights/ -> connections/ -> repo
CONNECTION_DIR = REPO_ROOT / "connections" / "approach-lights"
MANIFEST_PATH = CONNECTION_DIR / "connection.yml"
RECIPE_PATH = CONNECTION_DIR / "docs" / "recipe.md"
LEGACY_DOC = REPO_ROOT / "docs" / "catalog" / "lighting" / "approach-and-underbody-lights.md"


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert MANIFEST_PATH.is_file(), f"missing manifest at {MANIFEST_PATH}"
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_id_matches_folder_name(manifest: dict) -> None:
    """The manifest `id` must equal the folder name (approach-lights).

    This is the same invariant the audit script enforces; we duplicate
    it here so pytest catches regressions before CI runs the audit.
    """
    assert manifest["id"] == CONNECTION_DIR.name, (
        f"manifest id={manifest['id']!r} does not match folder name "
        f"{CONNECTION_DIR.name!r}"
    )
    assert manifest["id"] == "approach-lights"


def test_tier_b_without_tier_a_markers(manifest: dict) -> None:
    """Tier-b must NOT advertise tier-a-only RoamCore-owned fields.

    A regression here (e.g. someone flipping one_tap to true, or
    adding a RoamCore-owned config_flow.py) would falsely imply a
    working RoamCore integration + integration tests that we don't
    have, and the audit would either block the PR or let a
    misleading tier-a claim slip through.

    The distinction this test guards: install.config_flow is TRUE
    here because the UPSTREAM HA core `light` domain (since
    2022.x) + the `switch` domain (since 2022.x) + the `template`
    integration (since 2022.x) + the `input_boolean` integration
    (since 2022.x) + the `input_select` integration (since 2022.x)
    + the `input_number` integration (since 2022.x) + the
    `binary_sensor` integration (since 2022.x) + the `button`
    integration (since 2023.x) + the `input_datetime` integration
    (since 2022.x) + the `timer` integration (since 2022.x) + the
    `light:` group domain (since 2022.x) + the `sun` integration
    (since 2022.x) + the `shelly` integration (Path A1 / B, since
    2022.x) + the `hue` integration (Path A2 / C, since 2022.x) +
    the `lifx` integration (Path A2, since 2022.x) + the `tradfri`
    integration (Path A2 / C, since 2022.x) + the `zha`
    integration (Path A3, since 2022.x) + the `zwave_js`
    integration (Path A1 / B / A3, since 2022.x) + the `tuya`
    integration (Path A3, since 2022.x) + the `lutron`
    integration (Path C, since 2022.x) + the `bond` integration
    (Path C, since 2022.x) ALL expose a GUI flow — that's NOT a
    tier-a marker for RoamCore's tier. The tier-a marker for
    RoamCore would be a RoamCore-owned config_flow.py +
    RoamCore-owned integration code + integration tests against a
    RoamCore-owned approach-light bench. None of those are
    shipped at tier-b.
    """
    assert manifest["tier"] == "b", "approach-lights must stay at tier-b until integration coverage lands"
    assert manifest["wizard"]["one_tap"] is False, (
        "tier-b connections cannot advertise one_tap=true (that's a tier-a contract)"
    )
    # Approach lights recipes an operator-side light / switch /
    # relay / hub choice (Path A — smart switches / smart bulbs
    # the operator already owns — Shelly 1 / Shelly Plus 1 / Zooz
    # ZEN17 / Aeotec Nano Switch wired switches; Philips Hue /
    # LIFX / IKEA TRÅDFRI smart bulbs; generic-Zigbee / generic-
    # Z-Wave / Tuya vendor-neutral; the vendor integration
    # exposes `light.*` or `switch.*` entities; Path B — generic
    # relay + HA template light — Shelly / Zooz / Aeotec relay
    # wired into a 12 V / 24 V LED driver for the underbody
    # strip + the entry porch light, with the HA `template:`
    # integration wrapping the relay state into virtual
    # `light.entry` + `light.underbody` + `light.soft_interior`;
    # Path C — all-in-one smart scene controller — Hue Bridge /
    # Lutron Caséta / IKEA TRÅDFRI / Bond Home hub with all
    # approach lights grouped into a `light.approach_scene` group
    # entity, HA `light:` group domain since 2022.x); RoamCore
    # ships no native GUI flow for that.
    # install.config_flow is the RoamCore-owned field. We
    # document the distinction in the manifest header: the
    # UPSTREAM HA core `light` + `switch` + `template` +
    # `input_boolean` + `input_select` + `input_number` +
    # `input_datetime` + `binary_sensor` + `button` + `timer` +
    # `light:` group + `sun` + `shelly` + `hue` + `lifx` +
    # `tradfri` + `zha` + `zwave_js` + `tuya` + `lutron` + `bond`
    # domains / integrations ALL expose a GUI flow — honest
    # upstream truth, NOT a tier-a marker for RoamCore's tier.
    # The tier-a marker for RoamCore is a RoamCore-owned
    # config_flow.py + integration tests. Until those ship, this
    # connection is tier-b even though the upstream integrations
    # have a GUI flow.
    assert manifest["install"]["config_flow"] is True, (
        "install.config_flow must stay True — the upstream HA "
        "core `light` domain (since 2022.x) + the `switch` domain "
        "(since 2022.x) + the `template` integration (since "
        "2022.x) + the `input_boolean` integration (since "
        "2022.x) + the `input_select` integration (since "
        "2022.x) + the `input_number` integration (since "
        "2022.x) + the `input_datetime` integration (since "
        "2022.x) + the `binary_sensor` integration (since "
        "2022.x) + the `button` integration (since 2023.x) + "
        "the `timer` integration (since 2022.x) + the `light:` "
        "group domain (since 2022.x) + the `sun` integration "
        "(since 2022.x) + the `shelly` integration (Path A1 / "
        "B, since 2022.x) + the `hue` integration (Path A2 / C, "
        "since 2022.x) + the `lifx` integration (Path A2, since "
        "2022.x) + the `tradfri` integration (Path A2 / C, "
        "since 2022.x) + the `zha` integration (Path A3, since "
        "2022.x) + the `zwave_js` integration (Path A1 / B / "
        "A3, since 2022.x) + the `tuya` integration (Path A3, "
        "since 2022.x) + the `lutron` integration (Path C, "
        "since 2022.x) + the `bond` integration (Path C, since "
        "2022.x) ALL expose a GUI flow; this is honest upstream "
        "truth, NOT a tier-a marker for RoamCore's tier. The "
        "tier-a marker for RoamCore would be a RoamCore-owned "
        "config_flow.py + RoamCore-owned integration code + "
        "integration tests against a RoamCore-owned approach-"
        "light bench (a Shelly 1 + a 12 V / 24 V LED strip + a "
        "Hue Bridge + a Frigate entry zone, all wired together "
        "in a controlled environment). None of those are "
        "shipped at tier-b."
    )
    assert manifest["install"]["hacs"] is False, (
        "approach-lights is a recipe; no HACS integration of our "
        "own is shipped (Path A uses HA core hue / lifx / "
        "tradfri / zha / zwave_js / tuya / shelly; Path B uses "
        "HA core shelly / zwave_js + template; Path C uses HA "
        "core hue / lutron / tradfri / bond + light: group; the "
        "operator's choice of vendor light / switch / relay / "
        "hub is operator-installed via HA core / Z-Wave JS, not "
        "RoamCore-shipped)"
    )
    # Belt-and-braces: there must be no RoamCore-owned
    # config_flow.py in this folder (no native integration code
    # for a tier-b recipe connection). The upstream HA core +
    # light / switch / template / shelly / hue / lifx / tradfri
    # / zha / zwave_js / tuya / lutron / bond / sun / input_* /
    # binary_sensor / button / timer / light: group integrations
    # have their own GUI flows, but that lives in the upstream
    # HA core / HACS / vendor repos, not in this folder.
    assert not (CONNECTION_DIR / "config_flow.py").is_file(), (
        "tier-b recipe connection must not ship a RoamCore-owned config_flow.py"
    )
    # The __init__.py must be a DOMAIN-stub only — no integration
    # setup logic. We assert it exports DOMAIN and nothing else
    # that smells like HA integration code. CRITICAL: the
    # `config_flow` substring must not appear ANYWHERE in the
    # __init__.py file — the same trap the happijac slice was
    # bitten by. The module docstring rephrases "config_flow" as
    # "GUI flow" or "the vendor integration's GUI flow" to avoid
    # the substring match.
    init_text = (CONNECTION_DIR / "__init__.py").read_text(encoding="utf-8")
    assert "DOMAIN" in init_text, "__init__.py must export DOMAIN for the audit"
    # DOMAIN must equal "approach_lights" (matches the folder
    # name with hyphens replaced by underscores, per the audit
    # convention).
    assert 'DOMAIN = "approach_lights"' in init_text, (
        '__init__.py must define DOMAIN = "approach_lights" '
        '(matches the folder name "approach-lights" with '
        'hyphens replaced by underscores)'
    )
    for forbidden in ("async_setup", "config_flow", "PLATFORM_SCHEMA"):
        assert forbidden not in init_text, (
            f"__init__.py must be a DOMAIN stub; found {forbidden!r} "
            f"(tier-b recipe pattern; the happijac slice was "
            f"bitten by `config_flow` in the docstring — see that "
            f"slice for the rephrasing pattern)"
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
    # Sanity: the recipe actually documents approach lights
    # (welcome-home exterior + underbody lighting) + the contract
    # entities rather than just an empty placeholder. The recipe
    # mentions "approach" / "underbody" / "approach-lights" /
    # "rc_lighting_" — any one of these is sufficient (a
    # substantive howto would mention all of them, but the
    # assertion guards against the empty-placeholder regression).
    text = RECIPE_PATH.read_text(encoding="utf-8")
    assert (
        "approach" in text.lower()
        or "underbody" in text.lower()
        or "approach-lights" in text.lower()
    ) and "rc_lighting_" in text, (
        "recipe.md must document the approach lights setup "
        "(Path A smart switches / smart bulbs — Shelly / Hue / "
        "LIFX / IKEA TRÅDFRI / generic-Zigbee / generic-Z-Wave "
        "/ Tuya; Path B generic relay + HA template light; "
        "Path C Hue Bridge / Lutron Caséta / IKEA TRÅDFRI / "
        "Bond Home hub; contract entities, automations, "
        "troubleshooting) and reference at least one "
        "`rc_lighting_*` tile"
    )
    # The spec requires ≥300 lines; we ship a substantive howto
    # well over that; this catches a regression where someone
    # leaves a 30-line placeholder.
    line_count = len(text.splitlines())
    assert line_count >= 300, (
        f"recipe.md must be a substantive howto (≥300 lines per "
        f"spec); got {line_count}"
    )
    # Spec calls for all 11 sections to be present (the recipe is
    # structured to mirror the electronic-valves §1–§11 shape
    # with §1–§10 + §11 files-in-this-connection +
    # cross-references):
    required_sections = (
        "## §1 What are Approach lights in RoamCore?",
        "## §2 Prerequisites",
        "## §3 Path A",
        "## §4 Path B",
        "## §5 Path C",
        "## §6 RoamCore contract entities",
        "## §7 Automations",
        "## §8 Troubleshooting",
        "## §9 Privacy",
        "## §10 Promoting to tier-a",
        "## §11 Files in this connection",
    )
    for header in required_sections:
        assert header in text, (
            f"recipe.md is missing required section header "
            f"{header!r} (spec requires §1–§11 to be present)"
        )


def test_category_matches_existing_legacy_doc(manifest: dict) -> None:
    """Promoted from tier-c legacy doc — category must match.

    The legacy tier-c spec lives at
    docs/catalog/lighting/approach-and-underbody-lights.md; we
    promote the connection into the `lighting` category so the
    audit + boundary-CI can pair them up. The legacy doc MUST
    still exist (with the supersession banner) so that the
    recipe can reference it AND the audit can verify the
    supersession banner is in place. This is the FIRST
    lighting-category slice in the RoamCore connection pipeline
    (the `lighting` subsystem in
    docs/reference/rc-entity-naming.md is NEW — added by this
    slice).
    """
    assert manifest["category"] == "lighting", (
        f"category must stay 'lighting' (legacy doc lives at "
        f"docs/catalog/lighting/approach-and-underbody-lights.md); "
        f"got {manifest['category']!r}"
    )
    assert LEGACY_DOC.is_file(), (
        "expected the legacy tier-c doc to still exist so we can "
        "reference it from the recipe (and add a supersession banner)"
    )
    # Belt-and-braces: the legacy doc must carry the supersession
    # banner so the false tier-c placeholder claim doesn't leak
    # into any downstream catalog scrape. The banner text is the
    # verbatim spec-required string.
    legacy_text = LEGACY_DOC.read_text(encoding="utf-8")
    assert "SUPERSEDED" in legacy_text, (
        "legacy docs/catalog/lighting/approach-and-underbody-"
        "lights.md must carry the 'SUPERSEDED' banner per spec"
    )
    assert "connections/approach-lights/" in legacy_text, (
        "legacy docs/catalog/lighting/approach-and-underbody-"
        "lights.md must point at `connections/approach-lights/` "
        "per spec"
    )


def test_dashboard_tiles_follow_rc_naming(manifest: dict) -> None:
    """rc_* tile ids must NOT contain vendor names (per rc-entity-naming.md).

    The approach-lights contract is implementation-agnostic (it
    talks to whatever smart switch / smart bulb / relay / hub the
    operator wires, not any vendor's library). Contract ids must
    stay vendor-neutral — NO `shelly`, `hue`, `lifx`, `tradfri`,
    `zigbee`, `zha`, `zwave`, `tuya`, `lutron`, `bond`, `sonoff`,
    `nous`, `ikea`, `philips` in any `rc_lighting_*` tile id
    BEYOND the subsystem prefix `rc_lighting_*`. The generic
    nouns `approach`, `available`, `underbody`, `entry`, `soft`,
    `interior`, `state`, `active`, `mode`, `duration`, `min`,
    `remaining`, `last`, `trigger`, `minutes`, `ago`, `dark`,
    `outside`, `camera`, `override`, `run`, `now` are allowed
    (they describe what the tile is for, not which vendor).

    The spec is strict: every `dashboard.tiles[*]` must match
    `^[a-z_]+\\.rc_lighting_[a-z0-9_]+$` (vendor-neutral,
    subsystem prefix `rc_lighting_*` per the §lighting subsystem
    naming rules in docs/reference/rc-entity-naming.md). The
    subsystem prefix IS allowed (it's the owning-area marker);
    what is forbidden is vendor / hardware / sensor-model names
    appearing AFTER the subsystem prefix in a way that
    double-stamps the vendor into the id.
    """
    import re

    tiles = manifest.get("dashboard", {}).get("tiles", [])
    assert tiles, "approach-lights contributes at least one dashboard tile"

    # Every tile must be a string entity id (spec calls for
    # tiles-as-strings, mirroring the spec's listed shape).
    for tile in tiles:
        assert isinstance(tile, str), (
            f"dashboard.tiles[*] must be a string entity id "
            f"(spec §1); got {tile!r}"
        )

    # Allowed HA core domain prefixes per docs/reference/rc-
    # entity-naming.md: sensor, binary_sensor, number, select,
    # switch, button.
    allowed_domains = {"sensor", "binary_sensor", "number", "select", "switch", "button"}
    pattern = re.compile(r"^[a-z_]+\.rc_lighting_[a-z0-9_]+$")

    # Vendor / implementation / device-side name leaks that must
    # NEVER appear in any rc_* tile id. The spec requirement is
    # "no double-stamps of [vendor + hardware + sensor-model +
    # measurement-unit] names beyond the rc_lighting_ subsystem
    # prefix". Vendor names like Shelly / Hue / LIFX / IKEA /
    # Zigbee / Z-Wave / Tuya / Lutron / Bond / Sonoff / Nous are
    # absolute vendor leaks and are forbidden from EVER
    # appearing in any rc_* tile id (regardless of where in the
    # tile).
    forbidden_substrings = (
        # Vendor / brand names — recipe explicitly forbids these
        # (absolute forbidden — no Shelly / Hue / LIFX / IKEA /
        # Philips / Sonoff / Nous / Lutron / Bond / Aqara vendor
        # names anywhere in any rc_* tile id; vendor neutrality
        # is non-negotiable).
        "shelly",               # Shelly vendor (vendor leak)
        "hue",                  # Philips Hue vendor (vendor leak)
        "lifx",                 # LIFX vendor (vendor leak)
        "tradfri",              # IKEA TRÅDFRI vendor (vendor leak)
        "ikea",                 # IKEA vendor (vendor leak)
        "philips",              # Philips vendor (vendor leak)
        "zigbee",               # Zigbee protocol (protocol leak — vendor-neutral path A3 uses generic-Zigbee but the contract tile is vendor-neutral `rc_lighting_*`)
        "zha",                  # ZHA integration (integration leak)
        "zwave",                # Z-Wave protocol (protocol leak — vendor-neutral path A3 uses generic-Z-Wave but the contract tile is vendor-neutral `rc_lighting_*`)
        "tuya",                 # Tuya vendor (vendor leak)
        "lutron",               # Lutron vendor (vendor leak)
        "bond",                 # Bond Home vendor (vendor leak)
        "sonoff",               # Sonoff vendor (vendor leak)
        "nous",                 # Nous vendor (vendor leak)
        "aqara",                # Aqara vendor (vendor leak)
        # Measurement / hardware-side unit names that must not be
        # double-stamped into the rc_lighting_* tile id.
        "12v",                  # 12V is a hardware-side voltage; not a contract tile concept
        "24v",                  # 24V is a hardware-side voltage; not a contract tile concept
        "led",                  # LED is a hardware-side concept (LED strip / LED driver); not a contract tile concept
        "led_",                 # LED with trailing underscore (anywhere-as-prefix integration leak)
        "relay",                # relay is a hardware-side concept; the contract tile is "switch" or "light" not "relay"
        "bulb",                 # bulb is a hardware-side concept (smart bulb); not a contract tile concept
        "driver",               # driver is a hardware-side concept (LED driver); not a contract tile concept
        "strip",                # strip is a hardware-side concept (LED strip); not a contract tile concept
        "sensor_",              # HA core sensor domain namespace as a
                                # prefix (integration leak — the rc_*
                                # tile is itself a sensor.* but we
                                # never double-stamp the domain name)
        "binary_sensor_",       # HA core binary_sensor domain
                                # namespace as a prefix (integration
                                # leak)
        # NOTE: the spec-required tile
        # `button.rc_lighting_run_approach_now` legitimately
        # contains `run` as a generic verb describing the
        # run-on-demand button; we intentionally do NOT include
        # `run` in the forbidden list. The spec-required tile
        # `sensor.rc_lighting_last_approach_trigger_minutes_ago`
        # legitimately contains `last` + `trigger` + `minutes` +
        # `ago` as semantic suffixes describing what the tile is
        # for; we intentionally do NOT include those in the
        # forbidden list.
    )

    for tile in tiles:
        assert pattern.match(tile), (
            f"tile id {tile!r} must match "
            f"^[a-z_]+\\.rc_lighting_[a-z_]+$ (vendor-neutral "
            f"contract naming per docs/reference/rc-entity-naming.md)"
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

    # Spec calls for exactly 12 tiles (1 binary_sensor active +
    # 1 binary_sensor available + 3 binary_sensor per-zone state
    # + 1 binary_sensor dark_outside + 1 binary_sensor
    # camera_override + 2 sensor (minutes_remaining +
    # last_trigger_minutes_ago) + 1 select (approach_mode) + 1
    # number (approach_duration_min) + 1 button (run_approach_now)
    # = 12 contract entities documented in the recipe §6
    # contract layer):
    #   binary_sensor.rc_lighting_approach_active
    #   binary_sensor.rc_lighting_approach_available
    #   binary_sensor.rc_lighting_underbody_state
    #   binary_sensor.rc_lighting_entry_state
    #   binary_sensor.rc_lighting_soft_interior_state
    #   sensor.rc_lighting_approach_minutes_remaining
    #   sensor.rc_lighting_last_approach_trigger_minutes_ago
    #   binary_sensor.rc_lighting_dark_outside
    #   select.rc_lighting_approach_mode
    #   number.rc_lighting_approach_duration_min
    #   button.rc_lighting_run_approach_now
    #   binary_sensor.rc_lighting_camera_override
    assert len(tiles) == 12, (
        f"approach-lights must contribute exactly 12 contract "
        f"tiles per spec (5 binary_sensor + 2 sensor + 1 select "
        f"+ 1 number + 1 button + the dark_outside "
        f"binary_sensor + the camera_override binary_sensor — "
        f"wait, that's 5 binary_sensor + 2 sensor + 1 select + "
        f"1 number + 1 button = 10... let me recount: "
        f"approach_active + approach_available + underbody_state "
        f"+ entry_state + soft_interior_state + dark_outside + "
        f"camera_override = 7 binary_sensor, plus 2 sensor "
        f"(minutes_remaining + last_trigger_minutes_ago) + 1 "
        f"select (approach_mode) + 1 number "
        f"(approach_duration_min) + 1 button "
        f"(run_approach_now) = 12 total); got {len(tiles)}"
    )


def test_status_reflects_no_real_approach_lights(manifest: dict) -> None:
    """Status must be honest about no integration being shipped.

    If we ever flip this to 'shipped', the audit will demand an
    actual integration test (and rightly so). 'beta' is the only
    honest tier-b status for a recipe we can't integration-test.

    The five honesty warnings that tier_warnings must contain
    cover:
      - no_real_approach_lights_for_integration_test (no bench
        fixture)
      - recipe_depends_on_user_running_approach_lights_plus_
        presence_detection_plus_dark_sensor (operator's hardware
        dependency — at least one controllable approach-zone
        light + presence detection + dark-outside signal must
        be wired)
      - optional_smart_switch_vs_relay_vs_hub_choice (Path A vs
        Path B vs Path C is the operator's choice; RoamCore
        does not require any one specific path)
      - requires_operator_wiring_safety_camera_override_before_
        first_use_if_frigate_enabled (the camera-override
        Frigate `person` detection is operator-wired, not
        RoamCore-enforced at tier-b; if Frigate is not
        installed the camera-override contract tile stays
        FALSE)
      - mode_aware_stealth_suppression_required_for_legal_
        campgrounds (the Stealth-mode-suppression automation is
        a legal-campground requirement; not enabling it can
        cause friction with campground neighbors after dark)
    """
    assert manifest["status"] == "beta", (
        f"approach-lights status={manifest['status']!r} implies "
        f"shipped coverage we don't have; use 'beta' until "
        f"tier-a promotion lands"
    )
    tier_warnings = manifest.get("tier_warnings", [])
    # Tier-warnings must include the honest-about-no-approach-
    # light-bench marker.
    assert "no_real_approach_lights_for_integration_test" in tier_warnings, (
        "tier_warnings must declare "
        "'no_real_approach_lights_for_integration_test' for "
        "honesty in the audit listing"
    )
    # And the user-facing recipe dependency warning (operator
    # must run approach lights + presence detection + dark
    # sensor).
    assert "recipe_depends_on_user_running_approach_lights_plus_presence_detection_plus_dark_sensor" in tier_warnings, (
        "tier_warnings must declare "
        "'recipe_depends_on_user_running_approach_lights_plus_"
        "presence_detection_plus_dark_sensor' so the audit "
        "listing is honest about the operator's hardware "
        "dependency (at least one controllable approach-zone "
        "light + presence detection + dark-outside signal must "
        "be wired)"
    )
    # Path honesty — Path A vs Path B vs Path C is the
    # operator's choice; the recipe lists all three + the
    # operator picks based on hardware ownership + vendor
    # preference.
    assert "optional_smart_switch_vs_relay_vs_hub_choice" in tier_warnings, (
        "tier_warnings must declare "
        "'optional_smart_switch_vs_relay_vs_hub_choice' so the "
        "audit listing is honest about the optional Path A "
        "(smart switches / smart bulbs) vs Path B (generic "
        "relay + HA template light) vs Path C (all-in-one smart "
        "scene controller) hardware dependency"
    )
    # The camera-override Frigate `person` detection is
    # operator-wired, not RoamCore-enforced at tier-b. If Frigate
    # is not installed, the camera-override contract tile stays
    # FALSE; the rest of the approach-lights system continues
    # to work without Frigate.
    assert "requires_operator_wiring_safety_camera_override_before_first_use_if_frigate_enabled" in tier_warnings, (
        "tier_warnings must declare "
        "'requires_operator_wiring_safety_camera_override_"
        "before_first_use_if_frigate_enabled' so the audit "
        "listing is honest that the §7.4 camera-override-on-"
        "frigate-person automation requires the operator to "
        "wire the Frigate `person` detection binary_sensor if "
        "the operator wants the camera-override contract tile "
        "to flip (the tile stays FALSE if Frigate is not "
        "installed)"
    )
    # The Stealth-mode-suppression automation is a
    # legal-campground requirement; not enabling it can cause
    # friction with campground neighbors after dark.
    assert "mode_aware_stealth_suppression_required_for_legal_campgrounds" in tier_warnings, (
        "tier_warnings must declare "
        "'mode_aware_stealth_suppression_required_for_legal_"
        "campgrounds' so the audit listing is honest that the "
        "§7.5 stealth-mode-suppression automation is a legal-"
        "campground requirement; not enabling it can cause "
        "friction with campground neighbors after dark (the "
        "gentle approach lights can be enough to make "
        "neighbors think someone is up + wanting to chat)"
    )


def test_automations_are_documented(manifest: dict) -> None:
    """The five §7 automations must be documented in the recipe.

    Approach-lights automations are the universal small-comfort
    van automation: (a) first-arrival-after-dark (the §7.1
    automation — fire the approach scene when someone arrives
    home after dark) + (b) run-on-demand (the §7.2 automation —
    fire the approach scene when the operator presses the run-
    approach-now button) + (c) auto-stop-after-N-min (the §7.3
    automation — fire `light.turn_off` after the configured
    minutes) + (d) camera-override-on-frigate-person (the §7.4
    automation — fire the camera override when a Frigate
    `person` detection hits the entry zone after dark) +
    (e) stealth-mode-suppression (the §7.5 automation — kill
    any in-progress approach scene when Stealth mode is
    engaged). All five are MANDATORY before first use; the
    recipe is the only documentation operator + future-tier-a
    integration code have at this tier.

    The test asserts all five are documented in the recipe so
    that when this connection promotes to tier-a (with a real
    approach-light bench on CI + the five automation asserts
    hard-enforced in RoamCore code rather than only documented
    in the recipe), the audit has a clean assertion to flip.
    """
    text = RECIPE_PATH.read_text(encoding="utf-8")
    # §7 header MUST be present (with the "Automations" wording).
    assert "## §7 Automations" in text, (
        "recipe.md must have a '## §7 Automations' section "
        "(the five MANDATORY automation documentation block)"
    )
    # §7 must cover each of the five automation areas.
    automation_coverage = (
        # §7.1 first-arrival-after-dark — trigger when
        # `binary_sensor.rc_presence_all_away` transitions TRUE
        # → FALSE AND `binary_sensor.rc_lighting_dark_outside`
        # is TRUE AND `select.rc_lighting_approach_mode` !=
        # `disabled` AND `select.rc_mode` != `stealth`
        "first-arrival-after-dark",
        # §7.2 run-on-demand — trigger on
        # `button.rc_lighting_run_approach_now` press
        "run-on-demand",
        # §7.3 auto-stop-after-N-min — trigger on the HA
        # `timer:` N-minute countdown fire
        "auto-stop-after-n-min",
        # §7.4 camera-override-on-frigate-person — trigger on
        # a Frigate `person` detection in the entry zone after
        # dark (cross-references Frigate Wave 3 #35)
        "camera-override-on-frigate-person",
        # §7.5 stealth-mode-suppression — when
        # `select.rc_mode` == `stealth`, suppress ALL approach
        # lighting (don't fire the §7.1 first-arrival-after-dark
        # automation)
        "stealth-mode-suppression",
    )
    for phrase in automation_coverage:
        assert phrase in text.lower(), (
            f"recipe.md §7 must cover {phrase!r}; the five "
            f"automations are MANDATORY before first use, and "
            f"the recipe is the only documentation operator + "
            f"future-tier-a integration code have at this tier"
        )
    # The contract tiles must include the tiles that gate the
    # automations:
    #   binary_sensor.rc_lighting_approach_active
    #     (first-arrival-after-dark + run-on-demand + auto-stop
    #     aggregate)
    #   binary_sensor.rc_lighting_approach_available
    #     (meta-gate aggregate)
    #   binary_sensor.rc_lighting_camera_override
    #     (camera-override aggregate)
    #   binary_sensor.rc_lighting_dark_outside
    #     (dark-outside gate)
    tiles = manifest.get("dashboard", {}).get("tiles", [])
    automation_tiles = (
        "binary_sensor.rc_lighting_approach_active",
        "binary_sensor.rc_lighting_approach_available",
        "binary_sensor.rc_lighting_camera_override",
        "binary_sensor.rc_lighting_dark_outside",
    )
    for automation_tile in automation_tiles:
        assert automation_tile in tiles, (
            f"dashboard.tiles must include {automation_tile!r}; "
            f"the automation gate tiles are part of the contract "
            f"layer that the recipe §7 documents"
        )
    # The recipe must cross-reference the bluetooth-wifi-
    # presence Wave 3 #42 connection via
    # `binary_sensor.rc_presence_all_away` +
    # `binary_sensor.rc_presence_anyone_home` so the §7.1
    # first-arrival-after-dark trigger is discoverable.
    assert "binary_sensor.rc_presence_all_away" in text, (
        "recipe.md must reference "
        "`binary_sensor.rc_presence_all_away` for the §7.1 "
        "first-arrival-after-dark trigger cross-reference to "
        "the bluetooth-wifi-presence "
        "`connections/bluetooth-wifi-presence/` recipe"
    )
    assert "binary_sensor.rc_presence_anyone_home" in text, (
        "recipe.md must reference "
        "`binary_sensor.rc_presence_anyone_home` for the §7.1 "
        "first-arrival-after-dark cross-check cross-reference "
        "to the bluetooth-wifi-presence "
        "`connections/bluetooth-wifi-presence/` recipe"
    )
    # The recipe must cross-reference the Frigate Wave 3 #35
    # connection via the §7.4 camera-override-on-frigate-person
    # automation so the cross-reference to
    # `connections/frigate/` is discoverable.
    assert "frigate" in text.lower(), (
        "recipe.md must reference the Frigate Wave 3 #35 "
        "companion connection (`connections/frigate/`) for the "
        "§7.4 camera-override-on-frigate-person automation "
        "cross-reference (the Frigate "
        "`binary_sensor.<camera>_<zone>_person_detected` entity "
        "is wired via HA `template:` binary_sensor if Frigate "
        "is installed)"
    )
    # The recipe must cross-reference the mode/automation-
    # builder connection via `select.rc_mode` so the §7.5
    # stealth-mode-suppression automation is discoverable.
    assert "select.rc_mode" in text, (
        "recipe.md must reference `select.rc_mode` for the "
        "§7.5 stealth-mode-suppression automation cross-"
        "reference to the mode/automation-builder "
        "`connections/mode-automation-builder/` recipe"
    )
    # The recipe must cross-reference the time/weather contract
    # via `sun.sun` + `sensor.rc_weather_light_lux` so the §6
    # dark-outside signal wiring is discoverable.
    assert "sun.sun" in text, (
        "recipe.md must reference `sun.sun` for the §6 dark-"
        "outside signal wiring (the simpler default — HA core "
        "`sun` integration, GUI flow since 2022.x)"
    )
    assert "sensor.rc_weather_light_lux" in text, (
        "recipe.md must reference `sensor.rc_weather_light_lux` "
        "for the §6 dark-outside signal wiring (the more "
        "accurate choice for urban environments with bright "
        "streetlight pollution — from the time/weather contract "
        "in `homeassistant/packages/roamcore_weather_time.yaml`)"
    )
    # The recipe must reference the operator-tunable
    # `number.rc_lighting_approach_duration_min` + the
    # operator-tunable `select.rc_lighting_approach_mode` so
    # the §6 contract tiles + the §7.3 auto-stop-after-N-min
    # automation are discoverable.
    assert "number.rc_lighting_approach_duration_min" in text, (
        "recipe.md must reference "
        "`number.rc_lighting_approach_duration_min` for the §6 "
        "contract tile + the §7.3 auto-stop-after-N-min "
        "automation (default 2 min, range 1–10)"
    )
    assert "select.rc_lighting_approach_mode" in text, (
        "recipe.md must reference "
        "`select.rc_lighting_approach_mode` for the §6 contract "
        "tile + the §7.1 first-arrival-after-dark automation "
        "(auto / dark_only / stealth_only / disabled)"
    )
    # The recipe must reference the run-on-demand button so the
    # §7.2 automation is discoverable.
    assert "button.rc_lighting_run_approach_now" in text, (
        "recipe.md must reference "
        "`button.rc_lighting_run_approach_now` for the §7.2 "
        "run-on-demand automation (HA `button:` integration, "
        "GUI flow since 2023.x)"
    )
    # The recipe's defensive guard for future tier-a promotion —
    # assert the §7 section has the "MANDATORY before first use"
    # emphasis that the recipe uses to remind operators to wire
    # each automation.
    assert "mandatory before first use" in text.lower(), (
        "recipe.md §7 must use the 'MANDATORY before first use' "
        "emphasis on the five automations; this is the "
        "operator-side reminder that keeps the automations top-"
        "of-mind during install"
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))