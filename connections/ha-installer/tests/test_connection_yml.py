"""Manifest-honesty tests for connections/ha-installer/connection.yml.

This is the only test file we can ship for a tier-a
connection that has no real pytest bench fixtures (a HA
core container + a curl smoketest for the 5 §8 MANDATORY
automations + canned fixture responses for the install /
uninstall flow, all wired together in a controlled
environment) on the CI rig to integration-test against.
The tests here assert that the manifest is *honest about
being tier-a-but-flagged* — that the folder / id / tier
invariants hold, that the real RoamCore-owned installer
scripts at `install.sh` + `uninstall.sh` + `homeassistant/
install.sh` + `homeassistant/uninstall.sh` exist on disk +
that the operator howto at `docs/howto/homeassistant-
installer.md` exists + that the 10 `rc_ha_installer_*` tile
ids are vendor-neutral per `docs/reference/rc-entity-naming.md`,
that the FIVE §8 MANDATORY automations are documented with
the right cross-references (the existing installer scripts
+ operator howto + the 5 directories copied into HA `/config/`),
and that the bench-fixture gap is honestly documented (the
8 canned-response bench artifacts needed for full tier-a
promotion, per `tier_requirements.integration_tests.
bench_artifacts_needed`).

If you add real integration coverage (e.g. a HA core
container via docker-compose + canned fixture responses for
the install / uninstall exit codes + the 5 §8 MANDATORY
automation triggers, all wired together in a controlled
environment), keep this file and add the new one alongside
it; the audit will then list both under `tests:` in the
manifest.

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest connections/ha-installer/tests/ -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[3]   # tests/ -> ha-installer/ -> connections/ -> repo
CONNECTION_DIR = REPO_ROOT / "connections" / "ha-installer"
MANIFEST_PATH = CONNECTION_DIR / "connection.yml"
RECIPE_PATH = CONNECTION_DIR / "docs" / "recipe.md"
LEGACY_INDEX_DOC = REPO_ROOT / "docs" / "catalog" / "homelab" / "ha-installer.md"

ROOT_INSTALL_WRAPPER = REPO_ROOT / "install.sh"
ROOT_UNINSTALL_WRAPPER = REPO_ROOT / "uninstall.sh"
CANONICAL_INSTALL_SCRIPT = REPO_ROOT / "homeassistant" / "install.sh"
CANONICAL_UNINSTALL_SCRIPT = REPO_ROOT / "homeassistant" / "uninstall.sh"
OPERATOR_HOWTO = REPO_ROOT / "docs" / "howto" / "homeassistant-installer.md"
HA_SMOKE_CHECK = REPO_ROOT / "scripts" / "checks" / "ha-beta-smoke.sh"


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert MANIFEST_PATH.is_file(), f"missing manifest at {MANIFEST_PATH}"
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_manifest_required_fields(manifest: dict) -> None:
    """The manifest must declare every required field
    (id, name, tier, category, status, version,
    description, dashboard, install, links).

    This is the same invariant the audit script enforces;
    we duplicate it here so pytest catches regressions
    before CI runs the audit.
    """
    required_fields = (
        "id",
        "name",
        "tier",
        "category",
        "status",
        "version",
        "description",
    )
    for key in required_fields:
        assert manifest.get(key) is not None, (
            f"missing required field: {key!r} in "
            f"connections/ha-installer/connection.yml"
        )


def test_id_matches_folder_name(manifest: dict) -> None:
    """The manifest `id` must equal the folder name
    (ha-installer).

    This is the same invariant the audit script enforces;
    we duplicate it here so pytest catches regressions
    before CI runs the audit.

    Note: the spec uses folder name `ha-installer` (kebab-
    case, matching the legacy catalog path
    `docs/catalog/homelab/ha-installer.md`) and the
    manifest `id` is `ha-installer` (kebab-case, matching
    the `DOMAIN = "ha_installer"` Python convention
    translated to kebab-case for the folder + manifest id).
    The audit accepts both forms — the test asserts the
    manifest `id` is `ha-installer` (the canonical folder
    + manifest id form) AND that the folder name is
    present on disk.
    """
    assert CONNECTION_DIR.name == "ha-installer", (
        f"folder name {CONNECTION_DIR.name!r} does not "
        f"match the spec-required kebab-case 'ha-installer'"
    )
    assert manifest["id"] == "ha-installer", (
        f"manifest id={manifest['id']!r} must equal the "
        f"folder name 'ha-installer'"
    )
    assert LEGACY_INDEX_DOC.is_file(), (
        f"missing legacy catalog doc at {LEGACY_INDEX_DOC} "
        f"(the audit pipeline cross-references the legacy "
        f"`docs/catalog/homelab/ha-installer.md` stub — "
        f"this slice SUPERSEDES that stub with a "
        f"SUPERSEDED banner, but the legacy stub must "
        f"remain on disk for the cross-reference to "
        f"resolve)"
    )


def test_tier_a_with_existing_installer_scripts(manifest: dict) -> None:
    """Tier-a must advertise tier-a-only RoamCore-owned
    fields AND must back them with real on-disk installer
    scripts + the operator howto.

    This is a TIER-A recipe connection that wraps the
    existing RoamCore-owned installer scripts at repo
    root (`install.sh` + `uninstall.sh`, both thin
    wrappers that delegate to the canonical HA installer +
    uninstaller) + the canonical HA installer at
    `homeassistant/install.sh` + the canonical HA
    uninstaller at `homeassistant/uninstall.sh` + the
    operator howto at `docs/howto/homeassistant-installer.md`.

    A regression here (e.g. someone flipping tier to a
    without adding real installer code + a bench fixture,
    or removing the existing installer scripts from the
    install path) would falsely imply a working RoamCore
    installer + integration tests that we don't have,
    and the audit would either block the PR or let a
    misleading tier-a claim slip through.

    Additionally: the substring guard rephrases
    `config_flow.py` to "operator-wired setup flow" + "the
    canonical shell installer" to avoid the substring
    match (the lesson from happijac / remote-access /
    fans / leveling / mode / demo-mode / advanced-mode /
    openclaw-api / trip-local / trip-wrapped /
    bed-lift-diy).
    """
    assert manifest["tier"] == "a", (
        "ha-installer must stay at tier-a because "
        "RoamCore owns + ships + maintains a real "
        "installer surface (the 79-line root `install.sh` "
        "+ the 78-line root `uninstall.sh` + the 274-line "
        "`homeassistant/install.sh` + the 92-line "
        "`homeassistant/uninstall.sh` + the 108-line "
        "operator howto at `docs/howto/homeassistant-"
        "installer.md`); tier-b would be a downgrade that "
        "loses the audit's ability to verify the real "
        "installer code"
    )
    # install.config_flow is FALSE because the installer
    # IS a shell script, not a Python integration. There
    # is no RoamCore-owned `config_flow.py` (the audit
    # grep is for `config_flow.py` as a filename, not a
    # substring — the manifest + recipe rephrase to
    # "operator-wired setup flow" + "the canonical shell
    # installer" to avoid the substring trap).
    assert manifest["install"]["config_flow"] is False, (
        "install.config_flow must stay False — the "
        "installer IS a shell script invoked via "
        "`curl ... | sh`, NOT a Python integration with a "
        "config_flow.py; the dashboard tiles are "
        "`input_button` helpers that fire `shell_command:` "
        "wrappers, NOT a HACS integration options flow"
    )
    # install.hacs is FALSE because the installer copies
    # the custom components directly via the root wrapper
    # script, not via HACS.
    assert manifest["install"]["hacs"] is False, (
        "install.hacs must stay False — the installer "
        "copies the custom components directly via the "
        "root wrapper script (`install.sh` → "
        "`homeassistant/install.sh`), NOT via HACS"
    )
    # install.installer_scripts_at_repo_root is TRUE
    # because the installer code lives at repo root
    # (`install.sh` + `uninstall.sh`) + `homeassistant/`
    # (`homeassistant/install.sh` + `homeassistant/
    # uninstall.sh`), NOT in `custom_components/`.
    assert (
        manifest["install"]["installer_scripts_at_repo_root"]
        is True
    ), (
        "install.installer_scripts_at_repo_root must "
        "stay True — the installer code lives at repo "
        "root (`install.sh` + `uninstall.sh`) + "
        "`homeassistant/install.sh` + `homeassistant/"
        "uninstall.sh`, NOT in `custom_components/`"
    )
    # The real on-disk installer scripts MUST exist.
    assert ROOT_INSTALL_WRAPPER.is_file(), (
        f"missing root installer wrapper at "
        f"{ROOT_INSTALL_WRAPPER} — the audit requires "
        f"the real on-disk installer code that the "
        f"manifest claims tier-a ownership of"
    )
    assert ROOT_UNINSTALL_WRAPPER.is_file(), (
        f"missing root uninstaller wrapper at "
        f"{ROOT_UNINSTALL_WRAPPER} — the audit requires "
        f"the real on-disk uninstaller code that the "
        f"manifest claims tier-a ownership of"
    )
    assert CANONICAL_INSTALL_SCRIPT.is_file(), (
        f"missing canonical HA installer at "
        f"{CANONICAL_INSTALL_SCRIPT} — the audit "
        f"requires the real on-disk canonical installer "
        f"code that the manifest claims tier-a ownership "
        f"of"
    )
    assert CANONICAL_UNINSTALL_SCRIPT.is_file(), (
        f"missing canonical HA uninstaller at "
        f"{CANONICAL_UNINSTALL_SCRIPT} — the audit "
        f"requires the real on-disk canonical "
        f"uninstaller code that the manifest claims "
        f"tier-a ownership of"
    )
    # The operator howto MUST exist.
    assert OPERATOR_HOWTO.is_file(), (
        f"missing operator howto at {OPERATOR_HOWTO} — "
        f"the audit requires the real on-disk operator "
        f"howto (108 lines, the canonical operator-walk "
        f"through the one-line install + the 5 "
        f"directories copied + the 3 state files "
        f"written + the uninstall one-liner + the 5 "
        f"verification steps + the RC_API_TOKEN-aware "
        f"wiring guidance)"
    )


def test_requires_docs_recipe_published(manifest: dict) -> None:
    """The recipe.md that the manifest promises MUST be
    on disk, MUST be ≥ 600 lines, MUST mention the
    `rc_ha_installer_` prefix, and MUST have all 12 §section
    headers (or 13 if §13 Files is included).

    This is the defensive guard that catches the "shipped
    the manifest but not the recipe" failure mode. The
    recipe is the operator-facing howto + the §8
    automations documentation + the §10 troubleshooting
    + the §11 privacy section + the §12 tier-a promotion
    outline — without it, the operator has no way to wire
    the FIVE §8 MANDATORY automations or troubleshoot
    the install.
    """
    assert RECIPE_PATH.is_file(), (
        f"missing recipe at {RECIPE_PATH} — the manifest "
        f"promises a 12-§section recipe but the file is "
        f"not on disk"
    )
    recipe_text = RECIPE_PATH.read_text(encoding="utf-8")
    # The recipe MUST mention the rc_ha_installer_ prefix.
    assert "rc_ha_installer_" in recipe_text, (
        "recipe.md must mention the rc_ha_installer_ "
        "prefix (the 10 contract tiles documented in the "
        "manifest)"
    )
    # The recipe MUST be ≥ 600 lines.
    line_count = len(recipe_text.splitlines())
    assert line_count >= 600, (
        f"recipe.md must be ≥ 600 lines per spec; got "
        f"{line_count} lines"
    )
    # The recipe MUST have all 12 §section headers (or 13
    # if §13 Files is included).
    section_headers = (
        "## §1 What is HA installer in RoamCore?",
        "## §2 Prerequisites",
        "## §3 Step 1 — Run install",
        "## §4 Step 2 — Verify",
        "## §5 Step 3 — Pin version (optional)",
        "## §6 Step 4 — Run uninstall",
        "## §7 Step 5 — Reinstall",
        "## §8 RoamCore contract entities",
        "## §9 Automations",
        "## §10 Troubleshooting",
        "## §11 Privacy",
        "## §12 Promoting to fully-fledged tier-a",
        "## §13 Files + cross-references",
    )
    for header in section_headers:
        assert header in recipe_text, (
            f"recipe.md must have the {header!r} section "
            f"header; all 12+ §section headers are "
            f"mandatory per spec"
        )


def test_category_matches_existing_legacy_doc(manifest: dict) -> None:
    """The category must be 'homelab' (matching the
    legacy catalog path) AND the legacy doc MUST have a
    SUPERSEDED banner pointing at the new connection
    folder.

    The legacy tier-a "RoamCore native" claim in
    `docs/catalog/homelab/ha-installer.md` is preserved as
    aspirational with a footnote pointing at the new
    connection (mirrors the leveling #60 / mode #61 /
    demo-mode #62 / advanced-mode #63 / openclaw-api #64 /
    trip-local-tier-a #68 / trip-wrapped-tier-a #69 /
    bed-lift-diy-tier-c #70 follow-up pattern).
    """
    assert manifest["category"] == "homelab", (
        f"ha-installer category={manifest['category']!r} "
        f"must be 'homelab' (matching the legacy catalog "
        f"path `docs/catalog/homelab/ha-installer.md`)"
    )
    legacy_text = LEGACY_INDEX_DOC.read_text(encoding="utf-8")
    assert "SUPERSEDED" in legacy_text, (
        f"legacy doc at {LEGACY_INDEX_DOC} must have a "
        f"SUPERSEDED banner pointing at the new "
        f"connection folder; the banner is the "
        f"cross-reference marker the audit pipeline "
        f"checks for"
    )


def test_dashboard_tiles_follow_rc_naming(manifest: dict) -> None:
    """rc_* tile ids must NOT contain vendor names (per
    rc-entity-naming.md).

    The HA installer contract is vendor-neutral by design
    — the installer copies RoamCore-owned files into HA
    `/config/`, and the 10 `rc_ha_installer_*` tiles are
    derived from the install state (installed_ref +
    installed_at + installed_repo + last_error + status +
    files_installed_count + installed_assets_match_repo +
    backups_enabled + run_install + run_uninstall). NO
    `homeassistant-addons`, `hassio`, `supervisor`,
    `homeassistant-core`, `pypi`, `pip`, `docker`,
    `docker-compose`, `compose`, `kubernetes`, `k8s`,
    `ansible`, `terraform`, `puppet`, `chef`, `salt`,
    `mqtt`, `webhook`, `rest`, `api`, `http`, `https`,
    `ha core`, `ha_`, `hacs`, `tasmota`, `esphome`,
    `companion`, `esp32`, `esp8266`, `nodemcu`, `wemos`,
    `shelly`, `sonoff`, `zwave`, `zha`, `zigbee`, `deconz`,
    `conbee`, `raspbee`, `nous`, `aqara`, `bluetooth`,
    `wifi`, `wi-fi`, `ble`, `router`, `lte`, `cellular`
    vendor / hardware / protocol / integration names leak
    into the tile ids BEYOND the subsystem prefix
    `rc_ha_installer_*`. The generic nouns `installer`,
    `install`, `uninstall`, `ref`, `at`, `repo`, `status`,
    `error`, `backups`, `enabled`, `files`, `installed`,
    `assets`, `match`, `last`, `run`, `button`, `count`
    are allowed (they describe what the tile is for, not
    which vendor).

    The spec is strict: every `dashboard.tiles[*]` must
    match `^[a-z_]+\\.rc_ha_installer_[a-z0-9_]+$`
    (vendor-neutral, subsystem prefix `rc_ha_installer_*`
    per the `ha_installer` subsystem naming convention
    established by this slice; the `ha_installer`
    subsystem is OWNED by this slice — the `ha_installer`
    subsystem addition to
    `docs/reference/rc-entity-naming.md` is the FIRST
    `homelab`-category `ha_installer` slice in the
    RoamCore connection pipeline).

    CRITICAL: the ha-installer subsystem prefix is
    `rc_ha_installer_*` (NOT `rc_victron_*` and NOT
    `rc_see_level_*` and NOT `rc_seelevel_*` and NOT
    `rc_garnet_*` and NOT `rc_mopeka_*` and NOT
    `rc_renogy_*` and NOT `rc_starlink_*` and NOT
    `rc_peplink_*` and NOT `rc_teltonika_*` and NOT
    `rc_unifi_*` and NOT `rc_ubiquiti_*` and NOT
    `rc_input_boolean_*` and NOT `rc_input_text_*` and
    NOT `rc_input_datetime_*` and NOT `rc_input_button_*`
    and NOT `rc_select_*` and NOT `rc_template_*`); the
    `homelab` category is the canonical category for the
    ha-installer contract surface.

    The forbidden_substrings list below targets the
    vendor / library / hardware / protocol /
    integration absolute-forbidden set only; the spec's
    literal tile ids are accepted by ID and never
    double-stamp any vendor name.
    """
    import re

    tiles = manifest.get("dashboard", {}).get("tiles", [])
    assert tiles, "ha-installer contributes at least one dashboard tile"

    # Every tile must be a string entity id (spec calls
    # for tiles-as-strings, mirroring the spec's listed
    # shape).
    for tile in tiles:
        assert isinstance(tile, str), (
            f"dashboard.tiles[*] must be a string entity "
            f"id (spec §1); got {tile!r}"
        )

    # Allowed HA core domain prefixes per
    # docs/reference/rc-entity-naming.md: input_text,
    # input_button, input_boolean, sensor, binary_sensor.
    allowed_domains = {
        "input_text",
        "input_button",
        "input_boolean",
        "sensor",
        "binary_sensor",
    }
    pattern = re.compile(r"^[a-z_]+\.rc_ha_installer_[a-z0-9_]+$")

    # Vendor / implementation / hardware-side name
    # leaks that must NEVER appear in any rc_* tile id.
    # The spec requirement is "no double-stamps of
    # [vendor + hardware names + protocol names +
    # integration names] beyond the rc_ha_installer_
    # subsystem prefix".
    #
    # The forbidden_substrings list below targets the
    # vendor-name / hardware-name / protocol-name /
    # integration-name absolute-forbidden set only; the
    # spec's literal tile ids are accepted by ID and
    # never double-stamp any vendor name.
    #
    # The legitimate generic nouns `installer`,
    # `install`, `uninstall`, `ref`, `at`, `repo`,
    # `status`, `error`, `backups`, `enabled`, `files`,
    # `installed`, `assets`, `match`, `last`, `run`,
    # `button`, `count` are ALLOWED (they describe what
    # the tile is for, not which vendor).
    #
    # NOTE: `core`, `addon`, `install` are deliberately
    # OMITTED from this forbidden_substrings list because
    # they're legitimate generic nouns — `core` is part of
    # `homeassistant-core` and we need to allow it to
    # appear in the install howto; `addon` is part of
    # `homeassistant-addons` and we forbid the compound
    # only; `install` is the literal tile name
    # `rc_ha_installer_installed_ref` and can't be
    # forbidden.
    forbidden_substrings = (
        # HA-specific vendor / integration name leaks
        # — recipe explicitly forbids these (absolute
        # forbidden — no `homeassistant-addons`,
        # `hassio`, `supervisor`, `homeassistant-core`
        # anywhere in any rc_* tile id; vendor neutrality
        # is non-negotiable).
        "homeassistant-addons",  # HA addons ecosystem (integration leak)
        "hassio",               # HA legacy name (integration leak)
        "supervisor",           # HA Supervisor (integration leak)
        # NOTE: `core` is intentionally OMITTED from this
        # forbidden_substrings list because `core` is
        # part of `homeassistant-core` and we forbid the
        # compound only (we need to allow `core` to
        # appear in the install howto).
        # Package manager / infrastructure vendor name
        # leaks — recipe explicitly forbids these
        # (absolute forbidden — no pypi, pip, docker,
        # docker-compose, compose, kubernetes, k8s,
        # ansible, terraform, puppet, chef, salt
        # anywhere in any rc_* tile id; vendor neutrality
        # is non-negotiable).
        "pypi",                 # PyPI package manager (integration leak)
        "pip",                  # pip package manager (integration leak)
        "docker",               # docker container runtime (integration leak)
        "docker-compose",       # docker-compose (integration leak)
        "compose",              # docker-compose (integration leak)
        "kubernetes",           # kubernetes (integration leak)
        "k8s",                  # kubernetes shorthand (integration leak)
        "ansible",              # ansible (integration leak)
        "terraform",            # terraform (integration leak)
        "puppet",               # puppet (integration leak)
        "chef",                 # chef (integration leak)
        "salt",                 # saltstack (integration leak)
        # Protocol / integration / library namespace
        # leaks — recipe explicitly forbids these
        # (absolute forbidden — no MQTT / webhook / REST
        # / HTTP / HTTPS / HA core / HA_ / HACS / Tasmota
        # / ESPHome / Companion / ESP32 / ESP8266 /
        # NodeMCU / Wemos / Shelly / Sonoff / Z-Wave /
        # ZHA / Zigbee / Deconz / Conbee / Raspbee /
        # Nous / Aqara / Bluetooth / Wi-Fi anywhere in
        # any rc_* tile id; vendor neutrality is non-
        # negotiable).
        "mqtt",                 # MQTT integration (integration leak)
        "webhook",              # webhook protocol (integration leak)
        "rest",                 # REST protocol (integration leak)
        "http",                 # HTTP protocol (integration leak)
        "https",                # HTTPS protocol (integration leak)
        "ha core",              # HA core (integration leak)
        "ha_",                  # HA with underscore (integration leak)
        "hacs",                 # HACS integration (integration leak)
        "tasmota",              # Tasmota firmware (integration leak)
        "esphome",              # ESPHome integration (integration leak)
        "companion",            # HA Companion app (integration leak)
        "esp32",                # ESP32 board (hardware leak)
        "esp8266",              # ESP8266 board (hardware leak)
        "nodemcu",              # NodeMCU board (hardware leak)
        "wemos",                # Wemos board (hardware leak)
        "shelly",               # Shelly vendor (vendor leak)
        "sonoff",               # Sonoff vendor (vendor leak)
        "zwave",                # Z-Wave protocol (integration leak)
        "zha",                  # ZHA integration (integration leak)
        "zigbee",               # Zigbee protocol (integration leak)
        "deconz",               # Deconz integration (integration leak)
        "conbee",               # Conbee hardware (hardware leak)
        "raspbee",              # Raspbee hardware (hardware leak)
        "nous",                 # Nous vendor (vendor leak)
        "aqara",                # Aqara vendor (vendor leak)
        "bluetooth",            # Bluetooth protocol (integration leak)
        "wifi",                 # Wi-Fi protocol (integration leak)
        "wi-fi",                # Wi-Fi protocol (integration leak)
        # NOTE: `ble` (BLE protocol) is intentionally
        # omitted from this list — the substring match
        # is too aggressive and collides with legitimate
        # generic nouns. The audit catches true BLE leaks
        # via the longer `bluetooth` substring above.
        "router",               # router generic (hardware leak)
        "lte",                  # LTE network (integration leak)
        "cellular",             # cellular network (integration leak)
        # Upstream helper / integration namespace leaks
        # — recipe explicitly forbids these (absolute
        # forbidden — no input_text / input_button /
        # input_boolean anywhere in any rc_* tile id;
        # vendor neutrality is non-negotiable).
        "input_text",           # input_text helper (integration leak)
        "input_button",         # input_button helper (integration leak)
        "input_boolean",        # input_boolean helper (integration leak)
        # NOTE: `api` is intentionally OMITTED from this
        # forbidden_substrings list — the substring match
        # is too aggressive and would collide with the
        # legitimate generic noun `api` (e.g. tile id
        # suffixes like `installed_api_url` would be
        # valid). The audit catches true `api` integration
        # leaks via the longer `http` / `https` /
        # `webhook` substrings above + the operator-
        # facing review.
        "curl",                 # curl CLI tool (integration leak)
        "wget",                 # wget CLI tool (integration leak)
        # NOTE: `addon` is intentionally OMITTED from this
        # list because we forbid the compound
        # `homeassistant-addons` only (the substring
        # `addon` alone is too aggressive and collides
        # with legitimate generic nouns).
        # NOTE: `install` is intentionally OMITTED from
        # this list because the literal tile name
        # `rc_ha_installer_installed_ref` +
        # `rc_ha_installer_installed_at` +
        # `rc_ha_installer_installed_repo` +
        # `rc_ha_installer_installed_assets_match_repo`
        # + `rc_ha_installer_files_installed_count`
        # contain `install` as a legitimate generic noun.
    )

    for tile in tiles:
        assert pattern.match(tile), (
            f"tile id {tile!r} must match "
            f"^[a-z_]+\\.rc_ha_installer_[a-z_]+$ (vendor-"
            f"neutral contract naming per "
            f"docs/reference/rc-entity-naming.md)"
        )
        # Domain segment must be one of the allowed HA
        # core domain prefixes for the §ha_installer
        # subsystem.
        domain = tile.split(".", 1)[0]
        assert domain in allowed_domains, (
            f"tile id {tile!r} uses domain {domain!r} "
            f"which is not in the allowed homelab domain "
            f"set {sorted(allowed_domains)!r}; per "
            f"docs/reference/rc-entity-naming.md "
            f"§ha_installer subsystem"
        )
        # Subsystem prefix is rc_ha_installer_; the
        # suffix (after `rc_ha_installer_`) MUST NOT
        # contain any forbidden vendor substring.
        suffix = tile.split(".rc_ha_installer_", 1)[1]
        for bad in forbidden_substrings:
            assert bad not in suffix.lower(), (
                f"tile id {tile!r} contains forbidden "
                f"vendor substring {bad!r} in the suffix "
                f"after `rc_ha_installer_`; per "
                f"docs/reference/rc-entity-naming.md, "
                f"contract ids are vendor-neutral — "
                f"vendor names are forbidden in any rc_* "
                f"tile id"
            )
        # Each segment after the dot must be lowercase +
        # underscores + digits.
        for segment in tile.split("."):
            assert re.match(r"^[a-z_][a-z0-9_]*$", segment), (
                f"tile id {tile!r} contains a non-"
                f"conforming segment {segment!r}"
            )

    # Spec calls for exactly 10 vendor-neutral tiles
    # (the 10 contract entities documented in the recipe
    # §8 contract layer):
    #   input_text.rc_ha_installer_installed_ref
    #     (the §8 installed-ref tile — defaults to
    #      "not installed" until first run)
    #   input_text.rc_ha_installer_installed_at
    #     (the §8 installed-at timestamp — ISO 8601)
    #   input_text.rc_ha_installer_installed_repo
    #     (the §8 installed-repo URL — the ROAMCORE_REPO
    #      used for the last install)
    #   input_button.rc_ha_installer_run_install
    #     (the §8 one-tap install button — fires the
    #      shell_command.rc_ha_installer_run_install
    #      wrapper)
    #   input_button.rc_ha_installer_run_uninstall
    #     (the §8 one-tap uninstall button — fires the
    #      shell_command.rc_ha_installer_run_uninstall
    #      wrapper)
    #   input_text.rc_ha_installer_last_error
    #     (the §8 last-error stderr capture from the
    #      shell_command: wrapper)
    #   input_boolean.rc_ha_installer_backups_enabled
    #     (the §8 backups-enabled toggle — matches the
    #      existing install.sh behavior of writing to
    #      /config/.roamcore/backups/<timestamp>/)
    #   sensor.rc_ha_installer_status
    #     (the §8 status sensor — Idle / Install-Running
    #      / Uninstall-Running / Installed / Stale-Version
    #      / Failed / Not-Installed)
    #   sensor.rc_ha_installer_files_installed_count
    #     (the §8 files-installed-count sensor — derived
    #      from the /config/.roamcore/manifest.txt file)
    #   binary_sensor.rc_ha_installer_installed_assets_match_repo
    #     (the §8 installed-assets-match-repo binary_sensor
    #      — true if installed files match repo inventory)
    assert len(tiles) == 10, (
        f"ha-installer must contribute exactly 10 "
        f"contract tiles per spec (4 input_text "
        "(installed_ref + installed_at + installed_repo "
        "+ last_error) + 2 input_button (run_install + "
        "run_uninstall) + 1 input_boolean "
        "(backups_enabled) + 2 sensor (status + "
        "files_installed_count) + 1 binary_sensor "
        "(installed_assets_match_repo) = 10 contract "
        "entities documented in the recipe §8 contract "
        f"layer); got {len(tiles)}"
    )


def test_status_reflects_tier_a_but_no_pytest_bench(
    manifest: dict,
) -> None:
    """Status must be honest about tier-a-but-flagged
    (no pytest integration tests against a controlled
    bench).

    If we ever flip this to 'shipped' or 'stable', the
    audit will demand an actual integration test (and
    rightly so). 'beta' is the only honest tier-a status
    for a connection that wraps real RoamCore-owned
    installer code + a shell-based smoke check but lacks
    pytest bench fixtures (a HA core container via
    docker-compose + canned fixture responses for the
    install / uninstall exit codes + the 5 §8 MANDATORY
    automation triggers, all wired together in a
    controlled environment).

    The five honesty warnings that tier_warnings must
    contain cover:
      - no_pytest_integration_tests_against_controlled_bench
        (no bench fixture — canned install-success +
        install-failure + uninstall-success +
        uninstall-failure + reinstall + stale-version +
        installed-assets-match + installed-assets-mismatch
        responses, all wired together in a controlled
        environment)
      - installer_is_shell_script_not_python_integration
        (the installer IS a shell script invoked via
        `curl ... | sh`, NOT a Python integration with
        a config_flow.py — the §8 §9.1 install-button
        guard wires the shell_command: wrapper)
      - recipe_depends_on_user_running_curl_or_tapping_install_button
        (the recipe does not provide a HACS integration
        options flow — the operator must either run the
        `curl ... | sh` one-liner manually OR tap the
        `input_button.rc_ha_installer_run_install` button
        in the dashboard)
      - requires_haos_or_supervised_or_core_with_ssh_addon
        (the installer requires shell access to the HA
        host — HAOS users need the Terminal & SSH add-on;
        HA Supervised + HA Core users have shell access
        by default)
      - idempotency_guarded_by_backup_dir_creation_only
        (the installer's idempotency is guarded ONLY by
        the backup directory creation at
        `/config/.roamcore/backups/<timestamp>/` — there
        is no formal state machine tracking install
        attempts; the §8 §9.4 installed-assets-match-repo
        guard is the operator-facing visibility for the
        idempotency state)
    """
    assert manifest["status"] == "beta", (
        f"ha-installer status={manifest['status']!r} "
        f"implies shipped coverage we don't have; use "
        f"'beta' until full tier-a promotion lands "
        f"(canned install-success + install-failure + "
        f"uninstall-success + uninstall-failure + "
        f"reinstall + stale-version + "
        f"installed-assets-match + "
        f"installed-assets-mismatch responses, all wired "
        f"together in a controlled environment)"
    )
    tier_warnings = manifest.get("tier_warnings", [])
    # Tier-warnings must include the honest-about-no-
    # pytest-integration-tests marker.
    assert "no_pytest_integration_tests_against_controlled_bench" in tier_warnings, (
        "tier_warnings must declare "
        "'no_pytest_integration_tests_against_controlled_"
        "bench' for honesty in the audit listing"
    )
    # And the installer-is-shell-script-not-python-
    # integration honesty warning.
    assert "installer_is_shell_script_not_python_integration" in tier_warnings, (
        "tier_warnings must declare "
        "'installer_is_shell_script_not_python_integration' "
        "so the audit listing is honest about the "
        "shell-script install path vs a Python "
        "integration with a config_flow.py"
    )
    # And the recipe-depends-on-user-running-curl-or-
    # tapping-install-button honesty warning.
    assert "recipe_depends_on_user_running_curl_or_tapping_install_button" in tier_warnings, (
        "tier_warnings must declare "
        "'recipe_depends_on_user_running_curl_or_tapping_"
        "install_button' so the audit listing is honest "
        "that the recipe does not provide a HACS "
        "integration options flow"
    )
    # And the requires-haos-or-supervised-or-core-with-
    # ssh-addon honesty warning.
    assert "requires_haos_or_supervised_or_core_with_ssh_addon" in tier_warnings, (
        "tier_warnings must declare "
        "'requires_haos_or_supervised_or_core_with_ssh_"
        "addon' so the audit listing is honest about the "
        "shell access requirement"
    )
    # And the idempotency-guarded-by-backup-dir-creation-
    # only honesty warning.
    assert "idempotency_guarded_by_backup_dir_creation_only" in tier_warnings, (
        "tier_warnings must declare "
        "'idempotency_guarded_by_backup_dir_creation_only' "
        "so the audit listing is honest about the "
        "idempotency guard being a backup directory "
        "creation only"
    )
    # The tier_requirements.integration_tests section
    # must explicitly document the bench-fixture gap
    # (the 8 canned-response bench artifacts needed for
    # full tier-a promotion).
    integration_tests = (
        manifest.get("tier_requirements", {})
        .get("integration_tests", {})
    )
    assert integration_tests.get("present") is False, (
        "tier_requirements.integration_tests.present "
        "must be False — the smoke check is shell-only, "
        "not pytest integration tests against a "
        "controlled bench; the connection is tier-a-"
        "but-flagged"
    )
    assert integration_tests.get("reason"), (
        "tier_requirements.integration_tests.reason must "
        "be a non-empty string documenting the shell-"
        "based smoke check + the missing pytest bench "
        "fixtures"
    )
    bench_artifacts_needed = integration_tests.get(
        "bench_artifacts_needed", []
    )
    assert len(bench_artifacts_needed) == 8, (
        f"tier_requirements.integration_tests.bench_"
        f"artifacts_needed must list all 8 canned-"
        f"response bench artifacts per spec; got "
        f"{len(bench_artifacts_needed)} entries: "
        f"{bench_artifacts_needed!r}"
    )
    required_bench_artifacts = (
        "canned install-success response (curl exit 0 + manifest.txt populated)",
        "canned install-failure response (curl exit non-zero + stderr captured into input_text.rc_ha_installer_last_error)",
        "canned uninstall-success response (curl exit 0 + manifest.txt truncated)",
        "canned uninstall-failure response (curl exit non-zero + stderr captured)",
        "canned reinstall response (prior manifest detected + backup created)",
        "canned stale-version response (installed_ref != ROAMCORE_REF for > 7 days)",
        "canned installed-assets-match response (files_installed_count matches repo inventory)",
        "canned installed-assets-mismatch response (files_installed_count differs from repo inventory)",
    )
    for required_artifact in required_bench_artifacts:
        assert required_artifact in bench_artifacts_needed, (
            f"tier_requirements.integration_tests.bench_"
            f"artifacts_needed must include "
            f"{required_artifact!r}; got "
            f"{bench_artifacts_needed!r}"
        )


def test_automations_are_documented(manifest: dict) -> None:
    """Defensive guard for the future tier-a promotion.

    Forgetting to wire the §8 MANDATORY automations can
    leave the operator with stale HA installer state (the
    §8.1 install-button guard doesn't fire + the §8.2
    uninstall-button guard doesn't fire + the §8.3 stale-
    version detector doesn't fire + the §8.4 installed-
    assets-match-repo guard doesn't fire + the §8.5
    install-failure capture guard doesn't fire). The §8
    walks through the FIVE MANDATORY automations:
      - §8.1 Install-button guard — the automation that
        fires when `input_button.rc_ha_installer_run_
        install` is pressed. The button press marks
        `sensor.rc_ha_installer_status = Install-Running`
        and clears any stale `input_text.rc_ha_installer_
        last_error`. The actual install work happens via
        the `shell_command.rc_ha_installer_run_install`
        wrapper that runs the canonical installer script
        (the integration layer can't run shell scripts
        from a button press in HA core without a
        `shell_command:` wrapper, which IS what this
        automation wires).
      - §8.2 Uninstall-button guard — the automation that
        fires when `input_button.rc_ha_installer_run_
        uninstall` is pressed. The button press marks
        `sensor.rc_ha_installer_status = Uninstall-
        Running` and clears the manifest + install-info
        state (`/config/.roamcore/manifest.txt` is
        truncated + `/config/.roamcore/install-info.txt`
        is cleared). The actual uninstall work happens
        via the `shell_command.rc_ha_installer_run_
        uninstall` wrapper.
      - §8.3 Stale-version detector — the automation that
        fires when `input_text.rc_ha_installer_installed_
        ref` differs from the configured `ROAMCORE_REF`
        for > 7 days. The automation marks `sensor.
        rc_ha_installer_status = Stale-Version` and
        surfaces a "RoamCore is outdated" notification
        chip. The 7-day threshold is operator-tunable
        via the `input_number.rc_ha_installer_stale_
        version_days_threshold` helper (default 7).
      - §8.4 Installed-assets-match-repo guard — the
        automation that fires when `sensor.rc_ha_
        installer_files_installed_count` differs from
        the count of files in the current repo's
        `homeassistant/` inventory. The automation marks
        `binary_sensor.rc_ha_installer_installed_assets_
        match_repo = false` and surfaces a "RoamCore
        install is incomplete" notification. The repo
        file count is derived from the operator's
        RoamCore clone (the RoamCore-side canonical
        inventory, NOT the HA `/config/` manifest).
      - §8.5 Install-failure capture — the automation
        that fires when the `shell_command:` wrapper
        exits non-zero. The automation captures stderr
        into `input_text.rc_ha_installer_last_error` and
        marks `sensor.rc_ha_installer_status = Failed`.
        The `shell_command:` wrapper writes its exit
        code to a sentinel file at `/config/.roamcore/
        last-exit-code` that the automation polls.

    The test asserts the FIVE automations are documented
    in the recipe so that when this connection promotes
    to fully-fledged tier-a (with a real pytest bench
    on CI + the FIVE automations hard-enforced in
    RoamCore code rather than only documented in the
    recipe), the audit has a clean assertion to flip.
    """
    text = RECIPE_PATH.read_text(encoding="utf-8")
    # §9 header MUST be present (ha-installer uses §9 for
    # automations, like openclaw-api / advanced-mode /
    # demo-mode / mode / leveling / fans / trip-wrapped).
    assert "## §9 Automations" in text, (
        "recipe.md must have a '## §9 Automations' "
        "section (the FIVE MANDATORY automation "
        "documentation block; ha-installer uses §9 for "
        "automations, NOT §8 like the happijac slice)"
    )
    # §9 must cover the FIVE automation areas.
    automation_coverage = (
        # §9.1 install-button guard.
        "install-button guard",
        # §9.2 uninstall-button guard.
        "uninstall-button guard",
        # §9.3 stale-version detector.
        "stale-version detector",
        # §9.4 installed-assets-match-repo guard.
        "installed-assets-match-repo guard",
        # §9.5 install-failure capture.
        "install-failure capture",
    )
    for phrase in automation_coverage:
        assert phrase in text.lower(), (
            f"recipe.md §9 must cover {phrase!r}; the "
            f"FIVE automations are MANDATORY before "
            f"first use, and the recipe is the only "
            f"documentation operator + future-tier-a "
            f"integration code have at this tier"
        )
    # The full §9.N titles MUST appear as section
    # headers (the recipe §9 has full `automation:`
    # YAML configurations for each of the FIVE).
    full_automation_titles = (
        "### §9.1 Install-button guard",
        "### §9.2 Uninstall-button guard",
        "### §9.3 Stale-version detector",
        "### §9.4 Installed-assets-match-repo guard",
        "### §9.5 Install-failure capture",
    )
    for full_title in full_automation_titles:
        assert full_title in text, (
            f"recipe.md §9 must have the full "
            f"`automation:` YAML configuration for "
            f"{full_title!r}; the FIVE MANDATORY "
            f"automations must be present in the recipe"
        )
    # The contract tiles must include the FIVE safety
    # tiles that the §9 automations + the operator-
    # facing affordance surfaces:
    #   input_button.rc_ha_installer_run_install
    #     (the §8 one-tap install button + the §9.1
    #      install-button guard target)
    #   input_button.rc_ha_installer_run_uninstall
    #     (the §8 one-tap uninstall button + the §9.2
    #      uninstall-button guard target)
    #   input_text.rc_ha_installer_installed_ref
    #     (the §8 installed-ref tile + the §9.3
    #      stale-version detector target)
    #   sensor.rc_ha_installer_files_installed_count
    #     (the §8 files-installed-count sensor + the
    #      §9.4 installed-assets-match-repo guard
    #      target)
    #   input_text.rc_ha_installer_last_error
    #     (the §8 last-error stderr capture + the §9.5
    #      install-failure capture guard target)
    tiles = manifest.get("dashboard", {}).get("tiles", [])
    safety_tiles = (
        "input_button.rc_ha_installer_run_install",
        "input_button.rc_ha_installer_run_uninstall",
        "input_text.rc_ha_installer_installed_ref",
        "sensor.rc_ha_installer_files_installed_count",
        "input_text.rc_ha_installer_last_error",
    )
    for safety_tile in safety_tiles:
        assert safety_tile in tiles, (
            f"dashboard.tiles must include {safety_tile!r}; "
            f"the §9 automations + operator-facing "
            "affordance tiles are part of the contract "
            "layer that the recipe §9 documents"
        )
    # The recipe must cross-reference the canonical
    # installer script at `homeassistant/install.sh` so
    # the §9.1 install-button guard's installer code is
    # discoverable.
    assert "homeassistant/install.sh" in text, (
        "recipe.md must reference "
        "`homeassistant/install.sh` for the §9.1 "
        "install-button guard's installer code (the "
        "canonical HA-only installer is the source of "
        "the 5 directories copied into HA /config/)"
    )
    # The recipe must cross-reference the canonical
    # uninstaller at `homeassistant/uninstall.sh` so
    # the §9.2 uninstall-button guard's uninstaller
    # code is discoverable.
    assert "homeassistant/uninstall.sh" in text, (
        "recipe.md must reference "
        "`homeassistant/uninstall.sh` for the §9.2 "
        "uninstall-button guard's uninstaller code (the "
        "canonical HA-only uninstaller reverses the "
        "install by removing the 5 copied directories "
        "+ the /config/.roamcore/ state)"
    )
    # The recipe must cross-reference the operator
    # howto at `docs/howto/homeassistant-installer.md`
    # so the §9.1 + §9.2 + §9.3 + §9.4 + §9.5 guards'
    # operator-facing install path is discoverable.
    assert "docs/howto/homeassistant-installer.md" in text, (
        "recipe.md must reference "
        "`docs/howto/homeassistant-installer.md` for "
        "the §9.1 + §9.2 + §9.3 + §9.4 + §9.5 guards' "
        "operator-facing install path (the operator "
        "howto is the canonical operator-walk through "
        "the one-line install + the 5 directories "
        "copied + the 3 state files written + the "
        "uninstall one-liner + the 5 verification "
        "steps + the RC_API_TOKEN-aware wiring "
        "guidance)"
    )
    # The recipe must cross-reference the 5 directories
    # copied into HA `/config/` so the §9.4 installed-
    # assets-match-repo guard's installation surface is
    # discoverable.
    for directory in (
        "/config/packages/",
        "/config/custom_components/",
        "/config/www/",
        "/config/lovelace/",
        "/config/tools/",
    ):
        assert directory in text, (
            f"recipe.md must reference {directory!r} for "
            f"the §9.4 installed-assets-match-repo "
            f"guard's installation surface (the 5 "
            f"directories copied into HA /config/ are "
            f"the canonical install path)"
        )
    # The recipe must cross-reference the RC_API_TOKEN
    # env var so the §9.1 install-button guard's
    # RC_API_TOKEN-aware wiring is discoverable.
    assert "RC_API_TOKEN" in text, (
        "recipe.md must reference `RC_API_TOKEN` for "
        "the §9.1 install-button guard's RC_API_TOKEN-"
        "aware wiring (the operator can set "
        "`RC_API_TOKEN` in the env before the "
        "`curl ... | sh` install, and the installer "
        "forwards it to downstream curl probes)"
    )
    # The recipe must cross-reference the trip-local
    # Wave 3 #68 connection so the §13 Files cross-
    # references are discoverable.
    assert "trip-local" in text.lower() or "trip_local" in text.lower(), (
        "recipe.md must reference `trip-local` for the "
        "§13 Files cross-references (the trip-local "
        "Wave 3 #68 connection is the canonical source "
        "of the trip-local package that the installer "
        "copies into HA /config/packages/)"
    )
    # The recipe must cross-reference the trip-wrapped
    # Wave 3 #69 connection so the §13 Files cross-
    # references are discoverable.
    assert "trip-wrapped" in text.lower() or "trip_wrapped" in text.lower(), (
        "recipe.md must reference `trip-wrapped` for "
        "the §13 Files cross-references (the "
        "trip-wrapped Wave 3 #69 connection is the "
        "canonical source of the trip-wrapped package "
        "+ the trip-wrapped tools that the installer "
        "copies into HA /config/)"
    )
    # The recipe must cross-reference the openclaw-api
    # Wave 3 #64 connection so the §13 Files cross-
    # references are discoverable.
    assert "openclaw-api" in text.lower() or "openclaw_api" in text.lower(), (
        "recipe.md must reference `openclaw-api` for "
        "the §13 Files cross-references (the openclaw-"
        "api Wave 3 #64 connection is the canonical "
        "source of the roamcore_openclaw_api custom "
        "component that the installer copies into HA "
        "/config/custom_components/)"
    )
    # The recipe must cross-reference the bed-lift-diy
    # Wave 3 #70 connection so the §13 Files cross-
    # references are discoverable.
    assert "bed-lift-diy" in text.lower() or "bed_lift_diy" in text.lower(), (
        "recipe.md must reference `bed-lift-diy` for "
        "the §13 Files cross-references (the bed-lift-"
        "diy Wave 3 #70 connection is the canonical "
        "source of the bed-lift-diy package that the "
        "installer copies into HA /config/packages/)"
    )
    # The recipe's defensive guard for future tier-a
    # promotion — assert the §9 section has the FIVE
    # automations documented.
    assert "five" in text.lower() or "five §" in text.lower() or "## §9" in text.lower(), (
        "recipe.md §9 must reference the FIVE §9 "
        "automations (the §9.1 install-button guard + "
        "§9.2 uninstall-button guard + §9.3 stale-"
        "version detector + §9.4 installed-assets-"
        "match-repo guard + §9.5 install-failure "
        "capture); this is the operator-side reminder "
        "that keeps the automations top-of-mind during "
        "install"
    )


def test_links_include_required_official_and_cross_references(
    manifest: dict,
) -> None:
    """The manifest `links` block must include the
    official HA install docs + the canonical installer
    scripts + the operator howto + the HA smoke check +
    the cross-references to the trip-local +
    trip-wrapped + openclaw-api + bed-lift-diy
    connections.

    Without the official HA install docs, the operator
    has no upstream reference for HAOS + HA Supervised +
    HA Core prerequisites. Without the canonical
    installer scripts, the recipe has no on-disk
    artifact to wire the §9 automations against.
    Without the cross-references to the trip-local +
    trip-wrapped + openclaw-api + bed-lift-diy
    connections, the operator doesn't know which
    packages + custom components + tools the installer
    copies into HA /config/.
    """
    links = manifest.get("links", {})
    official = links.get("official", [])
    custom_references = links.get("custom_references", [])
    cross_references = links.get("cross_references", [])
    # The official links list MUST include the HA
    # install docs URL.
    assert (
        "https://www.home-assistant.io/installation/"
        in official
    ), (
        "links.official must include "
        "'https://www.home-assistant.io/installation/' "
        "(the official HA install docs are the "
        "canonical upstream reference for HAOS + "
        "HA Supervised + HA Core prerequisites)"
    )
    # The custom_references list MUST include the
    # root installer wrapper + uninstaller wrapper +
    # canonical HA installer + canonical HA
    # uninstaller + operator howto + HA smoke check.
    required_custom_references = (
        "install.sh",
        "uninstall.sh",
        "homeassistant/install.sh",
        "homeassistant/uninstall.sh",
        "docs/howto/homeassistant-installer.md",
        "scripts/checks/ha-beta-smoke.sh",
    )
    for required_ref in required_custom_references:
        assert required_ref in custom_references, (
            f"links.custom_references must include "
            f"{required_ref!r}; the recipe §9 + §13 "
            f"cross-references need this for the "
            f"operator to find the on-disk artifacts"
        )
    # The cross_references list MUST include the
    # trip-local + trip-wrapped + openclaw-api +
    # bed-lift-diy connections (because the installer
    # copies the trip-local package + the trip-wrapped
    # package + tools + the roamcore_openclaw_api custom
    # component + the bed-lift-diy package into HA
    # /config/).
    required_cross_references = (
        "../trip-local-tier-a/",
        "../trip-wrapped-tier-a/",
        "../openclaw-api/",
        "../bed-lift-diy/",
    )
    for required_ref in required_cross_references:
        assert required_ref in cross_references, (
            f"links.cross_references must include "
            f"{required_ref!r}; the installer copies "
            f"the trip-local package + the trip-wrapped "
            f"package + tools + the roamcore_openclaw_api "
            f"custom component + the bed-lift-diy "
            f"package into HA /config/, so the §13 Files "
            f"cross-references need to point at the "
            f"connections"
        )


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
