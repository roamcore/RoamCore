from __future__ import annotations

from datetime import datetime
import os
import asyncio

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    CONF_CONTRACT_VERSION,
    DEFAULT_CONTRACT_VERSION,
    CONF_OPENCLAW_API_ENABLED,
    DEFAULT_OPENCLAW_API_ENABLED,
    CONF_AUTO_PROVISION_ASSETS,
    DEFAULT_AUTO_PROVISION_ASSETS,
    CONF_PROVISION_REF,
    DEFAULT_PROVISION_REF,
)
from .openclaw_view import (
    OpenClawSummaryView,
    OpenClawSkillView,
    OpenClawRcDumpView,
    OpenClawTimeSeriesCatalogView,
    OpenClawTimeSeriesView,
    OpenClawAutomationIntentsView,
    OpenClawAutomationValidateView,
)
from .diagnostics_view import RoamcoreDiagnosticsView
from .system_summary_view import RoamcoreSystemSummaryView
from .update_view import RoamcoreUpdateView, fetch_latest_release_tag
import aiohttp

from .pmtiles_view import RoamcorePmtilesView

from .provision import provision_from_github
from .support_bundle import export_support_bundle

from .actions import (
    _utc_now_iso,
    allowlist_path,
    auditlog_path,
    load_allowlist_yaml,
    find_action,
    validate_constraints,
    append_audit_record,
)


PLATFORMS: list[Platform] = [Platform.SENSOR]


RESTART_NOTIFICATION_ID = "roamcore_restart_required"
PROVISIONED_MARKER_NAME = "provisioned.marker"
RESTART_MARKER_NAME = "restart_required.marker"

# Bump this when shipped /config/www assets (dashboard JS/CSS/etc) should be
# refreshed automatically for users.
ASSET_BUILD_ID = "2026-04-12T20:12Z"


def _secrets_path(hass: HomeAssistant) -> str:
    # HA config dir secrets.yaml
    return hass.config.path("secrets.yaml")


def _secrets_set_text(text: str, key: str, value: str) -> str:
    """Set or add a single key in secrets.yaml (best-effort, preserves other lines).

    We intentionally do line-based replacement to avoid rewriting the whole file
    (which would destroy comments/formatting).
    """
    import re

    key = str(key).strip()
    if not key:
        raise ValueError("key is required")
    # Quote value to be safe with special chars.
    v = str(value)
    v = v.replace('\\', '\\\\').replace('"', '\\"')
    new_line = f'{key}: "{v}"'

    lines = (text or "").splitlines()
    out = []
    found = False
    pat = re.compile(rf"^\s*{re.escape(key)}\s*:\s*(.*)$")
    for ln in lines:
        if pat.match(ln):
            out.append(new_line)
            found = True
        else:
            out.append(ln)
    if not found:
        if out and out[-1].strip() != "":
            out.append("")
        out.append(new_line)
    return "\n".join(out).rstrip("\n") + "\n"


def _secrets_delete_text(text: str, key: str) -> str:
    import re

    key = str(key).strip()
    if not key:
        raise ValueError("key is required")
    lines = (text or "").splitlines()
    pat = re.compile(rf"^\s*{re.escape(key)}\s*:\s*(.*)$")
    out = [ln for ln in lines if not pat.match(ln)]
    return "\n".join(out).rstrip("\n") + "\n"


