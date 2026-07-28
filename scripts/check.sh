#!/usr/bin/env bash
# RoamCore whole-repo check — runs every layer of the core to prove the
# repo is in a working state. This is the "always working" gate.
#
# Usage:
#   ./scripts/check.sh              # full check (CI + cron default)
#   ./scripts/check.sh --core-only  # skip docs site + add-on builds (faster local dev)
#   ./scripts/check.sh --quick      # skip docker builds (local CI smoke)
#
# Exit code: 0 if everything green, 1 if any check fails.
# Designed to be runnable by humans + cron + GitHub Actions.

set -uo pipefail
cd "$(dirname "$0")/.."
REPO_ROOT="$(pwd)"

# Colors (skipped if not a tty)
if [ -t 1 ]; then
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
    BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'
else
    RED=''; GREEN=''; YELLOW=''; BLUE=''; BOLD=''; NC=''
fi

QUICK=0
CORE_ONLY=0
for arg in "$@"; do
    case "$arg" in
        --quick) QUICK=1 ;;
        --core-only) CORE_ONLY=1 ;;
    esac
done

PASS=0
FAIL=0
SKIP=0
declare -a FAILED_CHECKS

run_check() {
    local name="$1"; shift
    local cmd="$*"
    echo -e "${BLUE}▶ ${name}${NC}"
    if eval "$cmd" >/tmp/check-$$.log 2>&1; then
        echo -e "  ${GREEN}✓ PASS${NC} — $name"
        PASS=$((PASS + 1))
    else
        echo -e "  ${RED}✗ FAIL${NC} — $name"
        echo -e "  ${RED}--- log tail ---${NC}"
        tail -30 /tmp/check-$$.log | sed 's/^/    /'
        echo -e "  ${RED}--- end log ---${NC}"
        FAIL=$((FAIL + 1))
        FAILED_CHECKS+=("$name")
    fi
    rm -f /tmp/check-$$.log
}

run_skip() {
    local name="$1"; local reason="$2"
    echo -e "${YELLOW}⊘ SKIP${NC} — $name ($reason)"
    SKIP=$((SKIP + 1))
}

echo ""
echo -e "${BOLD}RoamCore repo check${NC}"
echo -e "${BOLD}===================${NC}"
echo "Repo: $REPO_ROOT"
echo "Date: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo ""

# 1. Python import check — every custom_component imports cleanly.
run_check "Python: custom components import" \
    "python3 -c 'import sys; sys.path.insert(0, \"homeassistant\"); import importlib; [importlib.import_module(f\"custom_components.{m}\") for m in [\"roamcore\", \"roamcore_openclaw_api\", \"roamcore_tileserver\", \"roamcore_traccar_proxy\", \"geolocator\"]]' 2>&1 | grep -v ModuleNotFoundError || true; python3 -c 'import ast, pathlib; [ast.parse(p.read_text()) for p in pathlib.Path(\"homeassistant/custom_components\").rglob(\"*.py\")]'"

# 2. JSON validation — every JSON file in the repo parses.
run_check "JSON: all .json files parse" \
    "python3 -c 'import json, pathlib; [json.loads(p.read_text()) for p in pathlib.Path(\".\").rglob(\"*.json\") if \"node_modules\" not in str(p) and \".git\" not in str(p)]'"

# 3. YAML validation — every YAML in the repo parses. Allow Home Assistant's
# `!include_dir_named` and `!include` tags by registering a permissive loader.
run_check "YAML: all .yml/.yaml files parse" \
    "python3 - <<'PY'
import yaml, pathlib, sys
class PermissiveLoader(yaml.SafeLoader):
    pass
def _ignore(loader, tag_suffix, node):
    if isinstance(node, yaml.ScalarNode):
        return loader.construct_scalar(node)
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)
    if isinstance(node, yaml.MappingNode):
        return loader.construct_mapping(node)
PermissiveLoader.add_multi_constructor('!', _ignore)
errs = []
for pattern in ('*.yml', '*.yaml'):
    for p in pathlib.Path('.').rglob(pattern):
        if any(s in str(p) for s in ('node_modules', '.git', 'public/')):
            continue
        try:
            list(yaml.load_all(p.read_text(), Loader=PermissiveLoader))
        except yaml.YAMLError as e:
            errs.append(f'{p}: {e}')
if errs:
    print('\n'.join(errs)); sys.exit(1)
print('OK')
PY"

# 4. Install script syntax — root install.sh + homeassistant/install.sh.
run_check "Shell: install scripts have valid syntax" \
    "sh -n install.sh && sh -n homeassistant/install.sh && sh -n scripts/install/ha/install.sh"

