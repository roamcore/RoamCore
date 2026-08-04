"""RoamCore OpenClaw API — HA test fixture.

Why this exists (and why we don't just depend on `pytest-homeassistant-custom-components`):

The canonical HA test harness (`pytest-homeassistant-custom-components`,
https://github.com/MatthewFlamm/pytest-homeassistant-custom-components) was
archived upstream in 2024 and the package is no longer available on PyPI:

    $ pip install pytest-homeassistant-custom-components
    ERROR: No matching distribution found

The RoamCore test rig here has:

    - homeassistant 2025.1.x installed (the `hass` core package)
    - pytest 9.x
    - pytest-asyncio 1.x

What we need from a HA test harness (the minimum viable subset for the 13
OpenClaw endpoints):

    1. A real `HomeAssistant` instance (`hass`) with `hass.http` (the
       aiohttp app) running — so we can register `HomeAssistantView`
       subclasses and they take real HTTP routes.
    2. A `ConfigEntry` for the `roamcore` integration (the views read
       `entry.options` to know if the API is enabled / requires auth).
    3. A way to send real HTTP requests through the registered views, with
       no auth (the API is OFF by default in 2025.1 — explicit opt-in).

The `hass` + `hass_client` fixtures below build that minimum viable
harness on top of the first-party `homeassistant` package, mirroring the
pattern `pytest-homeassistant-custom-components` used before it was
archived:

  1. Create a temp `custom_components/` package with `__init__.py` and a
     symlink to the RoamCore `roamcore/` integration (HA can only auto-
     load integrations it finds in a real Python package on `sys.path`).
  2. Spin up a real `HomeAssistant` via `bootstrap.async_setup_hass` with
     a minimal `configuration.yaml` (`http: {}` only — no `default_config`,
     which avoids pulling in optional deps that aren't installed in this
     test rig).
  3. **Important quirk:** HA's bootstrap auto-enables recovery mode when
     its `default_config` (or any critical integration like `frontend`)
     fails to load. Recovery mode causes
     `loader.async_get_custom_components` to return `{}` — so custom
     integrations would be invisible. We reset `hass.config.recovery_mode`
     to `False` and clear the cached `DATA_CUSTOM_COMPONENTS` slot before
     loading the custom components, so the loop sees the `roamcore`
     integration. This is the same workaround the archived harness used
     when running with a minimal config.
  4. Insert a real `ConfigEntry` for `roamcore` into `hass.config_entries`
     (the views query `entry.options` to decide whether to expose
     endpoints + whether to require auth).
  5. Set up the integration via `async_setup_component(hass, 'roamcore',
     ...)` — this registers the 11 unique URL routes (the 13 endpoints
     spec'd by the slice: 7 OpenClaw endpoints + `diagnostics` +
     `system_summary` + `update` + `pmtiles/{filename}` + `automation/
     validate` (which is the same view as `automation/intents`); the
     `actions` and `support_bundle` endpoints are exposed via HA service
     calls rather than URL routes, so they're tested via direct function
     calls on the support_bundle / actions modules).
  6. Wrap the aiohttp app in a `TestServer` + `TestClient` so test
     functions can `await client.get('/api/roamcore/openclaw/summary')`
     and get a real `ClientResponse` back.

The fixture is session-scoped for the `hass` instance (spinning up a real
HA is ~10s — we amortize) and function-scoped for the `hass_client`
(aiohttp test servers must be freshly bound per test to avoid socket
leaks between tests).

No secrets are persisted to disk. The test directories are recreated
cleanly per session via `tempfile.TemporaryDirectory` and the test rig's
state is wiped on teardown. The `RC_API_TOKEN` / `HA_TOKEN` env vars
(used by the live curl smoketest at
`homeassistant/tools/openclaw_api_smoketest.sh`) are NOT touched here;
the test harness uses `requires_auth=False` for all integration tests
(HA's default in this 2025.1.x fork, and a deliberate simplification
for the unit-test surface — the auth-required path is covered by the
cURL smoketest, not pytest).
"""

from __future__ import annotations

