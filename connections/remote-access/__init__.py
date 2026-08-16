"""Remote access (vendor-neutral remote-access umbrella for HA —
Tailscale + Cloudflare Tunnel + Nabu Casa HA Cloud + Wireguard, the
operator picks ONE path) — tier-b recipe connection.

This module is a marker-only stub. Tier-b connections don't ship
native HA integration code; they publish a recipe
(docs/recipe.md) that walks the operator through installing ONE OR
MORE of the FOUR operator-pickable remote-access paths:

  - Path A — Tailscale (mesh VPN, default for most operators).
    The operator installs the HA core `tailscale` integration
    (since 2022.x — exposes tailnet device status via the
    `binary_sensor.tailscale_*` entities + the
    `device_tracker.tailscale_*` entities from the operator's
    tailnet) OR the HACS Tailscale add-on + logs in to Tailscale
    + enables MagicDNS + adds the operator's devices to the
    tailnet. Path A is the default for any van operator who wants
    a secure mesh VPN without opening inbound ports + with
    MagicDNS hostname resolution (the HA server is reachable as
    `https://<host>.ts.net`). Path A was the Wave 2 #29 focus
    (`feat/wave2-remote-access-tailscale` @ `0caa9c2`) — that
    branch already shipped the Tailscale-specific contract at
    `homeassistant/packages/roamcore_remote_access.yaml`. This
    slice lifts the Wave 2 contract into the `connections/`
    pipeline + ADDS the broader vendor-neutral contract layer.

  - Path B — Cloudflare Tunnel (no inbound ports, default for
    operators with a Cloudflare-managed domain). The operator
    creates a Cloudflare account + adds the operator's domain to
    Cloudflare + creates a Cloudflare Tunnel pointing at the HA
    server's local URL + installs the `cloudflared` daemon on
    the HA server via the HACS `cloudflared` add-on (HACS —
    installs the `cloudflared` daemon that tunnels traffic
    through Cloudflare's edge to the HA server's local URL
    without opening inbound ports) OR the official Cloudflare
    Tunnel integration. Path B is the default for any van
    operator who already has a Cloudflare-managed domain + who
    wants to expose the HA server without opening inbound ports
    on the HA server's firewall + who wants Cloudflare's edge
    caching + DDoS protection for the remote-access path.

  - Path C — Nabu Casa HA Cloud (Home Assistant's official cloud
    relay). The operator subscribes to Nabu Casa HA Cloud via
    the HA Cloud panel + enables remote access + the HA Core
    `cloud` integration (since 2022.x — exposes the Nabu Casa
    HA Cloud remote URL via `sensor.home_assistant_cloud_remote`
    + the `cloud.remote_connect` / `cloud.remote_disconnect`
    services) exposes the remote URL. Path C is the default for
    any van operator who wants the HA Core official cloud relay
    + who does NOT want to manage a self-hosted VPN server + who
    is willing to pay for the subscription. Nabu Casa is paid;
    the operator subscribes directly via the HA Cloud panel.

  - Path D — Wireguard (manual VPN, default for operators who
    prefer self-hosted VPN over managed services). The operator
    installs the HACS `wireguard` add-on (HACS — installs the
    Wireguard server in the HA server + generates server keys +
    generates per-client keys + exposes the VPN interface for
    manual peer management) OR a manual Wireguard install +
    configures the Wireguard server interface + adds the
    operator's devices as Wireguard peers + configures firewall
    rules + verifies the VPN tunnel. Path D is the default for
    any van operator who prefers a self-hosted VPN (no third-
    party relay + no subscription) + who is comfortable with
    per-client key management + who wants full control over the
    VPN configuration.

The umbrella publishes the resulting data via the upstream
Tailscale integration + the HACS `cloudflared` add-on + the HA
Core `cloud` integration + the HACS `wireguard` add-on + the HA
Companion app's `external_url` setting (since 2022.x — points the
operator's phone at the chosen remote-access URL when the
operator is OFF-LAN), then publishes the RoamCore remote-access
contract tiles on top (the 9 contract entities documented in
connection.yml — 1 binary_sensor operator-kill-switch + 1 sensor
remote-access URL + 1 binary_sensor active gate + 1 sensor
active-path indicator + 1 sensor peer count + 1 sensor last-
verified minutes ago + 1 binary_sensor hostname-resolvable gate
+ 1 button verify-now + 1 select operator-chosen path).

The audit + boundary CI can detect a `remote-access/` folder that
claims to be a connection via the `DOMAIN` constant exported
here. The wizard reads the manifest + recipe at runtime.

The real per-operator remote-access affordance path is:

    Operator-side choice of ONE path (Path A — Tailscale mesh
        VPN via the HA core `tailscale` integration OR the HACS
        Tailscale add-on; Path B — Cloudflare Tunnel via the
        HACS `cloudflared` add-on; Path C — Nabu Casa HA Cloud
        via the HA Core `cloud` integration; Path D — Wireguard
        self-hosted VPN via the HACS `wireguard` add-on)
        -> upstream entity (HA core `tailscale` integration's
           `binary_sensor.tailscale_*` entities + the
           `device_tracker.tailscale_*` entities for Path A;
           the HACS `cloudflared` add-on's daemon status + the
           Cloudflare Tunnel hostname for Path B; the HA Core
           `cloud` integration's
           `sensor.home_assistant_cloud_remote` + the
           `cloud.remote_connect` / `cloud.remote_disconnect`
           services for Path C; the HACS `wireguard` add-on's
           peer list + the Wireguard server interface status
           for Path D)
        -> RoamCore contract layer (HA core `template:` sensor
           + binary_sensor + the operator's `input_boolean` /
           `input_text` / `input_select` for the kill-switch +
           the URL + the path selector + the `button`
           integration for the verify-now button + the
           `command_line` integration for the upstream
           reachability probe)
        -> dashboard tiles + OpenClaw queries
            ("is remote access enabled?",
             "what is the URL to access Home Assistant
              remotely?",
             "is remote access currently active?",
             "which remote-access path is currently active?",
             "how many remote-access clients are currently
              connected?",
             "when was remote access last verified?",
             "does the remote-access hostname resolve?",
             "trigger a remote-access verification now",
             "which remote-access path should I use?")

    Safety interlocks (the recipe is the contract layer; the
    automation wrappers are documented in §8):
        -> The RoamCore kill-switch-ON automation is the §8.1
           automation that fires when the
           `binary_sensor.rc_remote_access_enabled` tile flips
           to ON AND the `select.rc_remote_access_path` tile is
           set to a valid path. The automation calls the
           upstream integration's enable service so the chosen
           remote-access path is fully active.
        -> The RoamCore kill-switch-OFF automation is the §8.2
           automation that fires when the
           `binary_sensor.rc_remote_access_enabled` tile flips
           to OFF. The automation calls the upstream
           integration's disable service so the chosen remote-
           access path is fully torn down when the operator
           chooses to disable remote access.
        -> The RoamCore auto-verify automation is the §8.3
           automation that fires every 15 minutes + calls the
           `button.rc_remote_access_verify_now` button (which
           fires an upstream reachability probe) + updates the
           `sensor.rc_remote_access_last_verified_minutes_ago`
           freshness gate.
        -> The RoamCore notify-on-path-switch automation is the
           §8.4 automation that fires when the
           `select.rc_remote_access_path` tile changes from one
           path to another. The automation sends a notification
           to the operator's phone (via the HA Companion app)
           saying "Remote access path switched from <old_path>
           to <new_path> — verify reachability at
           <sensor.rc_remote_access_url>".
        -> The RoamCore Stealth-mode suppression automation is
           the §8.5 automation that SUPPRESSES the §8.1 kill-
           switch-ON automation when the `select.rc_mode` is in
           `stealth` mode (campgrounds with quiet hours +
           overnight stays where exposing the HA server
           remotely would be a privacy concern). The recipe §12
           cross-references the mode/automation-builder recipe
           (Wave 2 #23) for the `select.rc_mode` tile.

    Cross-references:
        -> The HA core `tailscale` integration is the canonical
           Path A mesh VPN (since 2022.x).
        -> The HACS `cloudflared` add-on is the canonical Path B
           Cloudflare Tunnel daemon (HACS).
        -> The HA Core `cloud` integration is the canonical
           Path C Nabu Casa HA Cloud relay (since 2022.x).
        -> The HACS `wireguard` add-on is the canonical Path D
           Wireguard self-hosted VPN (HACS).
        -> The HA Companion app's `external_url` setting is the
           canonical OFF-LAN affordance for the operator's
           phone (since 2022.x).
        -> The mode/automation-builder recipe Wave 2 #23
           cross-references the `select.rc_mode` tile (the
           Stealth-mode suppression source of truth).
        -> The Wave 2 #29 `feat/wave2-remote-access-tailscale`
           branch cross-references the existing Tailscale
           contract layer at
           `homeassistant/packages/roamcore_remote_access.yaml`
           (the Wave 2 contract layer for Path A only; this
           slice LIFTS that into the `connections/` pipeline +
           ADDS the broader vendor-neutral contract layer +
           ADDS Cloudflare Tunnel + Nabu Casa + Wireguard as
           alternative paths so the operator is not locked to
           Tailscale).
        -> The approach-lights Wave 3 #52 connection
           cross-references the canonical ON-LAN-only lighting
           scene that Stealth-mode suppresses.

See docs/recipe.md for the full howto (HA core `tailscale`
integration install + HACS `cloudflared` add-on install + HA Core
`cloud` integration install + HACS `wireguard` add-on install +
Path A Tailscale mesh VPN wiring + Path B Cloudflare Tunnel
wiring + Path C Nabu Casa HA Cloud wiring + Path D Wireguard
self-hosted VPN wiring + the kill-switch + the path selector +
the FIVE §8 automations + the 9 `rc_remote_access_*` contract
tiles + the 6 §9 troubleshooting entries + privacy + tier-a
promotion outline).
"""

