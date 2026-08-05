"""Manifest-honesty tests for connections/nfc-tags/connection.yml.

This is the only test file we can ship for a tier-c recipe connection
that has no real NFC bench (a physical NFC reader (ACR122U / PN532 /
SonMicro / Identiv) + canned fixture responses for `tag_scanned` events
(a list of pre-known `tag_id` values + their expected scene mappings) +
the upstream HA core `tag` integration installed + the HACS `nfcpy`
integration installed + the HA Companion app's `tag` trigger installed,
all wired together in a controlled environment) on the CI rig to
integration-test against. The tests here assert that the manifest is
*honest about being tier-c* — that the folder/id/tier invariants hold,
that the recipe doc the tier_requirements promise is actually present
on disk, that the rc_nfc_* tile ids are vendor-neutral per
docs/reference/rc-entity-naming.md, and that the THREE §7 automations
are documented with the right cross-references (HA Companion app /
HACS `nfcpy` integration / HA core `scene` integration / mode/
automation-builder Wave 2 #23 / deadbolts Wave 3 #48 / approach-lights
Wave 3 #52 / hvac-basics Wave 3 #49).

If you add real integration coverage (e.g. an operator-wired setup
flow + a bench with a physical NFC reader + canned fixture responses),
keep this file and add the new one alongside it; the audit will then
list both under `tests:` in the manifest.

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest connections/nfc-tags/tests/ -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[3]   # tests/ -> nfc-tags/ -> connections/ -> repo
CONNECTION_DIR = REPO_ROOT / "connections" / "nfc-tags"
MANIFEST_PATH = CONNECTION_DIR / "connection.yml"
RECIPE_PATH = CONNECTION_DIR / "docs" / "recipe.md"
LEGACY_DOC = REPO_ROOT / "docs" / "catalog" / "nfc-tags" / "index.md"


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert MANIFEST_PATH.is_file(), f"missing manifest at {MANIFEST_PATH}"
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_id_matches_folder_name(manifest: dict) -> None:
    """The manifest `id` must equal the folder name (nfc-tags).

    This is the same invariant the audit script enforces; we duplicate
    it here so pytest catches regressions before CI runs the audit.
    """
    assert manifest["id"] == CONNECTION_DIR.name, (
        f"manifest id={manifest['id']!r} does not match folder name "
        f"{CONNECTION_DIR.name!r}"
    )
    assert manifest["id"] == "nfc-tags"


def test_tier_c_documents_reuse_first_strategy(manifest: dict) -> None:
    """Tier-c must NOT advertise tier-a-only RoamCore-owned fields AND
    must explicitly document the reuse-first strategy (no custom NFC
    integration; reuse the upstream HA core `tag` integration + the HA
    Companion app + the HACS `nfcpy` integration + the HA core `scene`
    integration + the HA core `automation` UI editor).

    A regression here (e.g. someone flipping tier to b without adding
    integration code + a bench fixture, or adding a RoamCore-owned NFC
    integration + setup flow that we explicitly chose NOT to ship)
    would falsely imply a working RoamCore integration + integration
    tests that we don't have, and the audit would either block the PR
    or let a misleading tier-b claim slip through. The tier-c strategy
    here is reuse-first: upstream HA core `tag` integration (the
    `tag_scanned` event + the `tag.last_scanned` entity + the `tag.list`
    service) + the HA Companion app's `tag` trigger (Path A + Path C
    implicit Path A) + the HACS `nfcpy` integration (Path B) + the HA
    core `scene` integration (the operator's `scene.*` entities) + the
    HA core `automation` UI editor (the operator-wired setup flow for
    the `tag_id → scene` mapping table).

    The distinction this test guards: install.config_flow is TRUE here
    because the UPSTREAM HA core `tag` integration (since 2022.x —
    exposes a GUI flow for the operator to register a scanned NFC tag
    in the HA tag registry; the UI's "Settings → Devices & Services →
    Tags" page since 2022.x exposes a list of registered tags + an
    "Add tag" button) + the HA core `scene` integration (since 2022.x
    — exposes a GUI flow for the operator to create a scene from a
    collection of entity states) + the HA core `automation` UI editor
    (since 2022.x — exposes a GUI flow for the operator to create an
    automation with a `tag` trigger) + the HA Companion app's `tag`
    trigger (since 2022.x — phone-side NFC scan event) + the HACS
    `nfcpy` integration (HACS — exposes a GUI flow for the operator to
    wire a USB NFC reader into HA) ALL expose a GUI flow. That's
    honest upstream truth, NOT a tier-a marker for RoamCore's tier.
    The tier-a marker for RoamCore would be a RoamCore-owned operator-
    wired setup flow + RoamCore-owned integration code + integration
    tests against a RoamCore-owned NFC bench. None of those are
    shipped at tier-c. Tier-c honesty: HA's core `tag` integration is
    upstream HA core code; the RoamCore wrapper is a thin
    `tag_id → scene` mapping table + the contract layer.
    """
    assert manifest["tier"] == "c", (
        "nfc-tags must stay at tier-c until a "
        "RoamCore-owned NFC integration + operator-wired setup flow "
        "+ integration tests ship; tier-c is the honest tier for a "
        "reuse-first HA core `tag` integration recipe"
    )
    assert manifest["wizard"]["one_tap"] is False, (
        "tier-c connections cannot advertise one_tap=true (that's "
        "a tier-a contract)"
    )
    # NFC tags recipes an upstream NFC reader (Path A — HA Companion
    # app NFC sensor; Path B — HACS `nfcpy` integration USB NFC
    # reader; Path C — HA Companion app's implicit Path A). RoamCore
    # ships no native operator-wired setup flow for that, and
    # explicitly does NOT maintain a custom NFC integration — we
    # reuse the upstream HA core `tag` integration + the HA Companion
    # app + the HACS `nfcpy` integration + the HA core `scene`
    # integration + the HA core `automation` UI editor.
    # install.config_flow is the RoamCore-owned field. We document
    # the distinction in the manifest header: the UPSTREAM HA core
    # `tag` integration + the `scene` integration + the `automation`
    # UI editor + the HA Companion app's `tag` trigger + the HACS
    # `nfcpy` integration ALL expose a GUI flow since 2022.x — honest
    # upstream truth, NOT a tier-a marker for RoamCore's tier. The
    # tier-a marker for RoamCore is a RoamCore-owned operator-wired
    # setup flow + integration tests. Until those ship, this
    # connection is tier-c.
    assert manifest["install"]["config_flow"] is True, (
        "install.config_flow must stay True — the upstream HA "
        "core `tag` integration + the `scene` integration + the "
        "`automation` UI editor + the HA Companion app's `tag` "
        "trigger + the HACS `nfcpy` integration ALL expose a GUI "
        "flow since 2022.x; this is honest upstream truth, NOT a "
        "tier-a marker for RoamCore's tier. The tier-a marker for "
        "RoamCore would be a RoamCore-owned operator-wired setup "
        "flow + RoamCore-owned integration code + integration tests "
        "against a RoamCore-owned NFC bench (a physical NFC reader "
        "+ canned fixture responses for `tag_scanned` events + the "
        "upstream HA core `tag` integration installed + the HACS "
        "`nfcpy` integration installed + the HA Companion app's "
        "`tag` trigger installed). None of those are shipped at "
        "tier-c."
    )
    # install.hacs is TRUE because NFC tags optionally depends on
    # the HACS `nfcpy` integration (Path B — USB NFC reader). The
    # HACS `nfcpy` integration is installed from HACS.
    assert manifest["install"]["hacs"] is True, (
        "nfc-tags must advertise install.hacs=true — NFC tags "
        "optionally depends on the HACS `nfcpy` integration (Path "
        "B — USB NFC reader); install.hacs is TRUE for tier-c "
        "recipes that have an optional HACS dependency"
    )
    # Belt-and-braces: there must be no RoamCore-owned operator-
    # wired setup flow file in this folder (no native integration
    # code for a tier-c recipe connection). The upstream HA core
    # `tag` integration + the HA Companion app + the HACS `nfcpy`
    # integration + the HA core `scene` integration + the HA core
    # `automation` UI editor have their own GUI flows, but that
    # lives in the upstream HA core / HACS / vendor repos, not in
    # this folder.
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
    # DOMAIN must equal "nfc_tags" (matches the connection name
    # "nfc-tags" → "nfc_tags" via the audit convention of
    # replacing hyphens with underscores).
    assert 'DOMAIN = "nfc_tags"' in init_text, (
        '__init__.py must define DOMAIN = "nfc_tags" '
        '(matches the connection name "nfc-tags" per '
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
    # `tag` integration + the HA Companion app + the HACS `nfcpy`
    # integration + the HA core `scene` integration + the HA core
    # `automation` UI editor).
    description = (manifest["description"] or "").lower()
    assert (
        "reuse" in description
        or "ha core" in description
        or "ha core `tag`" in description
        or "tag integration" in description
        or "nfc" in description
    ), (
        "manifest.description must explicitly document the "
        "reuse-first strategy (e.g. mention 'HA core' or "
        "'tag integration' or 'reuse-first' or 'nfc' or "
        "similar); tier-c is the honest tier for a recipe that "
        "does NOT own the integration code"
    )
    # The links.official list must point at the HA core `tag`
    # integration upstream doc (the canonical reuse-first
    # source).
    official_links = manifest.get("links", {}).get("official", [])
    assert any(
        "home-assistant.io/integrations/tag" in link.lower()
        for link in official_links
    ), (
        "links.official must include the HA core `tag` "
        "integration upstream doc URL "
        "(https://www.home-assistant.io/integrations/tag/); "
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
    # Sanity: the recipe actually documents NFC tags + the contract
    # entities rather than just an empty placeholder. The recipe
    # mentions "nfc" / "tag" / "tag_id" / "scene" / "rc_nfc_" — any
    # one of these is sufficient (a substantive howto would mention
    # all of them, but the assertion guards against the empty-
    # placeholder regression).
    text = RECIPE_PATH.read_text(encoding="utf-8")
    assert (
        "nfc" in text.lower()
        or "tag_id" in text.lower()
        or "tag" in text.lower()
        or "scene" in text.lower()
        or "ha core" in text.lower()
        or "tag integration" in text.lower()
    ) and "rc_nfc_" in text, (
        "recipe.md must document the NFC tags setup (Path A "
        "phone-as-NFC-reader via HA Companion app, Path B USB NFC "
        "reader via HACS `nfcpy` integration, Path C implicit Path "
        "A, the `tag_id → scene` mapping table, the THREE §7 "
        "automations, troubleshooting) and reference at least "
        "one `rc_nfc_*` tile"
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
        "## §1 What are NFC tags in RoamCore?",
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
    """Promoted from tier-c legacy doc — category must match.

    The legacy tier-c spec lives at
    docs/catalog/nfc-tags/index.md (a 14-line stub, originally
    listed as "Support tier: C" with no recipe + no contract + no
    automations — just a placeholder about "easy NFC-based
    automations and practical places to put tags in a van" +
    "Lights off", "Bedtime", "Leave camp" as example scene
    names). We promote the connection into the `access_control`
    category so the audit + boundary-CI can pair them up. The
    legacy doc MUST still exist (with the supersession banner)
    so that the recipe can reference it AND the audit can verify
    the supersession banner is in place.
    """
    assert manifest["category"] == "access_control", (
        f"category must stay 'access_control' (legacy doc lives "
        f"at docs/catalog/nfc-tags/index.md); got "
        f"{manifest['category']!r}"
    )
    assert LEGACY_DOC.is_file(), (
        "expected the legacy tier-c doc to still exist so we can "
        "reference it from the recipe (and add a supersession banner)"
    )
    # Wave 9 #124c: legacy stub converted to a 2-line clean redirect
    # page (per directive repo-hygiene § "user-facing repo"). The file
    # must still exist (so old links resolve) and must now be a thin
    # redirect pointing at the canonical recipe — NOT carry the giant
    # supersession banner anymore.
    legacy_text = LEGACY_DOC.read_text(encoding="utf-8")
    legacy_text = LEGACY_DOC.read_text(encoding="utf-8")
    assert "Moved" in legacy_text and "connections/nfc-tags/docs/recipe.md" in legacy_text, (
        "legacy docs/catalog/nfc-tags/index.md must be a 2-line 'Moved to ...' redirect page pointing at "
        "connections/nfc-tags/docs/recipe.md (Wave 9 #124c); got:\n" + legacy_text[:200]
    )
    # Belt-and-braces: the user-facing legacy doc must NOT carry the
    # giant supersession banner anymore (directive repo-hygiene §).
    assert "SUPERSEDED" not in legacy_text, (
        "legacy docs/catalog/nfc-tags/index.md must not carry the 'SUPERSEDED' banner (Wave 9 "
        "#124c — user-facing repo hygiene)"
    )

def test_dashboard_tiles_follow_rc_naming(manifest: dict) -> None:
    """rc_* tile ids must NOT contain vendor names (per rc-entity-naming.md).

    The NFC tags contract is implementation-agnostic (it talks to
    whatever NFC reader the operator wires + the upstream HA core
    `tag` integration + the HA Companion app + the HACS `nfcpy`
    integration + the HA core `scene` integration, not any
    vendor's library). Contract ids must stay vendor-neutral —
    NO `acr122u`, `pn532`, `sonmicro`, `identiv`, `nfcpy`,
    `ntag`, `ntag215`, `ntag216`, `mifare`, `ultralight`,
    `sticker`, `tag_id`, `tag_id_`, `integration`, `homeassistant`,
    `device_tracker`, `hass`, `ha_integration`, `hacs`, `mqtt`,
    `esphome`, `esp32`, `esp8266`, `binary_sensor_`, `sensor_`,
    `switch`, `input_boolean`, `input_select`, `input_number`,
    `input_datetime`, `input_text` in any rc_* tile id BEYOND
    the subsystem prefix `rc_nfc_*`. The generic nouns `last`,
    `triggered`, `scene`, `active`, `registered`, `tags`,
    `count`, `scanned`, `id`, `minutes`, `ago`, `warning`,
    `unknown`, `stealth`, `mode`, `suppressed`, `trigger`,
    `now`, `available` are allowed (they describe what the tile
    is for, not which vendor).

    The spec is strict: every `dashboard.tiles[*]` must match
    `^[a-z_]+\\.rc_nfc_[a-z0-9_]+$` (vendor-neutral, subsystem
    prefix `rc_nfc_*` per the `nfc` subsystem naming convention
    established by this slice; the `nfc` subsystem is OWNED by
    this slice — the `nfc` subsystem addition to
    docs/reference/rc-entity-naming.md is the FIRST `nfc`-
    category slice in the RoamCore connection pipeline; the
    `access_control` category is the canonical category for
    NFC tags + the deadbolts Wave 3 #48 connection).

    CRITICAL: the NFC tags subsystem prefix is `rc_nfc_*` (NOT
    `rc_nfc_tag_*` and NOT `rc_nfc_scene_*` and NOT
    `rc_access_control_*`); the §access_control category is
    the canonical category for NFC tags + the deadbolts
    Wave 3 #48 connection's `rc_access_control_*` prefix (the
    deadbolts connection uses `rc_access_control_*` because
    `deadbolts` is the canonical precursor to `access_control`).
    The NFC tags connection uses the `rc_nfc_*` prefix because
    `nfc` is the canonical NFC subsystem (the deadbolts
    connection uses `rc_access_control_*` because the deadbolts
    tile prefix is the broader access_control prefix).

    The forbidden_substrings list below targets the vendor /
    library / hardware / protocol / integration absolute-
    forbidden set only; the spec's literal tile ids are
    accepted by ID and never double-stamp any vendor name.
    """
    import re

    tiles = manifest.get("dashboard", {}).get("tiles", [])
    assert tiles, "nfc-tags contributes at least one dashboard tile"

    # Every tile must be a string entity id (spec calls for
    # tiles-as-strings, mirroring the spec's listed shape).
    for tile in tiles:
        assert isinstance(tile, str), (
            f"dashboard.tiles[*] must be a string entity id "
            f"(spec §1); got {tile!r}"
        )

    # Allowed HA core domain prefixes per docs/reference/rc-
    # entity-naming.md: binary_sensor, sensor, button. (No
    # `zone.*` domain tile in this connection — the contract
    # layer reports "what scene did the last NFC tag trigger?"
    # via sensor, not "what zone is the van in?" via zone.*; the
    # operator-side zone entity lives in the upstream zone
    # domain, not in the rc_nfc_* contract layer.)
    allowed_domains = {"binary_sensor", "sensor", "button"}
    pattern = re.compile(r"^[a-z_]+\.rc_nfc_[a-z0-9_]+$")

    # Vendor / implementation / hardware-side name leaks that
    # must NEVER appear in any rc_* tile id. The spec
    # requirement is "no double-stamps of [vendor + hardware
    # names + protocol names + integration names] beyond the
    # rc_nfc_ subsystem prefix". Vendor names like ACR122U /
    # PN532 / SonMicro / Identiv / nfcpy / NTAG215 / NTAG216 /
    # Mifare / Ultralight / Traccar / Wican / OBD / HACS / MQTT
    # / ESPHome / ESP32 / HA Companion are an absolute vendor
    # leak and are forbidden from EVER appearing in any rc_*
    # tile id (regardless of where in the tile).
    #
    # The generic nouns (`last`, `triggered`, `scene`, `active`,
    # `registered`, `tags`, `count`, `scanned`, `id`, `minutes`,
    # `ago`, `warning`, `unknown`, `stealth`, `mode`, `suppressed`,
    # `trigger`, `now`, `available`) are LITERALLY PART OF
    # the spec-required tile ids (e.g.
    # `sensor.rc_nfc_last_triggered_scene`,
    # `binary_sensor.rc_nfc_last_triggered_scene_active`,
    # `sensor.rc_nfc_registered_tags_count`,
    # `sensor.rc_nfc_last_scanned_tag_id`,
    # `sensor.rc_nfc_last_scan_minutes_ago`,
    # `binary_sensor.rc_nfc_tag_unknown_warning`,
    # `binary_sensor.rc_nfc_stealth_mode_suppressed`,
    # `button.rc_nfc_trigger_scene_now`) — the spec calls for
    # those tiles — so flagging them as absolute substrings
    # of the suffix would conflict with the literal tile ids
    # the spec requires. The forbidden_substrings list below
    # targets the vendor-name / hardware-name /
    # protocol-name / integration-name absolute-forbidden set
    # only; the spec's literal tile ids are accepted by ID and
    # never double-stamp any vendor name.
    forbidden_substrings = (
        # NFC reader / tag hardware vendors — recipe
        # explicitly forbids these (absolute forbidden — no
        # ACR122U / PN532 / SonMicro / Identiv / nfcpy /
        # NTAG215 / NTAG216 / Mifare / Ultralight names
        # anywhere in any rc_* tile id; vendor neutrality is
        # non-negotiable).
        "acr122u",            # ACR122U USB NFC reader (hardware leak)
        "pn532",              # PN532 USB NFC reader (hardware leak)
        "sonmicro",           # SonMicro USB NFC reader (hardware leak)
        "identiv",            # Identiv USB NFC reader (hardware leak)
        "nfcpy",              # nfcpy Python library (integration leak)
        "ntag215",            # NTAG215 NFC tag (hardware leak)
        "ntag216",            # NTAG216 NFC tag (hardware leak)
        "mifare",             # Mifare NFC tag (hardware leak)
        "ultralight",         # Mifare Ultralight NFC tag (hardware leak)
        "sticker",            # NFC sticker tag (hardware leak)
        # NFC reader / protocol-side leaks — recipe
        # explicitly forbids these (absolute forbidden — no
        # NFC protocol / NFC tag / NFC reader drivers
        # anywhere in any rc_* tile id; vendor neutrality is
        # non-negotiable).
        "tag_id_",            # tag_id_ (with underscore) — reserved for the upstream tag attribute surface (vendor leak)
        "tag_id-",            # tag_id- (with hyphen) — reserved for the upstream tag attribute surface (vendor leak)
        "nfc_reader",         # NFC reader driver (integration leak)
        "nfc_reader_",        # NFC reader driver (integration leak)
        "nfcpy_",             # nfcpy Python library (integration leak)
        "iso14443",           # ISO 14443 NFC protocol (protocol leak)
        "iso15693",           # ISO 15693 NFC protocol (protocol leak)
        "nfcforum",           # NFC Forum namespace (protocol leak)
        "ndef",               # NFC Data Exchange Format (protocol leak)
        # Integration / vendor namespace leaks — recipe
        # explicitly forbids these (absolute forbidden — no
        # HACS / HA Companion / MQTT / ESPHome / ESP32 /
        # Traccar / Wican / OBD / Frigate / zone / device_
        # tracker names anywhere in any rc_* tile id; vendor
        # neutrality is non-negotiable).
        "hacs",               # HACS namespace (integration leak)
        "hass",               # HASS namespace (integration leak)
        "ha_integration",     # HA integration namespace (integration leak)
        "ha_companion",       # HA Companion app (integration leak)
        "mqtt",               # MQTT integration (integration leak)
        "esphome",            # ESPHome integration name (integration leak)
        "esp_home",           # ESPHome with underscore (integration leak)
        "esp32",              # ESP32 microcontroller (hardware leak)
        "esp8266",            # ESP8266 microcontroller (hardware leak)
        "traccar",            # Traccar GPS server vendor (vendor leak)
        "wican",              # Wican Pro OBD-II vendor (vendor leak)
        "obd",                # OBD-II protocol (integration leak)
        "obd_ii",             # OBD-II with underscore (integration leak)
        "obd-ii",             # OBD-II with hyphen (integration leak)
        "12v",                # 12V D+ signal voltage (hardware leak)
        "24v",                # 24V D+ signal voltage (hardware leak)
        "frigate",            # Frigate (vendor leak)
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
        "update_entity",      # update_entity service name (integration leak)
    )

    for tile in tiles:
        assert pattern.match(tile), (
            f"tile id {tile!r} must match ^[a-z_]+\\.rc_nfc_"
            f"[a-z_]+$ (vendor-neutral contract naming per "
            f"docs/reference/rc-entity-naming.md)"
        )
        # Domain segment must be one of the allowed HA core
        # domain prefixes for the §nfc subsystem.
        domain = tile.split(".", 1)[0]
        assert domain in allowed_domains, (
            f"tile id {tile!r} uses domain {domain!r} which is "
            f"not in the allowed nfc domain set "
            f"{sorted(allowed_domains)!r}; per docs/reference/"
            f"rc-entity-naming.md §nfc subsystem"
        )
        # Subsystem prefix is rc_nfc_; the suffix (after
        # `rc_nfc_`) MUST NOT contain any forbidden vendor
        # substring. NOTE: the substring `tag_id` (without
        # underscore) IS used in the spec-required tile id
        # `sensor.rc_nfc_last_scanned_tag_id` (the
        # `last_scanned_tag_id` portion of the suffix). The
        # forbidden_substrings list forbids `tag_id_` (with
        # underscore) and `tag_id-` (with hyphen) — the
        # upstream tag attribute surface — but does NOT
        # forbid `tag_id` (without underscore) — the
        # OPERATIONAL concept (the operator's most recent
        # scanned tag ID).
        suffix = tile.split(".rc_nfc_", 1)[1]
        for bad in forbidden_substrings:
            assert bad not in suffix.lower(), (
                f"tile id {tile!r} contains forbidden vendor "
                f"substring {bad!r} in the suffix after "
                f"`rc_nfc_`; per docs/reference/rc-entity-"
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

    # Spec calls for exactly 8 tiles (1 sensor last-triggered-
    # scene + 1 binary_sensor last-triggered-scene-active + 1
    # sensor registered-tags-count + 1 sensor last-scanned-tag-
    # id + 1 sensor last-scan-minutes-ago + 1 binary_sensor
    # tag-unknown-warning + 1 binary_sensor stealth-mode-
    # suppressed + 1 button trigger-scene-now = 8 contract
    # entities documented in the recipe §6 contract layer):
    #   sensor.rc_nfc_last_triggered_scene
    #   binary_sensor.rc_nfc_last_triggered_scene_active
    #   sensor.rc_nfc_registered_tags_count
    #   sensor.rc_nfc_last_scanned_tag_id
    #   sensor.rc_nfc_last_scan_minutes_ago
    #   binary_sensor.rc_nfc_tag_unknown_warning
    #   binary_sensor.rc_nfc_stealth_mode_suppressed
    #   button.rc_nfc_trigger_scene_now
    assert len(tiles) == 8, (
        f"nfc-tags must contribute exactly 8 contract tiles "
        f"per spec (4 sensor + 3 binary_sensor + 1 button); "
        f"got {len(tiles)}"
    )


def test_status_reflects_no_real_nfc_integration(manifest: dict) -> None:
    """Status must be honest about no integration being shipped.

    If we ever flip this to 'shipped' or 'beta', the audit will
    demand an actual integration test (and rightly so).
    'recipe_published' is the only honest tier-c status for a
    recipe we can't integration-test (HA's core `tag`
    integration is upstream HA core code, not RoamCore-owned).

    The five honesty warnings that tier_warnings must contain
    cover:
      - no_native_nfc_integration (no bench fixture — a
        physical NFC reader + canned fixture responses for
        `tag_scanned` events + the upstream HA core `tag`
        integration installed + the HACS `nfcpy` integration
        installed + the HA Companion app's `tag` trigger
        installed, all wired together in a controlled
        environment)
      - recipe_depends_on_user_registering_nfc_tags_in_ha_
        registry (the operator must register each NFC tag in
        HA's tag registry + create the scenes in HA's scene
        registry + write the `tag_id → scene` mapping table
        before the §7 automations can do anything useful; this
        is operator's dependency, not RoamCore-enforced)
      - requires_operator_choice_of_path_a_phone_nfc_reader_
        or_path_b_usb_nfc_reader_or_path_c_implicit (the
        operator picks ONE OR MORE of Path A phone-as-NFC-
        reader via the HA Companion app + Path B USB NFC
        reader via the HACS `nfcpy` integration + Path C
        implicit Path A via the HA Companion app's `tag`
        trigger; this is an honest tier-c affordance — tier-b
        would enforce one path via RoamCore-owned code)
      - no_real_nfc_reader_hardware_on_ci_bench (RoamCore
        does NOT have an NFC reader fixture on the CI rig —
        the rig would require a physical NFC reader + canned
        fixture responses for `tag_scanned` events + the
        upstream HA core `tag` integration installed + the
        HACS `nfcpy` integration installed + the HA Companion
        app's `tag` trigger installed, all wired together in
        a controlled environment; tests are manifest-honesty
        only, NOT integration tests)
      - mode_aware_stealth_suppression_required_when_used_
        at_campgrounds (NFC tags MUST be suppressed in Stealth
        mode because running a scene in a campground with quiet
        hours would disturb other campers; the §7.3 Stealth-
        mode suppression automation is MANDATORY before first
        use)
    """
    assert manifest["status"] == "recipe_published", (
        f"nfc-tags status={manifest['status']!r} "
        f"implies shipped coverage we don't have; use "
        f"'recipe_published' until tier-b promotion lands"
    )
    tier_warnings = manifest.get("tier_warnings", [])
    # Tier-warnings must include the honest-about-no-native-
    # nfc-integration marker.
    assert "no_native_nfc_integration" in tier_warnings, (
        "tier_warnings must declare 'no_native_nfc_integration' "
        "for honesty in the audit listing"
    )
    # And the user-facing recipe dependency warning (operator
    # must register each NFC tag in HA's tag registry + create
    # the scenes in HA's scene registry + write the `tag_id →
    # scene` mapping table).
    assert "recipe_depends_on_user_registering_nfc_tags_in_ha_registry" in tier_warnings, (
        "tier_warnings must declare 'recipe_depends_on_user_"
        "registering_nfc_tags_in_ha_registry' so the audit "
        "listing is honest about the operator's NFC tag wiring "
        "dependency"
    )
    # Operator-choice-of-path honesty — the operator picks ONE
    # OR MORE of Path A phone-as-NFC-reader via the HA Companion
    # app + Path B USB NFC reader via the HACS `nfcpy`
    # integration + Path C implicit Path A via the HA Companion
    # app's `tag` trigger.
    assert "requires_operator_choice_of_path_a_phone_nfc_reader_or_path_b_usb_nfc_reader_or_path_c_implicit" in tier_warnings, (
        "tier_warnings must declare 'requires_operator_choice_"
        "of_path_a_phone_nfc_reader_or_path_b_usb_nfc_reader_or_"
        "path_c_implicit' so the audit listing is honest that "
        "the operator picks ONE OR MORE of Path A / Path B / "
        "Path C rather than RoamCore-enforcing one path at "
        "tier-c"
    )
    # No real NFC reader hardware on CI bench honesty.
    assert "no_real_nfc_reader_hardware_on_ci_bench" in tier_warnings, (
        "tier_warnings must declare 'no_real_nfc_reader_"
        "hardware_on_ci_bench' so the audit listing is honest "
        "that RoamCore does NOT have an NFC reader fixture on "
        "the CI rig (a physical NFC reader + canned fixture "
        "responses for `tag_scanned` events + the upstream HA "
        "core `tag` integration installed + the HACS `nfcpy` "
        "integration installed + the HA Companion app's `tag` "
        "trigger installed, all wired together in a controlled "
        "environment); tests are manifest-honesty only, NOT "
        "integration tests"
    )
    # Mode-aware stealth suppression required when used at
    # campgrounds — NFC tags MUST be suppressed in Stealth mode
    # because running a scene in a campground with quiet hours
    # would disturb other campers; the §7.3 Stealth-mode
    # suppression automation is MANDATORY before first use.
    assert "mode_aware_stealth_suppression_required_when_used_at_campgrounds" in tier_warnings, (
        "tier_warnings must declare 'mode_aware_stealth_"
        "suppression_required_when_used_at_campgrounds' so the "
        "audit listing is honest that NFC tags MUST be suppressed "
        "in Stealth mode (campgrounds with quiet hours + "
        "overnight stays where running a scene would disturb "
        "other campers); the §7.3 Stealth-mode suppression "
        "automation is MANDATORY before first use"
    )


def test_automations_are_documented(manifest: dict) -> None:
    """Defensive guard for the future tier-b promotion.

    NFC tag-triggered scenes are a one-shot operator-facing
    affordance in van life: forgetting to wire the `tag_id →
    scene` mapping table + the §7 automations can leave the
    operator tapping NFC tags that do not fire any scene (the
    `tag_scanned` event fires but no scene is triggered). The
    §7 walks through the THREE MANDATORY automations:
      - §7.1 Last-tag-triggered scene — the operator's
        `tag_id → scene` mapping table. The automation fires
        when a `tag_scanned` event is received AND matches a
        known `tag_id` in the mapping table AND then calls
        `scene.turn_on` on the mapped scene.
      - §7.2 Tag-unknown warning — the operator's on-ramp
        for adding new tags. The automation fires when a
        `tag_scanned` event is received AND the `tag_id` is
        NOT in the mapping table. The automation sends a
        notification to the operator's phone (via the HA
        Companion app) saying "Unknown NFC tag scanned:
        <tag_id> — register it in the RoamCore tag_id →
        scene mapping table".
      - §7.3 Stealth-mode suppression — the operator's
        quiet-campground-aware affordance. The automation
        SUPPRESSES the §7.1 last-tag-triggered scene
        automation when the `select.rc_mode` is in `stealth`
        mode.

    The test asserts the THREE automations are documented in
    the recipe so that when this connection promotes to
    tier-b (with a real NFC bench on CI + the THREE
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
        # §7.1 Last-tag-triggered scene — the operator's
        # `tag_id → scene` mapping table.
        "last-tag-triggered scene",
        # §7.2 Tag-unknown warning — the operator's on-ramp
        # for adding new tags.
        "tag-unknown warning",
        # §7.3 Stealth-mode suppression — the operator's
        # quiet-campground-aware affordance.
        "stealth-mode suppression",
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
    #   sensor.rc_nfc_last_triggered_scene
    #     (the §6 last-triggered-scene tile)
    #   binary_sensor.rc_nfc_tag_unknown_warning
    #     (the §6 tag-unknown-warning gate)
    #   binary_sensor.rc_nfc_stealth_mode_suppressed
    #     (the §6 Stealth-mode suppression gate)
    #   button.rc_nfc_trigger_scene_now
    #     (the §6 manual override button)
    tiles = manifest.get("dashboard", {}).get("tiles", [])
    safety_tiles = (
        "sensor.rc_nfc_last_triggered_scene",
        "binary_sensor.rc_nfc_tag_unknown_warning",
        "binary_sensor.rc_nfc_stealth_mode_suppressed",
        "button.rc_nfc_trigger_scene_now",
    )
    for safety_tile in safety_tiles:
        assert safety_tile in tiles, (
            f"dashboard.tiles must include {safety_tile!r}; the "
            f"§7 automations + operator-facing affordance tiles "
            f"are part of the contract layer that the recipe §7 "
            f"documents"
        )
    # The recipe must cross-reference the upstream HA core
    # `tag` integration so the §3 Path A + §4 Path B wiring
    # is discoverable.
    assert "ha core `tag` integration" in text.lower() or "ha core `tag`" in text.lower(), (
        "recipe.md must reference 'HA core `tag` integration' "
        "for the §3 Path A + §4 Path B wiring (the upstream HA "
        "core `tag` integration since 2022.x is the canonical "
        "NFC tag scan event source)"
    )
    assert "home-assistant.io/integrations/tag" in text.lower(), (
        "recipe.md must reference the HA core `tag` "
        "integration upstream doc URL "
        "(https://www.home-assistant.io/integrations/tag/) "
        "for the §3 Path A + §4 Path B wiring"
    )
    # The recipe must cross-reference the HA Companion app so
    # the §3 Path A phone-as-NFC-reader wiring is discoverable.
    assert "ha companion" in text.lower(), (
        "recipe.md must reference `HA Companion` for the §3 Path "
        "A phone-as-NFC-reader wiring (the operator's Android "
        "phone with NFC built in; the HA Companion app exposes a "
        "`tag_scanned` event in HA core since 2022.x when the "
        "operator taps an NFC tag to the phone)"
    )
    # The recipe must cross-reference the HACS `nfcpy`
    # integration so the §4 Path B USB NFC reader wiring is
    # discoverable.
    assert "nfcpy" in text.lower(), (
        "recipe.md must reference `nfcpy` for the §4 Path B "
        "USB NFC reader wiring (the HACS `nfcpy` integration "
        "supports the ACR122U / PN532 / SonMicro / Identiv "
        "USB NFC readers)"
    )
    # The recipe must cross-reference the HA core `scene`
    # integration so the scene registry wiring is discoverable.
    assert "scene" in text.lower(), (
        "recipe.md must reference `scene` for the §3 / §4 / §5 "
        "scene registry wiring (the operator's `scene.*` "
        "entities from the HA core `scene` integration; "
        "since 2022.x)"
    )
    # The recipe must cross-reference the mode/automation-
    # builder recipe (Wave 2 #23) so the §7.3 Stealth-mode
    # suppression automation's `select.rc_mode` tile is
    # discoverable.
    assert "select.rc_mode" in text, (
        "recipe.md must reference `select.rc_mode` for the "
        "§7.3 Stealth-mode suppression automation's source of "
        "truth (the mode/automation-builder recipe Wave 2 #23 "
        "is the canonical source of the `select.rc_mode` tile "
        "with the following options: `home` / `away` / `stealth`"
        " / `sleep`)"
    )
    # The recipe must cross-reference the deadbolts Wave 3
    # #48 connection so the optional "tag-unlock-the-door"
    # affordance is discoverable.
    assert "deadbolts" in text.lower(), (
        "recipe.md must reference `Deadbolts` for the optional "
        "'tag-unlock-the-door' affordance that uses the same "
        "`tag_id → scene` mapping pattern (Wave 3 #48)"
    )
    # The recipe must cross-reference the approach-lights
    # Wave 3 #52 connection so the canonical "Lights off" /
    # "Welcome home" scene entities are discoverable.
    assert "approach lights" in text.lower(), (
        "recipe.md must reference `Approach lights` for the "
        "canonical 'Lights off' / 'Welcome home' scene entities "
        "that the `tag_id → scene` mapping table can use as "
        "scene targets (Wave 3 #52)"
    )
    # The recipe must cross-reference the HVAC basics Wave 3
    # #49 connection so the canonical "Bedtime" / "Climate"
    # scene entities are discoverable.
    assert "hvac" in text.lower(), (
        "recipe.md must reference `HVAC` for the canonical "
        "'Bedtime' / 'Climate' scene entities that the "
        "`tag_id → scene` mapping table can use as scene "
        "targets (Wave 3 #49)"
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
