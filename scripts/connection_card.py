"""Connection card HTML emitter — pure helper for the connection catalogue UI.

Wave 9 #118 — Phase 1 catalog UI foundation.

This module is a *pure* Python helper: no I/O, no network, no filesystem.
It exists so the connection catalogue can render a consistent state chip,
tier chip and Connect button for any connection, without duplicating the
HTML/CSS contract across every page in the repo.

The 10 standard states (literal from
`memory/roamcore/2026-08-03-directive.md` §"Connection states are
standardized") are exposed as the `STANDARD_STATES` tuple. The matching
CSS classes (`.rc-state-chip.<kebab-case>`) live in `docs/styles/rc.css`
and are enforced by `scripts/checks/catalog-state-chip-smoke.sh`.

Tier vocabulary (Wave 9 #117 rebrand): legacy `tier: a|b|c` letter sort
keys survive as `.rc-tier.a|.b|.c` classes (kept for backward
compatibility with sister catalog pages that still emit
`data-tier="a|b|c"` attribute filters). The user-facing labels
"RoamCore Certified" / "Community Verified" / "Experimental" map onto
`.rc-tier.certified|verified|experimental` (and the equivalent
`.rc-chip.*` filter chips). `format_tier_chip` accepts both the legacy
letters AND the full-word vocabulary so future catalog pages and the
Starlink demo both render correctly.

Connect button (`format_connect_button`) emits an `<a class="rc-connect-
button" href="/connections/{slug}/connect">…</a>`. The default label is
"Connect"; callers override per-state ("Set up", "Reconnect", "Update",
"Learn more") to match what the operator needs to do next.

Compose the three via `format_connection_card` to render a single block
of HTML suitable for inlining in MkDocs markdown. The MkDocs build is
configured with the `md_in_html` markdown extension (see
`mkdocs.yml`), so raw HTML emitted here passes through unchanged.

Run as a module:
    python3 -m scripts.connection_card --help

Run the smoke:
    python3 -m scripts.connection_card --smoke

(Used by `scripts/checks/catalog-state-chip-smoke.sh` to validate the
helper still emits the 10 standard kebab-case CSS classes.)
"""

from __future__ import annotations

import argparse
import re
import sys

# The 10 standard states from the directive §"Connection states are
# standardized", verbatim. If we ever add a state (e.g. "Syncing",
# "Verifying"), update BOTH this tuple AND the smoke check AND the
# docs/reference/rc-connection-state-chip.md page together; the lockstep
# keeps the chip CSS, the test, and the user-facing docs in sync.
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

# Map each standard state to its kebab-case CSS class fragment. The
# mapping is explicit (not derived) so the directive's literal
# vocabulary and the chip-CSS contract are visually auditable side by
# side. Order matches STANDARD_STATES so a maintainer can read top-to-
# bottom and verify each row.
_STATE_KEBAB: dict[str, str] = {
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

# Tier vocabulary. Legacy `a|b|c` letter sort keys survive (kept for
# backward compatibility with sister catalog pages that still emit
# `data-tier="a|b|c"` attribute filters); the full-word vocabulary is
# the user-facing label surfaced on every page. `format_tier_chip`
# accepts BOTH forms and picks the right CSS class + label pair.
_LETTER_TO_FULLWORD: dict[str, str] = {
    "a": "certified",
    "b": "verified",
    "c": "experimental",
}
_LETTER_TO_LABEL: dict[str, str] = {
    "a": "RoamCore Certified",
    "b": "Community Verified",
    "c": "Experimental",
}
_FULLWORD_TO_LABEL: dict[str, str] = {
    "certified":    "RoamCore Certified",
    "verified":     "Community Verified",
    "experimental": "Experimental",
}
_VALID_TIER_INPUTS: frozenset[str] = frozenset(
    list(_LETTER_TO_FULLWORD) + list(_FULLWORD_TO_LABEL)
)


def _html_escape(text: str) -> str:
    """Escape user-supplied copy for safe HTML emission.

    The catalog is hand-curated today, but `format_state_chip` /
    `format_connection_card` accept arbitrary strings (state_reason,
    name) and a future bulk-import path might pull them from connection
    manifests authored by anyone. Escaping at emission is the cheapest
    place to defend against a rogue `<script>` tag or quote.
    """
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
    )


