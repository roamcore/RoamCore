#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RoamCore catalog UI: connection card formatter (state chip + tier chip + connect button).

Wave 9 #118 — Phase 1 catalog UI foundation + tier vocabulary rebrand.

This module is the USER-FACING RENDER LAYER for the catalog. Every catalog
page (and every future dashboard tile that wants to advertise a device
state) renders through one of these four pure functions:

    format_state_chip(state, reason=None)
        → a coloured <span> chip beside a device's name. 10 states.

    format_tier_chip(tier)
        → a small pill that names WHO BUILT THIS honestly. Accepts both
          the legacy "a"/"b"/"c" vocabulary and the new
          "certified"/"verified"/"experimental" vocabulary — the new
          vocabulary is what user-facing copy uses today.

    format_connect_button(slug, label=None)
        → a one-tap "Connect →" link to the device's setup page. The
          label defaults to "Connect"; pass an override for special-
          case devices ("Set up", "Open", "View").

    format_connection_card(name, slug, tier, state, reason=None)
        → composes all three into a single horizontal row, ready to
          paste into any catalog page's Markdown (with attr_list /
          md_in_html extensions enabled — MkDocs ships both by
          default).

The CSS lives in `docs/styles/rc.css` (the public MkDocs surface).
The 10 kebab state classes are listed in `STATE_TO_KEBAB_CLASS` below.

DESIGN RULES (enforced by the test rig in
`homeassistant/packages/tests/test_connection_card.py`):

    1. HTML escaping on EVERY input. Names with `<script>` in them
       must render as literal text, not as live HTML.
    2. Pure stdlib. No Jinja, no Markdown lib, no dependency surface.
       MkDocs already imports this file at build time; keep the
       install trivial.
    3. Deterministic output. No timestamps, no random ids. Two calls
       with the same inputs must produce byte-identical strings.
    4. CLI --smoke mode prints the 10 standard state chips + the 3
       tier chips + a composed sample card, so the smoke shell can
       grep them out and the operator can eyeball the result without
       running pytest.

USER-FACING ONE-LINER (used in the commit body and the IKEA doc):

    "When I open RoamCore's catalog, each device shows me at a glance
     whether it's ready to use, needs a small action from me, or has
     hit a problem — and tells me honestly who built it (RoamCore,
     community, or experimental)."
