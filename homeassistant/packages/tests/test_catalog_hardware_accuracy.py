"""Pytest contract rig for catalog "What you need" hardware accuracy.

Wave 9 follow-up to Wave 8 row #307 (alternator-charge-control). The
previous implementation of ``sensible_hardware_defaults()`` in
``scripts/build_catalog_lib.py`` matched on raw substrings of the
slug and produced two live mis-classifications on the user-facing
catalog:

  1. ``alternator-charge-control`` was told to buy a Zigbee smoke /
     CO detector (because ``"co" in "alternator-CHARGE-CONTROL"``).
  2. ``dns-blocker`` was told to buy a Z-Wave smart deadbolt (because
     ``"lock" in "DNS-BLOCKER"``).

This rig exercises the token-based replacement and pins the regressions
so they cannot recur. It uses the same sys.path bootstrap pattern as the
sister rigs in this directory (``test_catalog_ui_cards.py``,
``test_connection_card.py``, ...).

Run locally::

    cd /home/bernard/clawd/RoamCore
    python3 -m pytest homeassistant/packages/tests/test_catalog_hardware_accuracy.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# --- Sys.path bootstrap (mirrors the sister test rigs) ---
TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[3]   # tests/ -> packages/ -> homeassistant/ -> repo
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import build_catalog_lib as lib  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _lines_to_text(hardware: list[str]) -> str:
    """Render the hardware list as the same plain text render_page() emits.

    The catalog renders the list as ``- <item>`` lines; we mirror that
    shape so the keyword checks look like real grep invocations.
    """

    return "\n".join(f"- {h}" for h in hardware)


def _inventory() -> list[tuple[str, str, str]]:
    """Return ``[(slug, title, catalog_category), ...]`` for every YAML-backed connection.

    Walks ``connections/*/connection.yml`` via the library's discover
    helper so the rig stays in lockstep with whatever the generator
    sees. Excluded slugs are filtered out (the user-facing catalog
    never renders them).
    """

    conns, _ = lib.discover_connections(
        REPO_ROOT / "connections",
        excludes=("agent-actions-allowlist", "openclaw-api"),
    )
    return [
        (c.slug, c.title, c.catalog_category)
        for c in conns
        if not c.excluded
    ]


# ---------------------------------------------------------------------------
# Regression pins (the slice's whole reason for existing)
# ---------------------------------------------------------------------------


def test_regression_pin_alternator_charge_control_has_no_smoke_line():
    """``alternator-charge-control`` must NOT recommend a smoke / CO detector.

    The substring matcher shipped with a live line
    ``- Zigbee smoke / CO detector ($30–$80 each)`` on this page —
    a vanlifer setting up alternator charging was told to buy a
    smoke alarm.
    """

    hw = lib.sensible_hardware_defaults(
        "alternator-charge-control",
        "Alternator charge control",
        catalog_category="power",
    )
    text = _lines_to_text(hw).lower()
    assert "smoke" not in text, (
        "alternator-charge-control hardware list must not mention smoke "
        "detectors — the only token left that could trigger the smoke "
        "rule in the new matcher would be the smoke token itself, which "
        "is NOT in {alternator, charge, control}."
    )


def test_regression_pin_alternator_charge_control_has_alternator_regulator():
    """``alternator-charge-control`` MUST recommend an alternator regulator.

    The opposite half of pin #1: the page has to actually tell the
    vanlifer what to buy for alternator charging, not just stop
    recommending the wrong thing.
    """

    hw = lib.sensible_hardware_defaults(
        "alternator-charge-control",
        "Alternator charge control",
        catalog_category="power",
    )
    text = _lines_to_text(hw).lower()
    assert "alternator" in text and "regulator" in text, (
        "alternator-charge-control hardware list must recommend a smart "
        "alternator regulator (Wakespeed / Balmar / Sterling / REDARC) "
        f"so a vanlifer knows what to actually buy. Got: {hw!r}"
    )


def test_regression_pin_dns_blocker_has_no_deadbolt_line():
    """``dns-blocker`` must NOT recommend a Z-Wave deadbolt.

    The substring matcher shipped with a live line
    ``- Z-Wave smart deadbolt (Yale / Schlage) ($120–$250)`` on this
    page — a vanlifer setting up Pi-hole / AdGuard Home was told to
    buy a front door lock.
    """

    hw = lib.sensible_hardware_defaults(
        "dns-blocker",
        "Pi-hole or AdGuard Home",
        catalog_category="connectivity",
    )
    text = _lines_to_text(hw).lower()
    assert "deadbolt" not in text, (
        "dns-blocker hardware list must not mention a deadbolt — the "
        "substring 'lock' that used to match 'dns-bLOCKer' is gone "
        "now that matching is token-based."
    )


def test_regression_pin_dns_blocker_recommends_dns_gear():
    """``dns-blocker`` MUST recommend Pi-hole / AdGuard gear."""

    hw = lib.sensible_hardware_defaults(
        "dns-blocker",
        "Pi-hole or AdGuard Home",
        catalog_category="connectivity",
    )
    text = _lines_to_text(hw).lower()
    assert "pi-hole" in text or "adguard" in text, (
        f"dns-blocker hardware list must reference Pi-hole or AdGuard "
        f"hardware so a vanlifer knows what to buy. Got: {hw!r}"
    )


# ---------------------------------------------------------------------------
# Controls — prove the fix did not over-correct and break legitimate
# rules. ``smoke-co-gas-sensors`` MUST still get the smoke detector.
# ---------------------------------------------------------------------------


def test_control_smoke_co_gas_sensors_still_fires():
    """``smoke-co-gas-sensors`` tokenises to {smoke, co, gas} and MUST
    continue to fire the smoke-detector rule.

    The whole point of moving to token matching is that
    ``co`` (the real one) STILL matches while ``control`` (the
    impostor) does not. This test pins the legitimate match.
    """

    hw = lib.sensible_hardware_defaults(
        "smoke-co-gas-sensors",
        "Smoke / CO / gas safety sensors",
        catalog_category="safety",
    )
    text = _lines_to_text(hw).lower()
    assert "smoke" in text and "co" in text, (
        "smoke-co-gas-sensors hardware list must contain the smoke / CO "
        "detector line — the new matcher must still fire on the literal "
        "tokens {smoke, co, gas}. Got: "
        f"{_lines_to_text(hw)}"
    )


# ---------------------------------------------------------------------------
# Controls — every previously correct rule must still fire on its
# own canonical slug. These are the "did the rewrite preserve every
# rule" pins.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("slug", "title", "catalog_category", "required_substring"),
    [
        ("fans", "Fans", "comfort", "fan"),
        ("approach-lights", "Approach lights", "comfort", "light"),
        ("motion-based-lighting", "Motion-based lighting", "comfort", "light"),
        ("water-tanks", "Water tanks", "water", "tank"),
        ("leveling", "Leveling", "maintenance", "imu"),
        ("deadbolts", "Deadbolts", "safety", "deadbolt"),
        ("remote-access", "Remote access", "connectivity", "tailscale"),
        ("music-assistant", "Music Assistant", "comfort", "speaker"),
        ("map-dashboard", "RoamCore Map", "location", "gps"),
    ],
)
def test_existing_rules_still_fire(slug, title, catalog_category, required_substring):
    """Existing correct rules must still fire on their canonical slugs."""

    hw = lib.sensible_hardware_defaults(slug, title, catalog_category=catalog_category)
    assert hw, f"{slug} produced an empty hardware list — the rule that used to fire stopped firing"
    text = _lines_to_text(hw).lower()
    assert required_substring in text, (
        f"{slug} hardware list does not mention {required_substring!r}; "
        f"got: {_lines_to_text(hw)}"
    )


# ---------------------------------------------------------------------------
# Invariant: every slug in the inventory must (a) not raise and (b)
# not produce an empty list for a power-category slug.
# ---------------------------------------------------------------------------


def _all_slug_cases():
    """Yield (slug, title, catalog_category) for every connection in the inventory."""

    return _inventory()


@pytest.mark.parametrize(("slug", "title", "catalog_category"), _all_slug_cases())
def test_inventory_slug_does_not_raise(slug, title, catalog_category):
    """For every YAML slug, sensible_hardware_defaults() must not raise."""

    # The library does NOT raise today but we pin it as a guardrail
    # against future regressions (a future rule could crash on an
    # unexpected slug shape).
    try:
        hw = lib.sensible_hardware_defaults(slug, title, catalog_category=catalog_category)
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"sensible_hardware_defaults raised on slug {slug!r}: {exc}")
    assert isinstance(hw, list), (
        f"sensible_hardware_defaults must return a list for {slug!r}; "
        f"got {type(hw).__name__}"
    )


@pytest.mark.parametrize(("slug", "title", "catalog_category"), _all_slug_cases())
def test_inventory_slug_with_empty_list_only_outside_power(slug, title, catalog_category):
    """Only non-power slugs may legitimately have an empty hardware list.

    Power gear almost always requires something to buy; an empty
    list there would fall back to "Nothing extra" on the user-facing
    page and mislead the reader. The safety net in
    ``sensible_hardware_defaults()`` (catalog_category="power" +
    empty list) guarantees we emit at least a smart-shunt + fuse-
    block line instead.
    """

    hw = lib.sensible_hardware_defaults(slug, title, catalog_category=catalog_category)
    if catalog_category == "power":
        assert hw, (
            f"power slug {slug!r} produced an empty hardware list — "
            f"the power-category safety net should have fired."
        )


# ---------------------------------------------------------------------------
# Invariant: a hardware line's keywords must not contradict the slug.
# A smoke / CO / gas detector line only on a smoke / CO / gas slug;
# a deadbolt only on a lock slug; a fan only on a fan / vent slug;
# water gear only on a water / tank slug; etc. The whitelist +
# blacklist together cover the cases that the original substring
# matcher mis-classified plus a handful of obvious ones.
# ---------------------------------------------------------------------------


# Map each "exclusive" hardware keyword to the slug tokens that
# legitimately justify it. If a slug contains one of the listed
# tokens the line is allowed; otherwise the line is a bug.
_EXCLUSIVE_HARDWARE_RULES = {
    # Smoke / CO / gas — only on smoke / co / gas slugs.
    "smoke detector": {"smoke", "co", "gas"},
    "co detector": {"smoke", "co", "gas"},
    # Deadbolt — only on lock / deadbolt slugs.
    "smart deadbolt": {"lock", "locks", "deadbolt", "deadbolts"},
    # Fan / vent — only on fan / vent slugs.
    "vent fan": {"fan", "fans", "vent", "vents", "ventilation"},
    "circulation fan": {"fan", "fans", "vent", "vents", "ventilation"},
    # Water tank sensors — only on water / tank slugs.
    "tank sensor": {"water", "tank", "tanks"},
    "solenoid valve": {"water", "tank", "tanks"},
    # Alternator regulator — only on alternator slugs.
    "alternator regulator": {"alternator"},
    # Inverter-charger — only on inverter slugs.
    "inverter-charger": {"inverter"},
    # DNS blocker — only on dns slugs.
    "adguard": {"dns"},
    "pi-hole": {"dns"},
    "pi/hole": {"dns"},
}


def _slug_tokens_for(slug: str) -> set[str]:
    return lib._slug_tokens(slug)


@pytest.mark.parametrize(("slug", "title", "catalog_category"), _all_slug_cases())
def test_no_contradictory_hardware_for_slug(slug, title, catalog_category):
    """No slug may get a hardware line whose keyword contradicts the slug."""

    hw = lib.sensible_hardware_defaults(slug, title, catalog_category=catalog_category)
    tokens = _slug_tokens_for(slug)

    for line in hw:
        lowered = line.lower()
        for keyword, allowed_tokens in _EXCLUSIVE_HARDWARE_RULES.items():
            if keyword in lowered and not (tokens & allowed_tokens):
                pytest.fail(
                    f"slug {slug!r} (tokens={sorted(tokens)}) got a hardware line "
                    f"whose keyword {keyword!r} requires one of {sorted(allowed_tokens)}; "
                    f"the full line was: {line!r}"
                )


# ---------------------------------------------------------------------------
# Idempotency: the function must be deterministic — calling it twice
# returns the same list, with the same order. Also pins the de-dup +
# order-preserving behaviour so a future refactor cannot quietly
# break it.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("slug", "title", "catalog_category"), _all_slug_cases())
def test_idempotent_returns_same_list(slug, title, catalog_category):
    """Calling sensible_hardware_defaults() twice returns identical output."""

    a = lib.sensible_hardware_defaults(slug, title, catalog_category=catalog_category)
    b = lib.sensible_hardware_defaults(slug, title, catalog_category=catalog_category)
    assert a == b, (
        f"sensible_hardware_defaults is not deterministic for {slug!r}: "
        f"first call = {a!r}, second call = {b!r}"
    )


# ---------------------------------------------------------------------------
# Token-matcher unit tests (small, focused) — pins the helper behaviour
# so a future "let's also do substring matching" refactor doesn't slip
# past the integration tests above.
# ---------------------------------------------------------------------------


def test_token_matcher_only_matches_whole_tokens():
    """``co`` must NOT match ``control`` and ``lock`` must NOT match ``blocker``."""

    # Both bugs shipped in v1 — pin them at the helper level.
    assert not lib._matches({"control"}, "co"), (
        "the smoke rule must NOT fire on the token 'control' "
        "(this is the original alternator-charge-control bug)"
    )
    assert not lib._matches({"blocker"}, "lock"), (
        "the deadbolt rule must NOT fire on the token 'blocker' "
        "(this is the original dns-blocker bug)"
    )
    assert not lib._matches({"controls"}, "co"), "substring-style matching sneaked back in"


def test_token_matcher_accepts_multiple_stems():
    """``_matches`` accepts multiple stems via the ``a/b/c`` syntax."""

    # Internal contract: the helper's call sites use a single string
    # per category of stem (e.g. "fan/vent") so we can list singular
    # + plural + gerund + abbreviation in one place.
    assert lib._matches({"deadbolts"}, "lock/locks/deadbolt/deadbolts")
    assert lib._matches({"lighting"}, "light/lights/lighting/approach")
    assert not lib._matches({"lighting"}, "fan/vent")


def test_token_matcher_empty_token_set_returns_false():
    """An empty token set must not match anything (covers edge cases)."""

    assert not lib._matches(set(), "fan", "vent", "smoke")
    assert not lib._matches(set(), "deadbolt")


# ---------------------------------------------------------------------------
# Power safety-net pin (a non-token-matching power slug must still get
# a useful line via the safety net, so a new power connection that
# doesn't yet have a token rule lands "honest" instead of "Nothing
# extra"). The hypothetical ``inverter-idle-shutdown`` slug from the
# spec is our permanent test fixture for this.
# ---------------------------------------------------------------------------


def test_power_safety_net_fires_when_no_token_rule_matches():
    """A power slug with no token matches must still get the safety-net line."""

    # ``hypothetical-power-thing`` has no token that matches any
    # power rule. With the safety net, sensible_hardware_defaults
    # should return at least one non-empty line.
    hw = lib.sensible_hardware_defaults(
        "hypothetical-power-thing",
        "Hypothetical power thing",
        catalog_category="power",
    )
    assert hw, (
        "power-category safety net should emit at least one line for "
        "a power slug with no token matches"
    )


def test_power_safety_net_does_not_fire_outside_power():
    """Non-power slugs with no rule matches must keep returning [] (No extra fallback)."""

    # ``my-funky-thing`` is not power, not any covered rule → empty,
    # which renders as "Nothing extra" — the correct, honest answer
    # for a recipe that genuinely needs no gear.
    hw = lib.sensible_hardware_defaults(
        "my-funky-thing",
        "My funky thing",
        catalog_category="automation",
    )
    assert hw == [], (
        f"non-power slug with no token matches should produce an empty "
        f"list (which renders as 'Nothing extra'); got {hw!r}"
    )