def _slug_kebab(slug: str) -> str:
    """Validate a connection slug for safe inclusion in an href.

    Slugs come from `connections/<slug>/connection.yml` folder names —
    today they're hand-curated ASCII, but `format_connect_button`
    builds an `href` from them, so we belt-and-braces verify the slug
    is a non-empty kebab-case identifier before splicing it in. A
    malformed slug raises ValueError; callers don't catch it.
    """
    if not isinstance(slug, str) or not slug:
        raise ValueError("connection slug must be a non-empty string")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug):
        raise ValueError(
            f"connection slug {slug!r} is not a valid kebab-case "
            f"identifier (allowed: a-z, 0-9, '-'; must start with a-z or 0-9)"
        )
    return slug


def format_state_chip(
    state: str,
    state_reason: str | None = None,
) -> str:
    """Emit a connection-state chip as raw HTML.

    Returns a `<span class="rc-state-chip rc-state-{kebab-case}">…</span>`
    block. When `state_reason` is provided, a small subtitle span
    (`<span class="rc-state-chip-reason">…</span>`) is appended on the
    next line so the catalog auditor / operator can see why the
    connection is in its declared state.

    Raises ValueError when `state` is not one of the 10 standard states
    — drift (lowercase, "live", "wired", …) MUST be surfaced loudly so
    the connection manifest is fixed; we don't silently emit a chip
    that won't render.
    """
    if state not in _STATE_KEBAB:
        valid = ", ".join(sorted(_STATE_KEBAB))
        raise ValueError(
            f"unknown connection state {state!r}; expected one of "
            f"the 10 standard states ({valid}). Update the "
            f"connection's `state:` value to match the directive §"
            f"'Connection states are standardized'."
        )
    kebab = _STATE_KEBAB[state]
    safe_label = _html_escape(state)
    html = (
        f'<span class="rc-state-chip {kebab}">{safe_label}</span>'
    )
    if state_reason is not None:
        if not isinstance(state_reason, str) or not state_reason.strip():
            raise ValueError(
                "state_reason, when provided, MUST be a non-empty "
                "plain-English string explaining WHY the connection "
                "is in its declared state"
            )
        html += (
            f'\n<span class="rc-state-chip-reason">'
            f"{_html_escape(state_reason)}</span>"
        )
    return html


def format_tier_chip(tier: str) -> str:
    """Emit a tier (support-level) chip as raw HTML.

    Accepts BOTH the legacy `a|b|c` letter sort key AND the full-word
    vocabulary (`certified|verified|experimental`) — `format_tier_chip`
    picks the right CSS class + label pair. Returns a
    `<span class="rc-tier {variant}">…</span>` block.

    Raises ValueError on an unknown tier. The catalog's
    `data-tier="a|b|c"` attribute filters depend on the legacy letters
    surviving; full-word vocabulary adds the user-facing surface. Both
    paths render correctly side by side.
    """
    if not isinstance(tier, str) or not tier:
        raise ValueError(
            "tier must be a non-empty string (legacy 'a'|'b'|'c' "
            "or full-word 'certified'|'verified'|'experimental')"
        )
    t = tier.strip().lower()
    if t in _LETTER_TO_FULLWORD:
        variant = _LETTER_TO_FULLWORD[t]
        label = _LETTER_TO_LABEL[t]
    elif t in _FULLWORD_TO_LABEL:
        variant = t
        label = _FULLWORD_TO_LABEL[t]
    else:
        raise ValueError(
            f"unknown tier {tier!r}; expected legacy 'a'|'b'|'c' "
            f"or full-word 'certified'|'verified'|'experimental'. "
            f"Update the connection's `tier:` value to match the "
            f"Wave 9 #117 vocabulary rebrand."
        )
    return f'<span class="rc-tier {variant}">{_html_escape(label)}</span>'