"""

from __future__ import annotations

import argparse
import html
import sys
from typing import Optional


# ---------------------------------------------------------------------------
# Constants — the 10 standard connection states (verbatim from the directive
# §"Connection states are standardized"). The kebab CSS class is the
# kebab-cased lowercase of the state with spaces replaced by dashes. Adding
# a state requires updating BOTH this tuple AND the user-facing doc
# `docs/reference/rc-connection-states.md` AND the CSS classes in
# `docs/styles/rc.css` AND the cross-cutting pytest in
# `test_connection_state_field.py` in lockstep.
# ---------------------------------------------------------------------------

STANDARD_STATES: tuple[str, ...] = (
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

# The kebab CSS class for each state. Locked so the data layer, the render
# layer, and the CSS stay in lockstep — adding a state without updating
# the CSS raises a clear "no chip class for state" error.
STATE_TO_KEBAB_CLASS: dict[str, str] = {
    "Available": "available",
    "Detected": "detected",
    "Ready to connect": "ready-to-connect",
    "Connecting": "connecting",
    "Connected": "connected",
    "Needs information": "needs-information",
    "Needs attention": "needs-attention",
    "Unsupported": "unsupported",
    "Offline": "offline",
    "Update available": "update-available",
}

# The short label rendered inside the chip. Mostly the state name itself,
# but a couple of states read better shortened (e.g. "Update available" →
# "Update" inside a 22-char chip). The full text still surfaces via the
# `title` attribute on hover.
STATE_TO_CHIP_LABEL: dict[str, str] = {
    "Available": "Available",
    "Detected": "Detected",
    "Ready to connect": "Ready to connect",
    "Connecting": "Connecting",
    "Connected": "Connected",
    "Needs information": "Needs info",
    "Needs attention": "Needs attention",
    "Unsupported": "Unsupported",
    "Offline": "Offline",
    "Update available": "Update",
}

# The hover-title for each state (one short sentence explaining the state).
# These are the ONLY places the chip references the state by name in full;
# the chip itself uses the short label.
STATE_TO_TITLE: dict[str, str] = {
    "Available": "Code is shipped and the device is ready to install.",
    "Detected": "The system has seen the device and is figuring out what it is.",
    "Ready to connect": "The device is set up and waiting for you to link it.",
    "Connecting": "The device is linking up to your dashboard right now.",
    "Connected": "The device is wired into RoamCore and showing live readings.",
    "Needs information": "The device needs a small piece of information from you.",
    "Needs attention": "Something needs a quick look from you.",
    "Unsupported": "RoamCore cannot work with this device yet.",
    "Offline": "The device is not reachable right now.",
    "Update available": "A newer version is ready to install.",
}

# ---------------------------------------------------------------------------
# Tier vocabulary. BOTH vocabularies are supported by format_tier_chip().
# The new vocabulary (certified/verified/experimental) is what user-facing
# copy uses from Wave 9 #118 onwards; the legacy a/b/c vocabulary is kept
# for back-compat with every existing connection.yml (whose `tier:` field
# is still a single letter) and every existing test fixture.
# ---------------------------------------------------------------------------

LEGACY_TIER_LETTERS: tuple[str, ...] = ("a", "b", "c")

LEGACY_TIER_TO_LEGACY_LABEL: dict[str, str] = {
    "a": "A",
    "b": "B",
    "c": "C",
}

LEGACY_TIER_TO_LEGACY_CSS_CLASS: dict[str, str] = {
    "a": "a",
    "b": "b",
    "c": "c",
}

# Maps the legacy single-letter tier to the NEW vocabulary word. This is
# the canonical mapping — every catalog page that wants to advertise WHO
# BUILT THIS uses the new vocabulary at render time, regardless of what
# the underlying YAML `tier:` field carries.
LEGACY_TIER_TO_NEW_VOCAB: dict[str, str] = {
    "a": "certified",
    "b": "verified",
    "c": "experimental",
}

# The user-facing label for the new vocabulary. This is the prose Bernard
# wants a vanlifer to read on the catalog page.
NEW_VOCAB_TO_USER_LABEL: dict[str, str] = {
    "certified": "RoamCore Certified",
    "verified": "Community Verified",
    "experimental": "Experimental",
}

# The short hover-title for the new-vocabulary pill (one short sentence
# explaining who built it). The new vocabulary is intentionally honest:
# "Certified" = RoamCore maintains it end-to-end; "Verified" = a member
# of the community tested it on a real van and it works; "Experimental"
# = it builds but RoamCore hasn't integration-tested it yet.
NEW_VOCAB_TO_TITLE: dict[str, str] = {
    "certified": "RoamCore builds and maintains this end-to-end.",
    "verified": "A member of the community tested this on a real van.",
    "experimental": "It builds but hasn't been integration-tested yet.",
}


# ---------------------------------------------------------------------------
# Public API — the four pure functions the catalog render layer uses.
# ---------------------------------------------------------------------------


def state_chip_class(state: str) -> str:
    """Return the kebab CSS class for a state.

    Raises ValueError if the state is not in the 10-state allowlist.
    Used internally by `format_state_chip()`; exposed so the bash smoke
    can derive the expected class for every connection.yml without
    duplicating the mapping table.

    >>> state_chip_class("Available")
    'available'
    >>> state_chip_class("Ready to connect")
    'ready-to-connect'
    >>> state_chip_class("NotAState")
    Traceback (most recent call last):
        ...
    ValueError: state 'NotAState' is not in the 10-state allowlist [...]
    """
    if not isinstance(state, str) or not state.strip():
        raise ValueError(
            f"state must be a non-blank string from the 10-state "
            f"allowlist; got {state!r}"
        )
    if state not in STATE_TO_KEBAB_CLASS:
        raise ValueError(
            f"state {state!r} is not in the 10-state allowlist "
            f"{sorted(STATE_TO_KEBAB_CLASS)}. The 10 standard states "
            f"are locked in the directive §'Connection states are "
            f"standardized'."
        )
    return STATE_TO_KEBAB_CLASS[state]


def format_state_chip(state: str, reason: Optional[str] = None) -> str:
    """Render a connection state as a coloured chip.

    Output shape:
        <span class="rc-state-chip rc-state-chip--available"
              title="...">Available</span>
        <span class="rc-state-chip-reason">needs setup first</span>

    The `reason` argument is optional. When provided, it renders as a
    second inline span with a short plain-English note (e.g. "needs a
    smart plug" for the Starlink recipe). When None, only the chip
    span is returned.

    Every input is HTML-escaped; names with `<` or `&` survive intact
    in the rendered output as literal text.

    >>> format_state_chip("Available")
    '<span class="rc-state-chip rc-state-chip--available" title="Code is shipped and the device is ready to install.">Available</span>'

    >>> print(format_state_chip("Needs information", "enter your MQTT password"))
    <span class="rc-state-chip rc-state-chip--needs-information" title="The device needs a small piece of information from you.">Needs info</span>
    <span class="rc-state-chip-reason">enter your MQTT password</span>
    """
    css_class = state_chip_class(state)
    label = STATE_TO_CHIP_LABEL[state]
    title = STATE_TO_TITLE[state]
    # The chip itself: full CSS class chain (rc-state-chip + the modifier)
    chip_html = (
        f'<span class="rc-state-chip rc-state-chip--{css_class}" '
        f'title="{html.escape(title, quote=True)}">'
        f'{html.escape(label)}</span>'
    )
    if reason is None or not str(reason).strip():
        return chip_html
    # The reason is a short plain-English note rendered as a separate
    # inline span. Trimmed of leading/trailing whitespace; HTML-escaped.
    trimmed = str(reason).strip()
    return (
        chip_html
        + '\n<span class="rc-state-chip-reason">'
        + html.escape(trimmed)
        + '</span>'
    )


def normalize_tier(tier: str) -> str:
    """Return the new-vocabulary word for a tier input.

    Accepts both the legacy a/b/c vocabulary and the new
    certified/verified/experimental vocabulary. Returns the
    new-vocabulary word (the canonical form).

    Raises ValueError for any other input.

    >>> normalize_tier("a")
    'certified'
    >>> normalize_tier("certified")
    'certified'
    >>> normalize_tier("experimental")
    'experimental'
    """
    if not isinstance(tier, str) or not tier.strip():
        raise ValueError(
            f"tier must be a non-blank string from either vocabulary; "
            f"got {tier!r}"
        )
    raw = tier.strip()
    # Legacy vocabulary: single letter a/b/c.
    if raw.lower() in LEGACY_TIER_LETTERS:
        return LEGACY_TIER_TO_NEW_VOCAB[raw.lower()]
    # New vocabulary: long word certified/verified/experimental.
    if raw in NEW_VOCAB_TO_USER_LABEL:
        return raw
    # Case-insensitive fallback for the new vocabulary (helps the smoke
    # accept "Certified" from copy-paste).
    lowered = raw.lower()
    if lowered in NEW_VOCAB_TO_USER_LABEL:
        return lowered
    raise ValueError(
        f"tier {tier!r} is not in either vocabulary "
        f"(legacy: {LEGACY_TIER_LETTERS}; new: "
        f"{sorted(NEW_VOCAB_TO_USER_LABEL)}). The new vocabulary is "
        f"the canonical user-facing label."
    )


def format_tier_chip(tier: str) -> str:
    """Render a tier as a small pill that names WHO BUILT THIS.

    Accepts both vocabularies (`a` or `certified`, etc.) and returns
    the new-vocabulary pill — the legacy vocabulary is internally
    mapped to the new vocabulary at render time, so the catalog
    always reads "RoamCore Certified / Community Verified /
    Experimental" regardless of what the YAML `tier:` field carries.

    Output shape:
        <span class="rc-tier rc-tier--verified" title="...">Community Verified</span>

    >>> format_tier_chip("b")
    '<span class="rc-tier rc-tier--verified" title="A member of the community tested this on a real van.">Community Verified</span>'

    >>> format_tier_chip("certified")
    '<span class="rc-tier rc-tier--certified" title="RoamCore builds and maintains this end-to-end.">RoamCore Certified</span>'
    """
    new_vocab = normalize_tier(tier)
    label = NEW_VOCAB_TO_USER_LABEL[new_vocab]
    title = NEW_VOCAB_TO_TITLE[new_vocab]
    # Both .rc-tier and .rc-chip accept the same modifier classes —
    # .rc-tier is the catalog pill, .rc-chip is the dashboard badge.
    return (
        f'<span class="rc-tier rc-tier--{html.escape(new_vocab)} '
        f'rc-chip rc-chip--{html.escape(new_vocab)}" '
        f'title="{html.escape(title, quote=True)}">'
        f'{html.escape(label)}</span>'
    )


def format_connect_button(slug: str, label: Optional[str] = None) -> str:
    """Render a one-tap Connect button linking to a device's setup page.

    `slug` is the device id from the YAML `id:` field (e.g. "starlink",
    "mqtt"). The button renders as an anchor pointing to the docs
    page for that device; MkDocs resolves the link at build time.

    `label` defaults to "Connect". Override for special-case copy
    ("Set up", "Open", "View", "Wake").

    Output shape:
        <a class="rc-connect-button" href="...">Connect →</a>

    >>> format_connect_button("starlink")
    '<a class="rc-connect-button" href="starlink/" title="Open the setup page for Starlink">Connect →</a>'
    """
    if not isinstance(slug, str) or not slug.strip():
        raise ValueError(
            f"slug must be a non-blank string from the connection's "
            f"YAML `id:` field; got {slug!r}"
        )
    safe_slug = html.escape(slug.strip(), quote=True)
    if label is None or not str(label).strip():
        safe_label = "Connect"
        arrow = " →"
    else:
        safe_label = str(label).strip()
        # Don't append an arrow if the operator already wrote one.
        arrow = "" if safe_label.endswith(("→", "->", "&rarr;")) else " →"
    href = f"{safe_slug}/"
    return (
        f'<a class="rc-connect-button" href="{href}" '
        f'title="Open the setup page for {safe_slug}">'
        f'{html.escape(safe_label)}{arrow}</a>'
    )


def format_connection_card(
    name: str,
    slug: str,
    tier: str,
    state: str,
    reason: Optional[str] = None,
    connect_label: Optional[str] = None,
) -> str:
    """Compose all three primitives into a single horizontal row.

    Output shape (one `<div class="rc-state-chip-row">` wrapping a
    chip, a tier pill, and a connect button — ready to paste into any
    catalog page's Markdown with the `attr_list` + `md_in_html`
    extensions enabled, which MkDocs ships by default):

        <div class="rc-state-chip-row">
          <span class="rc-state-chip ...">Available</span>
          <span class="rc-tier ...">RoamCore Certified</span>
          <a class="rc-connect-button" href="...">Connect →</a>
        </div>

    >>> print(format_connection_card("Starlink", "starlink", "b", "Available"))
    <div class="rc-state-chip-row">
      <span class="rc-state-chip rc-state-chip--available" title="Code is shipped and the device is ready to install.">Available</span>
      <span class="rc-tier rc-tier--verified rc-chip rc-chip--verified" title="A member of the community tested this on a real van.">Community Verified</span>
      <a class="rc-connect-button" href="starlink/" title="Open the setup page for starlink">Connect →</a>
    </div>

    Every input is HTML-escaped. The slug is treated as already-safe
    (a connection `id:` is always kebab-case ASCII per the manifest
    schema); the name + reason + tier + state are escaped.
    """
    chip = format_state_chip(state, reason)
    pill = format_tier_chip(tier)
    button = format_connect_button(slug, connect_label)
    safe_name = html.escape(name)
    return (
        f'<div class="rc-state-chip-row" data-connection-name="{safe_name}">\n'
        f'  {chip}\n'
        f'  {pill}\n'
        f'  {button}\n'
        f'</div>'
    )


# ---------------------------------------------------------------------------
# CLI smoke — runnable as `python3 scripts/connection_card.py --smoke`.
# Prints the 10 state chips + 3 tier chips + a sample card so the bash
# smoke + a human operator can both eyeball the output.
# ---------------------------------------------------------------------------


def _smoke() -> int:
    """Print the 10 state chips + 3 tier chips + a sample card.

    Returns 0 on success. The bash smoke greps for the literal class
    names to assert presence; a human operator can eyeball the output
    in a terminal to sanity-check the look.
    """
    print("# 10 state chips")
    for state in STANDARD_STATES:
        print(format_state_chip(state))
    print()
    print("# State chip with reason (Needs information + reason)")
    print(format_state_chip("Needs information", "enter your MQTT password"))
    print()
    print("# 3 tier chips (new vocabulary)")
    for vocab in ("certified", "verified", "experimental"):
        print(format_tier_chip(vocab))
    print()
    print("# 3 tier chips (legacy vocabulary mapped to new)")
    for letter in LEGACY_TIER_LETTERS:
        print(format_tier_chip(letter))
    print()
    print("# Sample composed connection card (Starlink, tier-b, Available)")
    print(format_connection_card(
        name="Starlink",
        slug="starlink",
        tier="b",
        state="Available",
    ))
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="connection_card",
        description=(
            "RoamCore catalog UI: render a state chip + tier pill + "
            "Connect button (or print a smoke sample with --smoke)."
        ),
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help=(
            "Print the 10 standard state chips + 3 tier chips + a "
            "sample card to stdout. The bash smoke greps the output "
            "for the literal class names; a human can eyeball it."
        ),
    )
    args = parser.parse_args(argv)
    if args.smoke:
        return _smoke()
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())