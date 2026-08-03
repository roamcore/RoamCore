"""OBD2 PID (Parameter ID) decoder for the RoamCore WiCAN Pro integration.

Scope: GENERIC Mode-01 PIDs (ISO 15031-5 / SAE J1979) that any 2008+ OBD2-
compliant vehicle exposes. No vendor-proprietary PIDs (Ford Mode-22, GM
Mode-24, VAG Mode-1B, etc.) — those are out of scope for slice #6 and
require per-vehicle research that the operator can opt into later.

Each entry is a dataclass containing:
  - pid: 2-byte OBD2 PID (e.g. 0x0C for engine RPM)
  - name: short snake_case metric name (matches `rc_obd_<name>` contract id)
  - label: human-readable label for the dashboard
  - unit: SI unit string (passed to HA `unit_of_measurement`)
  - device_class: HA sensor device_class
  - bytes: number of data bytes returned by the vehicle (A-n where n = bytes)
  - decoder: callable(byte_array) -> float. Returns None on invalid input.

The decoder always takes the raw data byte payload (i.e. AFTER the PID
header — so for PID 0x0C the input is the 4 response data bytes, not the
6-byte full CAN frame).

References:
  - SAE J1979 (rev 2017): https://www.sae.org/standards/content/j1979_201708/
  - ISO 15031-5:2015 (road vehicles - emissions - OBD communication)
  - Custic WiCAN Pro REST API: GET /api/diagnostics returns a JSON dict
    keyed by decimal PID number, e.g. {"12": 840, "5": 86}. We accept that
    format too via `decode_value()`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class ObdPid:
    pid: int
    name: str
    label: str
    unit: str
    device_class: str
    bytes: int
    decoder: Callable[[bytes], Optional[float]]


def _decode_single_byte_pct(b: bytes) -> Optional[float]:
    """Decode a single-byte percentage: A * 100 / 255."""
    if len(b) < 1:
        return None
    return round(b[0] * 100.0 / 255.0, 2)


def _decode_coolant_temp(b: bytes) -> Optional[float]:
    """PID 0x05: Engine coolant temperature (°C). A - 40."""
    if len(b) < 1:
        return None
    return float(b[0] - 40)


def _decode_rpm(b: bytes) -> Optional[float]:
    """PID 0x0C: Engine RPM. (256 * A + B) / 4."""
    if len(b) < 2:
        return None
    return round((256 * b[0] + b[1]) / 4.0, 2)


def _decode_speed(b: bytes) -> Optional[float]:
    """PID 0x0D: Vehicle speed (km/h). A."""
    if len(b) < 1:
        return None
    return float(b[0])


def _decode_timing_advance(b: bytes) -> Optional[float]:
    """PID 0x0E: Timing advance (degrees before TDC). (A - 128) / 2."""
    if len(b) < 1:
        return None
    return round((b[0] - 128) / 2.0, 2)


def _decode_intake_air_temp(b: bytes) -> Optional[float]:
    """PID 0x0F: Intake air temperature (°C). A - 40."""
    if len(b) < 1:
        return None
    return float(b[0] - 40)


def _decode_maf(b: bytes) -> Optional[float]:
    """PID 0x10: Mass air flow (g/s). (256 * A + B) / 100."""
    if len(b) < 2:
        return None
    return round((256 * b[0] + b[1]) / 100.0, 3)


def _decode_throttle_pct(b: bytes) -> Optional[float]:
    """PID 0x11: Throttle position (%). A * 100 / 255."""
    if len(b) < 1:
        return None
    return round(b[0] * 100.0 / 255.0, 2)


def _decode_run_time(b: bytes) -> Optional[float]:
    """PID 0x1F: Engine run time since start (seconds). 256*A + B."""
    if len(b) < 2:
        return None
    return float(256 * b[0] + b[1])


def _decode_distance_since_dtc_clear(b: bytes) -> Optional[float]:
    """PID 0x31: Distance since DTC cleared (km). 256*A + B."""
    if len(b) < 2:
        return None
    return float(256 * b[0] + b[1])


def _decode_fuel_level_pct(b: bytes) -> Optional[float]:
    """PID 0x2F: Fuel tank level (%). A * 100 / 255."""
    if len(b) < 1:
        return None
    return round(b[0] * 100.0 / 255.0, 2)


def _decode_ambient_air_temp(b: bytes) -> Optional[float]:
    """PID 0x46: Ambient air temperature (°C). A - 40."""
    if len(b) < 1:
        return None
    return float(b[0] - 40)


def _decode_engine_load(b: bytes) -> Optional[float]:
    """PID 0x04: Calculated engine load (%). A * 100 / 255."""
    if len(b) < 1:
        return None
    return round(b[0] * 100.0 / 255.0, 2)


def _decode_fuel_rail_pressure(b: bytes) -> Optional[float]:
    """PID 0x22: Fuel rail pressure (kPa). 10 * (256*A + B)."""
    if len(b) < 2:
        return None
    return float(10 * (256 * b[0] + b[1]))


def _decode_fuel_trim_pct(b: bytes) -> Optional[float]:
    """PID 0x06, 0x07, 0x08, 0x09: Short/long term fuel trim (%). (A - 128) * 100 / 128."""
    if len(b) < 1:
        return None
    return round((b[0] - 128) * 100.0 / 128.0, 2)


def _decode_control_module_voltage(b: bytes) -> Optional[float]:
    """PID 0x42: Control module voltage (V). (256*A + B) / 1000."""
    if len(b) < 2:
        return None
    return round((256 * b[0] + b[1]) / 1000.0, 3)


def _decode_fuel_rate(b: bytes) -> Optional[float]:
    """PID 0x5E: Engine fuel rate (L/h). (256*A + B) / 20."""
    if len(b) < 2:
        return None
    return round((256 * b[0] + b[1]) / 20.0, 2)


# --- The full table of generic Mode-01 PIDs we surface ---
# Order matters — it's the polling order on the coordinator.
PID_TABLE: list[ObdPid] = [
    ObdPid(0x04, "engine_load", "Engine load", "%", "power_factor", 1, _decode_engine_load),
    ObdPid(0x05, "coolant_temp", "Coolant temperature", "°C", "temperature", 1, _decode_coolant_temp),
    ObdPid(0x06, "stft_bank1", "Short-term fuel trim (Bank 1)", "%", "", 1, _decode_fuel_trim_pct),
    ObdPid(0x07, "ltft_bank1", "Long-term fuel trim (Bank 1)", "%", "", 1, _decode_fuel_trim_pct),
    ObdPid(0x0C, "rpm", "Engine RPM", "rpm", "", 2, _decode_rpm),
    ObdPid(0x0D, "speed", "Vehicle speed", "km/h", "speed", 1, _decode_speed),
    ObdPid(0x0E, "timing_advance", "Timing advance", "°", "", 1, _decode_timing_advance),
    ObdPid(0x0F, "intake_air_temp", "Intake air temperature", "°C", "temperature", 1, _decode_intake_air_temp),
    ObdPid(0x10, "maf", "Mass air flow", "g/s", "", 2, _decode_maf),
    ObdPid(0x11, "throttle_pct", "Throttle position", "%", "", 1, _decode_throttle_pct),
    ObdPid(0x1F, "run_time", "Engine run time", "s", "duration", 2, _decode_run_time),
    ObdPid(0x22, "fuel_rail_pressure", "Fuel rail pressure", "kPa", "pressure", 2, _decode_fuel_rail_pressure),
    ObdPid(0x2F, "fuel_level_pct", "Fuel level", "%", "battery", 1, _decode_fuel_level_pct),
    ObdPid(0x31, "distance_since_dtc_clear", "Distance since DTC cleared", "km", "distance", 2, _decode_distance_since_dtc_clear),
    ObdPid(0x42, "control_module_voltage", "Control module voltage", "V", "voltage", 2, _decode_control_module_voltage),
    ObdPid(0x46, "ambient_air_temp", "Ambient air temperature", "°C", "temperature", 1, _decode_ambient_air_temp),
    ObdPid(0x5E, "fuel_rate", "Engine fuel rate", "L/h", "", 2, _decode_fuel_rate),
]


# Lookup table by hex PID
PID_BY_ID: dict[int, ObdPid] = {p.pid: p for p in PID_TABLE}

# Lookup by name (e.g. for unit tests + dashboard yaml)
PID_BY_NAME: dict[str, ObdPid] = {p.name: p for p in PID_TABLE}


def decode_bytes(pid: int, raw: bytes) -> Optional[float]:
    """Decode raw OBD2 data bytes for a given PID. Returns None on bad input."""
    entry = PID_BY_ID.get(pid)
    if entry is None:
        return None
    return entry.decoder(raw)


def decode_value(pid: int, value) -> Optional[float]:
    """Decode a value from the WiCAN Pro REST JSON dict (`{PID: value}`).

    The WiCAN sometimes returns the raw bytes, sometimes the pre-decoded
    scalar. We try to handle both cases.
    """
    entry = PID_BY_ID.get(pid)
    if entry is None:
        return None

    if isinstance(value, (int, float)):
        # REST endpoint returns pre-decoded scalars for some PIDs.
        # Caller has to know — we accept either format.
        return float(value)

    if isinstance(value, (bytes, bytearray, list, tuple)):
        return decode_bytes(pid, bytes(value))

    if isinstance(value, str):
        # Try hex-string ("0C A2 50" etc.)
        try:
            parts = [int(x, 16) for x in value.split()]
            return decode_bytes(pid, bytes(parts))
        except ValueError:
            return None

    return None


def contract_entity_id(pid: int) -> Optional[str]:
    """Return the canonical `rc_obd_<name>` contract entity_id for a PID."""
    entry = PID_BY_ID.get(pid)
    if entry is None:
        return None
    return f"sensor.rc_obd_{entry.name}"


def all_contract_entity_ids() -> list[str]:
    """All contract entity IDs in canonical order (matches PID_TABLE order)."""
    return [contract_entity_id(p.pid) for p in PID_TABLE]
