from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN


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


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    async_add_entities([RoamcoreOpenClawLastSeenSensor(hass, entry)], update_before_add=False)