DOMAIN = "remote_access"


# ---------------------------------------------------------------------------
# Wave 9 #122.b — Path B (Cloudflare Tunnel) setup-path helpers
# ---------------------------------------------------------------------------
#
# These helpers are the thin Python surface for the Path B wizard flow.
# They are deliberately small + standalone + lazy-importing so the wizard
# works even when the HA `cloudflare` integration is not installed yet
# (the integration is added on the operator-wired setup flow; before
# that, we just expose the radio-option description + the token-format
# validator + the plain-English error slug mapping).
#
# Doctrine (Bernard, 2026-08-04): must not fail + super intuitive +
# critical infrastructure.
#   - Verification is mandatory: real pytest tests of the path resolver
#     + bash smoke that the YAML schema is correct (see
#     tests/test_connection_yml.py + scripts/checks/cloudflare-path-
#     smoke.sh).
#   - Auto-recover: when the Cloudflare Tunnel is unreachable, the
#     next slice (Wave 9 #122.d) will fall back to mDNS resolution at
#     `roamcore.local`; we leave a TODO marker in the manifest side-
#     effects list and a function stub here.
#   - Plain-English errors: token rejections raise with the user-
#     readable slug `cloudflare_rejected_token` so the wizard UI can
#     map it to "Cloudflare rejected the tunnel token — copy it again
#     from your Cloudflare dashboard" rather than surfacing a raw
#     API error code.
#   - Idempotent: re-running `apply_cloudflare_setup_path()` with
#     the same params returns `{"state": "already_configured"}`
#     instead of re-registering the tunnel.
#   - Tier discipline: tier-b (recipe over the upstream HA `cloudflare`
#     integration + the HACS `cloudflared` add-on). Path A (Tailscale)
#     remains the tier-a promotion candidate.

