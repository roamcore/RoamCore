"""Pytest contract rig for the Phase 1 catalog UI proper render layer.

Wave 9 #125 — Phase 1 catalog UI proper: render 27 connection cards via
format_connection_card() + per-connection state: field.

Mirrors the sys.path import pattern used by the sister test rig
`test_connection_card.py` (the consumer of the format_connection_card
primitive) and `test_build_catalog_lib.py`-style rig (the data layer
that catalog rendering consumes).

Adds `scripts/` to sys.path so we can import `scripts/build_catalog.py`
+ `scripts/build_catalog_lib.py` + `scripts/connection_card.py` as
plain Python modules (no packaging required). We exercise:

  (1) `render_catalog_index()` emits one card per non-excluded item
      in the live inventory (≥20 cards today; current count = 28
      after the 5-slug exclude list).
  (2) Each emitted card carries the 4 chip CSS classes the
      `connection_card.format_connection_card()` primitive emits
      (rc-state-chip-row wrapper + rc-state-chip--<kebab> state +
      rc-tier--<vocab> tier + rc-connect-button).
  (3) `render_category_index()` emits the right card count per
      category (the per-category count must equal the per-category
      YAML count of non-excluded connections in that category).
  (4) `format_connection_card()` is called with the right args per
      item (name + slug + tier + state + reason), using a monkeypatched
      spy that records every call.
  (5) The render layer is inventory-driven — given a synthetic inventory
      written into a tempdir, the render layer emits the same cards
      that the live one would emit for the live inventory.

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest homeassistant/packages/tests/test_catalog_ui_cards.py -v
"""

from __future__ import annotations

import importlib.util
import re
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

# --- Sys.path bootstrap (mirrors the sister test rigs) ---
TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[3]   # tests/ -> packages/ -> homeassistant/ -> repo
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# Sister test rigs add `scripts/` then `import connection_card as cc`
# directly. We need build_catalog (the module under test) + connection_card
# (the consumer primitive) + build_catalog_lib (the data layer).
# `scripts/build_catalog.py` shadows the stdlib `builtins` slot for `build`
# (it has a `build()` function), so we load it via importlib.util to
# keep its `argparse` + `main()` surface intact.
import connection_card as cc  # noqa: E402  (sys.path bootstrap above)

import build_catalog_lib as lib  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "build_catalog_under_test",
    SCRIPTS_DIR / "build_catalog.py",
)
assert _spec is not None and _spec.loader is not None, (
    "could not load scripts/build_catalog.py via importlib.util — "
    "the file should exist at the standard scripts/ path."
)
build_catalog_under_test = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_catalog_under_test)


# --- Helper: re-build the inventory using the live data layer so every
# test works against the same source-of-truth Connection objects the
# render layer consumed. Mirrors test_connection_card.py's approach of
# importing the live data layer + the live render layer together.
def _live_user_facing():
    """Return the live list of non-excluded Connection objects.

    Same excludes the script applies: agent-actions-allowlist,
    openclaw-api, advanced-mode, demo-mode, mock-location-and-tracks.
    """
    excludes = [
        "agent-actions-allowlist",
        "openclaw-api",
        "advanced-mode",
        "demo-mode",
        "mock-location-and-tracks",
    ]
    conns, _skipped = lib.discover_connections(
        Path("connections"), excludes=excludes,
    )
    return [c for c in conns if not c.excluded]


# ---------------------------------------------------------------------------
# Section 1 — render_catalog_index emits one card per non-excluded item.
# ---------------------------------------------------------------------------