async def _async_write_text_atomic(path: str, text: str) -> None:
    import os
    import tempfile

    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=os.path.basename(path) + ".", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    finally:
        try:
            if os.path.exists(tmp):
                os.unlink(tmp)
        except Exception:
            pass


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up RoamCore from YAML (deprecated; prefer config entry)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up RoamCore from a config entry."""

    # If we previously asked for a restart after provisioning, clear that
    # notification on the next HA start (i.e., after the restart happened).
    try:
        restart_marker = hass.config.path(".roamcore", RESTART_MARKER_NAME)
        if os.path.exists(restart_marker):
            try:
                await hass.services.async_call(
                    "persistent_notification",
                    "dismiss",
                    {"notification_id": RESTART_NOTIFICATION_ID},
                    blocking=True,
                )
            except Exception:
                pass

            try:
                await hass.async_add_executor_job(lambda: os.remove(restart_marker))
            except Exception:
                pass
    except Exception:
        pass

    # Ensure options defaults exist
    options = dict(entry.options)
    if CONF_CONTRACT_VERSION not in options:
        options[CONF_CONTRACT_VERSION] = DEFAULT_CONTRACT_VERSION
    if CONF_OPENCLAW_API_ENABLED not in options:
        options[CONF_OPENCLAW_API_ENABLED] = DEFAULT_OPENCLAW_API_ENABLED

    if options != dict(entry.options):
        hass.config_entries.async_update_entry(entry, options=options)

    # HACS-first: auto-provision RoamCore assets into /config.
    # We guard with a marker file so this is idempotent and never loops.
    # Additionally, we re-provision when ASSET_BUILD_ID changes so critical
    # frontend fixes roll out without requiring the user to manually call
    # roamcore.provision_assets.
    try:
        auto = bool(options.get(CONF_AUTO_PROVISION_ASSETS, DEFAULT_AUTO_PROVISION_ASSETS))
        ref = str(options.get(CONF_PROVISION_REF, DEFAULT_PROVISION_REF) or DEFAULT_PROVISION_REF)
        marker = hass.config.path(".roamcore", PROVISIONED_MARKER_NAME)
        restart_marker = hass.config.path(".roamcore", RESTART_MARKER_NAME)
        marker_txt = ""
        try:
            if os.path.exists(marker):
                marker_txt = await hass.async_add_executor_job(lambda: open(marker, "r", encoding="utf-8").read())
        except Exception:
            marker_txt = ""

        needs = (not os.path.exists(marker)) or (f"asset_build={ASSET_BUILD_ID}" not in marker_txt)

        if auto and needs:
            try:
                async with aiohttp.ClientSession() as session:
                    result = await provision_from_github(
                        session=session,
                        repo="https://github.com/roamcore/RoamCore",
                        ref=ref,
                        config_dir=hass.config.path(""),
                        state_dir=".roamcore",
                    )

                await _async_write_text_atomic(
                    marker,
                    f"provisioned_at={datetime.now().isoformat()}\nref={ref}\nasset_build={ASSET_BUILD_ID}\n",
                )
                await _async_write_text_atomic(
                    restart_marker,
                    f"created_at={datetime.now().isoformat()}\nreason=assets_provisioned\nbackup_dir={result.backup_dir}\n",
                )

                # Clear any previous provisioning failure notification.
                hass.async_create_task(
                    hass.services.async_call(
                        "persistent_notification",
                        "dismiss",
                        {"notification_id": "roamcore_provisioning_failed"},
                        blocking=False,
                    )
                )

                # Notify user to restart to pick up packages/components.
                hass.async_create_task(
                    hass.services.async_call(
                        "persistent_notification",
                        "create",
                        {
                            "title": "RoamCore: restart required",
                            "message": "RoamCore provisioned dashboard/packages/tools into /config. Restart Home Assistant to load everything.",
                            "notification_id": RESTART_NOTIFICATION_ID,
                        },
                        blocking=False,
                    )
                )
            except Exception as e:
                # If auto-provisioning fails, surface a persistent notification with recovery steps.
                try:
                    service_link = "https://my.home-assistant.io/redirect/developer_services/?service=roamcore.provision_assets"
                    err = f"{type(e).__name__}: {e}"
                    msg = "\n".join(
                        [
                            "RoamCore tried to auto-provision assets into /config but failed.",
                            f"Error: {err}",
                            "",
                            "To retry: Settings → Developer Tools → Services → call roamcore.provision_assets.",
                            f"Quick link: {service_link}",
                            "",
                            "Service data (optional):",
                            "  repo: https://github.com/roamcore/RoamCore",
                            f"  ref: {ref}",
                            "",
                            "Common causes: no internet/DNS, GitHub blocked, or storage permissions.",
                        ]
                    )
                    hass.async_create_task(
                        hass.services.async_call(
                            "persistent_notification",
                            "create",
                            {
                                "title": "RoamCore provisioning failed",
                                "message": msg,
                                "notification_id": "roamcore_provisioning_failed",
                            },
                            blocking=False,
                        )
                    )
                except Exception:
                    pass
    except Exception:
        # Provisioning is best-effort; never break HA startup.
        pass

    # Register HTTP endpoints (OpenClaw API)
    # NOTE: always register views so the enable toggle can take effect immediately
    # without requiring a HA restart/reload. Each view checks the config entry
    # option at request-time and returns 404 when disabled.
    hass.http.register_view(OpenClawSummaryView(hass, entry.entry_id))
    hass.http.register_view(OpenClawSkillView(hass, entry.entry_id))
    hass.http.register_view(OpenClawRcDumpView(hass, entry.entry_id))
    hass.http.register_view(OpenClawTimeSeriesCatalogView(hass, entry.entry_id))
    hass.http.register_view(OpenClawTimeSeriesView(hass, entry.entry_id))
    hass.http.register_view(OpenClawAutomationIntentsView(hass, entry.entry_id))
    hass.http.register_view(OpenClawAutomationValidateView(hass, entry.entry_id))

    # Always-on, authenticated diagnostics endpoint for the UI/support.
    hass.http.register_view(RoamcoreDiagnosticsView(hass, entry.entry_id))

    # Always-on, authenticated deterministic system summary (UI + agents).
    hass.http.register_view(RoamcoreSystemSummaryView(hass))

    # Always-on, authenticated update endpoint for the Settings UI.
    hass.http.register_view(RoamcoreUpdateView(hass, entry.entry_id))

    # Always-on, authenticated PMTiles endpoint (Range-friendly) for MapLibre/PMTiles.
    hass.http.register_view(RoamcorePmtilesView(hass))

    # Entities used for onboarding/verification (e.g. OpenClaw last-seen sensor).
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services used by the setup wizard.
    async def _svc_secrets_set(call):
        key = str(call.data.get("key") or "").strip()
        value = str(call.data.get("value") or "")
        p = _secrets_path(hass)

        def _read():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return f.read()
            except FileNotFoundError:
                return ""

        old = await hass.async_add_executor_job(_read)
        new = _secrets_set_text(old, key=key, value=value)
        await hass.async_add_executor_job(lambda: __import__("os").path.exists(p))
        await _async_write_text_atomic(p, new)

    async def _svc_secrets_delete(call):
        key = str(call.data.get("key") or "").strip()
        p = _secrets_path(hass)

        def _read():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return f.read()
            except FileNotFoundError:
                return ""

        old = await hass.async_add_executor_job(_read)
        new = _secrets_delete_text(old, key=key)
        await _async_write_text_atomic(p, new)

    # Safe to call repeatedly (HA will overwrite handler with same name).
    hass.services.async_register(
        DOMAIN,
        "secrets_set",
        _svc_secrets_set,
        schema=None,
    )
    hass.services.async_register(
        DOMAIN,
        "secrets_delete",
        _svc_secrets_delete,
        schema=None,
    )

    # --- Options helpers (for dashboard UX) ---
    # The RoamCore dashboard (roamcore-pages.js) uses these to provide a simple
    # toggle + onboarding flow without requiring the user to dig into HA's
    # integration options UI.
    async def _svc_options_set(call):
        data = call.data or {}
        enabled = data.get("openclaw_api_enabled", None)
        requires_auth = data.get("openclaw_api_requires_auth", None)

        # Find the (single) RoamCore config entry.
        entries = hass.config_entries.async_entries(DOMAIN)
        if not entries:
            raise ValueError("No RoamCore config entry found")
        ent = entries[0]

        opts = dict(ent.options)
        changed = False

        if enabled is not None:
            opts[CONF_OPENCLAW_API_ENABLED] = bool(enabled)
            changed = True
        if requires_auth is not None:
            opts[CONF_OPENCLAW_API_REQUIRES_AUTH] = bool(requires_auth)
            changed = True

        if changed:
            hass.config_entries.async_update_entry(ent, options=opts)

    hass.services.async_register(
        DOMAIN,
        "options_set",
        _svc_options_set,
        schema=None,
    )

    # --- Agent Actions Gateway (Roadmap) ---
    # Default-deny, user-owned allowlist + audit log. This is intentionally
    # conservative: we only support setting input_* helpers and running scripts.
    # If the global kill switch is off, nothing executes.
    async def _svc_action_execute(call):
        action_id = str(call.data.get("action_id") or "").strip()
        args = call.data.get("args") or {}
        reason = str(call.data.get("reason") or "").strip()

        cfg_dir = hass.config.path("")
        allow_path = allowlist_path(cfg_dir)
        log_path = auditlog_path(cfg_dir)

        record: dict = {
            "ts": _utc_now_iso(),
            "action_id": action_id,
            "reason": reason,
            "args": args,
            "result": {"ok": False},
        }

        try:
            if not action_id:
                record["result"] = {"ok": False, "error": "action_id is required"}
                return

            # Kill switch must exist and be ON.
            enabled = hass.states.get("input_boolean.rc_agent_actions_enabled")
            if not enabled or enabled.state != "on":
                record["result"] = {"ok": False, "error": "agent actions disabled"}
                return

            policy = load_allowlist_yaml(allow_path)
            act = find_action(policy, action_id=action_id)
            if not act:
                record["result"] = {"ok": False, "error": "action not allowlisted"}
                return

            kind = str(act.get("kind") or "").strip()
            target = act.get("target") or {}
            constraints = act.get("constraints") or {}

            # MVP supported kinds
            if kind == "set_helper":
                entity_ids = target.get("entity_id")
                if isinstance(entity_ids, str):
                    entity_ids = [entity_ids]
                if not isinstance(entity_ids, list) or not entity_ids:
                    record["result"] = {"ok": False, "error": "invalid target.entity_id"}
                    return

                value = args.get("value")
                ok, err = validate_constraints(constraints, value)
                if not ok:
                    record["result"] = {"ok": False, "error": f"constraints: {err}"}
                    return

                # Enforce input_* only.
                bad = [e for e in entity_ids if not str(e).startswith("input_")]
                if bad:
                    record["result"] = {"ok": False, "error": "set_helper only supports input_* entities"}
                    return

                for eid in entity_ids:
                    domain = str(eid).split(".", 1)[0]
                    if domain == "input_text":
                        await hass.services.async_call(
                            "input_text",
                            "set_value",
                            {"entity_id": eid, "value": str(value if value is not None else "")},
                            blocking=True,
                        )
                    elif domain == "input_number":
                        await hass.services.async_call(
                            "input_number",
                            "set_value",
                            {"entity_id": eid, "value": float(value)},
                            blocking=True,
                        )
                    elif domain == "input_select":
                        await hass.services.async_call(
                            "input_select",
                            "select_option",
                            {"entity_id": eid, "option": str(value)},
                            blocking=True,
                        )
                    elif domain == "input_boolean":
                        svc = "turn_on" if bool(value) else "turn_off"
                        await hass.services.async_call(
                            "input_boolean",
                            svc,
                            {"entity_id": eid},
                            blocking=True,
                        )
                    else:
                        record["result"] = {"ok": False, "error": f"unsupported helper domain: {domain}"}
                        return

                record["result"] = {"ok": True}

            elif kind == "run_script":
                entity_id = target.get("entity_id")
                if not isinstance(entity_id, str) or not entity_id:
                    record["result"] = {"ok": False, "error": "invalid target.entity_id"}
                    return
                if not entity_id.startswith("script.rc_"):
                    record["result"] = {"ok": False, "error": "run_script only supports script.rc_*"}
                    return
                await hass.services.async_call(
                    "script",
                    entity_id.split(".", 1)[1],
                    {},
                    blocking=True,
                )
                record["result"] = {"ok": True}
            else:
                record["result"] = {"ok": False, "error": "unsupported action kind"}
                return
        finally:
            try:
                append_audit_record(log_path, record)
            except Exception:
                pass

    hass.services.async_register(
        DOMAIN,
        "action_execute",
        _svc_action_execute,
        schema=None,
    )

    async def _svc_provision_assets(call):
        # Download the repo archive and copy homeassistant/* assets into /config.
        # Intended for HACS installs where only custom_components are installed.
        repo = str(call.data.get("repo") or "https://github.com/roamcore/RoamCore").strip()
        ref = str(call.data.get("ref") or "main").strip()
        config_dir = hass.config.path("")
        state_dir = ".roamcore"

        marker = hass.config.path(".roamcore", PROVISIONED_MARKER_NAME)
        restart_marker = hass.config.path(".roamcore", RESTART_MARKER_NAME)

        async with aiohttp.ClientSession() as session:
            result = await provision_from_github(
                session=session,
                repo=repo,
                ref=ref,
                config_dir=config_dir,
                state_dir=state_dir,
            )

        # Mark as provisioned so auto-provision won't re-run on next start.
        try:
            await _async_write_text_atomic(
                marker,
                f"provisioned_at={datetime.now().isoformat()}\nrepo={repo}\nref={ref}\nasset_build={ASSET_BUILD_ID}\n",
            )
        except Exception:
            pass

        # Ask user to restart, and make it self-clearing on next HA start.
        try:
            await _async_write_text_atomic(
                restart_marker,
                f"created_at={datetime.now().isoformat()}\nreason=assets_provisioned\nbackup_dir={result.backup_dir}\n",
            )
        except Exception:
            pass

        try:
            hass.async_create_task(
                hass.services.async_call(
                    "persistent_notification",
                    "dismiss",
                    {"notification_id": "roamcore_provisioning_failed"},
                    blocking=False,
                )
            )
            hass.async_create_task(
                hass.services.async_call(
                    "persistent_notification",
                    "create",
                    {
                        "title": "RoamCore: restart required",
                        "message": "RoamCore provisioned dashboard/packages/tools into /config. Restart Home Assistant to load everything.",
                        "notification_id": RESTART_NOTIFICATION_ID,
                    },
                    blocking=False,
                )
            )
        except Exception:
            pass

    hass.services.async_register(
        DOMAIN,
        "provision_assets",
        _svc_provision_assets,
        schema=None,
    )

    async def _svc_export_support_bundle(call):
        # Export a diagnostic bundle under /config/.roamcore/support/<timestamp>/
        # and optionally create a zip archive.
        include_zip = bool(call.data.get("zip", True))
        out = await export_support_bundle(hass, include_zip=include_zip)

        # Best-effort UX: tell the user where it went.
        try:
            msg = f"Support bundle exported:\n- dir: {out.get('dir')}"
            if out.get("zip"):
                msg += f"\n- zip: {out.get('zip')}"
            hass.async_create_task(
                hass.services.async_call(
                    "persistent_notification",
                    "create",
                    {"title": "RoamCore support bundle exported", "message": msg},
                    blocking=False,
                )
            )
        except Exception:
            pass

        return out

    hass.services.async_register(
        DOMAIN,
        "export_support_bundle",
        _svc_export_support_bundle,
        schema=None,
    )

    # --- Backup + Update ---
    # Settings UI calls this service.
    # Safe + reversible: take a Supervisor backup when available, then provision.
    hass.data.setdefault(DOMAIN, {})
    backup_update_lock: asyncio.Lock = hass.data[DOMAIN].setdefault("backup_update_lock", asyncio.Lock())

    async def _try_supervisor_backup(name: str) -> dict:
        """Attempt a full Home Assistant backup via built-in services (best-effort)."""

        try:
            if hass.services.has_service("backup", "create"):
                await hass.services.async_call("backup", "create", {"name": name}, blocking=True)
                return {"ok": True, "service": "backup.create"}
            if hass.services.has_service("hassio", "backup_full"):
                await hass.services.async_call("hassio", "backup_full", {"name": name}, blocking=True)
                return {"ok": True, "service": "hassio.backup_full"}
            return {"ok": False, "error": "no_backup_service"}
        except Exception as e:
            return {"ok": False, "error": f"{type(e).__name__}: {e}"}

    async def _svc_backup_update(call):
        repo = str(call.data.get("repo") or "https://github.com/roamcore/RoamCore").strip()
        ref = str(call.data.get("ref") or "").strip()
        target = str(call.data.get("target") or "").strip().lower()
        do_backup = bool(call.data.get("backup", True))

        if backup_update_lock.locked():
            await hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "RoamCore update already running",
                    "message": "A RoamCore Backup + Update is already in progress. Please wait for it to finish.",
                    "notification_id": "roamcore_backup_update_in_progress",
                },
                blocking=False,
            )
            return

        async with backup_update_lock:
            # Resolve latest release tag server-side for determinism.
            if not ref and target in ("latest", "latest_release", "release"):
                try:
                    ref = await fetch_latest_release_tag(repo)
                except Exception:
                    ref = ""

            # Default ref: configured option (fallback to main).
            if not ref:
                try:
                    cur_entry = hass.config_entries.async_get_entry(entry.entry_id)
                    cur_opts = dict(cur_entry.options) if cur_entry else {}
                    ref = str(cur_opts.get(CONF_PROVISION_REF, DEFAULT_PROVISION_REF) or DEFAULT_PROVISION_REF)
                except Exception:
                    ref = DEFAULT_PROVISION_REF

            started_at = datetime.now().isoformat()
            status_notif_id = "roamcore_backup_update"
            try:
                await hass.services.async_call(
                    "persistent_notification",
                    "create",
                    {
                        "title": "RoamCore Backup + Update",
                        "message": f"Starting…\n- repo: {repo}\n- ref: {ref}\n- at: {started_at}",
                        "notification_id": status_notif_id,
                    },
                    blocking=False,
                )
            except Exception:
                pass

            backup_result: dict = {"ok": False, "error": None}
            if do_backup:
                backup_name = str(call.data.get("backup_name") or f"RoamCore pre-update ({ref}) {started_at}")
                backup_result = await _try_supervisor_backup(backup_name)

            # Provision assets (also creates per-file backups under /config/.roamcore/backups/).
            config_dir = hass.config.path("")
            marker = hass.config.path(".roamcore", PROVISIONED_MARKER_NAME)
            restart_marker = hass.config.path(".roamcore", RESTART_MARKER_NAME)

            try:
                async with aiohttp.ClientSession() as session:
                    result = await provision_from_github(
                        session=session,
                        repo=repo,
                        ref=ref,
                        config_dir=config_dir,
                        state_dir=".roamcore",
                    )
            except Exception as e:
                msg = "\n".join(
                    [
                        "Update failed.",
                        f"- repo: {repo}",
                        f"- ref: {ref}",
                        f"- backup: {backup_result}",
                        f"- error: {type(e).__name__}: {e}",
                        "",
                        "You can retry from RoamCore → Settings → Backup + Update.",
                    ]
                )
                try:
                    await hass.services.async_call(
                        "persistent_notification",
                        "create",
                        {"title": "RoamCore update failed", "message": msg, "notification_id": status_notif_id},
                        blocking=False,
                    )
                except Exception:
                    pass
                return

            # Mark as provisioned so auto-provision won't re-run on next start.
            try:
                await _async_write_text_atomic(
                    marker,
                    f"provisioned_at={datetime.now().isoformat()}\nrepo={repo}\nref={ref}\n",
                )
            except Exception:
                pass

            # Ask user to restart, and make it self-clearing on next HA start.
            try:
                await _async_write_text_atomic(
                    restart_marker,
                    "\n".join(
                        [
                            f"created_at={datetime.now().isoformat()}",
                            "reason=backup_update",
                            f"backup_dir={result.backup_dir}",
                            f"backup_result={backup_result}",
                            "",
                        ]
                    ),
                )
            except Exception:
                pass

            msg = "\n".join(
                [
                    "Update complete.",
                    f"- repo: {repo}",
                    f"- ref: {ref}",
                    f"- backup: {backup_result}",
                    f"- per-file backup dir: {result.backup_dir}",
                    "",
                    "Next step: Restart Home Assistant.",
                    "Rollback:",
                    "- Restore a Supervisor backup (preferred), OR",
                    "- Restore files from /config/.roamcore/backups/<timestamp>/",
                ]
            )
            try:
                await hass.services.async_call(
                    "persistent_notification",
                    "create",
                    {"title": "RoamCore: restart required", "message": msg, "notification_id": RESTART_NOTIFICATION_ID},
                    blocking=False,
                )
            except Exception:
                pass

    hass.services.async_register(
        DOMAIN,
        "backup_update",
        _svc_backup_update,
        schema=None,
    )

    # ------------------------------------------------------------------
    # RoamCore Labs (share setups/dashboards) — Wave 2 #32
    # ------------------------------------------------------------------
    # Privacy: the helpers use only the stdlib (tarfile, json, pathlib).
    # No HTTP, no third-party imports, no telemetry. The bundle is a
    # local file the owner shares by whatever channel they trust.
    # ------------------------------------------------------------------

    async def _svc_labs_export_setup(call):
        """Bundle the active RoamCore setup as a local tar.gz."""
        target_path = call.data.get("target_path") or None
        dashboard_file = call.data.get("dashboard_file") or None
        packages_dir = call.data.get("packages_dir") or None

        # Lazy import so the helper is only pulled in when the service
        # is actually called. We resolve the helper path relative to
        # this file so the install path (e.g. /config/custom_components/roamcore/)
        # does not break the lookup.
        import os
        import sys as _sys
        _HERE = os.path.dirname(os.path.abspath(__file__))
        _TOOLS = os.path.abspath(os.path.join(_HERE, "..", "..", "tools"))
        if _TOOLS not in _sys.path:
            _sys.path.insert(0, _TOOLS)
        try:
            from labs import common as _labs_common  # noqa: WPS433
        except Exception as exc:
            raise RuntimeError(
                f"roamcore.labs_export_setup: cannot import labs.common: {exc}"
            )

        try:
            result = await hass.async_add_executor_job(
                _labs_common.build_export,
                target_path=target_path,
                dashboard_file=dashboard_file,
                packages_dir=packages_dir,
                dry_run=False,
            )
        except _labs_common.BundleError as exc:
            raise RuntimeError(f"labs export failed: {exc}")
        except OSError as exc:
            raise RuntimeError(f"labs export filesystem error: {exc}")

        # Mirror the values into the wizard's read-out helpers so the
        # dashboard chip refreshes on the next render. We use HA
        # services directly so the contract entities stay in sync.
        last_path = result.get("path") or ""
        try:
            await hass.services.async_call(
                "input_text",
                "set_value",
                {"entity_id": "input_text.rc_labs_last_export_path",
                 "value": last_path},
                blocking=False,
            )
        except Exception:
            pass

        try:
            await hass.services.async_call(
                "logbook",
                "log",
                {
                    "name": "RoamCore Labs",
                    "message": (
                        f"Exported setup bundle to {last_path} "
                        f"(packages={len(result.get('manifest', {}).get('packages', []))})"
                    ),
                },
                blocking=False,
            )
        except Exception:
            pass

    async def _svc_labs_import_setup(call):
        """Stage a RoamCore Labs bundle for apply-on-next-reload.

        dry_run defaults to true (the operator can opt in to a real
        extract by passing dry_run=false). The bundle is unpacked into
        /config/.storage/roamcore_labs/imports/<stem>_<timestamp>/ and
        the path is reflected into input_text.rc_labs_pending_import so
        the wizard can render the pending-import pill.
        """
        bundle_path = (call.data.get("bundle_path") or "").strip()
        if not bundle_path:
            raise RuntimeError("bundle_path is required")

        apply_flag = bool(call.data.get("apply") or False)
        # Default dry_run to true so a slip-up doesn't extract.
        dry_run = bool(call.data.get("dry_run", True))

        import os
        import sys as _sys
        _HERE = os.path.dirname(os.path.abspath(__file__))
        _TOOLS = os.path.abspath(os.path.join(_HERE, "..", "..", "tools"))
        if _TOOLS not in _sys.path:
            _sys.path.insert(0, _TOOLS)
        try:
            from labs import common as _labs_common  # noqa: WPS433
            from labs.import_setup import stage_bundle as _labs_stage  # noqa: WPS433
        except Exception as exc:
            raise RuntimeError(
                f"roamcore.labs_import_setup: cannot import helpers: {exc}"
            )

        try:
            result = _labs_stage(
                bundle_path=bundle_path,
                apply=apply_flag,
                dry_run=dry_run,
            )
        except _labs_common.BundleError as exc:
            raise RuntimeError(f"labs import failed: {exc}")
        except OSError as exc:
            raise RuntimeError(f"labs import filesystem error: {exc}")

        # Reflect into the contract helpers so the wizard chip refreshes.
        last_status = result.get("apply") and "apply_on_next_reload" or (
            "staged" if not result["dry_run"] else "dry_run"
        )
        if dry_run:
            last_status = "dry_run"
        try:
            await hass.services.async_call(
                "input_text",
                "set_value",
                {"entity_id": "input_text.rc_labs_pending_import",
                 "value": bundle_path},
                blocking=False,
            )
            await hass.services.async_call(
                "input_text",
                "set_value",
                {"entity_id": "input_text.rc_labs_last_import_status",
                 "value": last_status},
                blocking=False,
            )
        except Exception:
            pass

        try:
            await hass.services.async_call(
                "logbook",
                "log",
                {
                    "name": "RoamCore Labs",
                    "message": (
                        f"{'Dry-run' if dry_run else 'Staged'} import of "
                        f"{bundle_path} (status={last_status})"
                    ),
                },
                blocking=False,
            )
        except Exception:
            pass

    hass.services.async_register(
        DOMAIN,
        "labs_export_setup",
        _svc_labs_export_setup,
        schema=None,
    )

    hass.services.async_register(
        DOMAIN,
        "labs_import_setup",
        _svc_labs_import_setup,
        schema=None,
    )

    # ------------------------------------------------------------------
    # RoamCore Gamification (opt-in streak + trophy subsystem) — Wave 2 #33
    # ------------------------------------------------------------------
    # Privacy: pure HA service call. No outbound HTTP, no telemetry,
    # no third-party imports. The trophy service is intentionally
    # boring: it just flips an input_boolean ON so the dashboard can
    # render the trophy as "seen" rather than "new". Idempotent.
    # ------------------------------------------------------------------

    KNOWN_TROPHIES = frozenset({
        "first_trip_wrapped",
        "first_power_session",
        "first_automation",
        "first_share_exported",
        "first_offline_driving_day",
        "first_setup_complete",
        "first_twilight_handling",
    })

    async def _svc_gamification_acknowledge_trophy(call):
        """Flip the matching input_boolean.rc_gamification_trophy_seen_<id> ON.

        The kill-switch (``input_boolean.rc_gamification_enabled``) is
        intentionally NOT consulted here: acknowledging a trophy is a
        pure UI operation and should not be blocked by the master
        switch. The trigger sensors are the ones that gate on the
        master switch; this service is the read-only acknowledgement
        path.

        Raises ``ValueError`` on invalid trophy_id. The error is
        surfaced via ``hass.components.persistent_notification`` so the
        operator can see the message without digging into logs.
        """
        trophy_id = str(call.data.get("trophy_id") or "").strip()
        if trophy_id not in KNOWN_TROPHIES:
            try:
                await hass.services.async_call(
                    "persistent_notification",
                    "create",
                    {
                        "title": "RoamCore gamification: unknown trophy_id",
                        "message": (
                            f"trophy_id {trophy_id!r} is not in the known set: "
                            f"{sorted(KNOWN_TROPHIES)}"
                        ),
                        "notification_id": "roamcore_gamification_unknown_trophy",
                    },
                    blocking=False,
                )
            except Exception:
                pass
            raise ValueError(
                f"unknown trophy_id: {trophy_id!r}"
            )

        entity_id = f"input_boolean.rc_gamification_trophy_seen_{trophy_id}"
        try:
            await hass.services.async_call(
                "input_boolean",
                "turn_on",
                {"entity_id": entity_id},
                blocking=True,
            )
        except Exception as exc:
            raise RuntimeError(
                f"gamification acknowledge failed: {type(exc).__name__}: {exc}"
            )

        # Best-effort: log the acknowledgement in the logbook.
        try:
            await hass.services.async_call(
                "logbook",
                "log",
                {
                    "name": "RoamCore Gamification",
                    "message": f"Acknowledged trophy {trophy_id}",
                },
                blocking=False,
            )
        except Exception:
            pass

    hass.services.async_register(
        DOMAIN,
        "gamification_acknowledge_trophy",
        _svc_gamification_acknowledge_trophy,
        schema=None,
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Home Assistant does not currently provide a stable public API to unregister
    # HTTP views. We leave the view registered for the life of the process.
    try:
        await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    except Exception:
        pass
    return True
