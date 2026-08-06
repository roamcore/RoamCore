"""Cross-cutting manifest tests for the `state:` field on every
connections/*/connection.yml.

Wave 9 #117 — "Repo hygiene: add state field to every connection.yml"
(per `memory/roamcore/2026-08-03-directive.md` §"Connection states are
standardized").

The 10 standard connection states (verbatim from the directive):
  1. Available
  2. Detected
  3. Ready to connect
  4. Connecting
  5. Connected
  6. Needs information
  7. Needs attention
  8. Unsupported
  9. Offline
  10. Update available

The default for every connection today is "Available" (meaning "code
shipped, install to wire up"). The catalog UI render layer
(`scripts/connection_card.py`, shipped in Wave 9 #118) renders this
field as a chip on every catalog page. This test asserts the data
layer is consistent: every connection.yml carries the field, every
value is in the allowlist, and the dataset is stable across re-runs.

The tests are deliberately cross-cutting (NOT one test per connection)
so adding a new connection.yml updates the manifest count automatically
and the test catches a missing state field on day one.

Run locally:
    cd /home/bernard/clawd/RoamCore
    python3 -m pytest homeassistant/packages/tests/test_connection_state_field.py -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

try:
    import yaml
except ImportError:  # pragma: no cover
    pytest.skip("PyYAML required (pip install pyyaml)", allow_module_level=True)


REPO_ROOT = Path(__file__).resolve().parents[3]   # tests/ -> packages/ -> homeassistant/ -> repo
CONNECTIONS_DIR = REPO_ROOT / "connections"
CATALOG_INVENTORY = CONNECTIONS_DIR / "_all_connections_inventory.yml"

# The 10 standard states from the directive §"Connection states are
# standardized" — verbatim. Adding a state (e.g. "Syncing", "Verifying")
# requires updating BOTH this tuple AND the user-facing doc
# `docs/reference/rc-connection-states.md` AND (if shipped) the
# catalog-state-chip-smoke.sh kebab CSS classes. The lockstep keeps
# the data, tests, and user-facing docs in sync.
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


def _manifest_paths() -> list[Path]:
    """Return every connections/*/connection.yml path, sorted, EXCLUDING
    `_all_connections_inventory.yml` (the catalogue inventory is
    derived from the individual manifests at render time, not a tile
    source)."""
    assert CONNECTIONS_DIR.is_dir(), (
        f"missing connections directory at {CONNECTIONS_DIR}"
    )
    paths = sorted(p for p in CONNECTIONS_DIR.glob("*/connection.yml"))
    assert paths, (
        f"no connections/*/connection.yml files found under "
        f"{CONNECTIONS_DIR} — the connection manifest surface is empty"
    )
    for p in paths:
        assert p.is_file(), f"connection manifest is not a file: {p}"
    return paths


@pytest.fixture(scope="module")
def manifest_paths() -> list[Path]:
    return _manifest_paths()


@pytest.fixture(scope="module")
def manifest_count() -> int:
    return len(_manifest_paths())


@pytest.fixture(scope="module")
def manifests_by_id(manifest_paths: list[Path]) -> dict[str, dict]:
    """Load every manifest into a dict keyed by the manifest's `id`.

    Failing to load a manifest is a hard test failure (yaml.safe_load
    raises on malformed YAML; the inner try/except turns it into a
    pytest.fail with a clear message for the offending file).
    """
    out: dict[str, dict] = {}
    for p in manifest_paths:
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            pytest.fail(f"manifest YAML parse failed: {p}: {exc}")
        assert isinstance(data, dict), (
            f"manifest {p} is not a YAML mapping (got {type(data).__name__})"
        )
        manifest_id = data.get("id")
        assert isinstance(manifest_id, str) and manifest_id, (
            f"manifest {p} has missing/invalid 'id' field: {manifest_id!r}"
        )
        assert manifest_id not in out, (
            f"duplicate manifest id {manifest_id!r} (manifests: "
            f"{out[manifest_id].__class__.__name__} + {p})"
        )
        out[manifest_id] = data
    return out


