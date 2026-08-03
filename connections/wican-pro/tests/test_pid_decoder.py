"""Unit tests for the OBD2 PID decoder.

These tests are derived directly from SAE J1979 (rev 2017) §6.3
(Standard PIDs) and the canonical Mode-01 PID table. Each test case
includes both the hex response and the expected decoded value, so a
bug in the decoder fails fast.

Reference test vectors are taken from:
  - https://en.wikipedia.org/wiki/OBD-II_PIDs#Standard_PIDs_(Mode_01)
  - SAE J1979 (rev 2017), Appendix B (test cases)
"""

from __future__ import annotations

import pytest

import sys
import pathlib

# Make the custom_components dir importable
_COMP = pathlib.Path(__file__).resolve().parents[3] / "homeassistant" / "custom_components" / "roamcore_wican"
sys.path.insert(0, str(_COMP))

from pids import (  # noqa: E402
    PID_TABLE,
    PID_BY_ID,
    PID_BY_NAME,
    contract_entity_id,
    decode_bytes,
    decode_value,
    all_contract_entity_ids,
)


# --- Engine RPM (PID 0x0C) — (256*A + B) / 4 ---

def test_rpm_idle():
    # Typical idle: 0x0C 0A 28 -> (10*256 + 40)/4 = 650 RPM
    assert decode_bytes(0x0C, bytes([0x0A, 0x28])) == 650.0


def test_rpm_cruise():
    # Highway cruise: 0x0C 12 34 -> (18*256 + 52)/4 = 1165 RPM
    assert decode_bytes(0x0C, bytes([0x12, 0x34])) == 1165.0


def test_rpm_zero():
    # Engine off: 0x0C 00 00 -> 0
    assert decode_bytes(0x0C, bytes([0x00, 0x00])) == 0.0


def test_rpm_too_short():
    # Defensive: missing bytes -> None
    assert decode_bytes(0x0C, bytes([0x0A])) is None


def test_rpm_empty():
    assert decode_bytes(0x0C, b"") is None


# --- Vehicle speed (PID 0x0D) ---

def test_speed_zero():
    # Stopped: 0x0D 00
    assert decode_bytes(0x0D, bytes([0x00])) == 0.0


def test_speed_highway():
    # 120 km/h: 0x0D 78 -> 120
    assert decode_bytes(0x0D, bytes([0x78])) == 120.0


def test_speed_max():
    # 255 km/h: 0x0D FF
    assert decode_bytes(0x0D, bytes([0xFF])) == 255.0


# --- Coolant temp (PID 0x05) — A - 40 ---

def test_coolant_cold():
    # Cold start (0°C): 0x05 28 -> 40 - 40 = 0
    assert decode_bytes(0x05, bytes([0x28])) == 0.0


def test_coolant_warm():
    # Operating temp (~82°C): 0x05 7A -> 122 - 40 = 82
    assert decode_bytes(0x05, bytes([0x7A])) == 82.0


def test_coolant_hot():
    # Overheat warning (112°C): 0x05 98 -> 152 - 40 = 112
    assert decode_bytes(0x05, bytes([0x98])) == 112.0


def test_coolant_negative():
    # Below freezing: 0x05 00 -> -40°C (sensor minimum)
    assert decode_bytes(0x05, bytes([0x00])) == -40.0


# --- Throttle position (PID 0x11) — A * 100 / 255 ---

def test_throttle_closed():
    # Idle (closed): 0x11 00 -> 0%
    assert decode_bytes(0x11, bytes([0x00])) == 0.0


def test_throttle_half():
    # Half throttle: 0x11 80 -> 128 * 100 / 255 = 50.196... -> 50.2
    assert decode_bytes(0x11, bytes([0x80])) == round(128 * 100 / 255, 2)


def test_throttle_full():
    # Full throttle: 0x11 FF -> 100%
    assert decode_bytes(0x11, bytes([0xFF])) == 100.0


# --- MAF (PID 0x10) — (256*A + B) / 100 ---

def test_maf_idle():
    # Idle (3.20 g/s): 0x10 01 40
    assert decode_bytes(0x10, bytes([0x01, 0x40])) == 3.2


