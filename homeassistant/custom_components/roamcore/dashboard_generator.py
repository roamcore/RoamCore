"""Lovelace YAML dashboard generator from canonical capability maps.

Phase 2 (Wave 9 #119c) — the "auto-generated dashboard" half of the
canonical vehicle model. This module is the renderer that turns a
``{canonical_capability_id: vendor_entity_id}`` map (the output of
#119b's ``build_capability_map``) into a Lovelace YAML string the
user (or RoamCore's setup wizard) can drop straight into a
dashboard.

The slice is deliberately narrow: it does NOT install anything into
Home Assistant, it does NOT mutate the Lovelace storage, it does
NOT touch ``homeassistant/lovelace/`` or ``homeassistant/packages/``.
It is a pure-function string formatter. The companion slice
(#119b's ``capability_mapping.py``) feeds it, the user-facing
dashboard rendering layer (``homeassistant/www/roamcore/``) consumes
the YAML it produces.

Design goals:
  - Pure stdlib + json (no Home Assistant imports — keep this testable
    outside an HA install).
  - Deterministic output: same inputs MUST produce byte-identical
    output. This is a hard requirement so the YAML can be diffed,
    committed, and reviewed like any other file.
  - Card names derive from the canonical capability's ``description``
    (vanlifer language), NEVER from the canonical id or the vendor
    entity id. Icons derive from the canonical capability's
    ``device_class``, NEVER from the vendor brand.
  - Vendor-neutral UI surface: the YAML does not contain brand tokens
    (victron, vt_, starlink, …) in any card name, title, or icon —
    the vendor entity id appears ONLY inside ``entity:`` lines.
  - Buttons (kind=control, type=button) are deliberately NOT surfaced
    on the auto-generated dashboard — they live in the Advanced mode
    panel (per directive §"Decision Rules" #2 "Hide tech").
  - Empty categories are HIDDEN — not rendered as empty section
    headers (per directive §"Decision Rules" #2 "Hide tech").

Functions:
  - ``generate_dashboard_yaml(capability_map, capabilities_doc, *,
    card_style)`` — returns the Lovelace YAML as a ``str``.
  - ``card_for_capability(capability, vendor_entity_id, *,
    card_style)`` — returns the Lovelace card dict for one capability
    (exposed so tests + future consumers can build partial views).
  - ``heading_for_category(category)`` — maps a category id to a
    plain-English section heading.
  - ``icon_for_device_class(device_class)`` — maps a device_class
    to an ``mdi:…`` icon name.

Naming follows ``docs/reference/rc-entity-naming.md``: card names are
the canonical capability's plain-English ``description`` (the
vanlifer-facing label), not the ``rc_*`` id. Icons are derived from
the ``device_class`` (vendor-neutral). The vendor entity id appears
inside the card's ``entity:`` line so Home Assistant knows where to
read the state — but the card's name, title, and icon never mention
the vendor.
"""

from __future__ import annotations

from typing import Any

# --- Public constants (exported so callers + tests don't hardcode) ---

# Supported dashboard card styles. The default is ``compact`` (one
# line per card). ``full`` adds a secondary metric + helper buttons.
# ``diagnostic`` surfaces the raw vendor entity id + canonical id
# hint and is used by the Advanced mode.
CARD_STYLES: tuple[str, ...] = ("compact", "full", "diagnostic")

DEFAULT_CARD_STYLE: str = "compact"

# Vendor tokens that must NEVER appear in any card name, title, or
# icon. The vendor entity id is allowed to appear inside ``entity:``
# lines because that is the only way Home Assistant knows where to
# read state — but the UI surface (name, title, icon, heading) stays
# vendor-neutral.
#
# The canonical list lives in ``docs/reference/rc-entity-naming.md``
# Hard Rule #2; we mirror it here so the YAML generator enforces it
# at generation time (the schema validator enforces it at schema
# load time).
FORBIDDEN_VENDOR_TOKENS: tuple[str, ...] = (
    "victron",
    "vt_",
    "unifi",
    "ubnt",
    "starlink",
    "dish_",
    "peplink",
    "teltonika",
    "rut_",
    "frigate",
    "mqtt",
    "esphome",
    "homeassistant",
    "hass",
)