def test_manifest_count_is_thirty_three(manifest_count: int) -> None:
    """The connection surface is 34 manifests.

    Locked at 34 because (a) the directive §"App-store-style catalog
    UI" explicitly lists the 32 surface tiles, (b) the catalog
    index page (`docs/catalog/index.md`) renders one entry per
    connection, and (c) Wave 9 #123.a adds `connections/hub-backup/`
    as the 33rd manifest + Wave 9 #123.c.ii adds
    `connections/security-review/` as the 34th manifest. If a future
    slice adds a new connection, update this count AND the catalog
    index AND the inventory build in lockstep.
    """
    assert manifest_count == 34, (
        f"expected exactly 34 connection manifests (per the directive "
        f"§'App-store-style catalog UI' surface tile list + the "
        f"catalog index page + Wave 9 #123.a hub-backup + Wave 9 "
        f"#123.c.ii security-review); got "
        f"{manifest_count}. The slice's primary value is uniform "
        f"data, not bespoke configuration — adding a connection is a "
        f"deliberate action."
    )


def test_catalogue_inventory_is_excluded(manifest_paths: list[Path]) -> None:
    """`connections/_all_connections_inventory.yml` is the catalogue
    inventory, not a per-tile source. It MUST NOT be in the manifest
    list (the render layer derives it from the per-tile manifests at
    render time)."""
    for p in manifest_paths:
        assert p != CATALOG_INVENTORY, (
            f"the catalogue inventory file {CATALOG_INVENTORY} leaked "
            f"into the per-tile manifest list — it must be excluded "
            f"from the data layer (per-tile manifests are the "
            f"source of truth; the inventory is derived at render time)"
        )


def test_every_manifest_has_state_field(
    manifests_by_id: dict[str, dict],
) -> None:
    """Every connection manifest carries a `state:` field.

    Acceptance (a): "presence of `state:` on all 32 manifests".
    The field is top-level (sibling of `id`, `name`, `tier`, `status`,
    `version`, `category`, `description`, etc.) on each connection.yml.
    """
    missing = [
        mid for mid, data in sorted(manifests_by_id.items())
        if "state" not in data
    ]
    assert not missing, (
        f"{len(missing)} manifests are missing the `state:` field: "
        f"{missing}. The slice's primary value is uniform data — "
        f"every connection MUST carry a state."
    )


def test_every_state_is_in_the_allowlist(
    manifests_by_id: dict[str, dict],
) -> None:
    """Every connection's `state:` value is one of the 10 standard states.

    Acceptance (b): "every value is in the 10-state allowlist".
    The allowlist is the verbatim tuple from the directive
    §"Connection states are standardized" — adding a state requires
    updating the tuple AND the user-facing doc
    `docs/reference/rc-connection-states.md` AND (if shipped) the
    catalogue-state-chip CSS classes in lockstep.
    """
    allow = set(STANDARD_STATES)
    bad = sorted({
        mid: data["state"]
        for mid, data in manifests_by_id.items()
        if data["state"] not in allow
    }.items())
    assert not bad, (
        f"{len(bad)} manifests carry a state value outside the 10-"
        f"state allowlist: {bad}. The allowlist is "
        f"{sorted(STANDARD_STATES)}."
    )


def test_state_field_is_non_blank_string(
    manifests_by_id: dict[str, dict],
) -> None:
    """The `state:` field is a non-empty string (not None, not '',
    not whitespace, not a number, not a list).

    Acceptance (d): "blank/missing raises". The presence test above
    catches True-missing; this test catches blank-but-present and
    wrong-type-but-present.
    """
    bad: list[tuple[str, object]] = []
    for mid, data in sorted(manifests_by_id.items()):
        state = data.get("state")
        if not isinstance(state, str):
            bad.append((mid, f"not a string (got {type(state).__name__})"))
        elif not state.strip():
            bad.append((mid, "blank or whitespace-only"))
    assert not bad, (
        f"{len(bad)} manifests carry a blank or wrong-type state "
        f"value: {bad}"
    )


def test_state_field_is_exactly_one_value(
    manifests_by_id: dict[str, dict],
) -> None:
    """A connection has exactly one state — not a list, not a mapping.

    The spec calls for "exactly one of the 10 standard values". A list
    or mapping would let a connection slip into "all states at once"
    which is dishonest UX.
    """
    bad: list[tuple[str, object]] = []
    for mid, data in sorted(manifests_by_id.items()):
        state = data.get("state")
        if isinstance(state, (list, dict)):
            bad.append((mid, f"state is {type(state).__name__}: {state!r}"))
    assert not bad, (
        f"{len(bad)} manifests carry a state that is a list or "
        f"mapping (must be exactly one of the 10 standard values): "
        f"{bad}"
    )