def test_maf_zero():
    # 0 g/s: 0x10 00 00
    assert decode_bytes(0x10, bytes([0x00, 0x00])) == 0.0


# --- Fuel level (PID 0x2F) — A * 100 / 255 ---

def test_fuel_empty():
    # Empty: 0x2F 00 -> 0%
    assert decode_bytes(0x2F, bytes([0x00])) == 0.0


def test_fuel_half():
    # Half: 0x2F 80 -> 128 * 100 / 255 = 50.196 -> 50.2
    assert decode_bytes(0x2F, bytes([0x80])) == round(128 * 100 / 255, 2)


def test_fuel_full():
    # Full: 0x2F FF -> 100%
    assert decode_bytes(0x2F, bytes([0xFF])) == 100.0


# --- Control module voltage (PID 0x42) — (256*A + B) / 1000 ---

def test_voltage_12v():
    # 12.000V: 0x42 30 C0 -> (256*48 + 192)/1000 = 12480/1000 = 12.48
    assert decode_bytes(0x42, bytes([0x30, 0xC0])) == 12.48


def test_voltage_14v_charging():
    # 14.000V (alternator charging): 0x42 36 B0 -> (256*54 + 176)/1000 = 14000/1000 = 14.0
    assert decode_bytes(0x42, bytes([0x36, 0xB0])) == 14.0


# --- Engine load (PID 0x04) — A * 100 / 255 ---

def test_engine_load_idle():
    # Idle (10%): 0x04 1A -> 26 * 100 / 255 = 10.2
    assert decode_bytes(0x04, bytes([0x1A])) == round(0x1A * 100 / 255, 2)


def test_engine_load_full():
    # Full load: 0x04 FF -> 100%
    assert decode_bytes(0x04, bytes([0xFF])) == 100.0


# --- Timing advance (PID 0x0E) — (A - 128) / 2 ---

def test_timing_zero():
    # 0 degrees: 0x0E 80
    assert decode_bytes(0x0E, bytes([0x80])) == 0.0


def test_timing_advanced():
    # 15 degrees BTDC: 0x0E 9E -> (158-128)/2 = 15.0
    assert decode_bytes(0x0E, bytes([0x9E])) == 15.0


def test_timing_retarded():
    # -5 degrees: 0x0E 7A -> (122-128)/2 = -3.0
    assert decode_bytes(0x0E, bytes([0x7A])) == -3.0


# --- Fuel rate (PID 0x5E) — (256*A + B) / 20 ---

def test_fuel_rate_idle():
    # 0.50 L/h idle: 0x5E 00 0A -> 10/20 = 0.5
    assert decode_bytes(0x5E, bytes([0x00, 0x0A])) == 0.5


def test_fuel_rate_high():
    # 10 L/h: 0x5E 00 C8 -> 200/20 = 10.0
    assert decode_bytes(0x5E, bytes([0x00, 0xC8])) == 10.0


# --- Short/long term fuel trim (PID 0x06, 0x07) — (A - 128) * 100 / 128 ---

def test_stft_zero():
    # 0% trim: 0x06 80
    assert decode_bytes(0x06, bytes([0x80])) == 0.0


def test_stft_lean():
    # +5% trim (ECU adding fuel): 0x06 8A -> (138-128)*100/128 = 7.8125
    assert decode_bytes(0x06, bytes([0x8A])) == 7.81


def test_stft_rich():
    # -5% trim (ECU pulling fuel): 0x06 76 -> (118-128)*100/128 = -7.8125
    assert decode_bytes(0x06, bytes([0x76])) == -7.81


# --- Engine run time (PID 0x1F) — 256*A + B ---

def test_run_time_zero():
    # 0s: 0x1F 00 00
    assert decode_bytes(0x1F, bytes([0x00, 0x00])) == 0.0


def test_run_time_hour():
    # 1 hour (3600s): 0x1F 0E 10 -> (256*14 + 16) = 3600
    assert decode_bytes(0x1F, bytes([0x0E, 0x10])) == 3600.0


# --- Distance since DTC clear (PID 0x31) ---

def test_distance_zero():
    # 0 km: 0x31 00 00
    assert decode_bytes(0x31, bytes([0x00, 0x00])) == 0.0


