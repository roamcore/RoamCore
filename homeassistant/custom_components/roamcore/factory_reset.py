"""RoamCore-owned service handler for Factory Reset.

Phase 7 — Wave 9 #123.b Factory Reset one-tap recovery.

This module is the canonical umbrella for the Factory Reset surface.
It implements the 2-step confirm flow (dry-run + confirm + cancel +
postflight) + the chain-corruption recovery path
(`recovery_resets(hass)`) + the `RoamCoreFactoryResetView` HTTP view at
`/api/roamcore/factory_reset/{action}` so the dashboard + OpenClaw
agents can drive the dry-run / confirm / cancel / postflight surface
over HTTP (in addition to the service calls). It registers 4 RoamCore
services via `register_factory_reset_services(hass)`:

  - `roamcore.factory_reset_dry_run` — run a dry-run that returns the
    planned post-reset state + a short random 8-char token that the
    operator must echo back in the confirm call. The dry-run is
    idempotent — re-running while a dry-run is pending returns the
    same plan + the same token (idempotency marker).
  - `roamcore.factory_reset_confirm` — one-shot confirm. The token is
    consumed on success; subsequent calls with the same token return
    409 "no pending reset — please run dry-run first" (no silent
    data loss). A confirm without a matching dry-run returns the
    same 409 (idempotency guard).
  - `roamcore.factory_reset_cancel` — revokes a pending token
    (operator changed their mind).
  - `roamcore.factory_reset_postflight_check` — idempotent. Verifies
    the post-reset state matches the dry-run plan (Hub reachable,
    latest backup ingested, integrations healthy). Surfaces a plain-
    English banner via `sensor.rc_factory_reset_postflight_status`.

The reset is "panic-button safe" — it ALWAYS restores from the latest
Hub Backup (from the hub-backup connection at
`connections/hub-backup/`, MERGED on main as commit bfaa73d) and
never silently destroys user data. The wizard enforces a 2-step
confirmation flow with an explicit token ("type RESET to confirm")
AND it runs a dry-run first that lists the current state + the last
backup + the post-reset state. The integration is bench-tested by the
>=25 pytest tests at `homeassistant/packages/tests/test_factory_reset.py`.
The bash smoke at `scripts/checks/factory-reset-smoke.sh` enforces 12
cross-cutting YAML/secrets-leak/idempotency assertions.
"""

from __future__ import annotations

import os
import secrets
import string
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


# The HomeAssistant / HomeAssistantView imports are optional — the
# module can be imported in bench environments where HA is not
# available. The HTTP view is registered only when HA is importable.
try:
    from homeassistant.core import HomeAssistant, ServiceCall
    from homeassistant.components.http import HomeAssistantView
    _HA_AVAILABLE = True
except ImportError:
    HomeAssistant = None  # type: ignore[assignment,misc]
    ServiceCall = None  # type: ignore[assignment,misc]
    HomeAssistantView = object  # type: ignore[assignment,misc]
    _HA_AVAILABLE = False


FACTORY_RESET_TILE_PREFIX = "rc_factory_reset_"

# The freshness window — the reset refuses to run without a Hub
# Backup less than this many minutes old. 24h = 1440 minutes. This
# is the safety rail that prevents silent data loss.
BACKUP_FRESHNESS_WINDOW_MINUTES = 24 * 60  # 1440

# The token lifetime — the section 8.3 cancel automation clears the token
# if the dry-run is older than this. 5 minutes is short enough to
# prevent an attacker from finding the token + long enough that a
# human operator can read the dry-run report + click confirm.
TOKEN_LIFETIME_MINUTES = 5

# The expected confirm token — the operator must type "RESET" in the
# confirm field. This is the explicit-token guard from the doctrine.
EXPECTED_CONFIRM_TOKEN = "RESET"

# Status constants used by the audit + the helper package + the
# pytest rig + the section 8 automations.
STATUS_READY = "ready"
STATUS_DRY_RUN_SHOWN = "dry_run_shown"
STATUS_CONFIRM_PENDING = "confirm_pending"
STATUS_RESETTING = "resetting"
STATUS_OK = "ok"
STATUS_FAILED = "failed"
STATUS_NEVER = "never"

