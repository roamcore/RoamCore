"""Binary sensor platform for the RoamCore WiCAN Pro integration.

Exposes:
  - binary_sensor.rc_obd_connected — TRUE when the coordinator has had
    a successful poll in the last 3*poll_interval seconds, FALSE otherwise.
  - binary_sensor.rc_obd_dtc_active — TRUE when the DB has any active
    (not-yet-cleared) DTC codes, FALSE otherwise.
"""

from __future__ import annotations

from datetime import timedelta

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import WicanCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the WiCAN Pro binary sensors from a config entry."""
    coordinator: WicanCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            WicanConnectedBinarySensor(coordinator),
            WicanDtcActiveBinarySensor(coordinator),
        ]
    )


class WicanConnectedBinarySensor(CoordinatorEntity[WicanCoordinator], BinarySensorEntity):
    """binary_sensor.rc_obd_connected — true when WiCAN is reachable."""

    _attr_has_entity_name = True
    _attr_name = "OBD connected"
    _attr_unique_id = "rc_obd_connected"

    def __init__(self, coordinator: WicanCoordinator) -> None:
        super().__init__(coordinator)
        self.entity_id = "binary_sensor.rc_obd_connected"

    @property
    def is_on(self) -> bool:
        return self.coordinator.last_successful_ts is not None

    @property
    def available(self) -> bool:
        return True  # binary sensor itself is always available; its state reflects the device

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "device_name": self.coordinator.device_name,
            "last_successful_ts": self.coordinator.last_successful_ts,
            "session_id": self.coordinator.session_id,
        }


class WicanDtcActiveBinarySensor(CoordinatorEntity[WicanCoordinator], BinarySensorEntity):
    """binary_sensor.rc_obd_dtc_active — true when active DTCs exist."""

    _attr_has_entity_name = True
    _attr_name = "OBD DTC active"
    _attr_unique_id = "rc_obd_dtc_active"
    _attr_device_class = "problem"

    def __init__(self, coordinator: WicanCoordinator) -> None:
        super().__init__(coordinator)
        self.entity_id = "binary_sensor.rc_obd_dtc_active"

    @property
    def is_on(self) -> bool:
        try:
            return len(self.coordinator.db.list_active_dtcs()) > 0
        except Exception:
            return False

    @property
    def extra_state_attributes(self) -> dict:
        try:
            dtcs = self.coordinator.db.list_active_dtcs()
        except Exception:
            dtcs = []
        return {
            "count": len(dtcs),
            "codes": [d["code"] for d in dtcs],
            "first_seen": {d["code"]: d["ts"] for d in dtcs},
        }
