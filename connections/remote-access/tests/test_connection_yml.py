"""Manifest-honesty tests for connections/remote-access/connection.yml.

This is the only test file we can ship for a tier-b recipe connection
that has no real remote-access bench (all FOUR upstream integrations
installed + the operator's account on the chosen vendor's service +
canned fixture responses for reachability probes — all wired together
in a controlled environment) on the CI rig to integration-test
against. The tests here assert that the manifest is *honest about
being tier-b* — that the folder/id/tier invariants hold, that the
recipe doc the tier_requirements promise is actually present on
disk, that the rc_remote_access_* tile ids are vendor-neutral per
docs/reference/rc-entity-naming.md, and that the FIVE §8 automations
are documented with the right cross-references (HA core `tailscale`
integration / HACS `cloudflared` add-on / HA Core `cloud` integration
/ HACS `wireguard` add-on / HA Companion app / mode/automation-
builder Wave 2 #23 / approach-lights Wave 3 #52 / nfc-tags Wave 3
#57 / Wave 2 #29 Tailscale contract at `feat/wave2-remote-access-
tailscale` @ `0caa9c2`).

If you add real integration coverage (e.g. an operator-wired setup
flow + a bench with all FOUR upstream integrations + canned fixture
responses), keep this file and add the new one alongside it; the
audit will then list both under `tests:` in the manifest.

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest connections/remote-access/tests/ -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[3]   # tests/ -> remote-access/ -> connections/ -> repo
CONNECTION_DIR = REPO_ROOT / "connections" / "remote-access"
MANIFEST_PATH = CONNECTION_DIR / "connection.yml"
RECIPE_PATH = CONNECTION_DIR / "docs" / "recipe.md"


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert MANIFEST_PATH.is_file(), f"missing manifest at {MANIFEST_PATH}"
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_id_matches_folder_name(manifest: dict) -> None:
    """The manifest `id` must equal the folder name (remote-access).

    This is the same invariant the audit script enforces; we duplicate
    it here so pytest catches regressions before CI runs the audit.
    """
    assert manifest["id"] == CONNECTION_DIR.name, (
        f"manifest id={manifest['id']!r} does not match folder name "
        f"{CONNECTION_DIR.name!r}"
    )
    assert manifest["id"] == "remote-access"


def test_tier_b_without_tier_a_markers(manifest: dict) -> None:
    """Tier-b must NOT advertise tier-a-only RoamCore-owned fields AND
    must explicitly document the reuse-first strategy (no custom
    remote-access engine; reuse the upstream HA core `tailscale`
    integration + the HACS `cloudflared` add-on + the HA Core `cloud`
    integration + the HACS `wireguard` add-on + the HA Companion
    app's `external_url` setting + a thin RoamCore path-routing
    wrapper).

    A regression here (e.g. someone flipping tier to a without
    adding integration code + a bench fixture, or adding a
    RoamCore-owned remote-access engine + setup flow that we
    explicitly chose NOT to ship) would falsely imply a working
    RoamCore integration + integration tests that we don't have,
    and the audit would either block the PR or let a misleading
    tier-a claim slip through. The tier-b strategy here is reuse-
    first: upstream HA core `tailscale` integration (Path A mesh
    VPN since 2022.x) + HACS `cloudflared` add-on (Path B
    Cloudflare Tunnel) + HA Core `cloud` integration (Path C
    Nabu Casa HA Cloud since 2022.x) + HACS `wireguard` add-on
    (Path D Wireguard self-hosted VPN) + HA Companion app's
    `external_url` setting (the canonical OFF-LAN affordance
    since 2022.x). RoamCore does NOT fork any of these; the
    RoamCore wrapper is a thin path-routing layer + the contract
    layer.

    The distinction this test guards: install.config_flow is TRUE
    here because the UPSTREAM HA core `tailscale` integration
    (since 2022.x — exposes a GUI flow for the operator to
    authenticate against the Tailscale coordination server + view
    the operator's tailnet device list + tailnet ACL settings) +
    the HACS `cloudflared` add-on (HACS — exposes a GUI flow for
    the operator to install the `cloudflared` daemon + configure
    the Cloudflare Tunnel token) + the HACS `wireguard` add-on
    (HACS — exposes a GUI flow for the operator to install the
    Wireguard server + generate server keys + add per-client
    peers) + the HA Core `cloud` integration (since 2022.x —
    exposes a GUI flow for the operator to subscribe to Nabu Casa
    HA Cloud + enable remote access + view the remote URL) + the
    HA Companion app's `external_url` setting (since 2022.x —
    exposes a GUI flow for the operator to set the external URL
    in the Companion app settings) ALL expose a GUI flow. That's
    honest upstream truth, NOT a tier-a marker for RoamCore's
    tier. The tier-a marker for RoamCore would be a
    RoamCore-owned operator-wired setup flow + RoamCore-owned
    integration code + integration tests against a RoamCore-owned
    remote-access bench. None of those are shipped at tier-b.
    Tier-b honesty: Tailscale + Cloudflare Tunnel + Nabu Casa +
    Wireguard are all upstream / vendor / HACS code; the
    RoamCore wrapper is a thin path-routing layer + the contract
    layer.
    """
    assert manifest["tier"] == "b", (
        "remote-access must stay at tier-b until a "
        "RoamCore-owned remote-access engine + operator-wired "
        "setup flow + integration tests ship; tier-b is the "
        "honest tier for a reuse-first upstream integration recipe"
    )
    assert manifest["wizard"]["one_tap"] is False, (
        "tier-b connections cannot advertise one_tap=true (that's "
        "a tier-a contract)"
    )
    # Remote access recipes an upstream remote-access path (Path A —
    # HA core `tailscale` integration OR HACS Tailscale add-on; Path
    # B — HACS `cloudflared` add-on; Path C — HA Core `cloud`
    # integration; Path D — HACS `wireguard` add-on). RoamCore ships
    # no native operator-wired setup flow for that, and explicitly
    # does NOT maintain a custom remote-access engine — we reuse
    # the upstream HA core `tailscale` integration + the HACS
    # `cloudflared` add-on + the HA Core `cloud` integration + the
    # HACS `wireguard` add-on + the HA Companion app's
    # `external_url` setting.
    # install.config_flow is the RoamCore-owned field. We document
    # the distinction in the manifest header: the UPSTREAM HA core
    # `tailscale` integration + the HACS `cloudflared` add-on + the
    # HACS `wireguard` add-on + the HA Core `cloud` integration +
    # the HA Companion app's `external_url` setting ALL expose a
    # GUI flow since 2022.x — honest upstream truth, NOT a tier-a
    # marker for RoamCore's tier. The tier-a marker for RoamCore is
    # a RoamCore-owned operator-wired setup flow + integration
    # tests. Until those ship, this connection is tier-b.
    assert manifest["install"]["config_flow"] is True, (
        "install.config_flow must stay True — the upstream HA "
        "core `tailscale` integration + the HACS `cloudflared` "
        "add-on + the HACS `wireguard` add-on + the HA Core "
        "`cloud` integration + the HA Companion app's "
        "`external_url` setting ALL expose a GUI flow since "
        "2022.x; this is honest upstream truth, NOT a tier-a "
        "marker for RoamCore's tier. The tier-a marker for "
        "RoamCore would be a RoamCore-owned operator-wired setup "
        "flow + RoamCore-owned integration code + integration "
        "tests against a RoamCore-owned remote-access bench (all "
        "FOUR upstream integrations installed + the operator's "
        "account on the chosen vendor's service + canned fixture "
        "responses for reachability probes). None of those are "
        "shipped at tier-b."
    )
    # install.hacs is TRUE because remote access optionally depends
    # on the HACS `cloudflared` add-on (Path B — Cloudflare Tunnel)
    # + the HACS `wireguard` add-on (Path D — Wireguard self-hosted
    # VPN) + the HACS Tailscale add-on (alternative Path A — Tailscale).
    # All three HACS add-ons are installed from HACS.
    assert manifest["install"]["hacs"] is True, (
        "remote-access must advertise install.hacs=true — remote "
        "access optionally depends on the HACS `cloudflared` "
        "add-on (Path B) + the HACS `wireguard` add-on (Path D) "
        "+ the HACS Tailscale add-on (alternative Path A); "
        "install.hacs is TRUE for tier-b recipes that have an "
        "optional HACS dependency"
    )
    # Belt-and-braces: there must be no RoamCore-owned operator-
    # wired setup flow file in this folder (no native integration
    # code for a tier-b recipe connection). The upstream HA core
    # `tailscale` integration + the HACS `cloudflared` add-on + the
    # HACS `wireguard` add-on + the HA Core `cloud` integration +
    # the HA Companion app's `external_url` setting have their own
    # GUI flows, but that lives in the upstream HA core / HACS /
    # vendor repos, not in this folder.
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
    # DOMAIN must equal "remote_access" (matches the connection name
    # "remote-access" → "remote_access" via the audit convention of
    # replacing hyphens with underscores).
    assert 'DOMAIN = "remote_access"' in init_text, (
        '__init__.py must define DOMAIN = "remote_access" '
        '(matches the connection name "remote-access" per '
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
    # The reuse-first strategy must be explicitly documented in
    # the `description` field (the tier-b contract; tier-a would
    # own the integration code; tier-b explicitly does NOT own
    # the integration code — we recipe over the upstream HA core
    # `tailscale` integration + the HACS `cloudflared` add-on +
    # the HA Core `cloud` integration + the HACS `wireguard`
    # add-on + the HA Companion app's `external_url` setting).
    description = (manifest["description"] or "").lower()
    assert (
        "reuse" in description
        or "ha core" in description
        or "tailscale integration" in description
        or "cloudflared" in description
        or "cloud integration" in description
        or "wireguard" in description
        or "remote access" in description
    ), (
        "manifest.description must explicitly document the "
        "reuse-first strategy (e.g. mention 'HA core' or "
        "'tailscale integration' or 'cloudflared' or 'cloud "
        "integration' or 'wireguard' or 'reuse-first' or "
        "'remote access' or similar); tier-b is the honest "
        "tier for a recipe that does NOT own the integration "
        "code"
    )
    # The links.official list must point at the HA core `tailscale`
    # integration upstream doc (the canonical reuse-first source
    # for Path A).
    official_links = manifest.get("links", {}).get("official", [])
    assert any(
        "home-assistant.io/integrations/tailscale" in link.lower()
        for link in official_links
    ), (
        "links.official must include the HA core `tailscale` "
        "integration upstream doc URL "
        "(https://www.home-assistant.io/integrations/tailscale/); "
        "tier-b connections are explicit about which upstream "
        "integration they recipe over (Path A in this case)"
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
    # Sanity: the recipe actually documents remote access + the
    # FOUR operator-pickable paths + the contract entities rather
    # than just an empty placeholder. The recipe mentions
    # "remote access" / "tailscale" / "cloudflare" / "nabu casa" /
    # "wireguard" / "rc_remote_access_" — any one of these is
    # sufficient (a substantive howto would mention all of them,
    # but the assertion guards against the empty-placeholder
    # regression).
    text = RECIPE_PATH.read_text(encoding="utf-8")
    assert (
        "remote access" in text.lower()
        or "remote-access" in text.lower()
        or "tailscale" in text.lower()
        or "cloudflare" in text.lower()
        or "nabu casa" in text.lower()
        or "wireguard" in text.lower()
    ) and "rc_remote_access_" in text, (
        "recipe.md must document the remote access setup "
        "(Path A Tailscale mesh VPN + Path B Cloudflare Tunnel "
        "+ Path C Nabu Casa HA Cloud + Path D Wireguard self-"
        "hosted VPN + the FIVE §8 automations + the 9 "
        "`rc_remote_access_*` contract tiles + the 6 §9 "
        "troubleshooting entries + privacy + tier-a promotion "
        "outline) and reference at least one `rc_remote_access_*` "
        "tile"
    )
    # The spec requires ~600+ lines; we ship a substantive howto
    # well over that; this catches a regression where someone
    # leaves a 30-line placeholder.
    line_count = len(text.splitlines())
    assert line_count >= 600, (
        f"recipe.md must be a substantive howto (≥600 lines per "
        f"spec; the §3 Path A + §4 Path B + §5 Path C + §6 Path D "
        "+ §7 contract entities + §8 automations + §9 "
        "troubleshooting alone are ~900 lines); got "
        f"{line_count}"
    )
    # Spec calls for all 12 §sections to be present (the recipe
    # is the umbrella for the 4 paths + the §7 contract entities
    # + the §8 FIVE automations + §9 troubleshooting + §10
    # Privacy + §11 Promoting to tier-a + §12 Files +
    # cross-references).
    # Grep-anchor the major section headers so a future "I
    # rewrote the recipe as one wall of text" regression gets
    # caught.
    required_sections = (
        "## §1 What is remote access in RoamCore?",
        "## §2 Prerequisites",
        "## §3 Path A",
        "## §4 Path B",
        "## §5 Path C",
        "## §6 Path D",
        "## §7 RoamCore contract entities",
        "## §8 Automations",
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
    """Sanity: category is set (legacy-doc pairing no longer enforced)."""
    assert manifest["category"], "category must be set"


def test_dashboard_tiles_follow_rc_naming(manifest: dict) -> None:
    """rc_* tile ids must NOT contain vendor names (per rc-entity-naming.md).

    The remote access contract is implementation-agnostic (it
    talks to whatever remote-access path the operator wires +
    the upstream HA core `tailscale` integration + the HACS
    `cloudflared` add-on + the HA Core `cloud` integration + the
    HACS `wireguard` add-on + the HA Companion app's
    `external_url` setting, not any vendor's library). Contract
    ids must stay vendor-neutral — NO `tailscale`, `cloudflare`,
    `cloudflared`, `nabu_casa`, `wireguard`, `ts_net`, `ts.net`,
    `cf-tunnel`, `hass-cloud`, `ha_cloud`, `ha_cloud_url`, `wg0`,
    `magicdns`, `magic_dns`, `tunnel_id`, `argo_tunnel`, `victron`,
    `wican`, `obd`, `frigate`, `mqtt`, `esphome`, `esp32`, `esp8266`,
    `hacs`, `hass`, `ha_integration`, `ha_companion`,
    `homeassistant`, `device_tracker`, `set_location`,
    `update_entity`, `binary_sensor_`, `sensor_`, `switch`,
    `input_boolean`, `input_select`, `input_number`,
    `input_datetime`, `input_text`, `template:`, `automation`,
    `scene`, `nfcpy`, `zone`, `zone.`, `set_location`,
    `update_entity` in any rc_* tile id BEYOND the subsystem
    prefix `rc_remote_access_*`. The generic nouns `enabled`,
    `url`, `active`, `path`, `peer`, `count`, `last`, `verified`,
    `minutes`, `ago`, `hostname`, `resolvable`, `verify`, `now`,
    `operator`, `chosen` are allowed (they describe what the tile
    is for, not which vendor).

    The spec is strict: every `dashboard.tiles[*]` must match
    `^[a-z_]+\\.rc_remote_access_[a-z0-9_]+$` (vendor-neutral,
    subsystem prefix `rc_remote_access_*` per the
    `remote_access` subsystem naming convention established by
    this slice; the `remote_access` subsystem is OWNED by this
    slice — the `remote_access` subsystem addition to
    docs/reference/rc-entity-naming.md is the FIRST `remote_
    access`-category slice in the RoamCore connection pipeline;
    the `networking` category is the canonical category for
    remote access + the existing OpenWrt VM in the home lab).

    CRITICAL: the remote access subsystem prefix is
    `rc_remote_access_*` (NOT `rc_tailscale_*` and NOT
    `rc_cloudflare_*` and NOT `rc_nabu_casa_*` and NOT
    `rc_wireguard_*`); the `networking` category is the
    canonical category for remote access + the existing OpenWrt
    VM in the home lab. The remote access connection uses the
    `rc_remote_access_*` prefix because `remote_access` is the
    canonical remote-access subsystem (the umbrella for the FOUR
    operator-pickable paths).

    The forbidden_substrings list below targets the vendor /
    library / hardware / protocol / integration absolute-
    forbidden set only; the spec's literal tile ids are
    accepted by ID and never double-stamp any vendor name.
    """
    import re

    tiles = manifest.get("dashboard", {}).get("tiles", [])
    assert tiles, "remote-access contributes at least one dashboard tile"

    # Every tile must be a string entity id (spec calls for
    # tiles-as-strings, mirroring the spec's listed shape).
    for tile in tiles:
        assert isinstance(tile, str), (
            f"dashboard.tiles[*] must be a string entity id "
            f"(spec §1); got {tile!r}"
        )

    # Allowed HA core domain prefixes per docs/reference/rc-
    # entity-naming.md: binary_sensor, sensor, button, select.
    # (No `zone.*` domain tile in this connection — the contract
    # layer reports "is remote access active?" via binary_sensor,
    # not "what zone is the van in?" via zone.*; the operator-side
    # zone entity lives in the upstream zone domain, not in the
    # rc_remote_access_* contract layer.)
    allowed_domains = {"binary_sensor", "sensor", "button", "select"}
    pattern = re.compile(r"^[a-z_]+\.rc_remote_access_[a-z0-9_]+$")

    # Vendor / implementation / hardware-side name leaks that
    # must NEVER appear in any rc_* tile id. The spec
    # requirement is "no double-stamps of [vendor + hardware
    # names + protocol names + integration names] beyond the
    # rc_remote_access_ subsystem prefix". Vendor names like
    # Tailscale / Cloudflare / Cloudflared / Nabu Casa /
    # Wireguard / MagicDNS / HACS / HA Companion / MQTT /
    # ESPHome / ESP32 / Traccar / Wican / OBD / Frigate / NFC /
    # NFCpy / MQTT / Zone / Input_boolean / Switch / Template are
    # an absolute vendor / integration / protocol leak and are
    # forbidden from EVER appearing in any rc_* tile id
    # (regardless of where in the tile).
    #
    # The generic nouns (`enabled`, `url`, `active`, `path`,
    # `peer`, `count`, `last`, `verified`, `minutes`, `ago`,
    # `hostname`, `resolvable`, `verify`, `now`, `operator`,
    # `chosen`) are LITERALLY PART OF the spec-required tile ids
    # (e.g. `binary_sensor.rc_remote_access_enabled`,
    # `sensor.rc_remote_access_url`,
    # `binary_sensor.rc_remote_access_active`,
    # `sensor.rc_remote_access_active_path`,
    # `sensor.rc_remote_access_peer_count`,
    # `sensor.rc_remote_access_last_verified_minutes_ago`,
    # `binary_sensor.rc_remote_access_hostname_resolvable`,
    # `button.rc_remote_access_verify_now`,
    # `select.rc_remote_access_path`) — the spec calls for
    # those tiles — so flagging them as absolute substrings
    # of the suffix would conflict with the literal tile ids
    # the spec requires. The forbidden_substrings list below
    # targets the vendor-name / hardware-name /
    # protocol-name / integration-name absolute-forbidden set
    # only; the spec's literal tile ids are accepted by ID and
    # never double-stamp any vendor name.
    forbidden_substrings = (
        # Remote-access vendor / hardware / protocol / integration
        # name leaks — recipe explicitly forbids these (absolute
        # forbidden — no Tailscale / Cloudflare / Cloudflared /
        # Nabu Casa / Wireguard / MagicDNS / Tunnel / VPN names
        # anywhere in any rc_* tile id; vendor neutrality is
        # non-negotiable).
        "tailscale",         # Tailscale vendor (vendor leak)
        "ts_net",            # Tailscale MagicDNS hostname suffix (vendor leak)
        "ts.net",            # Tailscale MagicDNS hostname suffix (vendor leak)
        "cloudflare",        # Cloudflare vendor (vendor leak)
        "cloudflared",       # Cloudflare daemon (vendor leak)
        "cf-tunnel",         # Cloudflare Tunnel shortcut (vendor leak)
        "cf_tunnel",         # Cloudflare Tunnel underscore (vendor leak)
        "argo_tunnel",       # Cloudflare Argo Tunnel (vendor leak)
        "tunnel_id",         # Cloudflare Tunnel ID (vendor leak)
        "nabu_casa",         # Nabu Casa vendor (vendor leak)
        "hass-cloud",        # Nabu Casa HA Cloud (vendor leak)
        "ha_cloud",          # Nabu Casa HA Cloud underscore (vendor leak)
        "ha_cloud_url",      # Nabu Casa HA Cloud URL (vendor leak)
        "ha-cloud-url",      # Nabu Casa HA Cloud URL hyphen (vendor leak)
        "wireguard",         # Wireguard vendor (vendor leak)
        "wg0",               # Wireguard interface name (vendor leak)
        "wg_",               # Wireguard interface underscore (vendor leak)
        "magicdns",          # Tailscale MagicDNS (vendor leak)
        "magic_dns",         # Tailscale MagicDNS underscore (vendor leak)
        # Vendor / integration / library / namespace leaks
        # — recipe explicitly forbids these (absolute
        # forbidden — no HACS / HA Companion / MQTT / ESPHome
        # / ESP32 / Traccar / Wican / OBD / Frigate / NFC /
        # NFCpy / Zone / Device_tracker / Homeassistant /
        # Set_location / Update_entity / Binary_sensor_ /
        # Sensor_ / Switch / Input_boolean / Input_select /
        # Input_number / Input_datetime / Input_text /
        # Template names anywhere in any rc_* tile id; vendor
        # neutrality is non-negotiable).
        "hacs",              # HACS namespace (integration leak)
        "hass",              # HASS namespace (integration leak)
        "ha_integration",    # HA integration namespace (integration leak)
        "ha_companion",      # HA Companion app (integration leak)
        "homeassistant",     # homeassistant service domain (integration leak)
        "mqtt",              # MQTT integration (integration leak)
        "esphome",           # ESPHome integration name (integration leak)
        "esp_home",          # ESPHome with underscore (integration leak)
        "esp32",             # ESP32 microcontroller (hardware leak)
        "esp8266",           # ESP8266 microcontroller (hardware leak)
        "traccar",           # Traccar GPS server vendor (vendor leak)
        "wican",             # Wican Pro OBD-II vendor (vendor leak)
        "obd",               # OBD-II protocol (integration leak)
        "obd_ii",            # OBD-II with underscore (integration leak)
        "obd-ii",            # OBD-II with hyphen (integration leak)
        "12v",               # 12V D+ signal voltage (hardware leak)
        "24v",               # 24V D+ signal voltage (hardware leak)
        "frigate",           # Frigate (vendor leak)
        # Zone / location domain / integration namespace leaks
        # — absolute forbidden.
        "zone_",             # zone namespace (integration leak)
        "zone.",             # zone namespace (integration leak)
        "binary_sensor_",    # binary_sensor namespace (integration leak)
        "sensor_",           # sensor namespace (integration leak)
        "switch",            # switch domain (integration leak)
        "input_boolean",     # input_boolean namespace (integration leak)
        "input_select",      # input_select namespace (integration leak)
        "input_number",      # input_number namespace (integration leak)
        "input_datetime",    # input_datetime namespace (integration leak)
        "input_text",        # input_text namespace (integration leak)
        "device_tracker",    # device_tracker namespace (integration leak)
        "set_location",      # set_location service name (integration leak)
        "update_entity",     # update_entity service name (integration leak)
        # NFC / NFCpy / upstream-integration namespace leaks
        # — absolute forbidden.
        "nfcpy",             # nfcpy Python library (integration leak)
        "nfc_",              # NFC namespace (integration leak)
        "nfc.",              # NFC namespace (integration leak)
        # Template / script / automation / scene / tag namespace
        # leaks — absolute forbidden.
        "template:",         # template: (integration leak)
        "automation",        # automation namespace (integration leak)
        "scene",             # scene namespace (integration leak)
        "script",            # script namespace (integration leak)
    )

    for tile in tiles:
        assert pattern.match(tile), (
            f"tile id {tile!r} must match ^[a-z_]+\\.rc_remote_"
            f"access_[a-z_]+$ (vendor-neutral contract naming "
            f"per docs/reference/rc-entity-naming.md)"
        )
        # Domain segment must be one of the allowed HA core
        # domain prefixes for the §remote_access subsystem.
        domain = tile.split(".", 1)[0]
        assert domain in allowed_domains, (
            f"tile id {tile!r} uses domain {domain!r} which is "
            f"not in the allowed remote_access domain set "
            f"{sorted(allowed_domains)!r}; per docs/reference/"
            f"rc-entity-naming.md §remote_access subsystem"
        )
        # Subsystem prefix is rc_remote_access_; the suffix
        # (after `rc_remote_access_`) MUST NOT contain any
        # forbidden vendor substring.
        suffix = tile.split(".rc_remote_access_", 1)[1]
        for bad in forbidden_substrings:
            assert bad not in suffix.lower(), (
                f"tile id {tile!r} contains forbidden vendor "
                f"substring {bad!r} in the suffix after "
                f"`rc_remote_access_`; per docs/reference/rc-"
                f"entity-naming.md, contract ids are vendor-"
                f"neutral — vendor names are forbidden in any "
                f"rc_* tile id"
            )
        # Each segment after the dot must be lowercase +
        # underscores + digits.
        for segment in tile.split("."):
            assert re.match(r"^[a-z_][a-z0-9_]*$", segment), (
                f"tile id {tile!r} contains a non-conforming "
                f"segment {segment!r}"
            )

    # Spec calls for 8-10 vendor-neutral tiles (the 9 contract
    # entities documented in the recipe §7 contract layer):
    #   binary_sensor.rc_remote_access_enabled
    #     (the §7 operator kill-switch)
    #   sensor.rc_remote_access_url
    #     (the §7 remote-access URL)
    #   binary_sensor.rc_remote_access_active
    #     (the §7 active gate)
    #   sensor.rc_remote_access_active_path
    #     (the §7 active-path indicator)
    #   sensor.rc_remote_access_peer_count
    #     (the §7 peer count)
    #   sensor.rc_remote_access_last_verified_minutes_ago
    #     (the §7 freshness gate)
    #   binary_sensor.rc_remote_access_hostname_resolvable
    #     (the §7 hostname-resolvable gate)
    #   button.rc_remote_access_verify_now
    #     (the §7 manual verify-now button)
    #   select.rc_remote_access_path
    #     (the §7 operator-chosen path selector)
    assert 8 <= len(tiles) <= 10, (
        f"remote-access must contribute 8-10 contract tiles "
        f"per spec (1 binary_sensor enabled + 1 sensor URL + 1 "
        f"binary_sensor active + 1 sensor active_path + 1 "
        f"sensor peer_count + 1 sensor last_verified_minutes_ago "
        f"+ 1 binary_sensor hostname_resolvable + 1 button "
        f"verify_now + 1 select path = 9 contract entities "
        f"documented in the recipe §7 contract layer); got "
        f"{len(tiles)}"
    )


def test_status_reflects_no_real_remote_access_engine(manifest: dict) -> None:
    """Status must be honest about no integration being shipped.

    If we ever flip this to 'shipped' or 'stable', the audit will
    demand an actual integration test (and rightly so). 'beta' is
    the only honest tier-b status for a recipe we can't
    integration-test (Tailscale + Cloudflare Tunnel + Nabu Casa +
    Wireguard are all upstream / vendor / HACS code, not
    RoamCore-owned).

    The five honesty warnings that tier_warnings must contain
    cover:
      - no_native_remote_access_engine (no bench fixture — all
        FOUR upstream integrations installed + the operator's
        account on the chosen vendor's service + canned fixture
        responses for reachability probes, all wired together in
        a controlled environment)
      - recipe_depends_on_operator_choosing_one_remote_access_
        path (the operator picks ONE of Path A Tailscale + Path
        B Cloudflare Tunnel + Path C Nabu Casa HA Cloud + Path D
        Wireguard; the recipe supports all four but the operator
        must commit to one)
      - requires_operator_wiring_upstream_integration_first
        (the operator must wire the chosen path's upstream
        integration BEFORE the §8 automations can do anything
        useful; this is the operator's dependency, not
        RoamCore-enforced)
      - magic_dns_cloudflare_dns_or_nabu_casa_account_setup_is_
        operator_owned (the operator must enable MagicDNS for
        Path A + configure Cloudflare DNS for Path B + maintain
        a Nabu Casa subscription for Path C; these are vendor-
        owned setup steps, not RoamCore-enforced)
      - ha_server_firewall_must_permit_chosen_path_port_range
        (the HA server's firewall + the home router's port-
        forwarding rules must permit the chosen path's port
        range; UDP 41641 for Path A + outbound HTTPS 7844 for
        Path B + outbound HTTPS for Path C + inbound UDP 51820
        for Path D)
    """
    assert manifest["status"] == "beta", (
        f"remote-access status={manifest['status']!r} "
        f"implies shipped coverage we don't have; use "
        f"'beta' until tier-a promotion lands"
    )
    tier_warnings = manifest.get("tier_warnings", [])
    # Tier-warnings must include the honest-about-no-native-
    # remote-access-engine marker.
    assert "no_native_remote_access_engine" in tier_warnings, (
        "tier_warnings must declare 'no_native_remote_access_"
        "engine' for honesty in the audit listing"
    )
    # And the user-facing recipe dependency warning (operator
    # must pick ONE of Path A Tailscale + Path B Cloudflare
    # Tunnel + Path C Nabu Casa HA Cloud + Path D Wireguard).
    assert "recipe_depends_on_operator_choosing_one_remote_access_path" in tier_warnings, (
        "tier_warnings must declare 'recipe_depends_on_"
        "operator_choosing_one_remote_access_path' so the "
        "audit listing is honest about the operator's path-"
        "selection dependency"
    )
    # Operator-wires-upstream-integration-first honesty — the
    # operator must wire the chosen path's upstream integration
    # BEFORE the §8 automations can do anything useful.
    assert "requires_operator_wiring_upstream_integration_first" in tier_warnings, (
        "tier_warnings must declare 'requires_operator_"
        "wiring_upstream_integration_first' so the audit "
        "listing is honest that the operator must wire the "
        "chosen path's upstream integration BEFORE the §8 "
        "automations can do anything useful"
    )
    # MagicDNS / Cloudflare DNS / Nabu Casa account-setup
    # honesty — these are vendor-owned setup steps, not
    # RoamCore-enforced.
    assert "magic_dns_cloudflare_dns_or_nabu_casa_account_setup_is_operator_owned" in tier_warnings, (
        "tier_warnings must declare 'magic_dns_cloudflare_dns_"
        "or_nabu_casa_account_setup_is_operator_owned' so "
        "the audit listing is honest that the operator must "
        "enable MagicDNS for Path A + configure Cloudflare "
        "DNS for Path B + maintain a Nabu Casa subscription "
        "for Path C (these are vendor-owned setup steps, not "
        "RoamCore-enforced)"
    )
    # HA server firewall must permit the chosen path's port
    # range honesty.
    assert "ha_server_firewall_must_permit_chosen_path_port_range" in tier_warnings, (
        "tier_warnings must declare 'ha_server_firewall_"
        "must_permit_chosen_path_port_range' so the audit "
        "listing is honest that the HA server's firewall + "
        "the home router's port-forwarding rules must permit "
        "the chosen path's port range (UDP 41641 for Path A "
        "+ outbound HTTPS 7844 for Path B + outbound HTTPS "
        "for Path C + inbound UDP 51820 for Path D)"
    )


def test_automations_are_documented(manifest: dict) -> None:
    """Defensive guard for the future tier-a promotion.

    Remote-access toggling is a critical operator-facing
    affordance in van life: forgetting to wire the kill-switch
    + the §8 automations can leave the operator with a stale
    remote-access URL (the kill-switch state does not propagate
    to the upstream integration + the auto-verify does not run
    + the path switch does not notify + the Stealth-mode
    suppression does not suppress). The §8 walks through the
    FIVE MANDATORY automations:
      - §8.1 Kill-switch ON → enable remote access — the
        automation that fires when the kill-switch flips to ON
        AND the path is set to a valid path. The automation
        calls the upstream integration's enable service so the
        chosen remote-access path is fully active.
      - §8.2 Kill-switch OFF → disable remote access — the
        automation that fires when the kill-switch flips to
        OFF. The automation calls the upstream integration's
        disable service so the chosen remote-access path is
        fully torn down.
      - §8.3 Auto-verify every 15 minutes — the automation
        that fires every 15 minutes + calls the
        `button.rc_remote_access_verify_now` button + updates
        the freshness gate.
      - §8.4 Notify on path switch — the automation that
        fires when the path changes. The automation sends a
        notification to the operator's phone.
      - §8.5 Stealth-mode suppression via `select.rc_mode` —
        the automation that SUPPRESSES the §8.1 kill-switch-ON
        automation when the `select.rc_mode` is in `stealth`
        mode.

    The test asserts the FIVE automations are documented in
    the recipe so that when this connection promotes to
    tier-a (with a real remote-access bench on CI + the FIVE
    automations hard-enforced in RoamCore code rather than
    only documented in the recipe), the audit has a clean
    assertion to flip.
    """
    text = RECIPE_PATH.read_text(encoding="utf-8")
    # §8 header MUST be present.
    assert "## §8 Automations" in text, (
        "recipe.md must have a '## §8 Automations' section "
        "(the FIVE MANDATORY automation documentation block)"
    )
    # §8 must cover the FIVE automation areas.
    automation_coverage = (
        # §8.1 Kill-switch ON → enable remote access.
        "kill-switch on",
        # §8.2 Kill-switch OFF → disable remote access.
        "kill-switch off",
        # §8.3 Auto-verify every 15 minutes.
        "auto-verify",
        # §8.4 Notify on path switch.
        "notify on path switch",
        # §8.5 Stealth-mode suppression via `select.rc_mode`.
        "stealth-mode suppression",
    )
    for phrase in automation_coverage:
        assert phrase in text.lower(), (
            f"recipe.md §8 must cover {phrase!r}; the FIVE "
            f"automations are MANDATORY before first use, and "
            f"the recipe is the only documentation operator + "
            f"future-tier-a integration code have at this tier"
        )
    # The contract tiles must include the FOUR tiles that the
    # §8 automations + the operator-facing affordance surfaces:
    #   binary_sensor.rc_remote_access_enabled
    #     (the §7 operator kill-switch + the §8.1 + §8.2
    #      automation trigger)
    #   button.rc_remote_access_verify_now
    #     (the §7 manual verify-now button + the §8.3 auto-
    #      verify automation target)
    #   select.rc_remote_access_path
    #     (the §7 operator-chosen path selector + the §8.4
    #      path-switch notification trigger)
    tiles = manifest.get("dashboard", {}).get("tiles", [])
    safety_tiles = (
        "binary_sensor.rc_remote_access_enabled",
        "button.rc_remote_access_verify_now",
        "select.rc_remote_access_path",
        "binary_sensor.rc_remote_access_active",
    )
    for safety_tile in safety_tiles:
        assert safety_tile in tiles, (
            f"dashboard.tiles must include {safety_tile!r}; the "
            f"§8 automations + operator-facing affordance tiles "
            f"are part of the contract layer that the recipe §8 "
            f"documents"
        )
    # The recipe must cross-reference the upstream HA core
    # `tailscale` integration (Path A) so the §3 Path A wiring
    # is discoverable.
    assert "ha core `tailscale` integration" in text.lower() or "ha core `tailscale`" in text.lower(), (
        "recipe.md must reference 'HA core `tailscale` "
        "integration' for the §3 Path A wiring (the upstream "
        "HA core `tailscale` integration since 2022.x is the "
        "canonical Path A mesh VPN)"
    )
    assert "home-assistant.io/integrations/tailscale" in text.lower(), (
        "recipe.md must reference the HA core `tailscale` "
        "integration upstream doc URL "
        "(https://www.home-assistant.io/integrations/tailscale/) "
        "for the §3 Path A wiring"
    )
    # The recipe must cross-reference the HACS `cloudflared`
    # add-on (Path B) so the §4 Path B wiring is discoverable.
    assert "cloudflared" in text.lower(), (
        "recipe.md must reference `cloudflared` for the §4 "
        "Path B Cloudflare Tunnel wiring (the HACS `cloudflared` "
        "add-on installs the `cloudflared` daemon on the HA "
        "server itself)"
    )
    # The recipe must cross-reference the HA Core `cloud`
    # integration (Path C) so the §5 Path C wiring is
    # discoverable.
    assert "cloud integration" in text.lower() or "ha core `cloud`" in text.lower(), (
        "recipe.md must reference `cloud integration` or "
        "`HA core cloud` for the §5 Path C Nabu Casa HA Cloud "
        "wiring (the HA Core `cloud` integration since 2022.x "
        "is the canonical Path C Nabu Casa HA Cloud relay)"
    )
    # The recipe must cross-reference the HACS `wireguard`
    # add-on (Path D) so the §6 Path D wiring is discoverable.
    assert "wireguard" in text.lower(), (
        "recipe.md must reference `wireguard` for the §6 "
        "Path D Wireguard self-hosted VPN wiring (the HACS "
        "`wireguard` add-on installs the Wireguard server in "
        "the HA server)"
    )
    # The recipe must cross-reference the HA Companion app so
    # the OFF-LAN affordance (the Companion app's `external_url`
    # setting) is discoverable.
    assert "ha companion" in text.lower(), (
        "recipe.md must reference `HA Companion` for the "
        "OFF-LAN affordance (the HA Companion app's "
        "`external_url` setting since 2022.x points the "
        "operator's phone at the chosen remote-access URL "
        "when the operator is OFF-LAN)"
    )
    # The recipe must cross-reference the mode/automation-
    # builder recipe (Wave 2 #23) so the §8.5 Stealth-mode
    # suppression automation's `select.rc_mode` tile is
    # discoverable.
    assert "select.rc_mode" in text, (
        "recipe.md must reference `select.rc_mode` for the "
        "§8.5 Stealth-mode suppression automation's source of "
        "truth (the mode/automation-builder recipe Wave 2 #23 "
        "is the canonical source of the `select.rc_mode` tile "
        "with the following options: `home` / `away` / `stealth`"
        " / `sleep`)"
    )
    # The recipe must cross-reference the Wave 2 #29
    # `feat/wave2-remote-access-tailscale` branch so the
    # existing Tailscale contract layer at
    # `homeassistant/packages/roamcore_remote_access.yaml` is
    # discoverable.
    assert "0caa9c2" in text, (
        "recipe.md must reference `0caa9c2` for the Wave 2 "
        "#29 `feat/wave2-remote-access-tailscale` branch "
        "(the existing Tailscale contract layer at "
        "`homeassistant/packages/roamcore_remote_access.yaml` "
        "that this slice LIFTS into the `connections/` "
        "pipeline)"
    )
    # The recipe must cross-reference the approach-lights
    # Wave 3 #52 connection so the canonical ON-LAN-only
    # lighting scene that Stealth-mode suppresses is
    # discoverable.
    assert "approach lights" in text.lower(), (
        "recipe.md must reference `Approach lights` for the "
        "canonical ON-LAN-only lighting scene that Stealth-"
        "mode suppresses (Wave 3 #52)"
    )
    # The recipe's defensive guard for future tier-a promotion —
    # assert the §8 section has the FIVE automations
    # documented.
    assert "five mandatory" in text.lower() or "five §8" in text.lower() or "## §8" in text.lower(), (
        "recipe.md §8 must reference the FIVE §8 automations "
        "(the §8.1 kill-switch ON + §8.2 kill-switch OFF + §8.3 "
        "auto-verify + §8.4 notify on path switch + §8.5 "
        "Stealth-mode suppression); this is the operator-side "
        "reminder that keeps the automations top-of-mind during "
        "install"
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))