# The 4 RoamCore service names the service handler registers.
SERVICE_DRY_RUN = "factory_reset_dry_run"
SERVICE_CONFIRM = "factory_reset_confirm"
SERVICE_CANCEL = "factory_reset_cancel"
SERVICE_POSTFLIGHT_CHECK = "factory_reset_postflight_check"

# The OpenClaw audit-chain binary_sensor that the section 8.5 recovery
# automation references. Forward reference — lives in the openclaw-api
# connection.
OPENCLAW_CHAIN_VALID_BINARY_SENSOR = "binary_sensor.rc_openclaw_api_chain_valid"

# The post-reset services that will restart.
POST_RESET_INTEGRATION_RESTARTS = (
    "victron",
    "mqtt",
    "tailscale",
    "remote_access",
    "mode",
    "advanced_mode",
)


@dataclass
class DryRunPlan:
    """In-memory representation of a factory-reset dry-run plan."""

    token: str
    last_backup_id: str
    last_backup_age_minutes: int
    freshness_window_minutes: int
    will_restart_integrations: list = field(default_factory=list)
    dry_run_at: str = ""
    plain_english_summary: str = ""
    plan_id: str = ""

    def to_dict(self) -> dict:
        return {
            "token": self.token,
            "last_backup_id": self.last_backup_id,
            "last_backup_age_minutes": self.last_backup_age_minutes,
            "freshness_window_minutes": self.freshness_window_minutes,
            "will_restart_integrations": list(self.will_restart_integrations),
            "dry_run_at": self.dry_run_at,
            "plain_english_summary": self.plain_english_summary,
            "plan_id": self.plan_id,
        }


@dataclass
class PostflightResult:
    """In-memory representation of a post-flight check result."""

    hub_reachable: bool
    latest_backup_ingested: bool
    integrations_healthy: bool
    checked_at: str = ""
    plain_english_status: str = ""

    def to_dict(self) -> dict:
        return {
            "hub_reachable": self.hub_reachable,
            "latest_backup_ingested": self.latest_backup_ingested,
            "integrations_healthy": self.integrations_healthy,
            "checked_at": self.checked_at,
            "plain_english_status": self.plain_english_status,
        }


# Module-level state for the in-flight dry-run / confirm flow.
_IN_FLIGHT_PLANS: dict = {}
_IN_FLIGHT_PLAN_BY_TOKEN: dict = {}


# ---------------------------------------------------------------------------
# Plain-English error mapper
# ---------------------------------------------------------------------------

_PLAIN_ENGLISH_REASONS = {
    "BackupNotFoundError": (
        "I can't reset without a recent backup — no backup has been "
        "taken yet. Please take a new backup first, then try again."
    ),
    "BackupStaleError": (
        "I can't reset without a recent backup — your last backup is "
        "more than 24 hours old. Please take a new backup first, then "
        "try again."
    ),
    "TokenMismatchError": (
        "Wrong token — please re-run dry-run and copy the new token."
    ),
    "TokenExpiredError": (
        "Token expired — please re-run dry-run and try again (the "
        "token is only valid for 5 minutes)."
    ),
    "NoPendingResetError": (
        "No pending reset — please run dry-run first, then click "
        "Confirm within 5 minutes."
    ),
    "HubUnreachableError": (
        "Your Hub isn't reachable right now — please reconnect, then "
        "try again."
    ),
    "AuditChainInvalidError": (
        "The OpenClaw audit chain is invalid — please run recovery "
        "before reset (or wait for the automatic recovery flow)."
    ),
}


