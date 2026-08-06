"""Pure-Python loader + validator for the RoamCore canonical vehicle model.

Phase 2 (Wave 9 #119) — the canonical vehicle model schema is the
foundational value of RoamCore: every connected device maps to a
canonical slot regardless of brand. The schema is data
(`connections/_schema/canonical_capabilities.json`), and this module
is the validator that enforces the schema rules.

Design goals:
  - Pure stdlib + json (no Home Assistant imports — keep this testable
    outside an HA install).
  - Returns a list of plain-English error strings (empty list = valid).
  - Naming rules follow `docs/reference/rc-entity-naming.md`:
      * `<domain>.rc_<subsystem>_<object>_<metric>`
      * the `rc_` prefix is mandatory
      * no vendor names (victron, unifi, starlink, vt_, …) in any
        contract id
  - Functions: load_capabilities, validate_capabilities,
    get_capabilities_by_category, find_capability.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

# --- Public constants (exported so callers + tests don't hardcode) ---

# The canonical 6 capability categories. Other subsystems exist in the
# broader RoamCore entity-naming doc (ventilation, vehicle, mode, etc.)
# but Phase 2 ships the 6 that every van has, in plain English, with
# no jargon. Categories are added in subsequent slices.
DEFAULT_CAPABILITY_CATEGORIES: tuple[str, ...] = (
    "power",
    "lighting",
    "climate",
    "water",
    "position",
    "network",
)

# Home Assistant domains that a capability may declare.
VALID_DOMAINS: tuple[str, ...] = (
    "sensor",
    "binary_sensor",
    "switch",
    "select",
    "number",
    "button",
    "text",
    "device_tracker",
)

# Telemetry kinds read state; controls mutate state. Both are first-class
# in the canonical model — see `docs/reference/rc-vehicle-model.md`.
VALID_KINDS: tuple[str, ...] = ("telemetry", "control")

# Vendor names that must NEVER appear in an `rc_*` capability id.
# `docs/reference/rc-entity-naming.md` Hard Rule #2.
# Listed lowercase so the check is case-insensitive.
FORBIDDEN_VENDOR_TOKENS: tuple[str, ...] = (
    "victron",
    "vt_",
    "unifi",
    "ubnt",
    "starlink",
    "peplink",
    "teltonika",
    "frigate",
    "mqtt",
    "esphome",
    "homeassistant",
    "hass",
)

# The naming pattern for capability ids in the canonical model.
# `<domain>.rc_<subsystem>_<object>_<metric>` per
# `docs/reference/rc-entity-naming.md`. The `<domain>.` prefix is
# omitted inside the JSON `id` field (it lives on the `type` field).
# The canonical example in the doc includes `sensor.rc_location_lat`
# (subsystem + metric only, 2 tokens after rc_), so we require at
# least 2 tokens after the prefix — that is `rc_<subsystem>_<thing>`.
# Three tokens (`rc_<subsystem>_<object>_<metric>`) is the common case.
_ID_PATTERN = re.compile(r"^rc_[a-z][a-z0-9]*(_[a-z][a-z0-9]*){1,}$")


# --- Public API ---


def load_capabilities(path: str | os.PathLike[str]) -> dict[str, Any]:
    """Read + JSON-parse the canonical capabilities file.

    Returns the full document (so callers can read the title /
    description / category list as well as the per-capability entries).

    Raises:
        FileNotFoundError: when `path` does not exist.
        json.JSONDecodeError: when the file is not valid JSON.
    """
    with open(path, "r", encoding="utf-8") as fp:
        return json.load(fp)


def validate_capabilities(caps: dict[str, Any]) -> list[str]:
    """Return a list of plain-English validation errors.

    An empty list means the document is valid. The function is
    deliberately total (never raises) so callers can aggregate errors
    across many documents without try/except noise.
    """
    errors: list[str] = []

    # --- Top-level shape ---
    if not isinstance(caps, dict):
        return ["top-level document must be a JSON object"]

    declared_categories = caps.get("capability_categories")
    capabilities = caps.get("capabilities")
    title = caps.get("title")

    if title is not None and not isinstance(title, str):
        errors.append("'title' must be a string when present")

    if not isinstance(declared_categories, list) or not declared_categories:
        errors.append(
            "'capability_categories' must be a non-empty list of strings"
        )
        declared_categories = []  # continue validating per-capability
    elif not all(isinstance(c, str) and c for c in declared_categories):
        errors.append(
            "'capability_categories' must contain only non-empty strings"
        )
        declared_categories = [c for c in declared_categories if isinstance(c, str)]

    if not isinstance(capabilities, list) or not capabilities:
        errors.append("'capabilities' must be a non-empty list")
        return errors

    if len(capabilities) < 12:
        errors.append(
            "schema must declare at least 12 capabilities (one per the 6 "
            f"minimum categories); found {len(capabilities)}"
        )

    # --- Per-capability checks ---
    seen_ids: set[str] = set()
    seen_categories: set[str] = set()
    for idx, cap in enumerate(capabilities):
        prefix = f"capabilities[{idx}]"

        if not isinstance(cap, dict):
            errors.append(f"{prefix}: must be a JSON object")
            continue

        cap_id = cap.get("id")
        category = cap.get("category")
        kind = cap.get("kind")
        cap_type = cap.get("type")
        description = cap.get("description")

        # id (must be rc_ prefixed and follow naming pattern)
        if not isinstance(cap_id, str) or not cap_id:
            errors.append(f"{prefix}.id: missing or empty")
        elif not cap_id.startswith("rc_"):
            errors.append(
                f"{prefix}.id ({cap_id!r}): must start with the rc_ prefix "
                "(RoamCore contract layer)"
            )
        elif not _ID_PATTERN.match(cap_id):
            errors.append(
                f"{prefix}.id ({cap_id!r}): must follow the rc-naming "
                "pattern rc_<subsystem>_<object>_<metric> (lowercase, "
                "underscore-separated, at least 2 tokens after rc_)"
            )
        else:
            # Vendor-name ban (case-insensitive substring check).
            lower_id = cap_id.lower()
            for vendor in FORBIDDEN_VENDOR_TOKENS:
                if vendor in lower_id:
                    errors.append(
                        f"{prefix}.id ({cap_id!r}): contains forbidden "
                        f"vendor token {vendor!r} (contract ids must be "
                        "vendor-neutral)"
                    )
                    break

            # Duplicate detection.
            if cap_id in seen_ids:
                errors.append(
                    f"{prefix}.id ({cap_id!r}): duplicate capability id "
                    "(every id must be unique)"
                )
            else:
                seen_ids.add(cap_id)

        # category
        if not isinstance(category, str) or not category:
            errors.append(f"{prefix}.category: missing or empty")
        elif category not in declared_categories:
            errors.append(
                f"{prefix}.category ({category!r}): not in the declared "
                f"capability_categories list {list(declared_categories)}"
            )
        else:
            seen_categories.add(category)

        # kind
        if kind not in VALID_KINDS:
            errors.append(
                f"{prefix}.kind ({kind!r}): must be one of {list(VALID_KINDS)}"
            )

        # type (HA domain)
        if cap_type not in VALID_DOMAINS:
            errors.append(
                f"{prefix}.type ({cap_type!r}): must be a Home Assistant "
                f"domain from {list(VALID_DOMAINS)}"
            )

        # description
        if not isinstance(description, str) or not description.strip():
            errors.append(
                f"{prefix}.description: must be a non-empty string"
            )

        # example_sources (optional but, when present, must be a list of strings)
        example_sources = cap.get("example_sources")
        if example_sources is not None:
            if not isinstance(example_sources, list):
                errors.append(
                    f"{prefix}.example_sources: must be a list when present"
                )
            elif not all(isinstance(s, str) and s for s in example_sources):
                errors.append(
                    f"{prefix}.example_sources: must contain only "
                    "non-empty strings"
                )

    return errors


def get_capabilities_by_category(
    caps: dict[str, Any], category: str
) -> list[dict[str, Any]]:
    """Return the subset of capabilities whose `category` matches.

    Unknown categories yield an empty list (never raises). Order is
    the document order from the JSON.
    """
    capabilities = caps.get("capabilities") or []
    return [c for c in capabilities if isinstance(c, dict) and c.get("category") == category]


def find_capability(caps: dict[str, Any], capability_id: str) -> dict[str, Any] | None:
    """Look up a single capability by id. Returns None when not found."""
    capabilities = caps.get("capabilities") or []
    for c in capabilities:
        if isinstance(c, dict) and c.get("id") == capability_id:
            return c
    return None
