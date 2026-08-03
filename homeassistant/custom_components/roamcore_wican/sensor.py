"""Sensor platform for the RoamCore WiCAN Pro integration.

Exposes one `sensor.rc_obd_<metric>` entity per generic Mode-01 PID we
support, plus a `sensor.rc_obd_session_readings` counter that surfaces
the running session's reading count.

All entity IDs follow `docs/reference/rc-entity-naming.md` (subsystem
prefix `rc_obd_*`). No vendor names. No WiCAN. No OBD2. The operator
sees "Engine RPM", not "WiCAN PID 0x0C".
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Optional

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import WicanCoordinator
from .pids import PID_TABLE


@dataclass(frozen=True)
class WicanSensorDescription(SensorEntityDescription):
    """Description for a WiCAN PID sensor, with a PID-aware value function."""

    pid: Optional[int] = None
    value_fn: Optional[Callable[[dict[int, float]], Optional[float]]] = None


def _latest(pid: int):
    """Return a value_fn that pulls a specific PID from the coordinator data."""
    def fn(data: dict[int, float]) -> Optional[float]:
        return data.get(pid)
    return fn


def _session_count(coordinator: WicanCoordinator):
    """Return a value_fn that pulls the running session's reading count from DB."""
    def fn(_data: dict[int, float]) -> Optional[float]:
        session = coordinator.db.get_session(coordinator.session_id) if coordinator.session_id else None
        return float(session["reading_count"]) if session else None
    return fn


SENSOR_DESCRIPTIONS: list[WicanSensorDescription] = [
    WicanSensorDescription(
        pid=p.pid,
        key=f"pid_{p.pid:02x}",
        translation_key=f"obd_{p.name}",
        name=f"OBD {p.label}",
        icon="mdi:car",
        native_unit_of_measurement=p.unit,
        device_class=p.device_class or None,
        state_class="measurement",
        value_fn=_latest(p.pid),
    )
    for p in PID_TABLE
] + [
    WicanSensorDescription(
        key="session_readings",
        translation_key="obd_session_readings",
        name="OBD session readings",
        icon="mdi:counter",
        native_unit_of_measurement="readings",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class="total_increasing",
        value_fn=None,  # set per-instance below
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the WiCAN Pro sensors from a config entry."""
    coordinator: WicanCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[WicanPidSensor] = []

    for desc in SENSOR_DESCRIPTIONS:
        if desc.key == "session_readings":
            value_fn = _session_count(coordinator)
        elif desc.value_fn is not None:
            value_fn = desc.value_fn
        else:
            continue
        entities.append(WicanPidSensor(coordinator, desc, value_fn))

    async_add_entities(entities)


class WicanPidSensor(CoordinatorEntity[WicanCoordinator], SensorEntity):
    """A single WiCAN PID sensor."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: WicanCoordinator,
        description: WicanSensorDescription,
        value_fn: Callable[[dict[int, float]], Optional[float]],
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._value_fn = value_fn
        if description.pid is not None:
            self._attr_unique_id = f"{coordinator.device_name}_{description.pid:02x}"
            self.entity_id = f"sensor.rc_obd_{PID_TABLE[[p.pid for p in PID_TABLE].index(description.pid)].name}"
        else:
            self._attr_unique_id = f"{coordinator.device_name}_session_readings"
            self.entity_id = "sensor.rc_obd_session_readings"

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        if self.entity_description.key == "session_readings":
            session = self.coordinator.db.get_session(self.coordinator.session_id) if self.coordinator.session_id else None
            if not session:
                return None
            return int(session["reading_count"])
        return self._value_fn(data)