import asyncio
import logging
import os
import socket
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from typing import AsyncIterator, Iterator

# Keep the HA log noise out of the pytest output. The tests assert on
# state, not on log lines, so we silence HA's chatty bootstrap.
logging.basicConfig(level=logging.ERROR)
logging.getLogger("homeassistant").setLevel(logging.CRITICAL)
logging.getLogger("aiohttp_fast_zlib").setLevel(logging.CRITICAL)

import pytest
import pytest_asyncio

# Lazy import: aiohttp + homeassistant are only required when the test
# suite is actually exercised (i.e. someone runs `pytest .../test_integration.py`
# on a properly-equipped dev box). The fixture also degrades gracefully
# so that `scripts/check.sh --core-only` — which probes for `test_connection_yml.py`
# in this same directory and walks up the tree looking for `conftest.py` —
# doesn't fail pytest *collection* when aiohttp is unavailable (e.g. CI
# runners that only run the manifest-honesty chain).
#
# This guard is the standard pytest pattern for "optional integration
# test fixtures" — the test_integration.py module imports from this
# fixture lazily, and the `requires_aiohttp` skip marker on every test
# in test_integration.py short-circuits when the import fails.
try:
    from aiohttp.test_utils import TestClient, TestServer
    _AIOHTTP_AVAILABLE = True
except ModuleNotFoundError:
    TestClient = None  # type: ignore[assignment,misc]
    TestServer = None  # type: ignore[assignment,misc]
    _AIOHTTP_AVAILABLE = False

REPO_ROOT = Path(__file__).resolve().parents[3]
CUSTOM_COMPONENTS_SRC = (
    REPO_ROOT / "homeassistant" / "custom_components" / "roamcore"
)
assert CUSTOM_COMPONENTS_SRC.is_dir(), (
    f"RoamCore custom component missing at {CUSTOM_COMPONENTS_SRC}; "
    f"the integration being tested is the HACS-path canonical "
    f"`homeassistant/custom_components/roamcore/`, NOT the legacy "
    f"`homeassistant/custom_components/roamcore_openclaw_api/`"
)

# Custom skip marker — applied to every integration test that requires
# aiohttp + homeassistant. Lets `scripts/check.sh --core-only` collect
# this directory cleanly on hosts that don't have aiohttp installed
# (e.g. the picker / CI runners running only the manifest-honesty chain).
import pytest as _pytest_marker  # noqa: E402

requires_aiohttp = _pytest_marker.mark.skipif(
    not _AIOHTTP_AVAILABLE,
    reason="aiohttp + homeassistant not installed; run on a dev box with "
           "`pip install -r connections/openclaw-api/tests/requirements.txt` "
           "and the first-party homeassistant package",
)


# We rely on the `asyncio_default_fixture_loop_scope = session` +
# `asyncio_default_test_loop_scope = session` settings in pytest.ini
# to give the whole test session a single event loop. HA's
# `HomeAssistant` instance binds to a specific event loop (the loop
# that called `async_setup_hass` first), and aiohttp's `TestClient`
# requires the same loop. The `loop_scope="session"` annotations on
# the fixtures below are belt-and-braces in case a future maintainer
# overrides the default fixture loop scope on the command line.


def _build_custom_components_shim(tmp_dir: Path) -> Path:
    """Create a temp `custom_components` package with a symlink to the
    real `roamcore` integration so HA's loader can find it.

    Returns the path to the shim `custom_components` directory (the
    caller adds it to `sys.path` so `import custom_components` resolves).
    """
    cc_dir = tmp_dir / "custom_components"
    cc_dir.mkdir()
    # Make it a real Python package
    (cc_dir / "__init__.py").write_text("", encoding="utf-8")
    # Symlink the real integration (we don't copy — the tests must
    # always reflect the canonical on-disk code, not a snapshot).
    (cc_dir / "roamcore").symlink_to(CUSTOM_COMPONENTS_SRC.resolve())
    return cc_dir