def format_connect_button(slug: str, label: str | None = None) -> str:
    """Emit a Connect button (anchor with `.rc-connect-button` class).

    Returns `<a class="rc-connect-button" href="/connections/{slug}/connect">…</a>`.
    Default label is "Connect"; callers override per-state ("Set up",
    "Reconnect", "Update", "Learn more") to match what the operator
    needs to do next. The slug is validated as kebab-case before
    splicing into the href so a malformed slug surfaces immediately.
    """
    safe_slug = _slug_kebab(slug)
    btn_label = label if label is not None else "Connect"
    if not isinstance(btn_label, str) or not btn_label.strip():
        raise ValueError("Connect-button label must be a non-empty string")
    return (
        f'<a class="rc-connect-button" '
        f'href="/connections/{safe_slug}/connect">'
        f"{_html_escape(btn_label)}</a>"
    )


def format_connection_card(
    slug: str,
    name: str,
    tier: str,
    state: str,
    state_reason: str | None = None,
) -> str:
    """Compose a full connection-card HTML block.

    Wraps the three primitives (state chip + tier chip + Connect
    button) in a single `<div class="rc-state-chip-row">…</div>`
    container so the catalog page can drop one block of HTML and get a
    self-contained, visually consistent row. The `name` is included as
    a sibling `<strong>` so the row is screen-reader-friendly without
    an additional heading.

    Suitable for inlining in MkDocs markdown — the `md_in_html`
    extension is enabled in `mkdocs.yml` so raw HTML passes through
    unchanged.
    """
    if not isinstance(name, str) or not name.strip():
        raise ValueError("connection name must be a non-empty string")
    chip = format_state_chip(state, state_reason)
    tier_chip = format_tier_chip(tier)
    button = format_connect_button(slug)
    return (
        '<div class="rc-state-chip-row">\n'
        f"  <strong>{_html_escape(name)}</strong>\n"
        f"  {chip}\n"
        f"  {tier_chip}\n"
        f"  {button}\n"
        "</div>"
    )


# --- CLI helpers (used by the smoke check + ad-hoc debugging) ----------

def _all_standard_state_chips() -> list[str]:
    """Emit one state chip per standard state, used by `--smoke`."""
    return [format_state_chip(s) for s in STANDARD_STATES]


def _smoke() -> int:
    """Self-check: emit one chip per state + assert the kebab-case
    CSS class appears in each. Exits 0 on success, 1 on any failure.

    Used by `scripts/checks/catalog-state-chip-smoke.sh` to validate
    the helper at every `check.sh` run.
    """
    failed = 0
    for state, chip_html in zip(STANDARD_STATES, _all_standard_state_chips()):
        # The CSS contract is `.rc-state-chip.<kebab-case>` (per the
        # styles appended to docs/styles/rc.css), so the HTML `class`
        # attribute is the literal `"rc-state-chip <kebab-case>"` form.
        # We assert the kebab-case variant of each state appears as a
        # second class on the chip — drift (e.g. lowercase title-case)
        # would skip the kebab mapping and the catalog audit would
        # render an unknown chip.
        expected_kebab = _STATE_KEBAB[state]
        expected_class = f"rc-state-chip {expected_kebab}"
        if expected_class not in chip_html:
            print(
                f"FAIL: chip for state {state!r} missing "
                f"expected class fragment {expected_class!r}: "
                f"{chip_html}",
                file=sys.stderr,
            )
            failed += 1
    if failed:
        return 1
    print(f"OK: {len(STANDARD_STATES)} standard-state chips emitted")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Emit connection-card HTML for the catalogue UI.",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Emit one chip per standard state and exit 0 / 1.",
    )
    args = parser.parse_args(argv)
    if args.smoke:
        return _smoke()
    parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())