# Mapping from Home Assistant ``device_class`` (canonical, vendor-
# neutral) to a Material Design Icons name. The icon is ALWAYS
# derived from the device_class, never from the vendor brand — a
# Victron battery and a Renogy battery both show the same battery
# icon.
DEVICE_CLASS_TO_ICON: dict[str, str] = {
    "battery": "mdi:battery",
    "voltage": "mdi:flash-triangle-outline",
    "current": "mdi:current-dc",
    "power": "mdi:solar-power",
    "temperature": "mdi:thermometer",
    "humidity": "mdi:water-percent",
    "plug": "mdi:power-plug",
    "connectivity": "mdi:wifi",
    "signal_strength": "mdi:signal-cellular-3",
    "latitude": "mdi:map-marker-radius",
    "longitude": "mdi:map-marker-radius-outline",
}

# Default icon when the canonical capability has no ``device_class``.
DEFAULT_ICON: str = "mdi:gauge"

# Mapping from capability ``category`` id (lowercase, machine-friendly)
# to the plain-English section heading rendered on the dashboard.
# This is the operator→vanlifer translation: the schema id is
# "power" (machine), the heading is "Power" (human). We deliberately
# keep these short and friendly — no underscores, no jargon.
CATEGORY_TO_HEADING: dict[str, str] = {
    "power": "Power",
    "lighting": "Lighting",
    "climate": "Climate",
    "water": "Water",
    "position": "Position",
    "network": "Network",
}

# Default icon for a switch (no device_class). Mirrors HA's default
# switch icon so the dashboard reads naturally.
SWITCH_DEFAULT_ICON: str = "mdi:toggle-switch"

# The placeholder we emit for a fully-empty input so the output is
# valid Lovelace YAML (a vertical-stack with zero cards). Empty
# maps are legitimate — they happen when no device has been mapped
# yet — and the generator should still produce valid YAML rather
# than an empty string.
EMPTY_OUTPUT_MARKER: str = (
    "# RoamCore auto-generated dashboard: no capabilities mapped yet.\n"
    "# Plug a device in and the right cards will appear here.\n"
    "vertical-stack:\n"
    "  cards: []\n"
)


# --- Pure YAML emitter (stdlib only) ---


