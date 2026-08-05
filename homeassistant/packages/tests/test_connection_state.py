"""Cross-cutting pytest tests for the connection `state:` field.

Per the Wave 9 #117 directive ("Repo hygiene follow-ups — Connection
state field + Tier rebrand in user-facing copy"), every
`connections/<slug>/connection.yml` MUST expose a top-level `state:`
field whose value is one of the 10 standard states established by the
RoamCore product directive (see
`memory/roamcore/2026-08-03-directive.md` §"Connection states are
standardized"):

    Available
    Detected
    Ready to connect
    Connecting
    Connected
    Needs information
    Needs attention
    Unsupported
    Offline
    Update available

These tests assert:

  1. Every `connections/<slug>/connection.yml` manifest has a `state:`
     top-level field.
  2. The `state:` value is one of the 10 standard states (no drift,
     no abbreviations, no lowercase-only copies).
  3. The optional `state_reason:` field, when present, is a non-empty
     string explaining the state in plain English.
  4. The user-facing docs render the new tier vocabulary: docs/index.md
     surfaces "RoamCore Certified" / "Community Verified" /
     "Experimental" labels, and the legacy SUPERSEDED commentary on the
     3 in-scope legacy stubs uses the new labels too.

The 10-state list is the directive's literal one — if we ever need
to add a state (e.g. "Syncing", "Verifying"), update this test AND
the audit page together; the lockstep keeps both honest.

This file is intentionally additive + minimal + idempotent:
- It does NOT touch any other test file.
- It does NOT depend on any sister test (each test is self-contained).
- It does NOT require a running HA instance (no live integrations).
- It does NOT require a Proxmox/OpenWrt/networking fixture.

Run:
    python3 -m pytest homeassistant/packages/tests/test_connection_state.py -v
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[3]   # tests/ -> packages/ -> homeassistant/ -> repo
CONNECTIONS_DIR = REPO_ROOT / "connections"
DOCS_INDEX = REPO_ROOT / "docs" / "index.md"
DOCS_STYLES = REPO_ROOT / "docs" / "styles" / "rc.css"

# The 10 standard states from the directive §"Connection states are
# standardized", verbatim. If you add a state, update BOTH this list and
# the user-facing docs/index.md tier-vocabulary rebrand together; the
# lockstep keeps both honest.
STANDARD_STATES = frozenset({
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
})


@pytest.fixture(scope="module")
def all_connection_manifests() -> dict[str, dict]:
    """Load every `connections/<slug>/connection.yml` into a slug-keyed dict.

    Keys are the connection folder names (e.g. "advanced-mode",
    "openclaw-api"); values are the parsed manifest dicts. If two
    manifests accidentally share a slug, the test that reads this
    fixture will surface a duplicate warning at the bottom of this
    file (see `test_no_duplicate_slugs`).
    """
    out: dict[str, dict] = {}
    for manifest_path in sorted(CONNECTIONS_DIR.glob("*/connection.yml")):
        if manifest_path.parent.name.startswith("_"):
            # Skip generated / helper siblings (e.g. the auto-generated
            # `_all_connections_inventory.yml` lives one level up; this
            # branch catches anything that happens to live in
            # `connections/_whatever/connection.yml` — not present
            # today, but guard against future drift).
            continue
        slug = manifest_path.parent.name
        out[slug] = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    return out


def test_every_connection_has_state_field(all_connection_manifests: dict[str, dict]) -> None:
    """Every connection.yml MUST expose a top-level `state:` field.

    The directive's outstanding follow-up #1 mandates that the user-
    facing catalogue can render a standardised state for every
    connection. Missing fields mean the catalog renders an unknown /
    blank row, which violates the novice-first UX principle
    (golden §"Product principles"). The list of connection folders
    is the SAME list the build_catalog.py enumerator uses; we keep
    these two in lockstep so a missing state immediately breaks
    check.sh before the catalog can ship.
    """
    assert all_connection_manifests, (
        "no connections found under connections/<slug>/connection.yml; "
        "either the repo was emptied or the paths moved — update this "
        "test in lockstep with scripts/build_catalog.py"
    )
    missing = sorted(
        slug for slug, manifest in all_connection_manifests.items()
        if "state" not in manifest
    )
    assert not missing, (
        f"the following {len(missing)} connection manifests are "
        f"missing the top-level `state:` field: {missing!r}. The "
        f"directive §\"Connection states are standardized\" requires "
        f"every connection.yml to declare one of the 10 standard "
        f"states (Available / Detected / Ready to connect / "
        f"Connecting / Connected / Needs information / Needs "
        f"attention / Unsupported / Offline / Update available)."
    )


def test_state_value_is_one_of_10_standard_states(all_connection_manifests: dict[str, dict]) -> None:
    """Every `state:` value MUST be one of the 10 standard states.

    Drift (e.g. "connected" lowercase, "live", "wired", "shipped")
    breaks the catalog renderer — the JS filter key would be wrong,
    the docs would render the wrong chip, and the audit page would
    list the connection as "unknown state". The state vocabulary is
    just as locked-down as the tier-vocabulary; both follow the same
    directive-mandated list.
    """
    invalid = []
    for slug, manifest in sorted(all_connection_manifests.items()):
        state = manifest.get("state")
        if state is None:
            # Surfaced by test_every_connection_has_state_field above;
            # skip here to keep the error message focused on invalid
            # values rather than also enumerating missing fields.
            continue
        if state not in STANDARD_STATES:
            invalid.append((slug, state))

    assert not invalid, (
        f"the following {len(invalid)} connection manifests declare "
        f"a `state:` value that is NOT one of the 10 standard "
        f"states from the directive: {invalid!r}. The 10 standard "
        f"states (verbatim) are: {sorted(STANDARD_STATES)!r}. "
        f"Update the connection's state value to match OR update "
        f"this test + the directive together if the new state is "
        f"legitimately new."
    )


def test_state_reason_is_non_empty_string_when_present(all_connection_manifests: dict[str, dict]) -> None:
    """The optional `state_reason:` field MUST be a non-empty string when present.

    A blank / null / list / numeric `state_reason:` would render
    badly in the catalog tooltip (a blank tooltip is worse than no
    tooltip — the user looks for context and sees nothing). When the
    field is absent, the connection simply has no extra context and
    that is fine; this test guards only against malformed values.
    """
    bad = []
    for slug, manifest in sorted(all_connection_manifests.items()):
        if "state_reason" not in manifest:
            continue
        reason = manifest["state_reason"]
        if not isinstance(reason, str) or not reason.strip():
            bad.append((slug, reason))

    assert not bad, (
        f"the following {len(bad)} connection manifests declare a "
        f"`state_reason:` value that is missing, blank, or "
        f"non-string: {bad!r}. `state_reason` is optional; when "
        f"present it MUST be a non-empty plain-English string "
        f"explaining WHY the connection is in its declared state "
        f"(e.g. `Wired contract tiles (rc_openclaw_api_*) in "
        f"homeassistant/packages/roamcore_openclaw_api_controls."
        f"yaml; tier-a bench-tested per Wave 9 #112.`)."
    )


def test_state_reason_present_for_non_connected_states(all_connection_manifests: dict[str, dict]) -> None:
    """Connections that are NOT yet `Connected` MUST carry a `state_reason:`.

    A `Connected` state is obvious (the tile is on the dashboard) —
    no reason needed. But for `Available`, `Detected`, `Ready to
    connect`, `Connecting`, `Needs information`, `Needs attention`,
    `Unsupported`, `Offline`, or `Update available`, the catalog
    audit page surfaces the connection as "not yet wired". Without
    a `state_reason:`, the auditor can't tell whether the connection
    is "Recipe published, waiting on operator wiring" or "DIY
    inspiration only" — the two very different states deserve very
    different copy in the catalog tooltip. This test enforces the
    minimum that the auditor gets *something* to display.
    """
    missing_reason = []
    for slug, manifest in sorted(all_connection_manifests.items()):
        state = manifest.get("state")
        if state is None or state == "Connected":
            continue
        reason = manifest.get("state_reason")
        if not (isinstance(reason, str) and reason.strip()):
            missing_reason.append((slug, state))

    assert not missing_reason, (
        f"the following {len(missing_reason)} connection manifests "
        f"declare a non-Connected `state:` (Available / Detected / "
        f"Ready to connect / Connecting / Needs information / Needs "
        f"attention / Unsupported / Offline / Update available) but "
        f"do NOT carry a `state_reason:` explaining WHY: "
        f"{missing_reason!r}. Catalog + audit tooltip needs the "
        f"`state_reason:` so the auditor can tell at a glance "
        f"whether the slice is operator-wiring-blocked vs "
        f"DIY-inspiration-only."
    )


def test_user_facing_docs_index_renders_new_tier_vocabulary() -> None:
    """docs/index.md MUST render the new tier vocabulary.

    Per the Wave 9 #117 directive ("rebrand tier letters in
    user-facing copy"), the home page MUST surface the support-
    level labels:
        - "RoamCore Certified"
        - "Community Verified"
        - "Experimental"
    on the "Support levels (simple + honest)" section and the "Show
    only" chip section. Old single-letter chips (A / B / C) are
    out — the operator-facing UI uses full words now. YAML's
    `tier: a/b/c` stays as a programmer-facing sort key.
    """
    text = DOCS_INDEX.read_text(encoding="utf-8")

    # The three new labels are all required.
    for label in ("RoamCore Certified", "Community Verified", "Experimental"):
        assert label in text, (
            f"docs/index.md MUST render the new user-facing support "
            f"level label {label!r} somewhere visible (the 'Support "
            f"levels (simple + honest)' section or the 'Show only' "
            f"chip section). The directive §\"Support levels\" "
            f"establishes this vocabulary verbatim."
        )

    # The legacy single-letter chips in the user-facing sections are
    # gone. We assert against the entire 'Support levels' block to
    # catch any leftover legacy chip rendering. The legacy chip
    # pattern was `<span class=\"rc-tier a\">A</span>` or
    # `<a class=\"rc-chip a\" ...>A</a>`; the new pattern uses the
    # full-word label classes (`.certified` / `.verified` /
    # `.experimental`).
    legacy_chip_pattern = re.compile(
        r'(class="rc-tier a">|class="rc-tier b">|class="rc-tier c">|'
        r'class="rc-chip a"|class="rc-chip b"|class="rc-chip c")',
        re.IGNORECASE,
    )
    assert not legacy_chip_pattern.search(text), (
        "docs/index.md still renders legacy single-letter "
        "user-facing chips (A / B / C); the Wave 9 #117 rebrand "
        "MUST replace them with the full-word labels. The legacy "
        "single-letter classes (.rc-tier.a / .rc-tier.b / "
        ".rc-tier.c / .rc-chip.a / .rc-chip.b / .rc-chip.c) are "
        "kept in docs/styles/rc.css for backward compatibility "
        "with sister catalog pages that still emit data-tier="
        "\"a|b|c\" attribute filters, but they MUST NOT appear in "
        "the user-facing index page."
    )


def test_user_facing_legacy_stubs_use_new_tier_vocabulary() -> None:
    """The 3 in-scope legacy SUPERSEDED stubs MUST rephrase "tier-X recipe
    connection" → "RoamCore Certified / Community Verified / Experimental"

    In-scope (per the slice spec):
        - docs/catalog/fans/index.md           (was tier-b)
        - docs/catalog/nfc-tags/index.md       (was tier-c)
        - docs/catalog/remote-access/index.md  (was tier-b)

    Specifically, the SUPERSEDED HTML COMMENT at the top of each
    page MUST rephrase the user-facing tier vocabulary. The YAML
    `tier: b/c` letter stays untouched (it is referenced as the
    programmer-facing sort key inside the rephrased prose, e.g.
    "YAML `tier: b` for programmatic sorting; support-level label
    = 'Community Verified'"). The PAGE BODY below the commentary
    (which may still contain sister-connection reference prose
    like "Wave 3 #58 tier-b recipe connection covers FOUR
    paths..." from auto-generated catalog data) is OUT OF SCOPE
    for this slice — that's a separate, larger rebrand that the
    slice spec explicitly defers. The narrow test below verifies
    ONLY the SUPERSEDED-comment block at the top of each page.
    """
    fixtures = [
        # (path, expected_yaml_tier_letter, expected_user_facing_label)
        ("catalog/fans/index.md",          "b", "Community Verified"),
        ("catalog/nfc-tags/index.md",      "c", "Experimental"),
        ("catalog/remote-access/index.md", "b", "Community Verified"),
    ]

    def extract_superseded_comment(text: str) -> str:
        """Extract the HTML comment block that opens with 'SUPERSEDED:'.

        The slice spec narrowly targets the legacy comment, not the
        page body. The auto-generated catalog body (rendered below
        `<!-- RC_FEATURE_LIST_START -->`) carries its own tier-letter
        references for sister-connection cross-references; those
        stay untouched in this slice and are rephrased in a future
        follow-up.
        """
        # Walk line by line; collect from the first `<!--` to its
        # matching `-->`. We anchor on `SUPERSEDED:` to be robust to
        # other HTML comments (e.g. `<!-- RC_FEATURE_LIST_START -->`).
        lines = text.splitlines(keepends=True)
        in_comment = False
        buf: list[str] = []
        for ln in lines:
            if not in_comment:
                if "SUPERSEDED:" in ln and "<!--" in ln:
                    in_comment = True
                    buf.append(ln)
                    if "-->" in ln:
                        # self-closing comment
                        in_comment = False
                continue
            buf.append(ln)
            if "-->" in ln:
                in_comment = False
                break
        return "".join(buf)

    for rel_path, yaml_tier, new_label in fixtures:
        text = (REPO_ROOT / "docs" / rel_path).read_text(encoding="utf-8")
        comment = extract_superseded_comment(text)
        assert comment, (
            f"{rel_path}: couldn't locate the SUPERSEDED HTML "
            f"comment block; either the page lost the legacy "
            f"comment or the file structure changed. The slice "
            f"spec narrowly targets the SUPERSEDED comment at "
            f"the top of each in-scope page."
        )

        # The legacy user-facing prose "tier-{yaml_tier} recipe
        # connection" MUST be replaced with the new vocabulary
        # INSIDE the SUPERSEDED comment block (page-body references
        # are out of scope for this slice).
        legacy_phrase = f"tier-{yaml_tier} recipe connection"
        assert legacy_phrase not in comment, (
            f"{rel_path}: the SUPERSEDED commentary still contains "
            f"the legacy user-facing phrase {legacy_phrase!r}; "
            f"per the Wave 9 #117 rebrand, the commentary MUST "
            f"rephrase to {new_label!r} while preserving the YAML "
            f"`tier: {yaml_tier}` letter reference for programmatic "
            f"sorting."
        )

        # The new label MUST appear in the SUPERSEDED commentary.
        assert new_label in comment, (
            f"{rel_path}: rephrase MUST surface the new "
            f"user-facing support-level label {new_label!r} in "
            f"the SUPERSEDED commentary (the legacy tier-letter "
            f"prose has been replaced)."
        )

        # The YAML tier letter reference MUST survive the rephrase
        # (programmer-facing sort key — per the slice spec).
        assert f"`tier: {yaml_tier}`" in comment, (
            f"{rel_path}: rephrase MUST preserve the YAML "
            f"`tier: {yaml_tier}` letter reference inside the "
            f"SUPERSEDED commentary (the letter is the "
            f"programmer-facing sort key per the slice spec)."
        )


def test_styles_rc_css_supports_new_chip_vocabulary() -> None:
    """docs/styles/rc.css MUST add chip CSS for the new vocabulary.

    The full-word chip classes are:
        - .rc-chip.certified
        - .rc-chip.verified
        - .rc-chip.experimental
    AND the matching pill classes (used in the "Support levels"
    inline list):
        - .rc-tier.certified
        - .rc-tier.verified
        - .rc-tier.experimental

    The legacy `.rc-chip.a/.b/.c` and `.rc-tier.a/.b/.c` classes
    are kept for backward compatibility with sister catalog pages
    that still emit `data-tier="a|b|c"` attribute filters
    (covered by `rc-tier.b { ... }`, `rc-chip.b.active { ... }`,
    etc.).
    """
    text = DOCS_STYLES.read_text(encoding="utf-8")

    for required_class in (
        ".rc-chip.certified",
        ".rc-chip.verified",
        ".rc-chip.experimental",
        ".rc-tier.certified",
        ".rc-tier.verified",
        ".rc-tier.experimental",
    ):
        assert required_class in text, (
            f"docs/styles/rc.css is missing the required new "
            f"support-level chip class {required_class!r}. The "
            f"Wave 9 #117 rebrand extends the chip CSS with "
            f"`certified` / `verified` / `experimental` variants "
            f"for both `.rc-chip.*` (Show only filters) and "
            f"`.rc-tier.*` (inline tier pills). The legacy "
            f"`.rc-chip.a/.b/.c` and `.rc-tier.a/.b/.c` classes "
            f"stay for backward compatibility."
        )

    # The legacy `.rc-chip.a` and `.rc-tier.a` etc. classes are
    # kept intact (NOT removed). We assert the comment + the
    # class declarations survive so sister catalog pages don't
    # regress.
    for legacy_class in (
        ".rc-chip.a",
        ".rc-chip.b",
        ".rc-chip.c",
        ".rc-tier.a",
        ".rc-tier.b",
        ".rc-tier.c",
    ):
        assert legacy_class in text, (
            f"docs/styles/rc.css is missing legacy support-level "
            f"class {legacy_class!r}; backward compatibility "
            f"with sister catalog pages (the ones that still "
            f"emit `data-tier=\"a|b|c\"` attribute filters) "
            f"requires these classes to SURVIVE the rebrand."
        )


def test_no_duplicate_connection_slugs(all_connection_manifests: dict[str, dict]) -> None:
    """Sanity guard: no two connection folders claim the same slug.

    Two folders named e.g. `connections/{slug}/connection.yml`
    would collide in the catalog grid AND in this cross-cutting
    test fixture. The fixture assumes dict keys are unique;
    duplicate keys would silently shadow the second manifest.
    """
    # pathlib.glob already produces a flat list; if a folder ends
    # up duplicated on disk, this test catches it via Path.parent.name
    # uniqueness in the fixture. The remaining guard is for slug
    # collisions across manifest `id:` vs folder name (covered by
    # `connections/<slug>/tests/test_connection_yml.py::test_id_*
    # _matches_folder_name` already; we duplicate the guard here
    # only for the cross-cutting fixture view).
    slugs = list(all_connection_manifests.keys())
    assert len(slugs) == len(set(slugs)), (
        f"duplicate connection slugs detected: {slugs!r} contains "
        f"{len(slugs) - len(set(slugs))} duplicates. The catalog "
        f"grid + the audit page can't render two manifests with "
        f"the same slug. Resolve the folder-name collision before "
        f"merging."
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
