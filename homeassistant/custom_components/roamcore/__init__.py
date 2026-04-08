from __future__ import annotations

from datetime import datetime
import os

from homeassistant.config_entries import ConfigEntry
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
)
from .diagnostics_view import RoamcoreDiagnosticsView
import aiohttp

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

    # Ensure options defaults exist
    options = dict(entry.options)
    if CONF_CONTRACT_VERSION not in options:
        options[CONF_CONTRACT_VERSION] = DEFAULT_CONTRACT_VERSION
    if CONF_OPENCLAW_API_ENABLED not in options:
        options[CONF_OPENCLAW_API_ENABLED] = DEFAULT_OPENCLAW_API_ENABLED

    if options != dict(entry.options):
        hass.config_entries.async_update_entry(entry, options=options)

    # HACS-first: auto-provision RoamCore assets into /config on first setup.
    # We guard with a marker file so this is idempotent and never loops.
    try:
        auto = bool(options.get(CONF_AUTO_PROVISION_ASSETS, DEFAULT_AUTO_PROVISION_ASSETS))
        ref = str(options.get(CONF_PROVISION_REF, DEFAULT_PROVISION_REF) or DEFAULT_PROVISION_REF)
        marker = hass.config.path(".roamcore", "provisioned.marker")
        if auto and not os.path.exists(marker):
            try:
                async with aiohttp.ClientSession() as session:
                    await provision_from_github(
                        session=session,
                        repo="https://github.com/roamcore/RoamCore",
                        ref=ref,
                        config_dir=hass.config.path(""),
                        state_dir=".roamcore",
                    )
                await hass.async_add_executor_job(lambda: _atomic_write(marker, f"provisioned_at={datetime.now().isoformat()}\nref={ref}\n"))

                # Notify user to restart to pick up packages/components.
                hass.async_create_task(
                    hass.services.async_call(
                        "persistent_notification",
                        "create",
                        {
                            "title": "RoamCore installed",
                            "message": "RoamCore provisioned dashboard/packages/tools into /config. Restart Home Assistant to load everything.",
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

    # Register HTTP endpoints (OpenClaw summary)
    if options.get(CONF_OPENCLAW_API_ENABLED, DEFAULT_OPENCLAW_API_ENABLED):
        hass.http.register_view(OpenClawSummaryView(hass, entry.entry_id))
        hass.http.register_view(OpenClawSkillView(hass, entry.entry_id))
        hass.http.register_view(OpenClawRcDumpView(hass, entry.entry_id))
        hass.http.register_view(OpenClawTimeSeriesCatalogView(hass, entry.entry_id))
        hass.http.register_view(OpenClawTimeSeriesView(hass, entry.entry_id))

    # Always-on, authenticated diagnostics endpoint for the UI/support.
    hass.http.register_view(RoamcoreDiagnosticsView(hass, entry.entry_id))

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

        async with aiohttp.ClientSession() as session:
            await provision_from_github(
                session=session,
                repo=repo,
                ref=ref,
                config_dir=config_dir,
                state_dir=state_dir,
            )

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

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Home Assistant does not currently provide a stable public API to unregister
    # HTTP views. We leave the view registered for the life of the process.
    return True