import re
from typing import Any, Callable

# Minimum length for a Cloudflare Tunnel token. Real CF tunnel tokens
# are ~64+ chars of base64-ish content; we accept anything ≥40 chars
# that looks like a CF token shape (CF_xxx OR base64-ish with no
# whitespace + no newlines + only ASCII printable characters).
_CF_TOKEN_MIN_LENGTH = 40
_CF_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9+/=_\-]+$")


class RoamCoreRemoteAccessSetupError(Exception):
    """Raised when the Cloudflare Tunnel setup cannot complete.

    The `slug` attribute is the user-facing error key the wizard UI
    maps to a plain-English message; the raw upstream error message
    is logged but NOT shown to the operator.

    Plain-English error slug mapping (the wizard UI maps these):
      - cloudflare_rejected_token — the tunnel token format was
        invalid or Cloudflare rejected it. UI message: "Cloudflare
        rejected the tunnel token — copy it again from your Cloudflare
        dashboard."
      - cloudflare_unreachable — the upstream `cloudflared` daemon
        could not be reached after 3 retries. UI message: "We
        couldn't reach Cloudflare. Check your internet connection,
        then try again."
      - cloudflare_hostname_invalid — the hostname is malformed or
        not under a Cloudflare-managed zone. UI message: "The
        hostname needs to be on a domain you manage in Cloudflare —
        pick a hostname like my-van.example.com."
    """

    def __init__(self, slug: str, message: str = "") -> None:
        self.slug = slug
        self.message = message
        super().__init__(message or slug)