def test_render_catalog_index_emits_one_card_per_non_excluded_item() -> None:
    """render_catalog_index() emits one connection card (rc-state-chip-row)
    per non-excluded connection in the live inventory.

    Mirrors the spec acceptance criterion: "generated docs/catalog/index.md
    contains ≥20 connection cards (sanity — actual count = non-excluded
    count, which is currently 33 per inventory; relaxed to ≥20 to allow
    for future exclude adjustments)."
    """
    user_facing = _live_user_facing()
    expected_count = len(user_facing)

    assert expected_count >= 20, (
        f"sanity guard: the live inventory should have ≥20 non-excluded "
        f"connections, got {expected_count}. If the inventory shrank, "
        f"update this assertion + the smoke threshold."
    )

    # Use a tempdir as the catalog_dir so we don't write to disk.
    with tempfile.TemporaryDirectory() as tmp:
        catalog_dir = Path(tmp)
        rendered = build_catalog_under_test.render_catalog_index(
            user_facing, catalog_dir,
        )

    card_count = rendered.count('class="rc-state-chip-row"')
    assert card_count == expected_count, (
        f"render_catalog_index() emitted {card_count} cards; expected "
        f"{expected_count} (one per non-excluded Connection object). "
        f"The render layer must mirror the data layer exactly."
    )


def test_render_catalog_index_emits_at_least_twenty_cards() -> None:
    """The rendered main catalog index contains ≥20 cards.

    Sanity guard against the inventory shrinking without the smoke
    threshold being updated. The spec's relaxed ≥20 threshold is the
    backstop.
    """
    user_facing = _live_user_facing()
    with tempfile.TemporaryDirectory() as tmp:
        catalog_dir = Path(tmp)
        rendered = build_catalog_under_test.render_catalog_index(
            user_facing, catalog_dir,
        )
    card_count = rendered.count('class="rc-state-chip-row"')
    assert card_count >= 20, (
        f"main catalog index must have ≥20 cards (spec §Acceptance); "
        f"got {card_count}. If the inventory shrank below 20, this "
        f"guard fires before a stale card count leaks into the docs site."
    )


# ---------------------------------------------------------------------------
# Section 2 — every emitted card carries the 4 chip CSS classes the
# primitive emits (rc-state-chip-row + rc-state-chip--<kebab> +
# rc-tier--<vocab> + rc-connect-button).
# ---------------------------------------------------------------------------


def test_every_card_has_state_chip_class() -> None:
    """Every emitted card carries the rc-state-chip--<kebab> modifier.

    The kebab class is the modifier that pairs with `.rc-state-chip`
    to pick up the colour treatment. A card without it renders as
    bare unstyled text — visible regression on every catalog page.
    """
    user_facing = _live_user_facing()
    with tempfile.TemporaryDirectory() as tmp:
        catalog_dir = Path(tmp)
        rendered = build_catalog_under_test.render_catalog_index(
            user_facing, catalog_dir,
        )
    cards = re.findall(
        r'<div class="rc-state-chip-row"[^>]*>(.*?)</div>',
        rendered,
        re.DOTALL,
    )
    assert len(cards) >= 20, (
        f"expected ≥20 cards in the rendered main catalog index; "
        f"found {len(cards)}."
    )
    for i, card in enumerate(cards):
        assert "rc-state-chip--" in card, (
            f"card #{i + 1} missing the rc-state-chip--<kebab> modifier; "
            f"got card content: {card[:200]}"
        )


def test_every_card_has_tier_chip_class() -> None:
    """Every emitted card carries the rc-tier--<vocab> modifier.
    """
    user_facing = _live_user_facing()
    with tempfile.TemporaryDirectory() as tmp:
        catalog_dir = Path(tmp)
        rendered = build_catalog_under_test.render_catalog_index(
            user_facing, catalog_dir,
        )
    cards = re.findall(
        r'<div class="rc-state-chip-row"[^>]*>(.*?)</div>',
        rendered,
        re.DOTALL,
    )
    for i, card in enumerate(cards):
        assert "rc-tier--" in card, (
            f"card #{i + 1} missing the rc-tier--<vocab> modifier; "
            f"got card content: {card[:200]}"
        )