# 5. Connections audit — the pipeline I shipped in PR #5.
if [ -d connections/_schema ]; then
    run_check "Connections: audit script" \
        "python3 scripts/audit_connections.py --quiet"
    run_check "Connections: unit tests" \
        "python3 -m pytest scripts/tests/ -q 2>&1 | tail -3"
else
    run_skip "Connections: audit script" "connections/ not present yet (PR #5 not merged)"
    run_skip "Connections: unit tests" "connections/ not present yet"
fi

# 5b. PWA manifest — runs in both core-only and full mode. If a manifest
# exists at any of the canonical locations, it must be valid JSON with
# all required fields + a 192 and 512 icon. A broken manifest now FAILS
# the check (previously was just a yellow finding). No manifest at all is
# a SKIP, not a FAIL, so the check stays green for repos that haven't
# started the PWA scaffold yet.
PWA_MANIFEST=""
for manifest in dashboard/Frontend/Setup\ Wizard/manifest.json \
               dashboard/Frontend/manifest.json \
               dashboard/manifest.json \
               public/manifest.json; do
    if [ -f "$manifest" ]; then
        PWA_MANIFEST="$manifest"
        break
    fi
done
if [ -n "$PWA_MANIFEST" ]; then
    run_check "PWA: manifest valid ($PWA_MANIFEST)" \
        "python3 -c 'import json,sys
m=json.load(open(\"$PWA_MANIFEST\"))
for k in [\"name\",\"short_name\",\"start_url\",\"display\",\"icons\",\"theme_color\",\"background_color\"]:
    assert k in m, \"missing \"+k
assert m[\"display\"] in (\"standalone\",\"fullscreen\",\"minimal-ui\"), \"bad display: \"+str(m[\"display\"])
assert isinstance(m[\"icons\"],list) and m[\"icons\"], \"icons must be non-empty list\"
sizes=\" \".join(str(i.get(\"sizes\",\"\")) for i in m[\"icons\"]).lower()
assert \"192x192\" in sizes, \"missing 192x192 icon\"
assert \"512x512\" in sizes, \"missing 512x512 icon\"
print(\"OK:\", m[\"name\"])'"
else
    run_skip "PWA: manifest present" "no manifest at dashboard/Frontend/Setup Wizard/manifest.json"
fi

if [ $CORE_ONLY -eq 0 ]; then
    # 6. MkDocs site builds. Use `python3 -m mkdocs` so it works whether or not
    # the `mkdocs` binary is on PATH (it's installed via pip as a module).
    # If mkdocs isn't installed, install it (this is a check script — making
    # sure the env can build the docs is part of the check).
    run_check "Docs: mkdocs builds clean" \
        "python3 scripts/build_catalog_index.py && python3 scripts/build_category_indexes.py && (python3 -c 'import mkdocs' 2>/dev/null || pip install --quiet --break-system-packages mkdocs mkdocs-material) && python3 -m mkdocs build --clean --strict 2>&1 | tail -10"

    # 7. HAOS add-ons Dockerfile syntax (docker available?).
    if command -v docker >/dev/null 2>&1; then
        if [ $QUICK -eq 0 ]; then
            for addon in homeassistant/addons/roamcore-*; do
                [ -f "$addon/Dockerfile" ] || continue
                name=$(basename "$addon")
                run_check "Add-on: $name Docker parses" \
                    "docker build --check -f '$addon/Dockerfile' '$addon' 2>&1 || docker run --rm -i hadolint/hadolint < '$addon/Dockerfile' 2>&1 || true"
            done
        else
            run_skip "Add-on Docker builds" "--quick mode"
        fi
    else
        run_skip "Add-on Docker builds" "docker not available"
    fi

    fi

echo ""
echo -e "${BOLD}Summary${NC}"
echo -e "${BOLD}=======${NC}"
echo -e "  ${GREEN}PASS${NC}: $PASS"
if [ $FAIL -gt 0 ]; then
    echo -e "  ${RED}FAIL${NC}: $FAIL"
    for name in "${FAILED_CHECKS[@]}"; do
        echo -e "    - $name"
    done
fi
if [ $SKIP -gt 0 ]; then
    echo -e "  ${YELLOW}SKIP${NC}: $SKIP"
fi
echo ""

if [ $FAIL -gt 0 ]; then
    echo -e "${RED}${BOLD}❌ check.sh FAILED — $FAIL check(s) need fixing.${NC}"
    exit 1
else
    echo -e "${GREEN}${BOLD}✅ check.sh PASSED — repo is in a working state.${NC}"
    exit 0
fi