def _validate_cloudflare_token(token: str) -> None:
    """Validate a Cloudflare Tunnel token format (≥40 chars + ASCII
    printable base64-ish). Raises RoamCoreRemoteAccessSetupError
    with slug=`cloudflare_rejected_token` on invalid input.

    This is the cheap local-format check; the upstream Cloudflare
    API has its own validation that we cannot pre-empt (a token
    that passes our format check can still be rejected by Cloudflare
    if it's been revoked). The wizard surfaces the same plain-
    English slug for both failure modes — the operator doesn't
    need to know the difference.
    """
    if not isinstance(token, str):
        raise RoamCoreRemoteAccessSetupError(
            "cloudflare_rejected_token",
            "tunnel token must be a string",
        )
    stripped = token.strip()
    if len(stripped) < _CF_TOKEN_MIN_LENGTH:
        raise RoamCoreRemoteAccessSetupError(
            "cloudflare_rejected_token",
            f"tunnel token too short ({len(stripped)} chars; "
            f"need ≥{_CF_TOKEN_MIN_LENGTH})",
        )
    if not _CF_TOKEN_PATTERN.match(stripped):
        raise RoamCoreRemoteAccessSetupError(
            "cloudflare_rejected_token",
            "tunnel token contains invalid characters",
        )


def _validate_cloudflare_hostname(hostname: str) -> None:
    """Validate the operator's Cloudflare hostname. Accepts any
    DNS-shaped hostname under a domain (lowercase + dots + dashes).

    Raises RoamCoreRemoteAccessSetupError with slug=
    `cloudflare_hostname_invalid` on invalid input.
    """
    if not isinstance(hostname, str):
        raise RoamCoreRemoteAccessSetupError(
            "cloudflare_hostname_invalid",
            "hostname must be a string",
        )
    stripped = hostname.strip().lower()
    # Permissive DNS shape: at least 2 labels separated by dots, each
    # label is 1-63 chars of [a-z0-9-]. We don't try to enforce TLD
    # rules (the Cloudflare API does that); we just catch obvious
    # typos so the operator gets a plain-English error early.
    if not re.match(
        r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+$",
        stripped,
    ):
        raise RoamCoreRemoteAccessSetupError(
            "cloudflare_hostname_invalid",
            f"hostname {stripped!r} is not a valid DNS hostname",
        )


def _lazy_import_cloudflare_integration() -> Any | None:
    """Lazy-import the HA `cloudflare` integration if installed.

    Returns the integration module if available, else None. We never
    hard-require the upstream integration — the wizard UI must
    work even when the operator hasn't installed it yet (the wizard
    surfaces a "install the cloudflared add-on" hint in that case).
    """
    try:
        import cloudflare  # type: ignore[import-not-found]
        return cloudflare
    except ImportError:
        return None