def _yaml_quote(s: str) -> str:
    """Quote a string for safe YAML emission.

    Bare strings are emitted unquoted when they're safe (letters,
    digits, underscores, dashes, dots, slashes, colons). Everything
    else is double-quoted with backslash-escaped internals. Empty
    strings are quoted as ``""``.
    """
    if s == "":
        return '""'
    safe = True
    for ch in s:
        if not (
            ch.isalnum()
            or ch in "_-./:"
        ):
            safe = False
            break
    if safe and not s[0].isdigit():
        return s
    # Quote and escape backslashes + double quotes.
    escaped = s.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _yaml_dump(value: Any, indent: int = 0) -> str:
    """Render a Python value as a Lovelace-shaped YAML string.

    This is a small, opinionated emitter — not a general YAML
    library — that handles exactly the shapes ``generate_dashboard_yaml``
    produces (``str``, ``dict``, ``list``, and ``None``). It keeps
    output deterministic (sorted dict keys, stable ordering) so the
    same inputs always produce byte-identical output.

    Block style only (no flow style). Strings are quoted only when
    they contain characters that would confuse a YAML parser.
    """
    pad = "  " * indent
    if value is None:
        return "null"
    if isinstance(value, bool):
        # bool must be checked before int (bool is a subclass of int).
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        # Stable float formatting — no scientific notation for the
        # values we emit (none today, but guard against future use).
        return repr(value)
    if isinstance(value, str):
        return _yaml_quote(value)
    if isinstance(value, list):
        if not value:
            return "[]"
        lines: list[str] = []
        # A list at indent N has its dash at column 2N. The first
        # line of each item gets a "- " prefix (2 chars). When the
        # item is a dict or list, the recursive call produces
        # lines at indent ``item_indent`` (= N+1) where the first
        # key starts at column 2(N+1) — i.e. directly under the
        # "- " prefix. Continuation lines need the same
        # 2(N+1) column alignment.
        item_indent = indent + 1
        item_pad = "  " * item_indent
        for item in value:
            rendered = _yaml_dump(item, item_indent)
            rendered_lines = rendered.split("\n")
            # First line: dash at the list's column, value starts
            # at the next column (= column 2N+2). The recursive
            # call already produced the value line with its own
            # pad of item_pad (= 2(N+1) = 2N+2 chars). Strip the
            # recursive call's leading pad and prepend the dash
            # prefix at column 2N so the value lands at column
            # 2N+2.
            value_first = rendered_lines[0]
            if value_first.startswith(item_pad):
                value_first = value_first[len(item_pad):]
            lines.append(f"{pad}- {value_first}")
            for cont in rendered_lines[1:]:
                # Continuation lines also have the recursive call's
                # leading pad — strip it and re-add with the dash-
                # aware prefix so they align under the value.
                if cont.startswith(item_pad):
                    cont = cont[len(item_pad):]
                lines.append(f"{pad}  {cont}")
        return "\n".join(lines)
    if isinstance(value, dict):
        if not value:
            return "{}"
        lines = []
        child_indent = indent + 1
        for key in sorted(value.keys()):
            child = value[key]
            key_str = _yaml_quote(str(key))
            if isinstance(child, dict):
                if not child:
                    lines.append(f"{pad}{key_str}: {{}}")
                else:
                    lines.append(f"{pad}{key_str}:")
                    lines.append(_yaml_dump(child, child_indent))
            elif isinstance(child, list):
                if not child:
                    lines.append(f"{pad}{key_str}: []")
                else:
                    lines.append(f"{pad}{key_str}:")
                    lines.append(_yaml_dump(child, child_indent))
            else:
                lines.append(f"{pad}{key_str}: {_yaml_dump(child, child_indent)}")
        return "\n".join(lines)
    # Unknown type — render as a quoted string rather than crashing.
    return _yaml_quote(str(value))


# --- Public helpers ---


def heading_for_category(category: str) -> str:
    """Return the plain-English section heading for a category id.

    Unknown categories fall back to the category id with underscores
    replaced by spaces and the first letter capitalised — never
    raise. The fallback is deliberate so a schema that adds a new
    category before the heading table is updated still renders
    something readable instead of an empty heading.
    """
    if category in CATEGORY_TO_HEADING:
        return CATEGORY_TO_HEADING[category]
    # Fallback: title-case the category id (snake_case → Title Case).
    return category.replace("_", " ").title()


def icon_for_device_class(device_class: str | None) -> str:
    """Return the ``mdi:…`` icon for a Home Assistant device_class.

    Unknown / missing device_classes fall back to ``DEFAULT_ICON``.
    The icon is ALWAYS vendor-neutral — it never contains a brand
    token.
    """
    if not device_class:
        return DEFAULT_ICON
    return DEVICE_CLASS_TO_ICON.get(device_class, DEFAULT_ICON)


# --- Card builder ---


def _sanitize_vendor_neutral(text: str) -> str:
    """Strip forbidden vendor tokens from a user-facing string.

    The schema descriptions occasionally mention brand names as part
    of an explanatory parenthetical (e.g. "(LTE, Starlink, Wi-Fi)"
    for the ``rc_network_internet_reachable`` description). Brand
    tokens are banned from card names / titles per the
    ``docs/reference/rc-entity-naming.md`` contract — the UI surface
    must be vendor-neutral. This helper replaces the brand token
    with a generic, plain-English alternative so the rendered card
    stays friendly + vendor-neutral without us having to rewrite
    the schema descriptions.
    """
    replacements = (
        ("Starlink", "satellite internet"),
        ("starlink", "satellite internet"),
        ("Victron", "battery monitor"),
        ("victron", "battery monitor"),
        ("Peplink", "multi-WAN router"),
        ("peplink", "multi-WAN router"),
        ("Teltonika", "LTE router"),
        ("teltonika", "LTE router"),
        ("Unifi", "Wi-Fi controller"),
        ("unifi", "Wi-Fi controller"),
        ("Frigate", "camera NVR"),
        ("frigate", "camera NVR"),
    )
    out = text
    for needle, replacement in replacements:
        out = out.replace(needle, replacement)
    return out