def test_distance_long():
    # 500 km since clear: 0x31 01 F4
    assert decode_bytes(0x31, bytes([0x01, 0xF4])) == 500.0


# --- decode_value (REST-JSON format from WiCAN) ---

def test_decode_value_int():
    # WiCAN REST: {"12": 840}
    assert decode_value(0x0C, 650) == 650.0


def test_decode_value_float():
    # WiCAN REST: {"42": 12.4}
    assert decode_value(0x42, 12.4) == 12.4


def test_decode_value_hex_string():
    # Some firmware versions return "0C 0A 28" as a string
    assert decode_value(0x0C, "0A 28") == 650.0


def test_decode_value_list():
    # Some firmware versions return [10, 40] as a list
    assert decode_value(0x0C, [0x0A, 0x28]) == 650.0


def test_decode_value_unknown_pid():
    # PID not in our table — return None rather than crash
    assert decode_value(0xFF, 100) is None


def test_decode_value_garbage():
    # Defensive: unparseable string -> None
    assert decode_value(0x0C, "not a number") is None


# --- Lookup tables ---

def test_pid_table_covers_canonical_set():
    """The 17 generic Mode-01 PIDs we surface are present."""
    expected = {
        0x04, 0x05, 0x06, 0x07, 0x0C, 0x0D, 0x0E, 0x0F, 0x10, 0x11,
        0x1F, 0x22, 0x2F, 0x31, 0x42, 0x46, 0x5E,
    }
    assert {p.pid for p in PID_TABLE} == expected


def test_pid_by_id_lookup():
    assert PID_BY_ID[0x0C].name == "rpm"
    assert PID_BY_ID[0x05].name == "coolant_temp"


def test_pid_by_name_lookup():
    assert PID_BY_NAME["rpm"].pid == 0x0C
    assert PID_BY_NAME["coolant_temp"].pid == 0x05


def test_no_duplicate_pids():
    pids = [p.pid for p in PID_TABLE]
    assert len(pids) == len(set(pids))


def test_no_duplicate_names():
    names = [p.name for p in PID_TABLE]
    assert len(names) == len(set(names))


def test_no_vendor_names_in_metric_names():
    """The naming rule says no vendor names in rc_obd_* ids."""
    forbidden = {"wican", "custic", "elm327", "obdlink", "viecar", "vesc"}
    for p in PID_TABLE:
        for word in forbidden:
            assert word not in p.name.lower(), f"PID {p.pid:02X} name {p.name!r} contains vendor {word!r}"


# --- Contract entity ids ---

def test_contract_entity_id_rpm():
    assert contract_entity_id(0x0C) == "sensor.rc_obd_rpm"


def test_contract_entity_id_unknown():
    assert contract_entity_id(0xFF) is None


def test_all_contract_entity_ids_use_rc_obd_prefix():
    for eid in all_contract_entity_ids():
        assert eid is not None
        assert eid.startswith("sensor.rc_obd_"), f"entity_id {eid!r} doesn't start with sensor.rc_obd_"


def test_all_contract_entity_ids_no_vendors():
    forbidden = {"wican", "custic", "elm327"}
    for eid in all_contract_entity_ids():
        for word in forbidden:
            assert word not in eid.lower(), f"entity_id {eid!r} contains vendor {word!r}"


def test_all_contract_entity_ids_unique():
    eids = all_contract_entity_ids()
    assert len(eids) == len(set(eids))


# --- Boundary cases / edge inputs ---

@pytest.mark.parametrize("bad_input", [None, -1, 99999, 256, -100])
def test_decode_bytes_out_of_range_pid(bad_input):
    # PIDs > 0xFF or < 0 shouldn't crash; they should just return None.
    # (Caller is responsible for passing a sane PID; we just don't crash.)
    assert decode_bytes(bad_input, bytes([0x00])) is None


def test_decode_bytes_too_many_bytes():
    # Extra trailing bytes are ignored (some firmware versions pad to 4 bytes).
    assert decode_bytes(0x0C, bytes([0x0A, 0x28, 0xFF, 0xFF])) == 650.0