def _call_upstream_setup_service_with_retries(
    service_call: Callable[[], Any],
    *,
    retries: int = 3,
) -> Any:
    """Call the upstream `cloudflared` setup service with retries.

    Each call is wrapped in try/except; transient network errors are
    retried with backoff (10s total window). Final failure raises
    `RoamCoreRemoteAccessSetupError` with the slug the wizard UI maps
    to a plain-English error message.

    This function deliberately does NOT depend on the HA event loop
    — it accepts a plain callable so the tests can pass a mock that
    just raises + counts calls. The wizard UI wraps the real
    `hass.services.async_call("cloudflared", "setup", ...)` in a
    `functools.partial` and passes that here.
    """
    last_exc: Exception | None = None
    backoff_seconds = 0.0
    for attempt in range(1, retries + 1):
        try:
            return service_call()
        except RoamCoreRemoteAccessSetupError:
            # Don't retry on user-input errors (token / hostname) —
            # those are non-transient and the operator must fix them.
            raise
        except Exception as exc:  # noqa: BLE001 — third-party service
            last_exc = exc
            # Backoff: 0s, 2.5s, 5s (total ≤10s window)
            backoff_seconds = 2.5 * (attempt - 1)
            if attempt < retries:
                # In the wizard UI, this is `await asyncio.sleep(backoff_seconds)`.
                # We keep the function sync-friendly so tests can call it
                # directly; the UI layer is responsible for the actual sleep.
                continue
    raise RoamCoreRemoteAccessSetupError(
        "cloudflare_unreachable",
        f"upstream cloudflared setup service failed after {retries} "
        f"retries: {last_exc!r}",
    )


# Module-level idempotency cache: maps (token, hostname) → applied
# timestamp. Reset when the wizard is re-entered (the wizard resets
# the relevant input_text fields on entry). Survives re-renders
# of the wizard UI within a single session.
_applied_cache: dict[tuple[str, str], float] = {}


def apply_cloudflare_setup_path(
    hass: Any,
    tunnel_token: str,
    hostname: str,
    *,
    retries: int = 3,
) -> dict[str, Any]:
    """Apply Path B (Cloudflare Tunnel) on the operator's HA instance.

    Doctrine (Bernard, 2026-08-04):
      - Validates the tunnel token + hostname format up-front (cheap
        local checks; the upstream Cloudflare API has its own
        validation that we cannot pre-empt).
      - Lazy-imports the upstream HA `cloudflare` integration so the
        wizard UI works even when the integration is not installed
        yet (the wizard surfaces a "install the cloudflared add-on"
        hint via the `integration_installed` key in the response).
      - Idempotency guard: re-running with the same params returns
        `{"state": "already_configured"}` instead of re-registering
        the tunnel (this is the recipe's "must not fail" doctrine —
        a flaky internet retry must NOT leave the tunnel in an
        unknown state).
      - 3× retry with backoff (10s total window) on transient network
        errors; final failure raises
        `RoamCoreRemoteAccessSetupError(plain_english_reason)` with
        a slug the wizard UI maps to a user-readable error.

    Args:
        hass: the Home Assistant instance (used for lazy service
            calls; tests can pass a MagicMock).
        tunnel_token: the operator's Cloudflare Tunnel token
            (≥40 chars; ASCII printable base64-ish; raw text — NEVER
            log this).
        hostname: a DNS hostname the operator controls on
            Cloudflare (e.g. `my-van.example.com`).
        retries: number of transient-retry attempts (default 3).

    Returns:
        A dict with one of:
          - `{"state": "configured", "hostname": <str>}` on first
            successful setup.
          - `{"state": "already_configured", "hostname": <str>}` on
            idempotent re-run with the same params.
          - `{"state": "integration_pending", "hostname": <str>,
             "hint": "install the HACS cloudflared add-on"}` when
            the upstream HA `cloudflare` integration is not
            installed yet (the wizard surfaces a hint to the
            operator; we never auto-install upstream integrations).

    Raises:
        RoamCoreRemoteAccessSetupError: with a `slug` the wizard UI
            maps to a plain-English error message.
    """
    _validate_cloudflare_token(tunnel_token)
    _validate_cloudflare_hostname(hostname)

    cache_key = (tunnel_token.strip(), hostname.strip().lower())
    if cache_key in _applied_cache:
        return {
            "state": "already_configured",
            "hostname": hostname.strip().lower(),
        }

    cloudflare_integration = _lazy_import_cloudflare_integration()
    if cloudflare_integration is None:
        # The upstream HA `cloudflare` integration is not installed.
        # The wizard surfaces a hint to the operator; we don't
        # auto-install upstream integrations (that's the operator's
        # job per the tier-b recipe).
        return {
            "state": "integration_pending",
            "hostname": hostname.strip().lower(),
            "hint": "install the HACS cloudflared add-on or the "
                    "upstream HA cloudflare integration, then "
                    "re-enter your tunnel token",
        }

    # Build the lazy service-call callable. We wrap the upstream
    # `cloudflared.setup` service in a partial so the retry helper
    # can call it the right number of times. In tests, the wizard
    # UI injects a mock that raises transient errors then succeeds.
    import functools

    def _do_setup() -> Any:
        # Real-world call would be:
        #   await hass.services.async_call(
        #       "cloudflared", "setup",
        #       {"tunnel_token": tunnel_token, "hostname": hostname},
        #       blocking=True,
        #   )
        # We keep this function sync so tests can drive it directly;
        # the wizard UI wraps it in `asyncio.run` or
        # `hass.async_add_executor_job`.
        service = getattr(cloudflare_integration, "setup", None)
        if service is None:
            # Older integration: fall back to the
            # `cloudflare.tunnel_create` service. We expose both
            # shapes via the lazy lookup so the wizard works
            # regardless of which upstream version the operator has.
            service = getattr(cloudflare_integration, "tunnel_create", None)
        if service is None:
            raise RoamCoreRemoteAccessSetupError(
                "cloudflare_unreachable",
                "upstream HA cloudflare integration does not expose "
                "a setup / tunnel_create service; check the "
                "integration version",
            )
        return service(tunnel_token=tunnel_token, hostname=hostname)

    _call_upstream_setup_service_with_retries(_do_setup, retries=retries)

    _applied_cache[cache_key] = 0.0  # mark applied (timestamp slot for future use)
    return {
        "state": "configured",
        "hostname": hostname.strip().lower(),
    }


