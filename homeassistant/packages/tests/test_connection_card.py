"""Pytest contract rig for the catalog UI state-chip primitive.

Wave 9 #118 — Phase 1 catalog UI state chip primitive + tier vocabulary
rebrand.

Mirrors the sys.path import pattern used by the sister test rig
`test_connection_state_field.py` (the data-layer counterpart for the
`state:` field). Adds `scripts/` to sys.path so we can import the
pure-Python helper `scripts/connection_card.py` without packaging
it as an installable module.

Tests cover:
  - Every one of the 10 standard states (parametrised) renders with
    the correct kebab CSS class + chip label + title text
  - The reason arg renders as a sibling span (or is omitted when None
    / blank)
  - HTML escaping on every input — names with `<script>` in them must
    render as literal text, never as live HTML
  - Both tier vocabularies render correctly (legacy a/b/c + new
    certified/verified/experimental) — and the legacy vocabulary is
    internally mapped to the new vocabulary at render time, so user-
    facing copy always reads "RoamCore Certified / Community Verified
    / Experimental" regardless of what the YAML `tier:` field carries
  - The Connect button accepts an optional label override + never
    appends a duplicate arrow when the operator already wrote one
  - The composed `format_connection_card()` wraps everything in the
    expected `<div class="rc-state-chip-row">` row + includes a
    `data-connection-name` attribute for OpenClaw reads
  - Every kebab CSS class referenced by the helper actually exists in
    the public CSS file `docs/styles/rc.css` (so the helper output
    never renders as bare unstyled spans)

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest homeassistant/packages/tests/test_connection_card.py -v
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

# --- Sys.path bootstrap (mirrors test_connection_state_field.py pattern) ---
# The helper lives at scripts/connection_card.py (no package marker,
# pure stdlib, deliberately NOT installed as a package). We add the
# scripts/ directory to sys.path so `import connection_card` resolves.
TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[3]   # tests/ -> packages/ -> homeassistant/ -> repo
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import connection_card as cc   # noqa: E402  (sys.path bootstrap above)


# Paths the test rig inspects directly (the CSS class existence check
# reads docs/styles/rc.css to make sure every kebab class the helper
# references actually exists — the helper would otherwise render as
# bare unstyled spans, which is the exact bug Wave 9 #118 exists to
# prevent).
RC_CSS_PATH = REPO_ROOT / "docs" / "styles" / "rc.css"
IKEA_DOC_PATH = REPO_ROOT / "docs" / "reference" / "rc-connection-state-chip.md"


# ---------------------------------------------------------------------------
# Section 1 — Every standard state renders with the correct kebab class.
# 10 parametrised tests + 1 alias mapping test = 11 tests.
# ---------------------------------------------------------------------------


# The 10 standard connection states + their expected kebab CSS class.
# This is the same tuple/order as `cc.STANDARD_STATES` but expressed
# as pytest parametrize kwargs so each state gets its own assertion
# label in the pytest output.
STATE_TO_KEBAB = [
    ("Available", "available"),
    ("Detected", "detected"),
    ("Ready to connect", "ready-to-connect"),
    ("Connecting", "connecting"),
    ("Connected", "connected"),
    ("Needs information", "needs-information"),
    ("Needs attention", "needs-attention"),
    ("Unsupported", "unsupported"),
    ("Offline", "offline"),
    ("Update available", "update-available"),
]


@pytest.mark.parametrize("state,kebab", STATE_TO_KEBAB)
def test_state_chip_renders_correct_kebab_class(state: str, kebab: str) -> None:
    """Every one of the 10 standard states renders with its kebab class.

    The kebab class is the modifier that pairs with `.rc-state-chip` to
    pick up the colour treatment. If this fails for one state, that
    state's chip will render as a bare unstyled span — visible
    regression on every catalog page that uses that state.
    """
    html = cc.format_state_chip(state)
    expected_class = f"rc-state-chip--{kebab}"
    assert expected_class in html, (
        f"state {state!r} rendered without the kebab class "
        f"{expected_class!r}; got: {html}"
    )
    # Belt-and-braces: the base class is also present (so the chip is
    # styled at all).
    assert "rc-state-chip" in html, (
        f"state {state!r} rendered without the base "
        f"'rc-state-chip' class; got: {html}"
    )


@pytest.mark.parametrize("state,kebab", STATE_TO_KEBAB)
def test_state_chip_escapes_state_input(state: str, kebab: str) -> None:
    """The chip output is well-formed HTML even if the state string
    contains HTML metacharacters.

    Belt-and-braces — none of the 10 standard states contain `<` or
    `&`, but the helper accepts arbitrary strings via the kebab-class
    helper, so a defensive escape on the title + label is essential.
    """
    html = cc.format_state_chip(state)
    # No raw `<` or `>` outside of HTML tag boundaries we wrote.
    # The label is escaped; the title is escaped with quote=True so
    # double-quotes inside never break the attribute.
    assert "<script>" not in html, (
        f"state {state!r} rendered without escaping; got: {html}"
    )


def test_state_chip_returns_single_span_without_reason() -> None:
    """`format_state_chip(state)` with no reason returns one span.

    No reason span is added when reason is None or blank — the chip
    is the only DOM node the catalog render layer needs.
    """
    html = cc.format_state_chip("Available")
    assert html.count("<span") == 1, (
        f"expected exactly one <span> when no reason is given; got: "
        f"{html}"
    )
    assert "rc-state-chip-reason" not in html, (
        f"no reason should be rendered; got: {html}"
    )


def test_state_chip_appends_reason_span_when_provided() -> None:
    """`format_state_chip(state, reason)` renders BOTH the chip and the reason.

    The reason is a short plain-English note that surfaces in a sibling
    span. It's HTML-escaped.
    """
    html = cc.format_state_chip(
        "Needs information", "enter your MQTT password"
    )
    assert html.count("<span") == 2, (
        f"expected exactly two <span> elements (chip + reason); got: "
        f"{html}"
    )
    assert "rc-state-chip-reason" in html, (
        f"reason span class missing; got: {html}"
    )
    assert "enter your MQTT password" in html, (
        f"reason text missing from output; got: {html}"
    )


def test_state_chip_reason_is_html_escaped() -> None:
    """The reason text is HTML-escaped — `<script>` in the reason must
    render as literal text, never as live HTML.
    """
    html = cc.format_state_chip(
        "Needs attention", "<script>alert('xss')</script>"
    )
    assert "<script>alert" not in html, (
        f"reason text was not escaped; got: {html}"
    )
    assert "&lt;script&gt;alert" in html, (
        f"reason text should be HTML-escaped; got: {html}"
    )


def test_state_chip_blank_reason_omits_reason_span() -> None:
    """A blank/whitespace-only reason is treated as None — no reason
    span is rendered.
    """
    for blank in ("", "   ", "\t\n"):
        html = cc.format_state_chip("Available", blank)
        assert "rc-state-chip-reason" not in html, (
            f"blank reason {blank!r} should not render a reason "
            f"span; got: {html}"
        )


def test_state_chip_unknown_state_raises() -> None:
    """An unknown state value raises ValueError.

    Mirrors the data-layer rule from `test_connection_state_field.py`
    — a state outside the 10-state allowlist is invalid and the
    helper must refuse to render a chip for it.
    """
    with pytest.raises(ValueError):
        cc.format_state_chip("NotAState")


def test_state_chip_blank_state_raises() -> None:
    """A blank/missing state raises — same lockstep rule.
    """
    for blank in (None, "", "   "):
        with pytest.raises(ValueError):
            cc.format_state_chip(blank)   # type: ignore[arg-type]


def test_state_chip_class_helper_matches_full_helper() -> None:
    """`state_chip_class(state)` returns the same kebab class the full
    helper uses — the bash smoke + a future CLI tool can derive the
    expected class without re-implementing the mapping table.
    """
    for state, kebab in STATE_TO_KEBAB:
        assert cc.state_chip_class(state) == kebab, (
            f"state_chip_class({state!r}) returned "
            f"{cc.state_chip_class(state)!r}, expected {kebab!r}"
        )


def test_state_chip_class_unknown_state_raises() -> None:
    """`state_chip_class()` raises on unknown state — same lockstep rule.
    """
    with pytest.raises(ValueError):
        cc.state_chip_class("NotAState")


def test_standard_states_tuple_is_exactly_ten() -> None:
    """The directive specifies exactly 10 standard states.

    Mirrors `test_connection_state_field.py::test_allowlist_size_is_ten`.
    A regression here (someone adds #11 by accident or removes one)
    breaks the user-facing doc + the catalogue chip CSS classes. The
    lockstep is the only way to keep the data layer honest.
    """
    assert len(cc.STANDARD_STATES) == 10, (
        f"the 10-state allowlist must remain exactly 10 entries "
        f"(per the directive §'Connection states are standardized'); "
        f"got {len(cc.STANDARD_STATES)}: {sorted(cc.STANDARD_STATES)}"
    )


# ---------------------------------------------------------------------------
# Section 2 — Both tier vocabularies render correctly.
# 3 legacy letters × 1 helper + 3 new words × 1 helper + 1 mapping
# test + 1 user-facing label test + 1 escape test + 1 unknown-tier
# test = 10 tests.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("letter", ["a", "b", "c"])
def test_legacy_tier_letter_renders_with_new_vocabulary_label(letter: str) -> None:
    """The legacy a/b/c tier vocabulary maps to the new vocabulary
    at render time — the user-facing label is "RoamCore Certified /
    Community Verified / Experimental" regardless of the YAML letter.
    """
    label_for_letter = {
        "a": "RoamCore Certified",
        "b": "Community Verified",
        "c": "Experimental",
    }
    html = cc.format_tier_chip(letter)
    assert label_for_letter[letter] in html, (
        f"legacy tier letter {letter!r} should render with the new "
        f"vocabulary label {label_for_letter[letter]!r}; got: {html}"
    )
    # The kebab modifier matches the new vocabulary word, not the
    # legacy letter.
    new_vocab = {"a": "certified", "b": "verified", "c": "experimental"}[letter]
    assert f"rc-tier--{new_vocab}" in html, (
        f"legacy tier letter {letter!r} should use the new-vocabulary "
        f"kebab class {new_vocab!r}; got: {html}"
    )


@pytest.mark.parametrize(
    "vocab,expected_label",
    [
        ("certified", "RoamCore Certified"),
        ("verified", "Community Verified"),
        ("experimental", "Experimental"),
    ],
)
def test_new_vocabulary_tier_renders_correctly(
    vocab: str, expected_label: str
) -> None:
    """The new tier vocabulary renders with the expected user label."""
    html = cc.format_tier_chip(vocab)
    assert expected_label in html, (
        f"new vocabulary word {vocab!r} should render with label "
        f"{expected_label!r}; got: {html}"
    )
    assert f"rc-tier--{vocab}" in html, (
        f"new vocabulary word {vocab!r} should use the matching "
        f"kebab class; got: {html}"
    )


def test_tier_chip_renders_with_rc_chip_class_too() -> None:
    """The tier chip carries BOTH `.rc-tier` and `.rc-chip` classes.

    `.rc-tier` is the catalog-page pill; `.rc-chip` is the dashboard
    badge. The helper emits both so the same modifier class works in
    both contexts.
    """
    for vocab in ("certified", "verified", "experimental"):
        html = cc.format_tier_chip(vocab)
        assert "rc-tier" in html, (
            f"tier chip for {vocab!r} missing .rc-tier base class; "
            f"got: {html}"
        )
        assert "rc-chip" in html, (
            f"tier chip for {vocab!r} missing .rc-chip base class; "
            f"got: {html}"
        )


def test_normalize_tier_maps_legacy_to_new() -> None:
    """`normalize_tier()` is the canonical mapping table — every
    legacy letter maps to its new-vocabulary word.
    """
    assert cc.normalize_tier("a") == "certified"
    assert cc.normalize_tier("b") == "verified"
    assert cc.normalize_tier("c") == "experimental"


def test_normalize_tier_passes_through_new_vocabulary() -> None:
    """`normalize_tier()` is idempotent on the new vocabulary.
    """
    assert cc.normalize_tier("certified") == "certified"
    assert cc.normalize_tier("verified") == "verified"
    assert cc.normalize_tier("experimental") == "experimental"


def test_normalize_tier_unknown_raises() -> None:
    """`normalize_tier()` raises on any other input.
    """
    for bad in ("", "   ", "d", "Tier-a", "tier-b", "complete", "99"):
        with pytest.raises(ValueError):
            cc.normalize_tier(bad)


def test_tier_chip_html_escapes_input() -> None:
    """The tier chip HTML-escapes the input — names with `<script>`
    must render as literal text. (Today the tier vocabulary is a fixed
    enum, but defensive escaping is cheap and the helper is the user-
    facing surface.)
    """
    # No real escape happens for the fixed enum, but the helper must
    # not crash on a `<` in the title attribute path.
    html = cc.format_tier_chip("certified")
    # The title is escaped with quote=True so a hypothetical injected
    # " character would break out — assert it didn't.
    assert html.count('title="') == 1, (
        f"tier chip should have exactly one title attribute; got: {html}"
    )


# ---------------------------------------------------------------------------
# Section 3 — Connect button (label override + arrow handling).
# 1 default label test + 2 label override tests + 1 no-double-arrow
# test + 1 slug validation test + 1 escape test = 6 tests.
# ---------------------------------------------------------------------------


def test_connect_button_default_label_is_connect() -> None:
    """The default Connect button label is "Connect →".
    """
    html = cc.format_connect_button("starlink")
    assert "Connect" in html, (
        f"default Connect button should mention 'Connect'; got: {html}"
    )
    assert "→" in html, (
        f"default Connect button should include the arrow; got: {html}"
    )


def test_connect_button_href_points_to_slug() -> None:
    """The Connect button's href is `<slug>/` (MkDocs resolves the
    trailing slash to the catalog page for that device).
    """
    html = cc.format_connect_button("starlink")
    assert 'href="starlink/"' in html, (
        f"Connect button href should be 'starlink/'; got: {html}"
    )


def test_connect_button_label_override() -> None:
    """The Connect button accepts a custom label override.

    Used for special-case copy ("Set up", "Open", "View", "Wake").
    """
    html = cc.format_connect_button("mqtt", label="Set up")
    assert "Set up" in html, (
        f"Connect button should use the override label 'Set up'; "
        f"got: {html}"
    )


def test_connect_button_does_not_double_arrow_when_label_already_has_one() -> None:
    """If the operator's label already ends with an arrow, the helper
    doesn't append a second one. (Defensive — prevents `Connect → →`.)
    """
    # Map each arrow suffix to the form it takes AFTER HTML escaping
    # (the label is HTML-escaped before render). The unicode arrow
    # `→` is not affected by HTML escaping; `->` becomes `-&gt;`
    # because `>` is escaped; `&rarr;` becomes `&amp;rarr;` because
    # `&` is escaped first.
    for raw_suffix, escaped_suffix in (
        ("→", "→"),       # not escaped
        ("->", "-&gt;"),  # > escaped
        ("&rarr;", "&amp;rarr;"),  # & escaped first
    ):
        html = cc.format_connect_button("starlink", label=f"Set up {raw_suffix}")
        assert html.count(escaped_suffix) == 1, (
            f"label ending with {raw_suffix!r} should not have a "
            f"second arrow appended; got: {html}"
        )


def test_connect_button_blank_slug_raises() -> None:
    """A blank slug raises — the helper refuses to render a button
    pointing nowhere.
    """
    for blank in ("", "   "):
        with pytest.raises(ValueError):
            cc.format_connect_button(blank)   # type: ignore[arg-type]


def test_connect_button_html_escapes_slug() -> None:
    """The slug is HTML-escaped on the href + title attributes.
    """
    # The slug is normally a kebab-case ASCII id, but defensive escaping
    # is cheap. Test with a safe-but-with-quotes slug.
    html = cc.format_connect_button('weird"slug')
    assert 'href="weird&quot;slug/"' in html or 'href="weird&#x22;slug/"' in html, (
        f"slug with quotes should be escaped; got: {html}"
    )


# ---------------------------------------------------------------------------
# Section 4 — Composed connection card.
# 1 composition test + 1 row class test + 1 data-attribute test + 1
# empty-reason test = 4 tests.
# ---------------------------------------------------------------------------


def test_composed_card_includes_all_three_primitives() -> None:
    """The composed `format_connection_card()` includes the state
    chip, the tier pill, AND the Connect button — wrapped in a
    `<div class="rc-state-chip-row">` row.
    """
    html = cc.format_connection_card(
        name="Starlink",
        slug="starlink",
        tier="b",
        state="Available",
    )
    assert "rc-state-chip" in html, (
        f"composed card missing the state chip; got: {html}"
    )
    assert "rc-tier" in html, (
        f"composed card missing the tier pill; got: {html}"
    )
    assert "rc-connect-button" in html, (
        f"composed card missing the Connect button; got: {html}"
    )
    assert "rc-state-chip-row" in html, (
        f"composed card missing the row wrapper class; got: {html}"
    )


def test_composed_card_row_wraps_all_three() -> None:
    """The row wrapper `<div class="rc-state-chip-row">` wraps ALL
    three primitives — the OpenClaw reader can locate the row by class
    and read all three attributes.
    """
    html = cc.format_connection_card(
        name="Starlink",
        slug="starlink",
        tier="b",
        state="Available",
    )
    # Extract the row opening + closing + everything between.
    open_idx = html.index('<div class="rc-state-chip-row"')
    close_idx = html.rindex("</div>")
    inside = html[open_idx:close_idx + len("</div>")]
    assert "rc-state-chip" in inside, (
        f"state chip not inside the row wrapper; got: {html}"
    )
    assert "rc-tier" in inside, (
        f"tier pill not inside the row wrapper; got: {html}"
    )
    assert "rc-connect-button" in inside, (
        f"Connect button not inside the row wrapper; got: {html}"
    )


def test_composed_card_data_attribute_carries_name() -> None:
    """The composed card carries a `data-connection-name` attribute
    on the row wrapper — OpenClaw can read the human-readable name
    from the rendered DOM without parsing the page text.
    """
    html = cc.format_connection_card(
        name="Starlink (Gen-2)",
        slug="starlink",
        tier="b",
        state="Available",
    )
    assert 'data-connection-name="Starlink (Gen-2)"' in html, (
        f"composed card missing the data-connection-name attribute "
        f"with the device name; got: {html}"
    )


def test_composed_card_html_escapes_name() -> None:
    """The device name is HTML-escaped on the data-connection-name
    attribute — a name with `<script>` must render as literal text,
    never as live HTML.
    """
    html = cc.format_connection_card(
        name="<script>alert('xss')</script>",
        slug="evil",
        tier="a",
        state="Available",
    )
    assert "<script>alert" not in html, (
        f"device name was not escaped; got: {html}"
    )
    assert "&lt;script&gt;alert" in html, (
        f"device name should be HTML-escaped; got: {html}"
    )


# ---------------------------------------------------------------------------
# Section 5 — CSS class existence in docs/styles/rc.css.
# 1 each-state-has-class test + 1 each-tier-has-class test = 2 tests.
# (These read the CSS file and assert every kebab class the helper
# references actually exists in the file. If a future slice adds a
# state without adding the CSS, this test fails before the catalog
# renders as bare unstyled spans.)
# ---------------------------------------------------------------------------


def test_rc_css_has_all_ten_state_chip_classes() -> None:
    """Every kebab class the helper emits exists in docs/styles/rc.css.

    The lockstep rule: data layer (10-state tuple) + render layer
    (state_chip_class) + CSS layer (.rc-state-chip--<kebab>) must
    stay in sync. If a future slice adds a state, this test fails
    on day one if the CSS hasn't been updated.
    """
    css_text = RC_CSS_PATH.read_text(encoding="utf-8")
    for state, kebab in STATE_TO_KEBAB:
        selector = f".rc-state-chip--{kebab}"
        assert selector in css_text, (
            f"CSS class {selector!r} (for state {state!r}) is "
            f"missing from {RC_CSS_PATH}. The data layer + render "
            f"layer + CSS layer must stay in lockstep — add the "
            f"selector to rc.css and re-run."
        )


def test_rc_css_has_all_three_tier_modifier_classes() -> None:
    """Every new-vocabulary tier modifier class exists in docs/styles/rc.css.

    Same lockstep rule as the state-chip classes. Adding a tier
    vocabulary word without updating the CSS fails this test.
    """
    css_text = RC_CSS_PATH.read_text(encoding="utf-8")
    for vocab in ("certified", "verified", "experimental"):
        # Both .rc-tier--<vocab> and .rc-chip--<vocab> must exist.
        assert f".rc-tier--{vocab}" in css_text, (
            f"CSS class .rc-tier--{vocab!r} is missing from "
            f"{RC_CSS_PATH}; the helper emits it but the CSS doesn't "
            f"define it — the pill will render unstyled."
        )
        assert f".rc-chip--{vocab}" in css_text, (
            f"CSS class .rc-chip--{vocab!r} is missing from "
            f"{RC_CSS_PATH}; the helper emits it but the CSS doesn't "
            f"define it — the badge will render unstyled."
        )


def test_rc_css_has_row_and_button_classes() -> None:
    """The row wrapper and Connect button classes also exist in rc.css.

    Same lockstep rule — the helper emits `.rc-state-chip-row` and
    `.rc-connect-button`, so the CSS must define them.
    """
    css_text = RC_CSS_PATH.read_text(encoding="utf-8")
    for cls in (
        ".rc-state-chip",
        ".rc-state-chip-reason",
        ".rc-state-chip-row",
        ".rc-connect-button",
    ):
        assert cls in css_text, (
            f"CSS class {cls!r} is missing from {RC_CSS_PATH}; the "
            f"helper emits it but the CSS doesn't define it."
        )


# ---------------------------------------------------------------------------
# Section 6 — IKEA user-facing doc exists + is well-formed.
# 1 file-exists test + 1 opening-sentence test + 1 no-jargon test = 3 tests.
# (Mirrors the contract test pattern for the sister IKEA doc
# `docs/reference/rc-connection-states.md`.)
# ---------------------------------------------------------------------------


def test_ikea_doc_exists() -> None:
    """The IKEA user-facing doc exists at docs/reference/rc-connection-state-chip.md.

    The doc is the user-facing surface — its absence means the
    catalogue chip primitive ships without a how-to-read-it guide.
    """
    assert IKEA_DOC_PATH.is_file(), (
        f"IKEA user-facing doc missing at {IKEA_DOC_PATH}; the "
        f"chip primitive must ship with a how-to-read-it guide."
    )


def test_ikea_doc_opens_in_plain_english() -> None:
    """The IKEA doc's first paragraph is in plain English.

    Defends against the operator-speak slop anti-pattern (the doc
    starts with the directive + commit jargon, not a sentence a
    vanlifer would read). The opening should say what the chip
    DOES for the user, in the user's world.
    """
    text = IKEA_DOC_PATH.read_text(encoding="utf-8")
    # Find the first paragraph after the H1.
    paragraphs = [
        p.strip() for p in text.split("\n\n") if p.strip()
    ]
    # Skip the H1 line.
    body_paragraphs = [
        p for p in paragraphs
        if not p.startswith("# ")
    ]
    assert body_paragraphs, "IKEA doc has no body paragraphs"
    opening = body_paragraphs[0]
    # Must be at least one full sentence (>= 40 chars).
    assert len(opening) >= 40, (
        f"IKEA doc opening is too short to be a real sentence: "
        f"{opening!r}"
    )
    # Must NOT contain operator jargon.
    jargon = [
        "directive", "Wave ", "tier-a", "tier-b", "tier-c",
        "cron", "sub-agent", "subagent", "commit SHA", "PR #",
    ]
    for word in jargon:
        assert word not in opening, (
            f"IKEA doc opening contains operator jargon {word!r}: "
            f"{opening!r}"
        )


def test_ikea_doc_has_no_file_paths_or_internal_jargon() -> None:
    """The IKEA doc contains no file paths, function names, or
    internal jargon (per the discipline block §B).

    The doc lives in `docs/` (the public MkDocs surface) — every
    sentence must read like an IKEA furniture catalogue.
    """
    text = IKEA_DOC_PATH.read_text(encoding="utf-8")
    forbidden = [
        "scripts/connection_card.py",
        "test_connection_card.py",
        "format_state_chip",
        "format_tier_chip",
        "format_connect_button",
        "format_connection_card",
        "catalog-state-chip-smoke.sh",
        "kebab CSS",
        "pytest",
    ]
    for word in forbidden:
        assert word not in text, (
            f"IKEA doc contains internal jargon {word!r}; the doc "
            f"lives in docs/ (the public MkDocs surface) and must "
            f"read like an IKEA furniture catalogue, not like an "
            f"engineering runbook."
        )