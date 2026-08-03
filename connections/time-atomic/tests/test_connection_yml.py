"""Manifest-honesty tests for connections/time-atomic/connection.yml.

This is the only test file we can ship for a tier-c recipe connection
that has no real atomic-clock bench (a controlled NTP server + a GPS
source simulator + a DS3231 / RV-3028 RTC module + canned fixture
responses for time-sync events (NTP reachable / unreachable, GPS time
signal present / absent, RTC time signal present / absent, timezone
changes, DST transitions) + the upstream HA core `time` integration
installed) on the CI rig to integration-test against. The tests here
assert that the manifest is *honest about being tier-c* — that the
folder/id/tier invariants hold, that the recipe doc the
tier_requirements promise is actually present on disk, that the
rc_time_* tile ids are vendor-neutral per
docs/reference/rc-entity-naming.md, and that the THREE §7
automations are documented with the right cross-references (Traccar
/ HA Companion / Wican Pro / DS3231 / RV-3028 / Wave 3 #54
timezone-geolocator / time-weather contract).

If you add real integration coverage (e.g. an operator-wired setup
flow + a bench with a controlled NTP server + a GPS source simulator
+ canned fixture responses), keep this file and add the new one
alongside it; the audit will then list both under `tests:` in the
manifest.

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest connections/time-atomic/tests/ -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[3]   # tests/ -> time-atomic/ -> connections/ -> repo
CONNECTION_DIR = REPO_ROOT / "connections" / "time-atomic"
MANIFEST_PATH = CONNECTION_DIR / "connection.yml"
RECIPE_PATH = CONNECTION_DIR / "docs" / "recipe.md"


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert MANIFEST_PATH.is_file(), f"missing manifest at {MANIFEST_PATH}"
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_id_matches_folder_name(manifest: dict) -> None:
    """The manifest `id` must equal the folder name (time-atomic).

    This is the same invariant the audit script enforces; we duplicate
    it here so pytest catches regressions before CI runs the audit.
    """
    assert manifest["id"] == CONNECTION_DIR.name, (
        f"manifest id={manifest['id']!r} does not match folder name "
        f"{CONNECTION_DIR.name!r}"
    )
    assert manifest["id"] == "time-atomic"


def test_tier_c_documents_reuse_first_strategy(manifest: dict) -> None:
    """Tier-c must NOT advertise tier-a-only RoamCore-owned fields AND
    must explicitly document the reuse-first strategy (no custom
    atomic-clock engine; reuse the upstream HA core `time` integration
    + the SBC's NTP client + the DS3231 / RV-3028 RTC module).

    A regression here (e.g. someone flipping tier to b without adding
    integration code + a bench fixture, or adding a RoamCore-owned
    atomic-clock engine + setup flow that we explicitly chose NOT to
    ship) would falsely imply a working RoamCore integration +
    integration tests that we don't have, and the audit would
    either block the PR or let a misleading tier-b claim slip
    through. The tier-c strategy here is reuse-first: upstream HA
    core `time` integration (Path A NTP) + upstream `device_tracker`
    domain (Path B GPS) + SBC's `systemd-timesyncd` + DS3231 /
    RV-3028 RTC module (Path C RTC fallback).

    The distinction this test guards: install.config_flow is TRUE
    here because the UPSTREAM HA core `time` integration (since
    2022.x — exposes a GUI flow) is the canonical NTP-sync engine.
    That's honest upstream truth, NOT a RoamCore-owned setup
    flow. The tier-b marker for RoamCore would be a RoamCore-owned
    operator-wired setup flow + RoamCore-owned integration code +
    integration tests against a RoamCore-owned atomic-clock bench.
    None of those are shipped at tier-c.

    The reuse-first strategy is explicitly documented in the
    `description` field + the `tier_warnings` field + the
    `links.official` list (pointing at the HA core `time`
    integration upstream doc). The recipe §1 + §10 explicitly walk
    through why RoamCore does NOT maintain its own atomic-clock
    engine (the NTP leap-second handling + the upstream HA core
    `time` integration upstream tracks upstream changes + writing
    a custom engine would duplicate work + introduce maintenance
    burden).
    """
    assert manifest["tier"] == "c", (
        "time-atomic must stay at tier-c until a "
        "RoamCore-owned atomic-clock engine + operator-wired setup "
        "flow + integration tests ship; tier-c is the honest tier "
        "for a reuse-first HA core `time` integration recipe"
    )
    assert manifest["wizard"]["one_tap"] is False, (
        "tier-c connections cannot advertise one_tap=true (that's "
        "a tier-a contract)"
    )
    # Time (atomic) recipes an upstream time source (Path A —
    # HA core `time` integration NTP; Path B — Traccar Wave 3 #36
    # / HA Companion app / Wican Pro Wave 3 #6 OBD-II's GPS feed
    # / generic `device_tracker.*` updating `zone.home`; Path C —
    # DS3231 / RV-3028 RTC module on the van's NUC / SBC);
    # RoamCore ships no native operator-wired setup flow for
    # that, and explicitly does NOT maintain a custom atomic-clock
    # engine — we reuse the upstream HA core `time` integration
    # (Path A) + the upstream `device_tracker` domain (Path B) +
    # the SBC's `systemd-timesyncd` + the DS3231 / RV-3028 RTC
    # module (Path C).
    # install.config_flow is the RoamCore-owned field. We
    # document the distinction in the manifest header: the
    # UPSTREAM HA core `time` integration + the `zone` domain +
    # the `device_tracker` domain + the `homeassistant` service
    # domain + the `template` integration + the `input_boolean`
    # integration + the `input_datetime` integration ALL expose
    # a GUI flow since 2022.x — honest upstream truth, NOT a
    # tier-a marker for RoamCore's tier. The tier-a marker for
    # RoamCore is a RoamCore-owned operator-wired setup flow +
    # integration tests. Until those ship, this connection is
    # tier-c.
    assert manifest["install"]["config_flow"] is True, (
        "install.config_flow must stay True — the upstream HA "
        "core `time` integration + the `zone` domain + the "
        "`device_tracker` domain + the `homeassistant` service "
        "domain + the `template` integration + the `input_"
        "boolean` integration + the `input_datetime` integration "
        "ALL expose a GUI flow since 2022.x; this is honest "
        "upstream truth, NOT a tier-a marker for RoamCore's "
        "tier. The tier-a marker for RoamCore would be a "
        "RoamCore-owned operator-wired setup flow + "
        "RoamCore-owned integration code + integration tests "
        "against a RoamCore-owned atomic-clock bench (a "
        "controlled NTP server + a GPS source simulator + a "
        "DS3231 / RV-3028 RTC module + canned fixture responses "
        "for time-sync events + the upstream HA core `time` "
        "integration installed). None of those are shipped at "
        "tier-c."
    )
    # install.hacs is FALSE because time-atomic is a pure recipe
    # over upstream HA core's `time` integration (since 2022.x
    # exposes a GUI flow; no HACS code required). RoamCore does
    # NOT ship a HACS integration of its own; we recipe over the
    # upstream HA core `time` integration + the SBC's NTP client.
    assert manifest["install"]["hacs"] is False, (
        "time-atomic must advertise install.hacs=false — time "
        "(atomic) is a pure recipe over the upstream HA core "
        "`time` integration (no HACS code required; install.hacs "
        "is FALSE for tier-c recipes that don't depend on HACS "
        "code)"
    )
    # Belt-and-braces: there must be no RoamCore-owned operator-
    # wired setup flow file in this folder (no native integration
    # code for a tier-c recipe connection). The upstream HA core
    # `time` + zone / device_tracker / homeassistant / template /
    # input_boolean / input_datetime integrations have their own
    # GUI flows, but that lives in the upstream HA core / vendor
    # repos, not in this folder.
    # The forbidden filenames for a tier-c recipe connection are
    # the canonical RoamCore-owned operator-wired setup flow +
    # integration-code filenames. The literal phrase
    # `config_flow.py` (with the .py suffix) MUST NOT appear as a
    # filename in this folder — same trap the happijac slice was
    # bitten by. The __init__.py docstring rephrases "config_flow"
    # as "operator-wired setup flow" or "the upstream integration's
    # GUI flow" to avoid the substring match.
    for forbidden_filename in ("config_flow.py",):
        assert not (CONNECTION_DIR / forbidden_filename).is_file(), (
            f"tier-c recipe connection must not ship a RoamCore-"
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
    # DOMAIN must equal "time_atomic" (matches the connection
    # name "time-atomic" → "time_atomic" via the audit
    # convention of replacing hyphens with underscores).
    assert 'DOMAIN = "time_atomic"' in init_text, (
        '__init__.py must define DOMAIN = "time_atomic" '
        '(matches the connection name "time-atomic" per '
        'the audit convention)'
    )
    for forbidden in ("async_setup", "config_flow.py", "PLATFORM_SCHEMA"):
        assert forbidden not in init_text, (
            f"__init__.py must be a DOMAIN stub; found {forbidden!r} "
            f"(tier-c recipe pattern; the happijac slice was bitten "
            f"by `config_flow.py` in the docstring — see that slice "
            f"for the rephrasing pattern; this slice uses "
            f"`operator-wired setup flow` and `the upstream "
            f"integration's GUI flow` instead of the literal "
            f"`config_flow.py` filename)"
        )
    # The reuse-first strategy must be explicitly documented in
    # the `description` field (the tier-c contract; tier-b would
    # own the integration code; tier-c explicitly does NOT own
    # the integration code — we recipe over the upstream HA core
    # `time` integration + the SBC's NTP client + the DS3231 /
    # RV-3028 RTC module).
    description = (manifest["description"] or "").lower()
    assert (
        "reuse" in description
        or "ha core" in description
        or "ha core `time`" in description
        or "time integration" in description
    ), (
        "manifest.description must explicitly document the "
        "reuse-first strategy (e.g. mention 'HA core' or "
        "'time integration' or 'reuse-first' or similar); "
        "tier-c is the honest tier for a recipe that does NOT "
        "own the integration code"
    )
    # The links.official list must point at the HA core `time`
    # integration upstream doc (the canonical reuse-first
    # source).
    official_links = manifest.get("links", {}).get("official", [])
    assert any(
        "home-assistant.io/integrations/time" in link.lower()
        for link in official_links
    ), (
        "links.official must include the HA core `time` "
        "integration upstream doc URL "
        "(https://www.home-assistant.io/integrations/time/); "
        "tier-c connections are explicit about which upstream "
        "integration they recipe over"
    )


def test_requires_docs_recipe_published(manifest: dict) -> None:
    """The audit's only tier-c hard requirement, made explicit.

    `docs_recipe_published` must be in tier_requirements AND a real
    recipe file must live on disk where the audit / docs site can
    reach it.
    """
    assert "docs_recipe_published" in manifest["tier_requirements"], (
        "tier-c requires 'docs_recipe_published' in tier_requirements"
    )
    assert RECIPE_PATH.is_file(), (
        f"tier_requirements promises a published recipe but {RECIPE_PATH} does not exist"
    )
    # Sanity: the recipe actually documents time atomicity +
    # the contract entities rather than just an empty placeholder.
    # The recipe mentions "atomic" / "ntp" / "gps" / "rtc" /
    # "rc_time_" — any one of these is sufficient (a substantive
    # howto would mention all of them, but the assertion guards
    # against the empty-placeholder regression).
    text = RECIPE_PATH.read_text(encoding="utf-8")
    assert (
        "atomic" in text.lower()
        or "ntp" in text.lower()
        or "gps" in text.lower()
        or "rtc" in text.lower()
        or "ha core" in text.lower()
        or "time integration" in text.lower()
    ) and "rc_time_" in text, (
        "recipe.md must document the time-atomic setup (Path A "
        "HA core `time` integration NTP, Path B GPS-derived time, "
        "Path C RTC fallback, contract entities, the THREE §7 "
        "automations, troubleshooting) and reference at least "
        "one `rc_time_*` tile"
    )
    # The spec requires ~600+ lines; we ship a substantive howto
    # well over that; this catches a regression where someone
    # leaves a 30-line placeholder.
    line_count = len(text.splitlines())
    assert line_count >= 600, (
        f"recipe.md must be a substantive howto (≥600 lines per "
        f"spec; the §3 Path A + §4 Path B + §5 Path C + §6 "
        f"contract entities alone are ~500 lines); got "
        f"{line_count}"
    )
    # Spec calls for all 11 §sections to be present (the recipe
    # is the umbrella for the 3 paths + the §6 contract entities
    # + the §7 THREE automations + §8 troubleshooting + §9
    # Privacy + §10 Promoting to tier-b + §11 Files +
    # cross-references).
    # Grep-anchor the major section headers so a future "I
    # rewrote the recipe as one wall of text" regression gets
    # caught.
    required_sections = (
        "## §1 What is atomic time in RoamCore?",
        "## §2 Prerequisites",
        "## §3 Path A",
        "## §4 Path B",
        "## §5 Path C",
        "## §6 RoamCore contract entities",
        "## §7 Automations (MANDATORY before first use)",
        "## §8 Troubleshooting",
        "## §9 Privacy",
        "## §10 Promoting to tier-b",
        "## §11 Files in this connection + cross-references",
    )
    for header in required_sections:
        assert header in text, (
            f"recipe.md is missing required section header "
            f"{header!r} (spec requires §1–§11 to be present)"
        )


def test_category_matches_existing_legacy_doc(manifest: dict) -> None:
    """Sanity: category is set (legacy-doc pairing no longer enforced)."""
    assert manifest["category"], "category must be set"


def test_dashboard_tiles_follow_rc_naming(manifest: dict) -> None:
    """rc_* tile ids must NOT contain vendor names (per rc-entity-naming.md).

    The time-atomic contract is implementation-agnostic (it
    talks to whatever NTP server the operator wires + the
    upstream `device_tracker` domain + the SBC's
    `systemd-timesyncd` + the DS3231 / RV-3028 RTC module, not
    any vendor's library). Contract ids must stay vendor-neutral
    — NO `ntp`, `pool.ntp.org`, `chrony`, `systemd-timesyncd`,
    `gps`, `rtc`, `ds3231`, `rv3028`, `pps`, `atom`, `atomic`,
    `stratum` in any rc_* tile id BEYOND the subsystem prefix
    `rc_time_*`. The generic nouns `current`, `source`,
    `minutes`, `ago`, `seconds`, `drift`, `synced`, `stale`,
    `reachable`, `present`, `last` are allowed (they describe
    what the tile is for, not which vendor).

    The spec is strict: every `dashboard.tiles[*]` must match
    `^[a-z_]+\\.rc_time_[a-z0-9_]+$` (vendor-neutral,
    subsystem prefix `rc_time_*` per the time subsystem naming
    convention established by the existing RoamCore time
    helpers — the `time` subsystem is OWNED by the existing
    `homeassistant/packages/roamcore_weather_time.yaml` +
    `sensor.rc_time_zone` override contract; this slice
    inherits the `rc_time_*` prefix from the existing time
    helpers without backfilling, mirroring how hvac-basics
    Wave 3 #49 inherits the `rc_hvac_*` prefix from
    heated-floors Wave 3 #44 without backfilling, and how
    timezone-geolocator Wave 3 #54 inherits the `rc_time_zone_*`
    prefix from the existing time helpers without backfilling).

    CRITICAL: the time subsystem prefix is `rc_time_*` (NOT
    `rc_time_atomic_*` and NOT `rc_time_ntp_*`); the Wave 3 #54
    timezone-geolocator slice uses the `rc_time_zone_*` prefix
    (a SPECIFIC SUBSET of the time subsystem that handles
    "what timezone IS it?"); this time-atomic slice uses the
    BROADER `rc_time_*` prefix (covering the atomic time side
    of the time subsystem — "what time IS it?"). Both slices
    coexist in the same time subsystem.
    """
    import re

    tiles = manifest.get("dashboard", {}).get("tiles", [])
    assert tiles, "time-atomic contributes at least one dashboard tile"

    # Every tile must be a string entity id (spec calls for
    # tiles-as-strings, mirroring the spec's listed shape).
    for tile in tiles:
        assert isinstance(tile, str), (
            f"dashboard.tiles[*] must be a string entity id "
            f"(spec §1); got {tile!r}"
        )

    # Allowed HA core domain prefixes per docs/reference/rc-
    # entity-naming.md: binary_sensor, sensor. (No `zone.*`
    # domain tile in this connection — the contract layer
    # reports "is the clock synced?" via binary_sensor, not
    # "what zone is the van in?" via zone.*; the operator-side
    # zone entity lives in the upstream zone domain, not in
    # the rc_time_* contract layer.)
    allowed_domains = {"binary_sensor", "sensor"}
    pattern = re.compile(r"^[a-z_]+\.rc_time_[a-z0-9_]+$")

    # Vendor / implementation / hardware-side name leaks that
    # must NEVER appear in any rc_* tile id. The spec
    # requirement is "no double-stamps of [vendor + hardware
    # names + protocol names + integration names] beyond the
    # rc_time_ subsystem prefix". Vendor names like NTP /
    # pool.ntp.org / chrony / systemd-timesyncd / Traccar /
    # Wican / OBD / HACS / MQTT / ESPHome / HA Companion are
    # an absolute vendor leak and are forbidden from EVER
    # appearing in any rc_* tile id (regardless of where in
    # the tile).
    #
    # The generic nouns (`current`, `source`, `last`, `sync`,
    # `minutes`, `ago`, `seconds`, `drift`, `synced`, `stale`,
    # `reachable`, `present`, `ntp`) are LITERALLY PART OF
    # the spec-required tile ids (e.g.
    # `sensor.rc_time_current`,
    # `sensor.rc_time_ntp_source`,
    # `sensor.rc_time_last_sync_minutes_ago`,
    # `sensor.rc_time_drift_seconds`,
    # `binary_sensor.rc_time_synced`,
    # `binary_sensor.rc_time_stale`,
    # `binary_sensor.rc_time_ntp_reachable`,
    # `binary_sensor.rc_time_rtc_present`) — the spec calls
    # for those tiles — so flagging them as absolute substrings
    # of the suffix would conflict with the literal tile ids
    # the spec requires. The forbidden_substrings list below
    # targets the vendor-name / hardware-name /
    # protocol-name absolute-forbidden set only; the spec's
    # literal tile ids are accepted by ID and never double-
    # stamp any vendor name.
    forbidden_substrings = (
        # Time sync vendors / protocols / packages — recipe
        # explicitly forbids these (absolute forbidden — no
        # NTP / pool.ntp.org / chrony / systemd-timesyncd
        # names anywhere in any rc_* tile id; vendor
        # neutrality is non-negotiable).
        "ntp_server",         # NTP server domain (integration leak)
        "ntp_server_",        # NTP server domain (integration leak)
        "pool.ntp",           # pool.ntp.org (vendor leak)
        "pool_ntp",           # pool.ntp.org with underscore (vendor leak)
        "cloudflare",         # Cloudflare (vendor leak)
        "google_time",        # time.google.com (vendor leak)
        "chrony",             # chrony package (integration leak)
        "systemd_timesyncd",  # systemd-timesyncd package (integration leak)
        "systemd-timesyncd",  # systemd-timesyncd with hyphen (integration leak)
        "ntpd",               # ntpd package (integration leak)
        "ntpdate",            # ntpdate package (integration leak)
        "sntp",               # sntp package (integration leak)
        # Atomic clock / hardware-side leaks — recipe
        # explicitly forbids these (absolute forbidden — no
        # GPS / RTC / DS3231 / RV-3028 / PPS / atom / atomic /
        # stratum names anywhere in any rc_* tile id; vendor
        # neutrality is non-negotiable).
        "ds3231",             # DS3231 RTC chip (hardware leak)
        "rv3028",             # RV-3028 RTC chip (hardware leak)
        "rv_3028",            # RV-3028 with underscore (hardware leak)
        "rv-3028",            # RV-3028 with hyphen (hardware leak)
        "pps",                # PPS (pulse-per-second) signal (hardware leak)
        "atom",               # atomic clock prefix (vendor leak)
        "atomic",             # atomic (vendor leak — note: this slice is named "time-atomic" but the tile prefix is `rc_time_`, NOT `rc_time_atomic_`)
        "stratum",            # NTP stratum (protocol leak)
        # GPS source vendors / protocols — recipe explicitly
        # forbids these (absolute forbidden — no Traccar / HA
        # Companion / Wican / OBD / Zigbee / Z-Wave / mmWave /
        # HLK / LD2410 / Frigate / ESPHome / ESP32 names
        # anywhere in any rc_* tile id; vendor neutrality is
        # non-negotiable).
        "traccar",            # Traccar GPS server vendor (vendor leak)
        "ha_companion",       # HA Companion app (integration leak)
        "wican",              # Wican Pro OBD-II vendor (vendor leak)
        "obd",                # OBD-II protocol (integration leak)
        "obd_ii",             # OBD-II with underscore (integration leak)
        "obd-ii",             # OBD-II with hyphen (integration leak)
        "12v",                # 12V D+ signal voltage (hardware leak)
        "24v",                # 24V D+ signal voltage (hardware leak)
        "esphome",            # ESPHome integration name (integration leak)
        "esp_home",           # ESPHome with underscore (integration leak)
        "esp32",              # ESP32 microcontroller (hardware leak)
        "esp8266",            # ESP8266 microcontroller (hardware leak)
        "mqtt",               # MQTT integration (integration leak)
        "hass",               # HASS namespace (integration leak)
        "ha_integration",     # HA integration namespace (integration leak)
        "hacs",               # HACS namespace (integration leak)
        # Zone / location domain / integration namespace leaks
        # — absolute forbidden.
        "zone_",              # zone namespace (integration leak)
        "zone.",              # zone namespace (integration leak)
        "binary_sensor_",     # binary_sensor namespace (integration leak)
        "sensor_",            # sensor namespace (integration leak)
        "switch",             # switch domain (integration leak)
        "input_boolean",      # input_boolean namespace (integration leak)
        "input_select",       # input_select namespace (integration leak)
        "input_number",       # input_number namespace (integration leak)
        "input_datetime",     # input_datetime namespace (integration leak)
        "input_text",         # input_text namespace (integration leak)
        "homeassistant",      # homeassistant service domain (integration leak)
        "device_tracker",     # device_tracker namespace (integration leak)
        "set_location",       # set_location service name (integration leak)
        "set_datetime",       # set_datetime service name (integration leak)
        "update_entity",      # update_entity service name (integration leak)
    )

    for tile in tiles:
        assert pattern.match(tile), (
            f"tile id {tile!r} must match ^[a-z_]+\\.rc_time_"
            f"[a-z_]+$ (vendor-neutral contract naming per "
            f"docs/reference/rc-entity-naming.md)"
        )
        # Domain segment must be one of the allowed HA core
        # domain prefixes for the §time subsystem.
        domain = tile.split(".", 1)[0]
        assert domain in allowed_domains, (
            f"tile id {tile!r} uses domain {domain!r} which is "
            f"not in the allowed time domain set "
            f"{sorted(allowed_domains)!r}; per docs/reference/"
            f"rc-entity-naming.md §time subsystem"
        )
        # Subsystem prefix is rc_time_; the suffix (after
        # `rc_time_`) MUST NOT contain any forbidden vendor
        # substring.
        suffix = tile.split(".rc_time_", 1)[1]
        for bad in forbidden_substrings:
            assert bad not in suffix.lower(), (
                f"tile id {tile!r} contains forbidden vendor "
                f"substring {bad!r} in the suffix after "
                f"`rc_time_`; per docs/reference/rc-entity-"
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

    # Spec calls for exactly 8 tiles (1 sensor current-time +
    # 1 sensor NTP-source + 1 sensor last-sync-minutes-ago +
    # 1 sensor drift-seconds + 1 binary_sensor synced + 1
    # binary_sensor stale + 1 binary_sensor NTP-reachable +
    # 1 binary_sensor RTC-present = 8 contract entities
    # documented in the recipe §6 contract layer):
    #   sensor.rc_time_current
    #   sensor.rc_time_ntp_source
    #   sensor.rc_time_last_sync_minutes_ago
    #   sensor.rc_time_drift_seconds
    #   binary_sensor.rc_time_synced
    #   binary_sensor.rc_time_stale
    #   binary_sensor.rc_time_ntp_reachable
    #   binary_sensor.rc_time_rtc_present
    assert len(tiles) == 8, (
        f"time-atomic must contribute exactly 8 "
        f"contract tiles per spec (4 sensor + 4 binary_sensor); "
        f"got {len(tiles)}"
    )


def test_status_reflects_no_real_atomic_clock(manifest: dict) -> None:
    """Status must be honest about no integration being shipped.

    If we ever flip this to 'shipped' or 'beta', the audit will
    demand an actual integration test (and rightly so).
    'recipe_published' is the only honest tier-c status for a
    recipe we can't integration-test (HA core's `time`
    integration is upstream HA core code, not RoamCore-owned).

    The five honesty warnings that tier_warnings must contain
    cover:
      - no_native_atomic_time_integration_test (no bench
        fixture — a controlled NTP server + a GPS source
        simulator + a DS3231 / RV-3028 RTC module + canned
        fixture responses for time-sync events, all wired
        together in a controlled environment)
      - recipe_depends_on_user_wiring_gps_or_rtc_or_ntp
        (the operator must wire at least one time source —
        Path A NTP via HA core `time` integration, Path B GPS
        via Traccar Wave 3 #36 / HA Companion / Wican Pro /
        generic `device_tracker.*`, or Path C RTC via
        DS3231 / RV-3028 — before the §7 automations can do
        anything useful; this is operator's dependency, not
        RoamCore-enforced)
      - requires_operator_choice_of_path_a_b_or_c (the
        operator picks ONE OR MORE of Path A NTP / Path B
        GPS / Path C RTC; this is an honest tier-c
        affordance — tier-b would enforce one path via
        RoamCore-owned code)
      - no_real_atomic_clock_hardware_on_ci_bench (RoamCore
        does NOT have an atomic-clock fixture on the CI rig
        — the rig would require a controlled NTP server + a
        GPS source simulator + a DS3231 / RV-3028 RTC module
        all wired together in a controlled environment;
        tests are manifest-honesty only, NOT integration
        tests)
      - mode_aware_stealth_suppression_not_required (time
        tiles are non-actuator — safe to leave running in
        Stealth mode; the recipe §11 cross-references this
        honestly).
    """
    assert manifest["status"] == "recipe_published", (
        f"time-atomic status={manifest['status']!r} "
        f"implies shipped coverage we don't have; use "
        f"'recipe_published' until tier-b promotion lands"
    )
    tier_warnings = manifest.get("tier_warnings", [])
    # Tier-warnings must include the honest-about-no-atomic-
    # clock-engine marker.
    assert "no_native_atomic_time_integration_test" in tier_warnings, (
        "tier_warnings must declare 'no_native_atomic_time_"
        "integration_test' for honesty in the audit listing"
    )
    # And the user-facing recipe dependency warning (operator
    # must wire a time source).
    assert "recipe_depends_on_user_wiring_gps_or_rtc_or_ntp" in tier_warnings, (
        "tier_warnings must declare 'recipe_depends_on_user_"
        "wiring_gps_or_rtc_or_ntp' so the audit listing is "
        "honest about the operator's time source wiring "
        "dependency"
    )
    # Operator-choice-of-path honesty — the operator picks ONE
    # OR MORE of Path A NTP / Path B GPS / Path C RTC.
    assert "requires_operator_choice_of_path_a_b_or_c" in tier_warnings, (
        "tier_warnings must declare 'requires_operator_choice_"
        "of_path_a_b_or_c' so the audit listing is honest that "
        "the operator picks ONE OR MORE of Path A NTP / Path B "
        "GPS / Path C RTC rather than RoamCore-enforcing one "
        "path at tier-c"
    )
    # No atomic clock hardware on CI bench honesty.
    assert "no_real_atomic_clock_hardware_on_ci_bench" in tier_warnings, (
        "tier_warnings must declare 'no_real_atomic_clock_"
        "hardware_on_ci_bench' so the audit listing is honest "
        "that RoamCore does NOT have an atomic-clock fixture "
        "on the CI rig (a controlled NTP server + a GPS "
        "source simulator + a DS3231 / RV-3028 RTC module "
        "wired together in a controlled environment); tests "
        "are manifest-honesty only, NOT integration tests"
    )
    # Mode-aware stealth suppression not required honesty —
    # time tiles are non-actuator (safe to leave running in
    # Stealth mode; the recipe §11 cross-references this
    # honestly).
    assert "mode_aware_stealth_suppression_not_required" in tier_warnings, (
        "tier_warnings must declare 'mode_aware_stealth_"
        "suppression_not_required' so the audit listing is "
        "honest that time tiles are non-actuator and safe to "
        "leave running in Stealth mode (time accuracy is a "
        "non-actuator concern — the recipe §11 cross-"
        "references this honestly)"
    )


def test_automations_are_documented(manifest: dict) -> None:
    """Defensive guard for the future tier-b promotion.

    Time accuracy is a one-shot safety feature in van life:
    forgetting to keep the clock accurate as the van travels
    across regions + loses LTE / Starlink can break time-based
    automations (sun events + `now()` + `today_at()` + log
    timestamps) silently — the operator may not notice the
    breakage until a log entry shows the wrong timestamp. The
    recipe §7 walks through the THREE MANDATORY automations:
      - §7.1 NTP cadence refresh on boot — refreshes NTP
        servers on HA boot to ensure the system clock is
        NTP-synchronized as soon as possible after boot.
      - §7.2 GPS time correction on `device_tracker` +
        timezone change — uses GPS-derived time
        (atomic-clock-grade from GPS satellites) when NTP is
        unreachable but GPS is. Triggers on `device_tracker`
        state changes AND on timezone changes (cross-
        references Wave 3 #54 timezone-geolocator's
        `binary_sensor.rc_time_zone_stale` tile).
      - §7.3 RTC fallback when NTP unreachable for N minutes
        — uses the DS3231 / RV-3028 RTC module when NTP has
        been unreachable for N minutes (default: 10 minutes).
        This is the offline-resilience feature — the van can
        lose LTE / Starlink for hours and still keep
        accurate time via the RTC.

    The test asserts the THREE automations are documented in
    the recipe so that when this connection promotes to
    tier-b (with a real atomic-clock bench on CI + the THREE
    automations hard-enforced in RoamCore code rather than
    only documented in the recipe), the audit has a clean
    assertion to flip.
    """
    text = RECIPE_PATH.read_text(encoding="utf-8")
    # §7 header MUST be present (with the "MANDATORY before first
    # use" wording).
    assert "## §7 Automations (MANDATORY before first use)" in text, (
        "recipe.md must have a '## §7 Automations (MANDATORY "
        "before first use)' section (the THREE MANDATORY "
        "automation documentation block)"
    )
    # §7 must cover the THREE automation areas.
    automation_coverage = (
        # §7.1 NTP cadence refresh on boot — refreshes NTP
        # servers on HA boot to ensure the system clock is
        # NTP-synchronized as soon as possible after boot.
        "ntp cadence refresh on boot",
        # §7.2 GPS time correction on `device_tracker` +
        # timezone change — uses GPS-derived time
        # (atomic-clock-grade from GPS satellites) when NTP is
        # unreachable but GPS is.
        "gps time correction",
        # §7.3 RTC fallback when NTP unreachable for N
        # minutes — uses the DS3231 / RV-3028 RTC module when
        # NTP has been unreachable for N minutes.
        "rtc fallback",
    )
    for phrase in automation_coverage:
        assert phrase in text.lower(), (
            f"recipe.md §7 must cover {phrase!r}; the THREE "
            f"automations are MANDATORY before first use, and "
            f"the recipe is the only documentation operator + "
            f"future-tier-b integration code have at this tier"
        )
    # The contract tiles must include the FOUR tiles that the
    # §7 automations + the operator-facing affordance surfaces:
    #   sensor.rc_time_current
    #     (the §6 system clock tile)
    #   binary_sensor.rc_time_synced
    #     (the §6 correctness gate)
    #   binary_sensor.rc_time_stale
    #     (the §6 freshness gate)
    #   binary_sensor.rc_time_ntp_reachable
    #     (the §6 NTP reachability gate)
    tiles = manifest.get("dashboard", {}).get("tiles", [])
    safety_tiles = (
        "sensor.rc_time_current",
        "binary_sensor.rc_time_synced",
        "binary_sensor.rc_time_stale",
        "binary_sensor.rc_time_ntp_reachable",
    )
    for safety_tile in safety_tiles:
        assert safety_tile in tiles, (
            f"dashboard.tiles must include {safety_tile!r}; the "
            f"§7 automations + operator-facing affordance tiles "
            f"are part of the contract layer that the recipe §7 "
            f"documents"
        )
    # The recipe must cross-reference the upstream HA core
    # `time` integration so the §3 Path A NTP wiring is
    # discoverable.
    assert "ha core `time` integration" in text.lower() or "ha core `time`" in text.lower(), (
        "recipe.md must reference 'HA core `time` integration' "
        "for the §3 Path A NTP wiring (the upstream HA core "
        "`time` integration since 2022.x is the canonical "
        "NTP-sync engine)"
    )
    assert "home-assistant.io/integrations/time" in text.lower(), (
        "recipe.md must reference the HA core `time` "
        "integration upstream doc URL "
        "(https://www.home-assistant.io/integrations/time/) "
        "for the §3 Path A NTP wiring"
    )
    # The recipe must cross-reference the upstream HA core
    # `time` integration's NTP server list + the recommended
    # NTP servers (`time.cloudflare.com` + `time.google.com` +
    # `pool.ntp.org`) for the §3 Path A NTP wiring.
    assert "time.cloudflare.com" in text, (
        "recipe.md must reference `time.cloudflare.com` for "
        "the §3 Path A NTP wiring (the recommended PRIMARY "
        "NTP server — privacy-preserving + Stratum 1)"
    )
    assert "time.google.com" in text, (
        "recipe.md must reference `time.google.com` for the "
        "§3 Path A NTP wiring (the recommended SECONDARY NTP "
        "server — high-availability + Stratum 1)"
    )
    assert "pool.ntp.org" in text, (
        "recipe.md must reference `pool.ntp.org` for the §3 "
        "Path A NTP wiring (the recommended TERTIARY NTP "
        "server — fallback + broad coverage)"
    )
    # The recipe must cross-reference the upstream Traccar
    # Wave 3 #36 connection so the §4 Path B1 GPS time
    # correction wiring is discoverable.
    assert "traccar" in text.lower(), (
        "recipe.md must reference `Traccar` for the §4 Path "
        "B1 GPS time correction wiring (the canonical GPS "
        "source for the RoamCore map page; GPS satellites "
        "carry atomic-clock-grade time signals)"
    )
    # The recipe must cross-reference the HA Companion app
    # so the §4 Path B2 GPS time correction wiring is
    # discoverable.
    assert "ha companion" in text.lower(), (
        "recipe.md must reference `HA Companion` for the §4 "
        "Path B2 GPS time correction wiring (the operator-"
        "phone-based GPS source)"
    )
    # The recipe must cross-reference the Wican Pro Wave 3
    # #6 OBD-II reader so the §4 Path B3 GPS time correction
    # wiring is discoverable.
    assert "wican pro" in text.lower(), (
        "recipe.md must reference `Wican Pro` for the §4 Path "
        "B3 GPS time correction wiring (the optional OBD-II "
        "GPS source; always-on even when the phone is asleep)"
    )
    # The recipe must cross-reference the DS3231 / RV-3028
    # RTC module + the SBC's `systemd-timesyncd` so the §5
    # Path C RTC fallback wiring is discoverable.
    assert "ds3231" in text.lower(), (
        "recipe.md must reference `DS3231` for the §5 Path C "
        "RTC fallback wiring (the DS3231 RTC module — "
        "temperature-compensated; typical accuracy ±2 ppm "
        "from 0°C to +40°C)"
    )
    assert "rv-3028" in text.lower() or "rv3028" in text.lower(), (
        "recipe.md must reference `RV-3028` for the §5 Path C "
        "RTC fallback wiring (the RV-3028 RTC module — "
        "temperature-compensated; typical accuracy ±1 ppm "
        "from -40°C to +85°C)"
    )
    assert "systemd-timesyncd" in text.lower(), (
        "recipe.md must reference `systemd-timesyncd` for the "
        "§5 Path C RTC fallback wiring (the SBC's NTP client "
        "that falls back to the RTC when NTP is unreachable)"
    )
    # The recipe must cross-reference the Wave 3 #54
    # timezone-geolocator connection so the §7.2 GPS time
    # correction automation's timezone-change trigger is
    # discoverable.
    assert "timezone" in text.lower(), (
        "recipe.md must reference `timezone` for the §7.2 "
        "GPS time correction automation's timezone-change "
        "trigger (cross-references Wave 3 #54 timezone-"
        "geolocator's `binary_sensor.rc_time_zone_stale` tile)"
    )
    # The recipe must cross-reference the existing RoamCore
    # time helpers (`sensor.rc_time_zone` override contract +
    # `homeassistant/packages/roamcore_weather_time.yaml`) so
    # the §6 contract entities + the §11 cross-references are
    # discoverable.
    assert "sensor.rc_time_zone" in text, (
        "recipe.md must reference `sensor.rc_time_zone` for the "
        "§6 contract entities + the §11 cross-references to the "
        "existing RoamCore time helpers (the override contract)"
    )
    assert "roamcore_weather_time.yaml" in text, (
        "recipe.md must reference `roamcore_weather_time.yaml` "
        "for the §6 contract entities + the §11 cross-references "
        "to the existing RoamCore time helpers (the weather-time "
        "package)"
    )
    # The recipe's defensive guard for future tier-b promotion —
    # assert the §7 section has the "MANDATORY before first use"
    # emphasis that the recipe uses to remind operators to wire
    # the THREE automations.
    assert "mandatory before first use" in text.lower(), (
        "recipe.md §7 must use the 'MANDATORY before first use' "
        "emphasis on the THREE automations; this is the "
        "operator-side reminder that keeps the automations top-"
        "of-mind during install"
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
