from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN


# How long the "last action" indicator stays ON after an audit record
# is appended. 60s gives a visible pulse without being noisy.
LAST_ACTION_HOLD_SEC = 60


class RoamcoreOpenClawLastSeenSensor(SensorEntity, RestoreEntity):
    """Tracks when any RoamCore OpenClaw endpoint was last accessed.

    Intended as a simple onboarding/verification signal.
    """

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:robot"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self._entry_id = entry.entry_id

        # Use an rc_* name so the entity_id is stable + matches RoamCore conventions.
        self._attr_name = "rc_openclaw_last_seen"
        self._attr_unique_id = f"{entry.entry_id}_rc_openclaw_last_seen"

        self._attr_native_value: Optional[datetime] = None
        self._attr_extra_state_attributes: dict[str, Any] = {"endpoint": None}

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        # Restore previous state (so "last seen" survives restart).
        last = await self.async_get_last_state()
        if last and last.state and last.state not in ("unknown", "unavailable"):
            try:
                dt = dt_util.parse_datetime(last.state)
                if dt is not None:
                    self._attr_native_value = dt_util.as_utc(dt)
            except Exception:
                pass
            try:
                ep = last.attributes.get("endpoint")
                if ep:
                    self._attr_extra_state_attributes = {"endpoint": str(ep)}
            except Exception:
                pass

        # Register into hass.data so HTTP views can update us.
        try:
            per_entry = self.hass.data.setdefault(DOMAIN, {}).setdefault(self._entry_id, {})
            per_entry["openclaw_last_seen_entity"] = self

            pending = per_entry.get("openclaw_last_seen")
            if isinstance(pending, dict) and pending.get("ts"):
                ts = pending.get("ts")
                endpoint = str(pending.get("endpoint") or "")
                if isinstance(ts, datetime):
                    self._attr_native_value = dt_util.as_utc(ts)
                    self._attr_extra_state_attributes = {"endpoint": endpoint or None}
        except Exception:
            # best-effort; never break startup
            pass

    def async_mark_seen(self, endpoint: str) -> None:
        self._attr_native_value = dt_util.utcnow()
        self._attr_extra_state_attributes = {"endpoint": str(endpoint or "") or None}
        self.async_write_ha_state()


class RoamcoreOpenClawApiLastActionBinarySensor(BinarySensorEntity, RestoreEntity):
    """Flips to ON for 60s whenever an audit record is appended.

    Shows up under Connectivity → OpenClaw in the dashboard and serves
    as a visible "something just happened" indicator next to the
    ``rc_openclaw_api_*`` contract tiles. ``device_class="safety"``
    surfaces it on the Safety panel too.
    """

    _attr_device_class = BinarySensorDeviceClass.SAFETY
    _attr_icon = "mdi:robot"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self._entry_id = entry.entry_id
        self._attr_name = "rc_openclaw_api_last_action"
        self._attr_unique_id = f"{entry.entry_id}_rc_openclaw_api_last_action"

        self._attr_is_on: bool = False
        self._last_action_ts: Optional[datetime] = None
        self._attr_extra_state_attributes: dict[str, Any] = {
            "last_action_id": None,
            "last_action_ts": None,
            "last_actor": None,
            "last_result": None,
        }
        self._cancel_off_timer = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        # Restore previous state.
        last = await self.async_get_last_state()
        if last and last.state in ("on", "off"):
            try:
                self._attr_is_on = (last.state == "on")
            except Exception:
                pass
            try:
                attrs = dict(last.attributes or {})
                self._attr_extra_state_attributes = {
                    "last_action_id": attrs.get("last_action_id"),
                    "last_action_ts": attrs.get("last_action_ts"),
                    "last_actor": attrs.get("last_actor"),
                    "last_result": attrs.get("last_result"),
                }
                ts = attrs.get("last_action_ts")
                if isinstance(ts, str):
                    try:
                        self._last_action_ts = dt_util.parse_datetime(ts)
                        if self._last_action_ts is not None:
                            self._last_action_ts = dt_util.as_utc(self._last_action_ts)
                    except Exception:
                        self._last_action_ts = None
            except Exception:
                pass

        # Register for HTTP view updates.
        try:
            per_entry = self.hass.data.setdefault(DOMAIN, {}).setdefault(self._entry_id, {})
            per_entry["openclaw_last_action_entity"] = self
        except Exception:
            pass

        # If we restored to "on", schedule the auto-off timer.
        if self._attr_is_on:
            self._schedule_auto_off()

    def _schedule_auto_off(self) -> None:
        """Schedule the auto-off flip in LAST_ACTION_HOLD_SEC seconds."""

        if self._cancel_off_timer is not None:
            try:
                self._cancel_off_timer()
            except Exception:
                pass
            self._cancel_off_timer = None

        async def _flip_off():
            self._attr_is_on = False
            self.async_write_ha_state()

        try:
            self._cancel_off_timer = self.hass.loop.call_later(
                LAST_ACTION_HOLD_SEC, lambda: self.hass.async_create_task(_flip_off())
            )
        except Exception:
            # Best-effort; the binary sensor may not flip back if the
            # scheduler is broken, but it will still reflect the latest
            # action on the next mark_action().
            pass

    def async_mark_action(self, record: dict[str, Any]) -> None:
        """Called by HTTP views when an audit record is appended."""

        try:
            ts_raw = str(record.get("ts") or "")
            ts = dt_util.parse_datetime(ts_raw) if ts_raw else dt_util.utcnow()
            if ts is not None:
                ts = dt_util.as_utc(ts)
        except Exception:
            ts = dt_util.utcnow()
        self._last_action_ts = ts

        actor = record.get("actor") or {}
        self._attr_extra_state_attributes = {
            "last_action_id": str(record.get("action_id") or "") or None,
            "last_action_ts": ts.isoformat() if ts else None,
            "last_actor": (
                f"{actor.get('kind', '?')}:{actor.get('id', '?')}"
                if isinstance(actor, dict) else None
            ),
            "last_result": str(record.get("result") or "") or None,
        }
        self._attr_is_on = True
        self.async_write_ha_state()
        self._schedule_auto_off()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    async_add_entities(
        [
            RoamcoreOpenClawLastSeenSensor(hass, entry),
            RoamcoreOpenClawApiLastActionBinarySensor(hass, entry),
        ],
        update_before_add=False,
    )