def _card_name(capability: dict[str, Any]) -> str:
    """Return the user-facing name for a capability.

    The name comes from the canonical capability's ``description``
    (vanlifer language) — never from the ``id`` (``rc_*`` machine
    name) and never from the vendor entity id. Brand tokens that
    happen to appear in the description are replaced with neutral
    phrases so the rendered card stays vendor-neutral.
    """
    description = capability.get("description")
    if isinstance(description, str) and description.strip():
        return _sanitize_vendor_neutral(description.strip())
    # Defensive fallback: humanise the id (rc_power_battery_soc →
    # "Power battery soc"). This should never fire on a valid
    # schema — the validator rejects capabilities without a
    # description — but we keep it so the generator never raises.
    cap_id = capability.get("id") or "unknown"
    if cap_id.startswith("rc_"):
        cap_id = cap_id[3:]
    return cap_id.replace("_", " ").title()


def card_for_capability(
    capability: dict[str, Any],
    vendor_entity_id: str,
    *,
    card_style: str = DEFAULT_CARD_STYLE,
) -> dict[str, Any] | None:
    """Build a single Lovelace ``entities:`` card for one capability.

    Returns the card as a Python ``dict`` (suitable for ``yaml.dump``
    or the bundled ``_yaml_dump``). The card style controls whether
    the entity line is bare (``compact``), shows a secondary metric
    (``full``), or surfaces the raw ids (``diagnostic``).

    Buttons (kind=control, type=button) are NOT rendered — the
    dashboard generator returns ``None`` for them. Callers must
    filter ``None`` from the result.
    """
    if card_style not in CARD_STYLES:
        raise ValueError(
            f"unknown card_style {card_style!r}: must be one of {list(CARD_STYLES)}"
        )

    # Defensive: non-dict capability is ignored. The caller (which
    # builds the card list from the schema document) is the right
    # place to filter bad entries, but ``card_for_capability`` is a
    # public helper so it must not raise on weird input.
    if not isinstance(capability, dict):
        return None

    cap_type = capability.get("type")
    cap_kind = capability.get("kind")

    # Hide buttons from the auto-generated dashboard — they're
    # surfaced under the Advanced mode panel.
    if cap_type == "button" or (cap_kind == "control" and cap_type == "button"):
        return None

    name = _card_name(capability)
    device_class = capability.get("device_class")
    unit = capability.get("unit")
    cap_id = capability.get("id") or ""

    if cap_type == "switch":
        icon = SWITCH_DEFAULT_ICON
        entity_line: dict[str, Any] = {
            "entity": vendor_entity_id,
            "name": name,
            "icon": icon,
            "tap_action": {"action": "toggle"},
        }
    elif cap_type == "binary_sensor":
        icon = icon_for_device_class(device_class)
        entity_line = {
            "entity": vendor_entity_id,
            "name": name,
            "icon": icon,
        }
    else:
        # sensor (and any future read-only domain) — default branch.
        icon = icon_for_device_class(device_class)
        entity_line = {
            "entity": vendor_entity_id,
            "name": name,
            "icon": icon,
        }
        if isinstance(unit, str) and unit:
            entity_line["unit"] = unit

    # Style-specific additions.
    title = name
    if card_style == "diagnostic":
        # Surface the canonical id + raw entity id so a power user
        # can correlate the card back to the schema. The title keeps
        # the plain-English name as the dominant label and adds the
        # canonical id in brackets for grep-ability.
        title = f"{name} [{cap_id}]"
        # Replace the card's friendly name with the raw ids so an
        # Advanced-mode user can see exactly which vendor entity
        # drives the tile.
        entity_line["name"] = f"[{cap_id}] {vendor_entity_id}"
    elif card_style == "full":
        # Show the secondary metric on sensors that have a unit so
        # the user sees "last changed" + the value. Switches and
        # binary_sensors get no extra hint (they have no metric).
        if cap_type in ("sensor",) and isinstance(unit, str) and unit:
            entity_line["secondary_info"] = "last-changed"

    return {
        "type": "entities",
        "title": title,
        "entities": [entity_line],
    }