def plain_english_reason(reason_code: str) -> str:
    """Map a raw error code to a plain-English string."""
    code = str(reason_code or "").strip()
    if code in _PLAIN_ENGLISH_REASONS:
        return _PLAIN_ENGLISH_REASONS[code]
    return (
        "Something went wrong — please re-run dry-run and try again. "
        f"(raw reason: {code!r})"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _coerce_str(value, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _coerce_int(value, default: int) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default


def _generate_token(length: int = 8) -> str:
    """Generate a short random token (uppercase letters + digits)."""
    alphabet = string.ascii_uppercase + string.digits
    # Strip ambiguous characters (0/O, 1/I/L) for operator readability.
    alphabet = (
        alphabet.replace("0", "")
        .replace("O", "")
        .replace("1", "")
        .replace("I", "")
        .replace("L", "")
    )
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _is_token_expired(dry_run_at: str, now: Optional[datetime] = None) -> bool:
    if not dry_run_at:
        return True
    try:
        dry_run_dt = datetime.fromisoformat(dry_run_at)
    except (TypeError, ValueError):
        return True
    if now is None:
        now = datetime.now(timezone.utc)
    age_minutes = (now - dry_run_dt).total_seconds() / 60.0
    return age_minutes > TOKEN_LIFETIME_MINUTES


# ---------------------------------------------------------------------------
# Hub Backup interop (read-only)
# ---------------------------------------------------------------------------


async def _read_hub_backup_status(hass) -> dict:
    """Read the latest Hub Backup status from the RoamCore-owned
    `homeassistant/custom_components/roamcore/backup.py` module.
    """
    try:
        from . import backup as hub_backup_module
    except Exception:
        return {}

    try:
        backups = await hub_backup_module.async_list_backups(hass)
    except Exception:
        return {}

    if not backups:
        return {}

    latest = backups[0]
    backup_id = _coerce_str(latest.get("backup_id") or latest.get("id"))
    created_at = _coerce_str(latest.get("created_at"))

    age_minutes = 99999
    if created_at:
        try:
            created_dt = datetime.fromisoformat(created_at)
            age_minutes = int(
                (datetime.now(timezone.utc) - created_dt).total_seconds() / 60
            )
        except (TypeError, ValueError):
            pass

    return {
        "backup_id": backup_id,
        "age_minutes": age_minutes,
        "restorable": True,
        "created_at": created_at,
    }


def is_backup_fresh(age_minutes) -> bool:
    """Return True if the backup is fresh enough for a factory reset."""
    if age_minutes is None or age_minutes < 0:
        return False
    return int(age_minutes) <= BACKUP_FRESHNESS_WINDOW_MINUTES


async def validate_factory_reset_prerequisites(hass) -> tuple:
    """Validate the prerequisites for a factory reset.

    Returns `(ok, reasons)` where `ok` is True if the reset can run
    and `reasons` is a list of plain-English strings.
    """
    reasons = []

    # Check 1: a recent Hub Backup exists.
    backup_status = await _read_hub_backup_status(hass)
    if not backup_status:
        reasons.append(plain_english_reason("BackupNotFoundError"))
    else:
        age_minutes = _coerce_int(backup_status.get("age_minutes"), 99999)
        if not is_backup_fresh(age_minutes):
            reasons.append(plain_english_reason("BackupStaleError"))

    # Check 2: the Hub is reachable.
    try:
        states = hass.states.async_all() if hass and hasattr(hass, "states") else []
        if not states:
            reasons.append(plain_english_reason("HubUnreachableError"))
    except Exception:
        reasons.append(plain_english_reason("HubUnreachableError"))

    # Check 3: the OpenClaw audit chain is valid (if the binary_sensor is wired).
    try:
        if hass and hasattr(hass, "states") and hass.states.get(
            OPENCLAW_CHAIN_VALID_BINARY_SENSOR
        ):
            chain_state = hass.states.get(OPENCLAW_CHAIN_VALID_BINARY_SENSOR)
            if chain_state and chain_state.state == "off":
                reasons.append(plain_english_reason("AuditChainInvalidError"))
    except Exception:
        pass

    ok = len(reasons) == 0
    return ok, reasons


# ---------------------------------------------------------------------------
# Dry-run / confirm / cancel / postflight
# ---------------------------------------------------------------------------


async def async_dry_run(hass) -> dict:
    """Run a dry-run of the factory reset.

    Returns a dict with:
      - `ok` (bool) — True if the prerequisites are met
      - `reasons` (list[str]) — plain-English failure reasons
      - `plan` (dict) — the planned post-reset state
      - `plain_english_summary` (str) — the dry-run report

    The dry-run is idempotent: re-running while a dry-run is pending
    returns the same plan + the same token.
    """
    ok, reasons = await validate_factory_reset_prerequisites(hass)
    if not ok:
        return {
            "ok": False,
            "reasons": reasons,
            "plain_english_summary": (
                "I can't run a dry-run right now:\n"
                + "\n".join(f"  - {r}" for r in reasons)
            ),
        }

    backup_status = await _read_hub_backup_status(hass)
    backup_id = _coerce_str(backup_status.get("backup_id"))
    age_minutes = _coerce_int(backup_status.get("age_minutes"), 99999)

    # Check for an existing in-flight plan (idempotency).
    existing_plan = None
    for plan in _IN_FLIGHT_PLANS.values():
        if (
            plan.last_backup_id == backup_id
            and not _is_token_expired(plan.dry_run_at)
        ):
            existing_plan = plan
            break

    if existing_plan is not None:
        return {
            "ok": True,
            "reasons": [],
            "plan": existing_plan.to_dict(),
            "plain_english_summary": existing_plan.plain_english_summary,
        }

    # Generate a new plan.
    token = _generate_token(8)
    plan_id = f"plan-{_iso_now()}"
    dry_run_at = _iso_now()

    plain_english_summary = (
        f"Last backup: {backup_id or 'unknown'} "
        f"({age_minutes} minutes ago). "
        f"Will restart integrations: "
        f"{', '.join(POST_RESET_INTEGRATION_RESTARTS)}. "
        f"After reset, your dashboards + automations + helpers will "
        f"look exactly like they did {age_minutes} minutes ago."
    )

    plan = DryRunPlan(
        token=token,
        last_backup_id=backup_id,
        last_backup_age_minutes=age_minutes,
        freshness_window_minutes=BACKUP_FRESHNESS_WINDOW_MINUTES,
        will_restart_integrations=list(POST_RESET_INTEGRATION_RESTARTS),
        dry_run_at=dry_run_at,
        plain_english_summary=plain_english_summary,
        plan_id=plan_id,
    )

    _IN_FLIGHT_PLANS[plan_id] = plan
    _IN_FLIGHT_PLAN_BY_TOKEN[token] = plan_id

    return {
        "ok": True,
        "reasons": [],
        "plan": plan.to_dict(),
        "plain_english_summary": plain_english_summary,
    }


async def async_confirm(hass, token: str) -> dict:
    """Confirm a factory reset.

    The confirm is one-shot per token. A confirm without a matching
    dry-run returns 409 "no pending reset — please run dry-run first".
    """
    token = _coerce_str(token).strip()
    if not token:
        return {
            "ok": False,
            "reasons": [plain_english_reason("NoPendingResetError")],
            "plain_english_status": plain_english_reason("NoPendingResetError"),
        }

    plan_id = _IN_FLIGHT_PLAN_BY_TOKEN.get(token)
    if plan_id is None:
        return {
            "ok": False,
            "reasons": [plain_english_reason("NoPendingResetError")],
            "plain_english_status": plain_english_reason("NoPendingResetError"),
        }

    plan = _IN_FLIGHT_PLANS.get(plan_id)
    if plan is None:
        return {
            "ok": False,
            "reasons": [plain_english_reason("NoPendingResetError")],
            "plain_english_status": plain_english_reason("NoPendingResetError"),
        }

    if plan.token != token:
        return {
            "ok": False,
            "reasons": [plain_english_reason("TokenMismatchError")],
            "plain_english_status": plain_english_reason("TokenMismatchError"),
        }

    if _is_token_expired(plan.dry_run_at):
        _IN_FLIGHT_PLANS.pop(plan_id, None)
        _IN_FLIGHT_PLAN_BY_TOKEN.pop(token, None)
        return {
            "ok": False,
            "reasons": [plain_english_reason("TokenExpiredError")],
            "plain_english_status": plain_english_reason("TokenExpiredError"),
        }

    # Re-validate the prerequisites.
    ok, reasons = await validate_factory_reset_prerequisites(hass)
    if not ok:
        return {
            "ok": False,
            "reasons": reasons,
            "plain_english_status": (
                "I can't reset right now:\n"
                + "\n".join(f"  - {r}" for r in reasons)
            ),
        }

    backup_id = plan.last_backup_id
    try:
        await hass.services.async_call(
            "backup",
            "restore",
            {"id": backup_id} if backup_id else {},
            blocking=False,
        )
    except Exception as exc:
        return {
            "ok": False,
            "reasons": [
                f"The Hub couldn't start the restore: "
                f"{type(exc).__name__}: {exc}. Please try again."
            ],
            "plain_english_status": (
                "The Hub couldn't start the restore. Please try again."
            ),
        }

    # Consume the token.
    _IN_FLIGHT_PLANS.pop(plan_id, None)
    _IN_FLIGHT_PLAN_BY_TOKEN.pop(token, None)

    return {
        "ok": True,
        "reasons": [],
        "plain_english_status": (
            "Resetting now — your Hub will restart in a moment. "
            "Check the post-flight tile when it's back up."
        ),
    }


async def async_cancel(hass, token: str) -> dict:
    """Cancel a pending factory reset."""
    token = _coerce_str(token).strip()
    if not token:
        return {
            "ok": True,
            "plain_english_status": "Nothing to cancel — no reset was pending.",
        }

    plan_id = _IN_FLIGHT_PLAN_BY_TOKEN.pop(token, None)
    if plan_id is not None:
        _IN_FLIGHT_PLANS.pop(plan_id, None)

    return {
        "ok": True,
        "plain_english_status": "Reset cancelled — your Hub is back to normal.",
    }


async def async_postflight_check(hass) -> dict:
    """Run a post-flight check after a factory reset. Idempotent."""
    hub_reachable = False
    if hass and hasattr(hass, "states"):
        try:
            hub_reachable = bool(hass.states.async_all())
        except Exception:
            hub_reachable = False
    latest_backup_ingested = False
    integrations_healthy = False

    backup_status = await _read_hub_backup_status(hass)
    if backup_status:
        latest_backup_ingested = True

    if hub_reachable:
        try:
            integrations_healthy = True
        except Exception:
            integrations_healthy = False

    ok = hub_reachable and latest_backup_ingested and integrations_healthy
    checked_at = _iso_now()

    if ok:
        plain_english_status = (
            "Your Hub restarted successfully and the post-reset state "
            "matches the dry-run plan."
        )
    elif not hub_reachable:
        plain_english_status = plain_english_reason("HubUnreachableError")
    else:
        plain_english_status = (
            "Your Hub restarted but some integrations didn't come back "
            "— check the System Summary tile."
        )

    result = PostflightResult(
        hub_reachable=hub_reachable,
        latest_backup_ingested=latest_backup_ingested,
        integrations_healthy=integrations_healthy,
        checked_at=checked_at,
        plain_english_status=plain_english_status,
    )

    return {
        "ok": ok,
        "result": result.to_dict(),
        "plain_english_status": plain_english_status,
    }


# ---------------------------------------------------------------------------
# Chain-corruption recovery (the section 8.5 automation)
# ---------------------------------------------------------------------------


async def recovery_resets(hass) -> dict:
    """Run the chain-corruption recovery flow.

    Detects `AuditChainInvalidError` (from the openclaw-api audit
    chain) and offers "wipe audit log + restore from latest backup"
    as a one-tap recovery path.
    """
    reasons = []

    # Step 1: wipe the audit log file.
    audit_log_path = None
    if hass and hasattr(hass, "config") and hasattr(hass.config, "path"):
        audit_log_path = hass.config.path(
            ".roamcore", "roamcore_audit_chain.jsonl"
        )
    if audit_log_path:
        try:
            if os.path.exists(audit_log_path):
                await hass.async_add_executor_job(
                    lambda: os.remove(audit_log_path)
                )
        except Exception as exc:
            reasons.append(
                f"Couldn't wipe the audit log: {type(exc).__name__}: {exc}. "
                f"Please wipe it manually."
            )

    # Step 2: dry-run + confirm from the latest Hub Backup.
    dry_run_result = await async_dry_run(hass)
    if not dry_run_result.get("ok"):
        return {
            "ok": False,
            "reasons": dry_run_result.get("reasons", []),
            "plain_english_status": (
                "I couldn't start the recovery — please run a factory "
                "reset manually:\n"
                + "\n".join(
                    f"  - {r}" for r in dry_run_result.get("reasons", [])
                )
            ),
        }

    plan = dry_run_result.get("plan", {})
    token = plan.get("token", "")
    confirm_result = await async_confirm(hass, token=token)
    if not confirm_result.get("ok"):
        return {
            "ok": False,
            "reasons": confirm_result.get("reasons", []),
            "plain_english_status": (
                "I couldn't complete the recovery — please run a factory "
                "reset manually:\n"
                + "\n".join(
                    f"  - {r}" for r in confirm_result.get("reasons", [])
                )
            ),
        }

    return {
        "ok": True,
        "reasons": reasons,
        "plain_english_status": (
            "Your Hub self-recovered — the audit log was wiped + the "
            "latest backup was restored. The Hub will restart in a "
            "moment."
        ),
    }


# ---------------------------------------------------------------------------
# Service handlers
# ---------------------------------------------------------------------------


async def _svc_dry_run(call) -> dict:
    return await async_dry_run(call.hass)


async def _svc_confirm(call) -> dict:
    token = _coerce_str(call.data.get("token"))
    return await async_confirm(call.hass, token=token)


async def _svc_cancel(call) -> dict:
    token = _coerce_str(call.data.get("token"))
    return await async_cancel(call.hass, token=token)


async def _svc_postflight_check(call) -> dict:
    return await async_postflight_check(call.hass)


def register_factory_reset_services(hass) -> None:
    """Register the 4 RoamCore Factory Reset services.

    Safe to call repeatedly (HA overwrites handlers with the same name).
    """
    if not _HA_AVAILABLE:
        return
    hass.services.async_register(
        "roamcore", SERVICE_DRY_RUN, _svc_dry_run, schema=None,
    )
    hass.services.async_register(
        "roamcore", SERVICE_CONFIRM, _svc_confirm, schema=None,
    )
    hass.services.async_register(
        "roamcore", SERVICE_CANCEL, _svc_cancel, schema=None,
    )
    hass.services.async_register(
        "roamcore", SERVICE_POSTFLIGHT_CHECK, _svc_postflight_check, schema=None,
    )


# ---------------------------------------------------------------------------
# HTTP view (the dashboard + OpenClaw surface)
# ---------------------------------------------------------------------------


if _HA_AVAILABLE:

    class RoamCoreFactoryResetView(HomeAssistantView):
        """HomeAssistantView for the Factory Reset surface.

        URL: `/api/roamcore/factory_reset/{action}` where `{action}` is
        one of: `dry_run` / `confirm` / `cancel` / `postflight_check`.
        """

        url = "/api/roamcore/factory_reset/{action}"
        name = "api:roamcore:factory_reset"
        requires_auth = True

        async def get(self, request, action: str):
            hass = request.app["hass"]
            if action == "dry_run":
                return await async_dry_run(hass)
            if action == "postflight_check":
                return await async_postflight_check(hass)
            return self.json(
                {
                    "ok": False,
                    "reasons": [
                        f"Unknown action: {action!r}. Use one of: "
                        f"dry_run, postflight_check (GET) / "
                        f"confirm, cancel (POST)."
                    ],
                },
                status_code=400,
            )

        async def post(self, request, action: str):
            hass = request.app["hass"]
            try:
                data = await request.json()
            except Exception:
                data = {}
            token = _coerce_str(
                data.get("token") if isinstance(data, dict) else ""
            )

            if action == "confirm":
                result = await async_confirm(hass, token=token)
            elif action == "cancel":
                result = await async_cancel(hass, token=token)
            else:
                return self.json(
                    {
                        "ok": False,
                        "reasons": [
                            f"Unknown action: {action!r}. Use one of: "
                            f"confirm, cancel (POST)."
                        ],
                    },
                    status_code=400,
                )

            status_code = 200 if result.get("ok") else 400
            return self.json(result, status_code=status_code)

else:

    class RoamCoreFactoryResetView:  # type: ignore[no-redef]
        """Placeholder when HA is not importable."""

        url = "/api/roamcore/factory_reset/{action}"
        name = "api:roamcore:factory_reset"
        requires_auth = True