def test_every_card_has_connect_button_class() -> None:
    """Every emitted card carries an rc-connect-button anchor.
    """
    user_facing = _live_user_facing()
    with tempfile.TemporaryDirectory() as tmp:
        catalog_dir = Path(tmp)
        rendered = build_catalog_under_test.render_catalog_index(
            user_facing, catalog_dir,
        )
    cards = re.findall(
        r'<div class="rc-state-chip-row"[^>]*>(.*?)</div>',
        rendered,
        re.DOTALL,
    )
    for i, card in enumerate(cards):
        assert "rc-connect-button" in card, (
            f"card #{i + 1} missing the rc-connect-button anchor; "
            f"got card content: {card[:200]}"
        )


def test_every_card_has_the_row_wrapper_class() -> None:
    """Every emitted card sits inside an rc-state-chip-row wrapper.

    The row wrapper is what makes the chip + tier pill + Connect
    button line up as a single row; OpenClaw readers locate the row
    by this class. A card outside the wrapper is a regression.
    """
    user_facing = _live_user_facing()
    with tempfile.TemporaryDirectory() as tmp:
        catalog_dir = Path(tmp)
        rendered = build_catalog_under_test.render_catalog_index(
            user_facing, catalog_dir,
        )
    # Count wrappers and connectors separately — the assertions above
    # already assert the inner primitives, so we just assert the
    # wrapper class is used.
    wrapper_count = rendered.count('class="rc-state-chip-row"')
    assert wrapper_count >= 20, (
        f"main catalog must have ≥20 rc-state-chip-row wrappers; "
        f"got {wrapper_count}."
    )


# ---------------------------------------------------------------------------
# Section 3 — render_category_index emits the right count per category.
# ---------------------------------------------------------------------------


def test_render_category_index_emits_per_category_count() -> None:
    """render_category_index() emits one card per non-excluded item in
    the category it was given.

    Drives the per-category YAML count check: for every category in
    the live inventory, the per-category count emitted by
    render_category_index() must equal the per-category YAML count.
    """
    from collections import defaultdict

    user_facing = _live_user_facing()
    by_cat: dict[str, list[lib.Connection]] = defaultdict(list)
    for c in user_facing:
        by_cat[c.catalog_category].append(c)

    for cat, items in sorted(by_cat.items()):
        rendered = build_catalog_under_test.render_category_index(items, cat)
        card_count = rendered.count('class="rc-state-chip-row"')
        assert card_count == len(items), (
            f"render_category_index({cat!r}) emitted {card_count} cards; "
            f"expected {len(items)} (one per non-excluded item in the "
            f"category). Drifting here is a data-layer + render-layer "
            f"disagreement."
        )


def test_render_category_index_emits_expected_primitives() -> None:
    """render_category_index() emits chips, tier pills, AND Connect buttons
    in each card — the same triplet the main catalog index uses.
    """
    user_facing = _live_user_facing()
    # Pick the comfort category (largest in the inventory).
    comfort = [c for c in user_facing if c.catalog_category == "comfort"]
    assert comfort, (
        "sanity: the inventory should have at least one comfort connection"
    )

    rendered = build_catalog_under_test.render_category_index(comfort, "comfort")
    cards = re.findall(
        r'<div class="rc-state-chip-row"[^>]*>(.*?)</div>',
        rendered,
        re.DOTALL,
    )
    for i, card in enumerate(cards):
        assert "rc-state-chip--" in card, (
            f"comfort card #{i + 1} missing the state chip modifier"
        )
        assert "rc-tier--" in card, (
            f"comfort card #{i + 1} missing the tier pill modifier"
        )
        assert "rc-connect-button" in card, (
            f"comfort card #{i + 1} missing the Connect button"
        )


# ---------------------------------------------------------------------------
# Section 4 — format_connection_card() is called with the right args per item.
# ---------------------------------------------------------------------------


