"""Pytest tests for `scripts/connection_card.py` (Wave 9 #118).

Per the Wave 9 #118 directive (Phase 1 catalog UI: state chip
primitive + Connect button helper), the connection catalogue UI MUST
emit a consistent state chip + tier chip + Connect button for any
connection. `scripts/connection_card.py` provides the pure Python
helper that emits the HTML. This test file pins down the contract:

  1. All 10 standard states emit a chip with the correct kebab-case
     CSS class.
  2. `format_state_chip` raises a plain-English `ValueError` for an
     unknown state (drift is surfaced loudly, not silently masked).
  3. `format_state_chip(state, state_reason=…)` renders the
     `<span class="rc-state-chip-reason">…</span>` subtitle.
  4. `format_tier_chip("a"|"b"|"c")` uses the legacy CSS classes;
     `"certified"|"verified"|"experimental"` uses the full-word
     vocabulary. Both render the correct user-facing label.
  5. `format_connect_button("starlink")` emits
     `href="/connections/starlink/connect"`.
  6. `format_connection_card(...)` composes all three primitives
     into a single `<div class="rc-state-chip-row">…</div>` block.
  7. The CSS classes referenced in emitted HTML exist in
     `docs/styles/rc.css` (smoke assertion against the style sheet).

The 10-state list is the directive's literal one — if we ever need to
add a state (e.g. "Syncing", "Verifying"), update this test AND
`scripts/connection_card.py` AND the chip CSS AND
`docs/reference/rc-connection-state-chip.md` together; the lockstep
keeps all four honest.

This file is intentionally additive + minimal + idempotent:
- It does NOT touch any other test file.
- It does NOT depend on any sister test (each test is self-contained).
- It does NOT require a running HA instance.
- It does NOT require a Proxmox/OpenWrt/networking fixture.

Run:
    python3 -m pytest homeassistant/packages/tests/test_connection_card.py -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

# `scripts/connection_card.py` lives at REPO_ROOT/scripts/. Add it to
# sys.path so the import works regardless of pytest's invocation
# directory (mirrors the import pattern used by
# `homeassistant/packages/tests/test_connection_state.py`, which uses
# sys.path insertion for the same reason — both test files live two
# levels under `homeassistant/packages/tests/` and need access to the
# repo's `scripts/` directory for their helpers).
REPO_ROOT = Path(__file__).resolve().parents[3]   # tests/ -> packages/ -> homeassistant/ -> repo
SCRIPTS_DIR = REPO_ROOT / "scripts"
DOCS_STYLES = REPO_ROOT / "docs" / "styles" / "rc.css"

import sys
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import connection_card  # noqa: E402  (sys.path tweak above is intentional)


# Expected kebab-case CSS-class fragments for each of the 10 standard
# states. Matches the mapping table at the top of
# `scripts/connection_card.py`; kept duplicated here so the test
# failure message is self-explanatory (which state went wrong, and
# what the expected class fragment is) without needing to re-read the
# helper source.
EXPECTED_KEBAB: dict[str, str] = {
    "Available":          "available",
    "Detected":           "detected",
    "Ready to connect":   "ready-to-connect",
    "Connecting":         "connecting",
    "Connected":          "connected",
    "Needs information":  "needs-information",
    "Needs attention":    "needs-attention",
    "Unsupported":        "unsupported",
    "Offline":            "offline",
    "Update available":   "update-available",
}


def test_standard_states_tuple_is_10() -> None:
    """The directive §"Connection states are standardized" lists 10
    states verbatim. The helper's tuple MUST have exactly those 10,
    in the directive order (so a maintainer can read top-to-bottom
    and verify each row).
    """
    assert len(connection_card.STANDARD_STATES) == 10, (
        f"expected 10 standard states, got {len(connection_card.STANDARD_STATES)}; "
        f"the directive §\"Connection states are standardized\" lists 10 verbatim. "
        f"Add or remove a state only if the directive itself changes."
    )
    expected = (
        "Available",
        "Detected",
        "Ready to connect",
        "Connecting",
        "Connected",
        "Needs information",
        "Needs attention",
        "Unsupported",
        "Offline",
        "Update available",
    )
    assert connection_card.STANDARD_STATES == expected, (
        f"STANDARD_STATES tuple diverged from the directive's "
        f"verbatim 10-state list. Got {connection_card.STANDARD_STATES!r}; "
        f"expected {expected!r}."
    )


@pytest.mark.parametrize("state", list(EXPECTED_KEBAB))
def test_format_state_chip_emits_kebab_class_for_each_state(state: str) -> None:
    """Every standard state MUST emit a chip with the kebab-case CSS
    class fragment listed in the spec. Drift (e.g. a hidden copy that
    lowercases the state, or a new state slipped in without updating
    the kebab map) would render an unstyled chip on the catalog.
    """
    chip = connection_card.format_state_chip(state)
    expected_class = f"rc-state-chip {EXPECTED_KEBAB[state]}"
    assert expected_class in chip, (
        f"chip for state {state!r} is missing expected class "
        f"fragment {expected_class!r}; got {chip!r}. The kebab-case "
        f"mapping in connection_card._STATE_KEBAB must stay in lockstep "
        f"with the chip CSS in docs/styles/rc.css."
    )
    # And the chip must use the same shape across all 10 states
    # (so the catalog audit can grep for a single pattern).
    assert chip.startswith("<span class=") and chip.endswith("</span>"), (
        f"chip for state {state!r} is malformed: {chip!r}"
    )


def test_format_state_chip_renders_state_reason_as_subtitle() -> None:
    """A non-None `state_reason` MUST append a subtitle span on its
    own line. The subtitle CSS class (`.rc-state-chip-reason`) is
    styled smaller + dimmer by `docs/styles/rc.css` so the chip stays
    visually compact while still surfacing the "why" copy.
    """
    chip = connection_card.format_state_chip(
        "Needs attention",
        state_reason="Last contact 6 hours ago — check the controller.",
    )
    assert "rc-state-chip needs-attention" in chip, chip
    assert (
        '<span class="rc-state-chip-reason">Last contact 6 hours ago — '
        'check the controller.</span>' in chip
    ), chip


def test_format_state_chip_without_state_reason_has_no_subtitle() -> None:
    """When `state_reason` is None (the common case), the chip MUST
    NOT emit a subtitle span. An empty subtitle would render a
    dangling punctuation-less line under the chip.
    """
    chip = connection_card.format_state_chip("Connected")
    assert "rc-state-chip-reason" not in chip, chip


def test_format_state_chip_raises_for_unknown_state() -> None:
    """An unknown state MUST raise `ValueError` with a plain-English
    error message that names the valid states. Silent fallback
    (returning an unknown-state chip) would render an unstyled blob
    on the catalog and break the audit grid.
    """
    for bad in ("connected", "Live", "wired", "shipped", "", "ready"):
        with pytest.raises(ValueError) as excinfo:
            connection_card.format_state_chip(bad)  # type: ignore[arg-type]
        msg = str(excinfo.value)
        assert "unknown connection state" in msg, msg
        # The error MUST list the valid states so the connection
        # author can fix their manifest without re-reading the
        # directive.
        for valid in ("Available", "Connected", "Update available"):
            assert valid in msg, (
                f"error message for state {bad!r} should list valid "
                f"states; got {msg!r}"
            )


def test_format_state_chip_raises_for_blank_state_reason() -> None:
    """A blank / non-string `state_reason` MUST raise ValueError. An
    empty subtitle would render a dangling line under the chip, which
    is worse than no subtitle at all.
    """
    with pytest.raises(ValueError):
        connection_card.format_state_chip("Connected", state_reason="")
    with pytest.raises(ValueError):
        connection_card.format_state_chip("Connected", state_reason="   ")
    with pytest.raises(ValueError):
        connection_card.format_state_chip("Connected", state_reason=42)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "tier,variant,label",
    [
        ("a", "certified",    "RoamCore Certified"),
        ("b", "verified",     "Community Verified"),
        ("c", "experimental", "Experimental"),
        ("A", "certified",    "RoamCore Certified"),  # case-insensitive
        (" certified ", "certified", "RoamCore Certified"),  # whitespace-tolerant
        ("certified",    "certified", "RoamCore Certified"),
        ("verified",     "verified",  "Community Verified"),
        ("experimental", "experimental", "Experimental"),
    ],
)
def test_format_tier_chip_accepts_both_vocabularies(
    tier: str, variant: str, label: str,
) -> None:
    """The helper MUST accept BOTH the legacy `a|b|c` letter sort key
    AND the full-word vocabulary (`certified|verified|experimental`).
    The legacy letters are kept for backward compatibility with sister
    catalog pages still rendering `data-tier="a|b|c"` attribute
    filters; the full-word vocabulary is the user-facing label.
    """
    chip = connection_card.format_tier_chip(tier)
    assert f"rc-tier {variant}" in chip, chip
    assert label in chip, chip


def test_format_tier_chip_raises_for_unknown_tier() -> None:
    """An unknown tier MUST raise ValueError with a plain-English
    error message. Silent fallback to the legacy `.a` class would
    break the full-word vocabulary contract.
    """
    for bad in ("d", "gold", "", "tier-a"):
        with pytest.raises(ValueError):
            connection_card.format_tier_chip(bad)  # type: ignore[arg-type]


def test_format_connect_button_emits_correct_href() -> None:
    """The Connect button MUST emit `href="/connections/{slug}/connect"`
    so the catalog router can land on the per-connection setup page.
    The slug is validated as kebab-case (a malformed slug raises).
    """
    html = connection_card.format_connect_button("starlink")
    assert 'href="/connections/starlink/connect"' in html, html
    assert "rc-connect-button" in html, html
    assert ">Connect</a>" in html, html


def test_format_connect_button_default_label_is_connect() -> None:
    """The default label is "Connect" — callers override per state
    ("Set up", "Reconnect", "Update", "Learn more") but the common
    case uses the bare verb.
    """
    html = connection_card.format_connect_button("mqtt")
    assert ">Connect</a>" in html, html


@pytest.mark.parametrize(
    "label",
    ["Set up", "Reconnect", "Update", "Learn more", "Connect"],
)
def test_format_connect_button_supports_overrides(label: str) -> None:
    """The label override MUST render the exact supplied copy. The
    catalog uses per-state labels to match what the operator needs
    to do next; a stale default would mislead ("Reconnect" surfaces
    when a brand-new connection is still in `Available` state).
    """
    html = connection_card.format_connect_button("starlink", label=label)
    assert f">{label}</a>" in html, html


def test_format_connect_button_raises_for_bad_slug() -> None:
    """A malformed slug (uppercase, spaces, leading dash, empty)
    MUST raise ValueError. The slug flows into the `href` attribute
    so a stray `<script>` or quote would be XSS; the validation is
    belt-and-braces for the hand-curated catalog today.
    """
    for bad in ("", "Starlink", "starlink!", "-starlink", "star link"):
        with pytest.raises(ValueError):
            connection_card.format_connect_button(bad)  # type: ignore[arg-type]


def test_format_connection_card_composes_all_three_primitives() -> None:
    """The composition helper MUST render all three primitives
    (state chip + tier chip + Connect button) inside a single
    `<div class="rc-state-chip-row">…</div>` wrapper so the catalog
    page can drop one block of HTML and get a self-contained row.
    The connection name is included as a sibling `<strong>` so the
    row is screen-reader-friendly without an additional heading.
    """
    html = connection_card.format_connection_card(
        slug="starlink",
        name="Starlink",
        tier="b",
        state="Ready to connect",
        state_reason="3-path recipe shipped.",
    )
    assert '<div class="rc-state-chip-row">' in html, html
    assert "</div>" in html, html
    assert "<strong>Starlink</strong>" in html, html
    assert "rc-state-chip ready-to-connect" in html, html
    assert (
        '<span class="rc-state-chip-reason">3-path recipe shipped.</span>'
        in html
    ), html
    assert "rc-tier verified" in html, html
    assert "Community Verified" in html, html
    assert 'href="/connections/starlink/connect"' in html, html
    assert ">Connect</a>" in html, html


def test_format_connection_card_without_state_reason() -> None:
    """The composition helper MUST handle a missing `state_reason`
    (the common case for `Connected` connections): no subtitle span.
    """
    html = connection_card.format_connection_card(
        slug="mqtt",
        name="MQTT",
        tier="b",
        state="Connected",
    )
    assert "rc-state-chip-reason" not in html, html
    assert "rc-state-chip connected" in html, html


def test_format_connection_card_raises_for_blank_name() -> None:
    """A blank connection name MUST raise ValueError. An empty
    `<strong></strong>` would render as a dangling visual gap in the
    row.
    """
    with pytest.raises(ValueError):
        connection_card.format_connection_card(
            slug="starlink",
            name="",
            tier="b",
            state="Connected",
        )


def test_state_chip_css_classes_exist_in_rc_css() -> None:
    """The CSS classes referenced by `format_state_chip` MUST exist
    in `docs/styles/rc.css`. Drift (helper emits a new state but the
    CSS isn't extended) would render an unstyled chip on the
    catalog. The smoke check
    (`scripts/checks/catalog-state-chip-smoke.sh`) enforces the same
    rule at every `check.sh` run; this test pins it down at the
    pytest layer too.
    """
    css = DOCS_STYLES.read_text(encoding="utf-8")
    required_classes = (
        ".rc-state-chip.available",
        ".rc-state-chip.detected",
        ".rc-state-chip.ready-to-connect",
        ".rc-state-chip.connecting",
        ".rc-state-chip.connected",
        ".rc-state-chip.needs-information",
        ".rc-state-chip.needs-attention",
        ".rc-state-chip.unsupported",
        ".rc-state-chip.offline",
        ".rc-state-chip.update-available",
        ".rc-state-chip-reason",
        ".rc-connect-button",
    )
    missing = [cls for cls in required_classes if cls not in css]
    assert not missing, (
        f"docs/styles/rc.css is missing the following CSS classes "
        f"emitted by scripts/connection_card.py: {missing!r}. The "
        f"helper and the chip CSS MUST stay in lockstep; update "
        f"both together when adding a new state or a new chip "
        f"variant."
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))