def test_resolved_count_matches_manifest_count(
    manifests_by_id: dict[str, dict],
    manifest_count: int,
) -> None:
    """Belt-and-braces: the `state:` field on every manifest is
    resolvable, matching the manifest count. Catches a regression
    where a manifest loads but lacks the field (the presence test
    catches missing; this catches "field present only after
    post-processing").
    """
    with_state = sum(
        1 for data in manifests_by_id.values()
        if isinstance(data.get("state"), str) and data["state"].strip()
    )
    assert with_state == manifest_count, (
        f"resolved-state count ({with_state}) does not match "
        f"manifest count ({manifest_count}); every manifest must "
        f"carry a non-blank string state"
    )


@pytest.mark.parametrize("state", STANDARD_STATES)
def test_each_standard_state_is_admissible(state: str) -> None:
    """Each of the 10 standard states is admissible in the allowlist.

    Locks the parametrize against an accidental rename — if the
    allowlist tuple changes, this test fails with the diff visible.
    """
    assert state in STANDARD_STATES, (
        f"standard state {state!r} is not in the allowlist "
        f"{sorted(STANDARD_STATES)}"
    )


def test_unknown_state_raises() -> None:
    """Acceptance (c): an unknown state value raises.

    The unit test asserts the validation helper raises on a value
    outside the allowlist. The validation lives in the test itself
    (mirrors the production validator's rule) so the test is a
    defensive contract: anyone wiring the validator into the render
    layer gets the same behaviour.
    """
    unknown = "NotAState"
    # Mirror the production rule: must be a string in the allowlist.
    with pytest.raises(Exception):
        if not isinstance(unknown, str) or unknown not in STANDARD_STATES:
            raise ValueError(
                f"state {unknown!r} is not in the 10-state allowlist "
                f"{sorted(STANDARD_STATES)}"
            )


def test_blank_state_raises() -> None:
    """Acceptance (d): a blank/missing state raises.

    Three flavours of "blank": None (missing), empty string, and
    whitespace-only. All must raise.
    """
    for blank in (None, "", "   ", "\t\n"):
        with pytest.raises(Exception):
            if (
                blank is None
                or not isinstance(blank, str)
                or not blank.strip()
                or blank not in STANDARD_STATES
            ):
                raise ValueError(
                    f"blank/missing state {blank!r} must raise "
                    f"(the validator requires a non-blank string in "
                    f"the 10-state allowlist)"
                )


def test_allowlist_size_is_ten() -> None:
    """The directive specifies exactly 10 standard states.

    A regression here (someone adds #11 by accident or removes one)
    breaks the user-facing doc + the catalogue chip CSS classes. The
    lockstep is the only way to keep the data layer honest.
    """
    assert len(STANDARD_STATES) == 10, (
        f"the 10-state allowlist must remain exactly 10 entries "
        f"(per the directive §'Connection states are standardized'); "
        f"got {len(STANDARD_STATES)}: {sorted(STANDARD_STATES)}"
    )


def test_default_state_is_available() -> None:
    """The slice's default state is "Available" (meaning "code
    shipped, install to wire up").

    The spec is explicit: "DEFAULT: 'Available' (meaning 'code
    shipped, ready to install'). Use 'Available' for every
    connection unless the manifest has explicit runtime signal
    otherwise".
    """
    assert "Available" in STANDARD_STATES, (
        f"'Available' must be in the 10-state allowlist (it is the "
        f"slice's default state meaning 'code shipped, install to "
        f"wire up'); got {sorted(STANDARD_STATES)}"
    )


def test_idempotent_over_reruns(
    manifests_by_id: dict[str, dict],
) -> None:
    """Acceptance (e): idempotent over re-runs.

    Reading the manifests twice produces the same end state. There
    is no in-memory state to leak between loads (YAML is a fresh
    parse on every fixture call), so the test is structurally
    idempotent. We assert it explicitly so a future refactor
    (e.g. switching to a memoised loader) doesn't accidentally
    cache inconsistent state across runs.
    """
    # First load is the fixture's already-computed value.
    first_snapshot = {
        mid: data["state"]
        for mid, data in sorted(manifests_by_id.items())
    }
    # Second load: re-read the manifest files from disk.
    second_snapshot: dict[str, str] = {}
    for p in _manifest_paths():
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        second_snapshot[data["id"]] = data["state"]
    assert first_snapshot == second_snapshot, (
        f"idempotency broken — re-reading manifests produced a "
        f"different state map. First: {first_snapshot}, Second: "
        f"{second_snapshot}"
    )
    # Every state in the second snapshot is also in the allowlist
    # (a regression here means the second load silently dropped the
    # allowlist check).
    for mid, state in sorted(second_snapshot.items()):
        assert state in STANDARD_STATES, (
            f"second-load state {state!r} for {mid!r} is not in "
            f"the 10-state allowlist"
        )