def test_format_connection_card_called_with_right_args_per_item() -> None:
    """render_catalog_index() calls format_connection_card(name, slug,
    tier, state, reason) per Connection object — same shape the
    connection_card primitive accepts.

    We monkeypatch format_connection_card with a spy that records
    every call, then assert the call args match the live Connection
    objects.
    """
    user_facing = _live_user_facing()
    # Bind the unbound real once — patching the module attribute
    # would otherwise recurse when the spy calls back into the
    # patched name.
    real_fn = cc.format_connection_card
    calls = []

    def spy(name, slug, tier, state, reason=None, connect_label=None):
        calls.append({
            "name": name,
            "slug": slug,
            "tier": tier,
            "state": state,
            "reason": reason,
        })
        return real_fn(
            name=name, slug=slug, tier=tier, state=state,
            reason=reason, connect_label=connect_label,
        )

    with mock.patch.object(
        build_catalog_under_test.connection_card,
        "format_connection_card",
        side_effect=spy,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            catalog_dir = Path(tmp)
            build_catalog_under_test.render_catalog_index(
                user_facing, catalog_dir,
            )

    assert len(calls) == len(user_facing), (
        f"spy recorded {len(calls)} calls; render_catalog_index should "
        f"call format_connection_card() once per non-excluded item "
        f"({len(user_facing)} items)."
    )

    # Build a lookup of live Connection objects by slug, so we can
    # assert every call's args came from the live data layer.
    by_slug = {c.slug: c for c in user_facing}
    for call in calls:
        slug = call["slug"]
        assert slug in by_slug, (
            f"format_connection_card() was called with unknown slug "
            f"{slug!r}; the data layer doesn't have it"
        )
        conn = by_slug[slug]
        # name == c.title (the short user-facing title)
        assert call["name"] == conn.title, (
            f"name mismatch for slug {slug!r}: called with {call['name']!r}, "
            f"Connection.title is {conn.title!r}"
        )
        # tier == c.tier (uppercase A/B/C)
        assert call["tier"] == conn.tier, (
            f"tier mismatch for slug {slug!r}: called with {call['tier']!r}, "
            f"Connection.tier is {conn.tier!r}"
        )
        # state is one of the 10 standard states; falls back to "Available"
        assert call["state"] in cc.STANDARD_STATES, (
            f"state {call['state']!r} is not in the 10-state allowlist; "
            f"the render layer must guard against drift here"
        )
        # The state on the wire should match what we sourced from the
        # Connection object's `state` field (which itself defaults to
        # "Available" if the YAML omits the field).
        expected_state = conn.state or "Available"
        assert call["state"] == expected_state, (
            f"state mismatch for slug {slug!r}: called with {call['state']!r}, "
            f"Connection.state is {expected_state!r}"
        )


def test_format_connection_card_called_per_category() -> None:
    """render_category_index() calls format_connection_card() exactly
    once per item in the category it was given.
    """
    user_facing = _live_user_facing()
    comfort = [c for c in user_facing if c.catalog_category == "comfort"]
    real_fn = cc.format_connection_card

    calls = []
    def spy(name, slug, tier, state, reason=None, connect_label=None):
        calls.append(slug)
        return real_fn(
            name=name, slug=slug, tier=tier, state=state,
            reason=reason, connect_label=connect_label,
        )

    with mock.patch.object(
        build_catalog_under_test.connection_card,
        "format_connection_card",
        side_effect=spy,
    ):
        build_catalog_under_test.render_category_index(comfort, "comfort")

    assert sorted(calls) == sorted([c.slug for c in comfort]), (
        f"render_category_index() called format_connection_card() with "
        f"{sorted(calls)}; expected {sorted([c.slug for c in comfort])}"
    )


# ---------------------------------------------------------------------------
# Section 5 — render layer is inventory-driven (regenerates against a
# synthetic inventory + asserts the rendered cards track the inventory).
# ---------------------------------------------------------------------------


def test_render_layer_is_inventory_driven(tmp_path: Path) -> None:
    """The render layer is a pure function of the inventory:
    give it N synthetic Connection objects and it emits exactly N
    cards in the same order (grouped by category).

    This is the inventory-driven property test from the spec — the
    render layer must depend on the inventory + the connection_card
    primitive, not on anything hidden in the live on-disk state.
    """
    # Build 3 synthetic Connection objects covering two categories.
    a = lib.Connection(
        slug="alpha",
        raw_id="alpha",
        name_raw="Alpha",
        title="Alpha",
        yaml_category="power",
        catalog_category="power",
        tier="A",
        status="shipped",
        install_method="one_line",
        raw_description="",
        summary="Alpha — synthetic.",
        state="Available",
        reason="",
    )
    b = lib.Connection(
        slug="bravo",
        raw_id="bravo",
        name_raw="Bravo",
        title="Bravo",
        yaml_category="ventilation",
        catalog_category="comfort",
        tier="B",
        status="shipped",
        install_method="one_line",
        raw_description="",
        summary="Bravo — synthetic.",
        state="Needs information",
        reason="needs an MQTT password",
    )
    c = lib.Connection(
        slug="charlie",
        raw_id="charlie",
        name_raw="Charlie",
        title="Charlie",
        yaml_category="lighting",
        catalog_category="comfort",
        tier="C",
        status="shipped",
        install_method="one_line",
        raw_description="",
        summary="Charlie — synthetic.",
        state="Detected",
        reason="",
    )

    # 1. main catalog index
    rendered = build_catalog_under_test.render_catalog_index(
        [a, b, c], tmp_path,
    )
    card_count = rendered.count('class="rc-state-chip-row"')
    assert card_count == 3, (
        f"synthetic inventory of 3 items should render 3 cards; got {card_count}"
    )
    # Each state surfaces the right kebab class.
    assert "rc-state-chip--available" in rendered, (
        "Alpha (state=Available) should produce the 'available' kebab class"
    )
    assert "rc-state-chip--needs-information" in rendered, (
        "Bravo (state='Needs information') should produce the "
        "'needs-information' kebab class"
    )
    assert "rc-state-chip--detected" in rendered, (
        "Charlie (state=Detected) should produce the 'detected' kebab class"
    )
    # Each tier surfaces the right tier class.
    assert "rc-tier--certified" in rendered, (
        "Alpha (tier=A) should produce the 'certified' tier class"
    )
    assert "rc-tier--verified" in rendered, (
        "Bravo (tier=B) should produce the 'verified' tier class"
    )
    assert "rc-tier--experimental" in rendered, (
        "Charlie (tier=C) should produce the 'experimental' tier class"
    )
    # The reason surfaces on the right card.
    assert "needs an MQTT password" in rendered, (
        "Bravo's reason should surface in the rendered HTML"
    )

    # 2. per-category indexes
    power_rendered = build_catalog_under_test.render_category_index([a], "power")
    assert power_rendered.count('class="rc-state-chip-row"') == 1, (
        f"power category with 1 item should render 1 card; "
        f"got {power_rendered.count('rc-state-chip-row')}"
    )

    comfort_rendered = build_catalog_under_test.render_category_index(
        [b, c], "comfort",
    )
    assert comfort_rendered.count('class="rc-state-chip-row"') == 2, (
        f"comfort category with 2 items should render 2 cards; "
        f"got {comfort_rendered.count('rc-state-chip-row')}"
    )


def test_render_layer_falls_back_to_available_when_state_missing(
    tmp_path: Path,
) -> None:
    """A Connection without an explicit state field falls back to
    "Available" — the neutral default per the Wave 9 #125 spec.

    The Connection dataclass defaults state to "Available" (added
    in Wave 9 #125). We confirm the render layer passes the
    default through unchanged.
    """
    conn = lib.Connection(
        slug="no-state",
        raw_id="no-state",
        name_raw="No-state",
        title="No-state",
        yaml_category="power",
        catalog_category="power",
        tier="B",
        status="shipped",
        install_method="one_line",
        raw_description="",
        summary="No-state — synthetic.",
        # state intentionally omitted — uses dataclass default
    )
    assert conn.state == "Available", (
        f"Connection dataclass default state should be 'Available'; "
        f"got {conn.state!r}"
    )

    rendered = build_catalog_under_test.render_category_index([conn], "power")
    assert "rc-state-chip--available" in rendered, (
        "Connection with default state should render the 'available' chip"
    )
    assert ">Available</span>" in rendered, (
        "Connection with default state should display the 'Available' label"
    )