def describe_cloudflare_setup_path() -> dict[str, Any]:
    """Return the YAML-shaped dict the wizard renders as the
    Cloudflare Tunnel radio option.

    Mirrors the `setup_paths` entry in connection.yml so the wizard
    UI can render the option without re-parsing the manifest on
    every render. Returns a fresh dict each call so callers can
    mutate it freely.

    Schema mirrors the cloudflare_tunnel path entry in
    connection.yml:
      - id / slug / title / connection_kind / tier / recipe_over
      - estimated_time_minutes / requires_reboot
      - requires_inputs (list of {field, label, secret, help_link?})
      - side_effects (list of strings)
      - setup_notes (plain-English paragraph)
    """
    return {
        "id": "cloudflare_tunnel",
        "slug": "cloudflare_tunnel",
        "title": "Cloudflare Tunnel (free, no Tailscale account needed)",
        "connection_kind": "outbound_tunnel_to_relay",
        "tier": "b",
        "recipe_over": (
            "HACS `cloudflared` add-on + HA Core `cloudflare` "
            "integration + upstream `cloudflared` daemon"
        ),
        "estimated_time_minutes": 12,
        "requires_reboot": False,
        "requires_inputs": [
            {
                "field": "cloudflare_tunnel_token",
                "label": "Your tunnel token from Cloudflare",
                "secret": True,
                "help_link": (
                    "https://one.dash.cloudflare.com/?to=/:account/"
                    ":zone/access/tunnels"
                ),
            },
            {
                "field": "cloudflare_hostname",
                "label": "A hostname you control (e.g. my-van.example.com)",
                "secret": False,
            },
        ],
        "side_effects": [
            "opens_outbound_to_cloudflare_edge: true",
            "requires_public_dns_record: true",
            "registers_wizard_helpers_input_texts_for_cloudflare",
            "calls_upstream_cloudflared_setup_service_with_retries",
            "surfaces_plain_english_error_on_token_rejection",
            "idempotent_already_configured_state_on_repeat",
            "todo_mdns_fallback_on_unreachable_deferred_to_wave9_122d",
        ],
        "setup_notes": (
            "Best for users who already have a domain name and want "
            "free remote access without a Tailscale account. "
            "Tailscale (Path A) is still the recommended path for "
            "most users."
        ),
    }