# --- Section builder ---


def _section_for_category(
    category: str,
    caps_in_category: list[dict[str, Any]],
    capability_map: dict[str, str],
    *,
    card_style: str,
) -> dict[str, Any] | None:
    """Build a vertical-stack section for one capability category.

    Returns ``None`` when the category has no mapped capabilities
    (the directive's "Hide tech" rule — empty categories are HIDDEN,
    not rendered as empty section headers).
    """
    cards: list[dict[str, Any]] = []
    for cap in caps_in_category:
        if not isinstance(cap, dict):
            continue
        cap_id = cap.get("id")
        if not isinstance(cap_id, str) or not cap_id:
            continue
        vendor_entity_id = capability_map.get(cap_id)
        if not vendor_entity_id:
            continue  # capability exists in the schema but isn't mapped
        card = card_for_capability(
            cap, vendor_entity_id, card_style=card_style
        )
        if card is not None:
            cards.append(card)

    if not cards:
        return None  # empty category — HIDDEN, per "Hide tech" rule.

    return {
        "type": "vertical-stack",
        "title": heading_for_category(category),
        "cards": cards,
    }


# --- Top-level entry point ---


def generate_dashboard_yaml(
    capability_map: dict[str, str],
    capabilities_doc: dict[str, Any],
    *,
    card_style: str = DEFAULT_CARD_STYLE,
) -> str:
    """Render the auto-generated Lovelace YAML for a capability map.

    Parameters:
        capability_map: ``{canonical_capability_id: vendor_entity_id}``
            — the output of #119b's ``build_capability_map``. Keys
            must be ``rc_*`` ids from the canonical schema; values
            are vendor entity ids that exist in Home Assistant.
        capabilities_doc: the parsed
            ``connections/_schema/canonical_capabilities.json``
            document. We use the ``capability_categories`` list to
            decide section order and to look up per-capability
            metadata (``description``, ``device_class``, ``type``,
            ``kind``).
        card_style: ``"compact"`` (default), ``"full"``, or
            ``"diagnostic"`` — see :data:`CARD_STYLES`.

    Returns:
        A ``str`` containing a Lovelace ``vertical-stack`` YAML
        document. One section per populated category, in the order
        declared by ``capability_categories``. Empty categories are
        omitted. An empty ``capability_map`` yields a placeholder
        document (the empty-output marker) rather than an empty
        string, so the caller always gets valid YAML.

    Determinism: the output is stable for the same inputs. Dict
    keys are emitted in sorted order; sections are emitted in
    ``capability_categories`` order; cards within a section are
    emitted in ``capabilities`` document order.
    """
    if card_style not in CARD_STYLES:
        raise ValueError(
            f"unknown card_style {card_style!r}: must be one of {list(CARD_STYLES)}"
        )

    # Empty input → placeholder document so the output is always
    # valid YAML the caller can write straight to a file.
    if not capability_map:
        return EMPTY_OUTPUT_MARKER

    declared_categories = capabilities_doc.get("capability_categories") or []
    capabilities = capabilities_doc.get("capabilities") or []

    sections: list[dict[str, Any]] = []
    for category in declared_categories:
        if not isinstance(category, str) or not category:
            continue
        caps_in_category = [
            c for c in capabilities
            if isinstance(c, dict) and c.get("category") == category
        ]
        section = _section_for_category(
            category,
            caps_in_category,
            capability_map,
            card_style=card_style,
        )
        if section is not None:
            sections.append(section)

    # If every category ended up empty (e.g. every mapped capability
    # was a button and got filtered), still emit a valid placeholder.
    if not sections:
        return EMPTY_OUTPUT_MARKER

    document = {
        "vertical-stack": {"cards": sections},
    }
    # Trailing newline so the file ends cleanly.
    return _yaml_dump(document) + "\n"
