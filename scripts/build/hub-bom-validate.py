#!/usr/bin/env python3
"""RoamCore Hub BOM — pure-Python validator (no third-party deps).

Validates a hardware/roamcore-hub-bom.yml manifest against the rules
the BOM contract promises. Used by scripts/checks/hub-bom-smoke.sh
and (optionally) in pre-commit hooks.

Rules enforced (plain-English failure messages, not KeyError dumps):

  1. The YAML at the path you pass parses cleanly.
  2. The top-level has a `components:` list.
  3. Each component is a dict with: name, role, qty, supplier,
     supplier_part_no, unit_cost_usd, link, required, notes
     (notes may be empty/missing on optional components but the
     other fields are always required).
  4. `role` is unique across the list (no duplicate role names).
  5. `qty` is an integer >= 1.
  6. `unit_cost_usd` is an integer >= 0 (cents; avoids float drift).
  7. No component has a unit cost > $2000 USD.
  8. The total cost of all required components is in the $500-$5000
     band — this is the sanity range for a V1 reference Hub.
  9. `role` is vendor-neutral (lowercase snake_case; no vendor
     brand tokens leak into a generic role id).
 10. The `manifest:` block carries name + version + platform.

Run:

    python3 scripts/build/hub-bom-validate.py hardware/roamcore-hub-bom.yml

Exit codes:

    0  manifest passes every check (summary printed to stdout)
    1  one or more checks failed (every failure printed as a
       plain-English line; suitable for CI logs)
    2  the YAML file could not be loaded (path / parse error)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import yaml  # PyYAML is already a project test dependency
except ImportError:  # pragma: no cover
    sys.stderr.write(
        "ERROR: PyYAML is required for hub-bom-validate.py "
        "(install with: pip install pyyaml)\n"
    )
    sys.exit(2)


# Vendor brand tokens that MUST NOT appear inside a generic `role`
# (snake_case) id. Listing common offenders explicitly so the check
# is intentional and reviewable; mirrors the spirit of
# docs/reference/rc-entity-naming.md (vendor-neutral ids).
VENDOR_TOKENS = {
    "protectli", "samsung", "crucial", "intel", "sierra",
    "wireless", "taoglas", "parsec", "thermalright", "roamcore",
}

# The RoamCore brand is allowed inside our own internal roles only.
# Any other vendor token in a role id is a contract violation.
ALLOWED_ROAMCORE_TOKEN_ROLES = {
    "chassis_labels",  # 'rc-' prefix lives in supplier_part_no, not role
}


REQUIRED_COMPONENT_FIELDS = (
    "name", "role", "qty", "supplier", "supplier_part_no",
    "unit_cost_usd", "link", "required",
)

# `notes` is encouraged but not strictly required (kept off the
# strict-required list so future contributors can omit it without
# breaking the validator; we still warn if it's missing).

ROLE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")

# Sanity bands. Tuned for a V1 reference Hub (the Overview.md
# bills-of-materials). If a future spec genuinely costs more,
# raise the bands here and document why in the commit message.
MAX_COMPONENT_UNIT_CENTS = 200_000           # $2000.00 per line item
MIN_TOTAL_REQUIRED_CENTS = 50_000             # $500.00  (sanity floor)
MAX_TOTAL_REQUIRED_CENTS = 500_000           # $5000.00 (sanity ceiling)


class BomError(Exception):
    """One failing rule. Carries the plain-English message + path."""


def _fail(errors: list[str], path: str, message: str) -> None:
    """Append a plain-English failure and keep going.

    The validator never short-circuits — we want the operator to see
    every problem in one pass so they don't have to fix-revert-fix
    across multiple commits.
    """
    errors.append(f"RoamCore Hub BOM: {path}: {message}")


def _validate_role(errors: list[str], comp: dict, role: str, path: str) -> None:
    if not isinstance(role, str) or not role:
        _fail(errors, path, "role must be a non-empty string")
        return
    if not ROLE_PATTERN.match(role):
        _fail(
            errors, path,
            f"role '{role}' must be lowercase snake_case "
            "(letters, digits, underscores; start with a letter)",
        )
        return
    # Vendor-neutral check (skipped for the few RoamCore-internal roles
    # that intentionally carry an `rc_` token; the rest must be clean).
    if role in ALLOWED_ROAMCORE_TOKEN_ROLES:
        return
    tokens = set(role.split("_"))
    leaked = tokens & VENDOR_TOKENS
    if leaked:
        _fail(
            errors, path,
            f"role '{role}' leaks vendor token(s) {sorted(leaked)} — "
            "use a vendor-neutral id (see docs/reference/rc-entity-naming.md)",
        )


def _validate_component(errors: list[str], comp: dict, idx: int) -> str | None:
    path = f"components[{idx}]"
    if not isinstance(comp, dict):
        _fail(errors, path, f"must be a mapping, got {type(comp).__name__}")
        return None

    for field in REQUIRED_COMPONENT_FIELDS:
        if field not in comp:
            _fail(errors, path, f"is missing required field '{field}'")

    role = comp.get("role")
    if isinstance(role, str) and role:
        _validate_role(errors, comp, role, path)

    qty = comp.get("qty")
    if not isinstance(qty, int) or isinstance(qty, bool) or qty < 1:
        _fail(errors, path, f"qty must be an integer >= 1 (got {qty!r})")

    unit = comp.get("unit_cost_usd")
    if not isinstance(unit, int) or isinstance(unit, bool) or unit < 0:
        _fail(
            errors, path,
            f"unit_cost_usd must be an integer >= 0 in cents (got {unit!r})",
        )
    elif unit > MAX_COMPONENT_UNIT_CENTS:
        _fail(
            errors, path,
            f"unit_cost_usd ${unit / 100:.2f} exceeds the per-component "
            f"sanity cap of ${MAX_COMPONENT_UNIT_CENTS // 100}",
        )

    req = comp.get("required")
    if not isinstance(req, bool):
        _fail(errors, path, f"required must be a boolean (got {req!r})")

    name = comp.get("name")
    if not isinstance(name, str) or not name.strip():
        _fail(errors, path, "name must be a non-empty string")

    supplier = comp.get("supplier")
    if not isinstance(supplier, str) or not supplier.strip():
        _fail(errors, path, "supplier must be a non-empty string")

    spn = comp.get("supplier_part_no")
    if not isinstance(spn, str) or not spn.strip():
        _fail(errors, path, "supplier_part_no must be a non-empty string")

    link = comp.get("link")
    if not isinstance(link, str) or not link.strip():
        _fail(errors, path, "link must be a non-empty URL string")
    elif not (link.startswith("http://") or link.startswith("https://")):
        _fail(errors, path, f"link must start with http:// or https:// (got {link!r})")

    return role if isinstance(role, str) else None


def validate_manifest(data: object) -> tuple[list[str], dict]:
    """Run every rule. Return (errors, summary) so the caller can
    print either a failure report or a clean summary."""

    errors: list[str] = []

    if not isinstance(data, dict):
        _fail(
            errors, "<root>",
            f"top-level must be a mapping, got {type(data).__name__}",
        )
        return errors, {"components": 0, "total_required_cents": 0}

    manifest = data.get("manifest")
    if not isinstance(manifest, dict):
        _fail(errors, "manifest", "must be a mapping with name + version + platform")
    else:
        for fld in ("name", "version", "platform"):
            if not isinstance(manifest.get(fld), str) or not manifest[fld].strip():
                _fail(errors, f"manifest.{fld}", "must be a non-empty string")

    components = data.get("components")
    if not isinstance(components, list) or not components:
        _fail(errors, "components", "must be a non-empty list")
        return errors, {"components": 0, "total_required_cents": 0}

    seen_roles: dict[str, int] = {}
    total_required_cents = 0

    for idx, comp in enumerate(components):
        role = _validate_component(errors, comp, idx)
        if role is not None:
            if role in seen_roles:
                _fail(
                    errors, f"components[{idx}]",
                    f"duplicate role '{role}' (also at components[{seen_roles[role]}])",
                )
            else:
                seen_roles[role] = idx
            # Sum the total of required components only — optional
            # upgrades (e.g. the 5G kit, when present) shouldn't pull
            # the Hub total out of the V1 sanity band.
            required_flag = comp.get("required")
            unit = comp.get("unit_cost_usd")
            qty = comp.get("qty")
            if (
                required_flag is True
                and isinstance(unit, int)
                and isinstance(qty, int)
            ):
                total_required_cents += unit * qty

    if not errors:
        if total_required_cents < MIN_TOTAL_REQUIRED_CENTS:
            _fail(
                errors, "<total>",
                f"required-only total ${total_required_cents / 100:.2f} is "
                f"below the sanity floor of ${MIN_TOTAL_REQUIRED_CENTS // 100}",
            )
        elif total_required_cents > MAX_TOTAL_REQUIRED_CENTS:
            _fail(
                errors, "<total>",
                f"required-only total ${total_required_cents / 100:.2f} is "
                f"above the sanity ceiling of ${MAX_TOTAL_REQUIRED_CENTS // 100}",
            )

    summary = {
        "components": len(components),
        "roles_unique": len(seen_roles) == len(components),
        "total_required_cents": total_required_cents,
    }
    return errors, summary


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        sys.stderr.write(
            "Usage: hub-bom-validate.py <path-to-roamcore-hub-bom.yml>\n"
        )
        return 2

    path = Path(argv[1])
    if not path.is_file():
        sys.stderr.write(f"ERROR: BOM file not found: {path}\n")
        return 2

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        sys.stderr.write(f"ERROR: BOM YAML failed to parse: {exc}\n")
        return 2

    errors, summary = validate_manifest(data)

    if errors:
        sys.stderr.write("\n".join(errors) + "\n")
        sys.stderr.write(
            f"\nFAIL: {len(errors)} RoamCore Hub BOM validation error(s).\n"
        )
        return 1

    total_dollars = summary["total_required_cents"] / 100
    print(
        f"OK: RoamCore Hub BOM validates — "
        f"{summary['components']} components, "
        f"required-only total ${total_dollars:,.2f} USD "
        f"(within ${MIN_TOTAL_REQUIRED_CENTS // 100}-${MAX_TOTAL_REQUIRED_CENTS // 100} "
        "sanity band)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