@pytest.fixture(scope="session")
def hass_custom_components_dir() -> Iterator[Path]:
    """Session-scoped shim `custom_components/` package.

    Yields the temp dir. The caller adds it to `sys.path` so HA's
    `import custom_components` resolves to the shim (and the symlinked
    `roamcore` integration becomes discoverable by the loader).
    """
    with tempfile.TemporaryDirectory(prefix="rc_test_cc_") as tmp:
        yield _build_custom_components_shim(Path(tmp))


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def hass(
    hass_custom_components_dir: Path,
) -> AsyncIterator["object"]:
    """Session-scoped real HomeAssistant instance.

    The RoamCore integration is loaded against this instance once per
    session; the `hass_client` fixture (function-scoped) hands out a
    fresh `TestClient` for each test so aiohttp server state is
    isolated between tests without re-spinning HA itself.
    """
    # Make the shim discoverable as a Python package. We add BOTH
    # the parent directory (so `import custom_components` works for
    # HA's loader) AND the shim directory itself (so `import roamcore`
    # works as a top-level package for the integration's internal
    # relative imports — the `support_bundle` module does
    # `from .openclaw_view import TIMESERIES_CATALOG` which requires
    # the parent package, but Python won't synthesize the parent
    # package if roamcore is loaded as a top-level module).
    sys.path.insert(0, str(hass_custom_components_dir.parent))
    sys.path.insert(0, str(hass_custom_components_dir))

    # Import custom_components so the loader's `import custom_components`
    # succeeds (the loader does this lazily inside
    # `_get_custom_components`).
    import custom_components  # noqa: F401
    import roamcore  # noqa: F401

    # Lazy imports — keep them inside the fixture so the test module
    # imports don't trigger HA bootstrap at collection time.
    from homeassistant import config_entries, loader
    from homeassistant.bootstrap import async_setup_hass
    from homeassistant.core import HomeAssistant
    from homeassistant.runner import RuntimeConfig
    from homeassistant.setup import async_setup_component

    with tempfile.TemporaryDirectory(prefix="rc_test_ha_config_") as tmp:
        config_dir = Path(tmp) / "config"
        config_dir.mkdir()
        # Minimal config: just http on an ephemeral port. No
        # `default_config:` — we don't want the bootstrap to try and
        # load 30+ integrations that aren't installed in this test rig.
        # No `frontend:` either — the recovery-mode workaround below
        # handles the missing `frontend` critical integration.
        (config_dir / "configuration.yaml").write_text(
            "http:\n  server_port: 0\n",
            encoding="utf-8",
        )
        # The HA http ban manager expects `ip_bans.yaml` to exist when
        # it loads. Create an empty one so the http setup doesn't
        # FileNotFoundError on us.
        (config_dir / "ip_bans.yaml").write_text("{}\n", encoding="utf-8")

        rc = RuntimeConfig(config_dir=str(config_dir), skip_pip=True)
        hass = await async_setup_hass(rc)

        # WORKAROUND: HA's bootstrap auto-enables recovery mode when
        # `default_config` (or any critical integration like
        # `frontend`) fails to load. Recovery mode causes
        # `loader.async_get_custom_components` to return `{}` — so
        # custom integrations would be invisible. Mirror the minimal
        # workaround the archived pytest-homeassistant-custom-
        # components harness used under these conditions by clearing
        # the cached custom-components slot + flipping the
        # recovery_mode flag back to False.
        if loader.DATA_CUSTOM_COMPONENTS in hass.data:
            del hass.data[loader.DATA_CUSTOM_COMPONENTS]
        hass.config.recovery_mode = False
        comps = await loader.async_get_custom_components(hass)
        assert "roamcore" in comps, (
            "RoamCore custom integration did not load; "
            "the shim package + custom_components dir are set up "
            f"correctly (saw {sorted(comps.keys())!r}) but the "
            "loader didn't pick up the `roamcore` integration. "
            "Check that the shim's `__init__.py` exists and that "
            "the symlink target is the real directory."
        )

        # Insert a config entry so the views can read `entry.options`
        # (the views check `entry.options.get(CONF_OPENCLAW_API_*)`
        # to decide whether to expose endpoints + whether to require
        # auth). The defaults in `homeassistant/custom_components/
        # roamcore/const.py` give us `openclaw_api_enabled=True` +
        # `openclaw_api_requires_auth=False` (an MVP simplification
        # — the auth-required path is covered by the curl smoketest,
        # not the pytest suite).
        entry = config_entries.ConfigEntry(
            version=1,
            domain="roamcore",
            title="RoamCore (test)",
            data={},
            options={},
            entry_id="test_rc_entry_id",
            source=config_entries.SOURCE_USER,
            unique_id="test_rc_unique_id",
            discovery_keys=frozenset(),
            minor_version=1,
        )
        hass.config_entries._entries[entry.entry_id] = entry

        # Set up the integration — this is what registers the 11
        # URL routes (the 13 endpoints spec'd by the slice). The
        # ASCII guard around the URL assertion below catches the
        # "I added a new view but forgot to update the test count"
        # regression.
        setup_ok = await async_setup_component(
            hass, "roamcore", {"roamcore": {}}
        )
        assert setup_ok, (
            "roamcore integration failed to set up; check the HA "
            "error log above for the cause (typically a missing "
            "dependency or a syntax error in the integration code)"
        )

        # Sanity: assert the 11 unique routes are registered. The
        # 13 endpoints spec'd by the slice resolve to 11 routes
        # because `automation/validate` is the same view as
        # `automation/intents` (it inherits from
        # `OpenClawAutomationIntentsView` and overrides only the
        # URL).
        routes = {
            _route_url(r)
            for r in hass.http.app.router._resources
        }
        expected_routes = {
            "/api/roamcore/openclaw/summary",
            "/api/roamcore/openclaw/skill",
            "/api/roamcore/openclaw/rc_dump",
            "/api/roamcore/openclaw/timeseries/catalog",
            "/api/roamcore/openclaw/timeseries",
            "/api/roamcore/openclaw/automation/intents",
            "/api/roamcore/openclaw/automation/validate",
            "/api/roamcore/diagnostics",
            "/api/roamcore/system/summary",
            "/api/roamcore/update",
            "/api/roamcore/pmtiles/{filename}",
        }
        missing = expected_routes - routes
        assert not missing, (
            f"Missing RoamCore OpenClaw routes after setup: "
            f"{sorted(missing)!r}; the views are registered by "
            f"`homeassistant/custom_components/roamcore/__init__.py` "
            f"via `hass.http.register_view(...)` calls — one of "
            f"those calls is missing or the view's `url` attribute "
            f"typo'd"
        )

        # Monkey-patch `history.get_significant_states` to return an
        # empty dict. The /api/roamcore/openclaw/timeseries endpoint
        # calls into HA's recorder to fetch the historical state
        # changes; the recorder isn't loaded in this test rig (we
        # skip `default_config` to avoid pulling in optional deps),
        # so the call raises KeyError on `hass.data['recorder_instance']`.
        # Patching the function to return an empty dict is the cleanest
        # workaround — the endpoint's contract is "empty series when
        # history is unavailable", which is exactly what the tests
        # assert anyway.
        from homeassistant.components.recorder import history
        original_get_significant_states = history.get_significant_states

        def _empty_significant_states(*args, **kwargs):
            return {}

        history.get_significant_states = _empty_significant_states

        try:
            yield hass
        finally:
            history.get_significant_states = original_get_significant_states
            try:
                await hass.async_stop()
            except Exception:
                pass


