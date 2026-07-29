#!/usr/bin/env bash
# RoamCore HACS packaging smoke check (Wave 2 #19)
#
# Validates that the repository is ready to be published as a HACS
# default-store integration:
#
#   1. hacs.json (repo root) parses as JSON, declares all 3 RoamCore
#      integration domains, sets content_in_root=false, and has a
#      country field.
#   2. Each of the 3 integration directories has a manifest.json with
#      the required HA fields (domain, name, version).
#   3. The primary RoamCore integration has:
#         - info.md (HACS-published metadata) — non-empty
#         - branding/icon.png and branding/logo.png — ≥256x256 PNGs
#   4. The two sub-integrations have their own hacs.json files that
#      parse as JSON.
#
# This script does NOT modify any file. It exits 0 on success, 1 on
# any validation failure.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

fail() { echo "ERROR: $*" >&2; exit 1; }
ok()   { echo "  OK: $*"; }

# Use python3 so we don't depend on jq.
python3_validate_json() {
    python3 -c 'import json,sys; json.load(open(sys.argv[1],"r",encoding="utf-8")); print("OK")' "$1"
}

python3_extract_json_field() {
    # $1 = file, $2 = dotted field path (only top-level keys supported here)
    python3 -c '
import json, sys
d = json.load(open(sys.argv[1], "r", encoding="utf-8"))
v = d.get(sys.argv[2])
if isinstance(v, list):
    print(" ".join(str(x) for x in v))
else:
    print("" if v is None else v)
' "$1" "$2"
}

python3_validate_manifest_required_fields() {
    # $1 = manifest path
    python3 -c '
import json, sys
required = ("domain", "name", "version")
m = json.load(open(sys.argv[1], "r", encoding="utf-8"))
missing = [k for k in required if k not in m or m[k] in (None, "")]
if missing:
    print("missing required fields:", missing, file=sys.stderr)
    sys.exit(1)
print(m["domain"], m["name"], m["version"])
' "$1"
}

python3_validate_png_dimensions() {
    # $1 = png path, $2 = min dimension
    python3 -c '
import struct, sys
path = sys.argv[1]
need = int(sys.argv[2])
with open(path, "rb") as f:
    sig = f.read(8)
    if sig != b"\x89PNG\r\n\x1a\n":
        print(f"not a PNG: {path}", file=sys.stderr); sys.exit(1)
    # IHDR is the first chunk after the 8-byte signature.
    length_bytes = f.read(4)
    length = struct.unpack(">I", length_bytes)[0]
    chunk_type = f.read(4)
    if chunk_type != b"IHDR":
        print(f"PNG missing IHDR chunk: {path}", file=sys.stderr); sys.exit(1)
    data = f.read(length)
    crc = f.read(4)
    width, height = struct.unpack(">II", data[:8])
    if width < need or height < need:
        print(f"PNG too small (need >= {need}x{need}, got {width}x{height}): {path}",
              file=sys.stderr)
        sys.exit(1)
print(f"{width}x{height}")
' "$1" "$2"
}

echo "== RoamCore HACS packaging smoke =="

# --- 1. Root hacs.json ---
ROOT_HACS="hacs.json"
[ -f "$ROOT_HACS" ] || fail "missing $ROOT_HACS at repo root"
python3_validate_json "$ROOT_HACS" >/dev/null || fail "$ROOT_HACS is not valid JSON"
ok "$ROOT_HACS parses as JSON"

# content_in_root must be false (we ship under homeassistant/custom_components)
CIR="$(python3_extract_json_field "$ROOT_HACS" content_in_root)"
[ "$CIR" = "False" ] || fail "$ROOT_HACS content_in_root must be false (got: $CIR)"
ok "content_in_root=false"

# country must be set
COUNTRY="$(python3_extract_json_field "$ROOT_HACS" country)"
[ -n "$COUNTRY" ] || fail "$ROOT_HACS missing required field 'country'"
ok "country=$COUNTRY"

# domains must include all 3 RoamCore integration domains
DOMAINS_LINE="$(python3_extract_json_field "$ROOT_HACS" domains)"
EXPECTED_DOMAINS=(roamcore roamcore_tileserver roamcore_traccar_proxy)
for d in "${EXPECTED_DOMAINS[@]}"; do
    case " $DOMAINS_LINE " in
        *" $d "*) ;;
        *) fail "$ROOT_HACS domains missing required integration: $d (have: $DOMAINS_LINE)" ;;
    esac
done
ok "domains=[$DOMAINS_LINE]"

# --- 2. Per-integration manifest.json checks ---
for d in "${EXPECTED_DOMAINS[@]}"; do
    MANIFEST="homeassistant/custom_components/$d/manifest.json"
    [ -f "$MANIFEST" ] || fail "missing $MANIFEST"
    parsed="$(python3_validate_manifest_required_fields "$MANIFEST")" \
        || fail "$MANIFEST does not have required fields (domain, name, version)"
    ok "$d/manifest.json has required fields ($parsed)"
done

# --- 3. Primary RoamCore integration metadata ---
ROAMCORE_DIR="homeassistant/custom_components/roamcore"
INFO_MD="$ROAMCORE_DIR/info.md"
[ -f "$INFO_MD" ] || fail "missing $INFO_MD (HACS integration metadata)"
INFO_BYTES="$(wc -c < "$INFO_MD")"
[ "$INFO_BYTES" -gt 200 ] || fail "$INFO_MD is suspiciously small ($INFO_BYTES bytes)"
ok "info.md present ($INFO_BYTES bytes)"

ICON="$ROAMCORE_DIR/branding/icon.png"
LOGO="$ROAMCORE_DIR/branding/logo.png"
[ -f "$ICON" ] || fail "missing $ICON"
[ -f "$LOGO" ] || fail "missing $LOGO"
icon_dims="$(python3_validate_png_dimensions "$ICON" 256)" \
    || fail "$ICON is not a PNG ≥ 256x256"
ok "branding/icon.png is ${icon_dims} PNG"
logo_dims="$(python3_validate_png_dimensions "$LOGO" 256)" \
    || fail "$LOGO is not a PNG ≥ 256x256"
ok "branding/logo.png is ${logo_dims} PNG"

# --- 4. Sub-integration hacs.json ---
for d in roamcore_tileserver roamcore_traccar_proxy; do
    SUB_HACS="homeassistant/custom_components/$d/hacs.json"
    [ -f "$SUB_HACS" ] || fail "missing $SUB_HACS"
    python3_validate_json "$SUB_HACS" >/dev/null \
        || fail "$SUB_HACS is not valid JSON"
    ok "$d/hacs.json parses as JSON"
done

# --- 5. Sub-integration hacs.json must reference its own domain ---
for d in roamcore_tileserver roamcore_traccar_proxy; do
    SUB_HACS="homeassistant/custom_components/$d/hacs.json"
    sub_domains="$(python3_extract_json_field "$SUB_HACS" domains)"
    case " $sub_domains " in
        *" $d "*) ok "$d/hacs.json domains=[$sub_domains]" ;;
        *) fail "$SUB_HACS domains missing self-reference '$d' (have: $sub_domains)" ;;
    esac
done

echo "All RoamCore HACS packaging smoke checks passed."