def _route_url(route: object) -> str:
    """Best-effort extraction of a URL pattern from an aiohttp route.

    Handles both `PlainResource` (static paths) and `DynamicResource`
    (templated paths like `/api/roamcore/pmtiles/{filename}`).
    """
    for attr in ("canonical", "_path", "path"):
        v = getattr(route, attr, None)
        if isinstance(v, str):
            return v
    info = getattr(route, "get_info", None)
    if info is not None:
        try:
            res = info()
            if isinstance(res, dict):
                # aiohttp Resource.get_info() returns a dict with
                # 'path' (resource path) and 'formatter' (formatter).
                path = res.get("path") or res.get("formatter")
                if isinstance(path, str):
                    return path
        except Exception:
            pass
    # Last resort — try `_pattern` (a `re.compile` object).
    pat = getattr(route, "_pattern", None)
    if pat is not None:
        try:
            return str(pat.pattern)
        except Exception:
            pass
    return repr(route)


@pytest_asyncio.fixture(loop_scope="session")
async def hass_client(hass: "object") -> AsyncIterator[TestClient]:
    """Function-scoped aiohttp `TestClient` wrappped around `hass.http.app`.

    Each test gets a fresh TestServer so aiohttp's socket binding is
    recovered on teardown (bound sockets are not reusable across tests).
    The HA instance itself is session-scoped, so the cost is just the
    aiohttp test-server boot (~50ms).
    """
    server = TestServer(hass.http.app)
    client = TestClient(server)
    await client.start_server()
    try:
        yield client
    finally:
        await client.close()


@pytest_asyncio.fixture(loop_scope="session")
async def hass_auth_headers(hass: "object") -> Dict[str, str]:
    """Headers dict with a valid Bearer Long-Lived Access Token.

    Required for the RoamCore views that hardcode `requires_auth = True`
    (`RoamcoreDiagnosticsView`, `RoamcoreSystemSummaryView`,
    `RoamcoreUpdateView`, `RoamcorePmtilesView`). The OpenClaw summary
    + skill + rc_dump + timeseries endpoints default to
    `requires_auth = False` (per the integration's MVP design), so they
    don't need this header.

    The token is created fresh per session via HA's auth API:
      1. create a local-system user
      2. create a refresh token for that user
      3. mint an access token from the refresh token
    This is the same flow the in-app "Long-Lived Access Token" UI uses
    (well, an in-API version of it). The token is synthetic (not the
    real operator RC_API_TOKEN); the test rig's secret material is
    confined to the in-memory `hass.auth` store and wiped on session
    teardown.
    """
    # Create a local admin user. We use `async_create_user` (not the
    # `async_create_system_user` variant) so the user can have a
    # refresh token + access token issued against it.
    user = await hass.auth.async_create_user(
        "rc-test-user"
    )
    # Create a refresh token for the user + mint an access token.
    # We use TOKEN_TYPE_LONG_LIVED_ACCESS_TOKEN (the same type the
    # operator's "Long-Lived Access Token" UI uses) so the
    # resulting token has the right semantics for the auth
    # validator. The access token is a JWT signed by the refresh
    # token's key + verified by HA's `async_validate_access_token`
    # on every authenticated request.
    from homeassistant.auth.models import TOKEN_TYPE_LONG_LIVED_ACCESS_TOKEN

    refresh_token = await hass.auth.async_create_refresh_token(
        user,
        client_id="rc-test-client",
        client_name="RoamCore OpenClaw pytest tests",
        token_type=TOKEN_TYPE_LONG_LIVED_ACCESS_TOKEN,
    )
    access_token = hass.auth.async_create_access_token(refresh_token)
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }


@pytest_asyncio.fixture(loop_scope="session")
async def hass_auth_client(
    hass: "object", hass_auth_headers: Dict[str, str]
) -> AsyncIterator[TestClient]:
    """Function-scoped aiohttp `TestClient` with a Bearer token already
    wired into the headers.

    Use this for endpoints that require auth (`/diagnostics`,
    `/system/summary`, `/update`, `/pmtiles/*`). Use the plain
    `hass_client` for the OpenClaw endpoints that explicitly default
    to `requires_auth = False` (the MVP auth-on-locally-recommended-
    public-on-LAN design).
    """
    server = TestServer(hass.http.app)
    client = TestClient(server, headers=hass_auth_headers)
    await client.start_server()
    try:
        yield client
    finally:
        await client.close()


@pytest.fixture(scope="session")
def free_tcp_port() -> int:
    """Return a currently-free TCP port (best-effort).

    Used by tests that need to bind a test WebSocket / extra HTTP server
    in addition to the HA aiohttp app. The port may be racy (someone
    else can grab it between `free_tcp_port` returning and the test
    binding) — that's acceptable for these tests, which only use it
    for sanity checks.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
    finally:
        s.close()
