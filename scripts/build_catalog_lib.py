#!/usr/bin/env python3
"""
RoamCore catalog build helpers.

Library for ``scripts/build_catalog.py``. Pure stdlib + PyYAML (used if
available). Provides:

* YAML loading with a graceful fallback parser
* Canonical-category mapping (yaml category -> docs/catalog/<dir>)
* Human-friendly title + 1-2 sentence summary extraction ("humanize")
* Install-method -> 5-line install block templater
* Markdown frontmatter / page rendering

Design goals
~~~~~~~~~~~~

* Read **only** the existing ``connections/*/connection.yml`` files —
  never edit the YAMLs themselves.
* Produce user-facing copy that reads like an IKEA furniture
  catalogue, not like an upstream-integration README. When in doubt,
  be less technical. Bernard will tell us if we went too far.
* Ruthlessly exclude internal / developer slices (see
  ``DEFAULT_EXCLUDE``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml  # PyYAML
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Default exclusion list
# ---------------------------------------------------------------------------
#
# These slices are real, working RoamCore features, but they are NOT
# user-facing catalogue material — they target operators / developers /
# agent authors. They still appear in ``connections/_all_connections_inventory.yml``
# so the developer reference stays complete.

DEFAULT_EXCLUDE: list[str] = [
    "agent-actions-allowlist",
    "openclaw-api",
]


# ---------------------------------------------------------------------------
# Canonical category mapping
# ---------------------------------------------------------------------------
#
# The YAML files use their own internal taxonomy (ventilation, lighting,
# map, homelab, …). The user-facing catalogue uses a smaller, friendlier
# set of buckets so a non-technical van owner can scan "all the comfort
# features" at a glance.

CATEGORY_MAP: dict[str, str] = {
    # power & energy
    "power": "power",
    "victron": "power",
    "alternator": "power",
    # connectivity / networking
    "networking": "connectivity",
    "tailscale": "connectivity",
    "remote-access": "connectivity",
    # safety
    "safety": "safety",
    "smoke": "safety",
    "co": "safety",
    "gas": "safety",
    # comfort (climate, fans, lighting, hvac, beds, audio)
    "ventilation": "comfort",
    "hvac": "comfort",
    "lighting": "comfort",
    "bed_lift": "comfort",
    "media": "comfort",
    # water
    "water": "water",
    # location & maps
    "map": "location",
    "presence": "location",
    # maintenance & diagnostics (vehicle OBD, leveling, deadbolts, NFC)
    "vehicle": "maintenance",
    "vehicle_obd": "maintenance",
    # security (locks, access control, NFC tags)
    "access_control": "security",
    "cctv": "security",
    # automation (recipes, scenes, motion, smart-automations)
    "automation": "automation",
    # ai / agent features (Mode, Advanced mode, Demo mode etc. all surface as "van behavior")
    "ai": "automation",
    # home lab / NAS / DNS / time
    "homelab": "misc",
    "time": "misc",
}


CATEGORY_DESCRIPTIONS: dict[str, str] = {
    "power": "Batteries, solar, alternators, inverters — anything that keeps the lights on.",
    "connectivity": "Internet, cellular, satellite, and the secure ways to reach the van from anywhere.",
    "safety": "Smoke, CO, gas, locks, and the alerts that keep you and the van out of trouble.",
    "comfort": "Climate, fans, lights, beds, audio — the small things that make the van feel like home.",
    "water": "Tanks, pumps, valves, leaks.",
    "location": "GPS, maps, presence, and knowing where the van is (and who's in it).",
    "maintenance": "Diagnostics, leveling, OBD — keeping the van itself healthy.",
    "security": "Locks, CCTV, access control.",
    "automation": "Recipes, scenes, and the automations that make the van feel like it has a mind of its own.",
    "ai": "AI summaries, mode inference, agent features — RoamCore's smarts.",
    "misc": "Tools that don't fit a single bucket — DNS, NAS, time sync, and more.",
}


# ---------------------------------------------------------------------------
# YAML loading with fallback
# ---------------------------------------------------------------------------


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file. Prefers PyYAML, falls back to a minimal parser."""

    text = path.read_text(encoding="utf-8")

    if yaml is not None:
        return yaml.safe_load(text) or {}

    # Fallback: extremely small parser that handles the subset we use
    # (top-level ``key: value`` + ``key:`` followed by indented block of
    # either scalar continuations or list items). Good enough for the
    # connection.yml files we ship; not a general-purpose YAML reader.
    return _minimal_yaml(text)


def _minimal_yaml(text: str) -> dict[str, Any]:
    """Tiny YAML subset parser used only if PyYAML is missing."""

    result: dict[str, Any] = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        if stripped.startswith("- "):
            # stray list at top level — ignore
            i += 1
            continue
        if ":" not in stripped:
            i += 1
            continue
        key, _, value = stripped.partition(":")
        key = key.strip()
        value = value.strip()
        i += 1
        if value == "":
            # block-style: gather indented lines
            block_lines: list[str] = []
            while i < len(lines):
                nxt = lines[i]
                if not nxt.strip():
                    i += 1
                    continue
                if nxt[: len(nxt) - len(nxt.lstrip())] == 0:
                    break
                if not (nxt.startswith(" ") or nxt.startswith("\t")):
                    break
                block_lines.append(nxt.strip())
                i += 1
            joined = " ".join(block_lines).strip()
            if joined.startswith("[") and joined.endswith("]"):
                inner = joined[1:-1]
                result[key] = [
                    p.strip().strip('"').strip("'")
                    for p in inner.split(",")
                    if p.strip()
                ]
            elif joined.startswith("- ") or " - " in joined:
                result[key] = [
                    p.lstrip("- ").strip().strip('"').strip("'")
                    for p in joined.split(" - ")
                    if p.strip()
                ]
            else:
                result[key] = joined
        elif value.startswith("[") and value.endswith("]"):
            inner = value[1:-1]
            result[key] = [
                p.strip().strip('"').strip("'")
                for p in inner.split(",")
                if p.strip()
            ]
        else:
            result[key] = value.strip('"').strip("'")
    return result


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class Connection:
    """Parsed, normalised view of a single ``connections/*/connection.yml``."""

    slug: str  # directory / branch name, e.g. ``fans``
    raw_id: str  # YAML ``id`` field, e.g. ``fans`` or ``rc_fans`` or ``agent_actions``
    name_raw: str  # full YAML ``name`` field
    title: str  # short user-facing title, e.g. ``Fans``
    yaml_category: str  # category as written in YAML, e.g. ``ventilation``
    catalog_category: str  # normalised for docs/catalog/<dir>, e.g. ``comfort``
    tier: str  # A / B / C (uppercase)
    status: str  # shipped / beta / recipe_published / planned
    install_method: str  # one_click / one_line / hacs / manual
    raw_description: str  # full description text
    summary: str  # 1-2 sentence human-facing blurb
    tags: list[str] = field(default_factory=list)
    additional_hardware: list[str] = field(default_factory=list)
    install_instructions: str = ""
    needs_curation_review: bool = False
    excluded: bool = False
    src_path: Path | None = None


# ---------------------------------------------------------------------------
# Title + summary extraction
# ---------------------------------------------------------------------------

_NAME_GARBAGE_TRAIL = re.compile(
    r"\s*[—-]\s*"
    r"(?:vendor[- ]neutral|tier[- ][abcd]|recipe connection|connection|"
    r"umbrella|operator picks ONE path)[^()]*$",
    re.IGNORECASE,
)

_PAREN_BLOCK = re.compile(r"\s*\([^()]*\)\s*")


def extract_title(name_raw: str) -> str:
    """Pull the short, user-facing title out of a verbose YAML ``name`` field.

    The YAML name is typically something like::

        "Fans (vendor-neutral fan-controller umbrella for HA — rooftop
        vent fans + circulation fans + bathroom exhaust fans, operator
        picks ONE path) — tier-b recipe connection"

    We want to surface just ``Fans``. We do this by stripping the
    parenthesised clarification, then trimming any trailing tier /
    recipe / umbrella breadcrumbs.
    """

    text = name_raw.strip().strip('"').strip("'")
    # Take everything before the first opening paren
    if "(" in text:
        text = text.split("(", 1)[0]
    # Strip the trailing "— tier-b recipe connection" / "— umbrella" etc.
    text = _NAME_GARBAGE_TRAIL.sub("", text)
    # Collapse whitespace and trim
    text = re.sub(r"\s+", " ", text).strip(" -—:,")
    # Final cleanup: keep the first capitalised phrase
    return text or name_raw.strip()


# Sentences that look like the legacy-stub one-liner. We pick the
# SHORTEST quoted span in the description if one is present.
_QUOTED_HUMAN_SENTENCE = re.compile(r'"([^.]{20,260})"')

# The "the umbrella for \"X\"" pattern used by every Wave-3 slice.
_UMBRELLA_FOR_PATTERN = re.compile(
    r'(?:the umbrella for|is the umbrella for|umbrella for)\s*"([^"]+)"',
    re.IGNORECASE,
)

# Unquoted variant: ``the umbrella for ignition-driven interior auto-off + soft-interior on stop`` —
# followed by either an em-dash + "is the X-category complement" or a period.
_UMBRELLA_FOR_BARE_PATTERN = re.compile(
    r"(?:the umbrella for|is the umbrella for|umbrella for)\s+(.+?)"
    r"(?:\s+[—-]+\s+is the\s|\.\s|\.$)",
    re.IGNORECASE,
)

# Strip HTML / Markdown link noise from candidate sentences
_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_BARE_URL_PATTERN = re.compile(r"<(https?://[^>]+)>|https?://\S+")


def humanize_summary(desc: str, title: str) -> str:
    """Return a 1-2 sentence, non-technical blurb about the connection.

    Strategy (in priority order):

    1. **The "umbrella for "X"" legacy stub.** Most slices carry a
       quoted legacy catalog line — usually the cleanest user-facing
       copy available. We detect ``the umbrella for "X"`` patterns
       and return just ``X``, polished.
    2. **The "what this connection is" sentence.** Almost every
       slice's description opens with a long sentence that introduces
       the feature in plain English. We grab that first sentence.
    3. **A quoted legacy sentence.** Any quoted sentence that looks
       like a real, grammatical sentence.
    4. **Body fallback.** Any 1-2 non-jargon sentences from the body.
    5. **Placeholder.** A short, friendly mention of the title.
    """

    if not desc:
        return f"{title} — RoamCore catalog entry."

    flat = re.sub(r"\s+", " ", desc).strip()

    # 1. the umbrella for "X" (quoted)
    umbrella = _UMBRELLA_FOR_PATTERN.search(flat)
    if umbrella:
        stub = _clean(umbrella.group(1))
        # Force capital first letter
        if stub and stub[0].islower():
            stub = stub[0].upper() + stub[1:]
        if _looks_like_real_sentence(stub):
            return stub

    # 1b. the umbrella for X (unquoted) — only use it if it looks
    #     like a real, grammatical sentence (not a " + " recipe bullet
    #     list).
    bare = _UMBRELLA_FOR_BARE_PATTERN.search(flat)
    if bare:
        stub = _clean(bare.group(1))
        if " + " in stub and not _looks_like_real_sentence(stub):
            pass  # fall through — recipe bullet list, not user copy
        else:
            if stub and stub[0].islower():
                stub = stub[0].upper() + stub[1:]
            if _looks_like_real_sentence(stub):
                return stub

    # 2. intro sentence (only if the description doesn't already start
    #    with an "umbrella for X" pattern, in which case the intro is
    #    just the YAML's name + the umbrella stub mashed together)
    umbrella_anywhere = (
        _UMBRELLA_FOR_PATTERN.search(flat)
        or _UMBRELLA_FOR_BARE_PATTERN.search(flat)
    )
    if umbrella_anywhere:
        # Description opens with an umbrella stub. Don't repeat the
        # meta-intro that wraps it.
        pass
    else:
        intro = _extract_intro_sentence(flat)
        if intro:
            cleaned = _clean(intro)
            if _looks_like_real_sentence(cleaned):
                return cleaned

    # 3. quoted legacy sentence
    candidates = _QUOTED_HUMAN_SENTENCE.findall(desc)
    for cand in sorted(candidates, key=len, reverse=True):
        cleaned = _clean(cand)
        if _looks_like_real_sentence(cleaned):
            return cleaned

    # 4. body fallback: any 1-2 non-jargon sentences from the body.
    #    Prefer sentences that don't start with the connection's title
    #    (those are usually just the YAML's name being repeated).
    sentences = re.split(r"(?<=[.!?])\s+", flat)
    title_words = set(w.lower() for w in re.findall(r"\w+", title) if len(w) > 3)
    picked: list[str] = []
    for s in sentences:
        if _is_too_jargon(s):
            continue
        if len(s) < 30:
            continue
        # Reject sentences that start by restating the title.
        leading_words = set(w.lower() for w in re.findall(r"\w+", s.split("—")[0])[:3])
        if title_words and leading_words & title_words:
            # mostly title-restating — skip
            continue
        picked.append(s)
        if len(picked) >= 2:
            break
    if picked:
        return _clean(" ".join(picked))

    # 5. placeholder
    return f"{title} — RoamCore catalog entry."


def _extract_intro_sentence(flat_desc: str) -> str | None:
    """Pick the opening sentence that introduces the connection in plain English.

    The opening sentence of a connection description usually runs
    ``<Title> (...) — the <category> complement: <one-line benefit>.``,
    ending at the first period. We want everything from the start of
    the sentence up to that first period, but only if it doesn't look
    like a recipe-style overview sentence.
    """

    # If there's an "umbrella for" earlier, the intro above it is just
    # the YAML's name + category restated — not useful.
    if _UMBRELLA_FOR_PATTERN.search(flat_desc[:400]):
        return None

    # Strip URLs first so we don't accidentally split on periods inside URLs
    sanitised = _BARE_URL_PATTERN.sub("", flat_desc)
    # Grab text up to the first period.
    end = sanitised.find(".")
    if end == -1 or end > 600:
        candidate = sanitised[:600]
    else:
        candidate = sanitised[: end + 1]

    # Reject obvious jargon intros
    if _is_too_jargon(candidate):
        return None

    if not _looks_like_real_sentence(candidate):
        return None

    # Reject if the candidate is mostly inside the title / header material
    # (these intros just repeat the YAML's name + category, which the
    # title already covers).
    lowered = candidate.lower()
    if lowered.startswith("roamcore does not ship"):
        return None
    if lowered.startswith("roamcore ships no"):
        return None
    if "vendor-neutral " in lowered[:120] and "umbrella" in lowered:
        return None
    if lowered.startswith("this connection provides"):
        return None
    if lowered.startswith("this connection exposes"):
        return None
    if lowered.startswith("the recipe expands"):
        return None
    if lowered.startswith("the recipe covers"):
        return None
    if lowered.startswith("the recipe walks"):
        return None
    # Skip intros that look like a bracket-quote sandwich: "..." — is the X-category complement
    if "— is the " in candidate and "category complement" in candidate:
        return None
    # Skip intros that are just "<Title> — the umbrella for X — is the Y-category complement"
    # form (these repeat the YAML's name; the user already sees the title).
    if "— the umbrella for " in lowered and "category complement" in lowered:
        return None
    # Skip intros that look like "<Title> (...) — the umbrella for X" without a
    # colon/quote immediately after (i.e. the umbrella stub is bare text).
    # For those we want to extract the umbrella stub itself, not the meta-intro.
    if "— the umbrella for " in lowered and '"' not in candidate:
        return None

    return candidate


def _looks_like_real_sentence(s: str) -> bool:
    """Heuristic: does this look like a real, grammatical sentence?"""

    s = s.strip()
    if not s:
        return False
    if len(s) < 20:
        return False
    # Must start with a capital letter or be a question
    if not (s[0].isupper() or s.endswith("?")):
        return False
    # Reject sentences that obviously start mid-sentence (lowercase
    # articles or continuations)
    if s.split()[0].lower() in {"the", "and", "or", "but", "is", "of", "to", "for", "in", "from", "with"}:
        return False
    return True


def _is_too_jargon(s: str) -> bool:
    """Heuristic: is this sentence almost entirely upstream-integration jargon?"""

    lowered = s.lower()
    jargon_phrases = (
        "rc_",
        "input_select",
        "input_boolean",
        "input_button",
        "fan.turn_on",
        "fan.set_percentage",
        "fan.set_preset",
        "fan.toggle",
        "fan.turn_off",
        "binary_sensor",
        "the recipe",
        "the umbrella",
        "umbrella publishes",
        "honesty footnote",
        "vendor-neutral ",
        "operator picks one path",
        "vendor integration",
        "hacs custom repository",
        "since 2022",
        "since 2023",
        "since 2024",
        "gui flow",
        "ha core",
        "input_text",
        "zwave_js",
        "roamcore ships no",
        "roamcore does not ship",
        "tile is",
        "tile surfaces",
        "tile aggregates",
        "tile is the",
        "tile is a",
        "binary_sensor.",
        "this connection exposes",
        "this connection provides",
        "the recipe expands",
        "the recipe covers",
        "the recipe walks",
        "the contract layer is",
        "the recipe's",
    )
    # If a sentence contains 2+ jargon phrases, it's a recipe/contract
    # overview, not user copy.
    hits = sum(1 for p in jargon_phrases if p in lowered)
    return hits >= 2


def _clean(s: str) -> str:
    """Polish a candidate sentence for the catalog page."""

    s = re.sub(r"\s+", " ", s).strip()
    s = s.replace("\u2014", "—").replace("\u2013", "-")
    # Strip markdown link syntax — keep the link text
    s = _LINK_PATTERN.sub(r"\1", s)
    # Strip bare URLs
    s = _BARE_URL_PATTERN.sub("", s)
    # Strip residual markdown emphasis
    s = s.replace("**", "").replace("__", "")
    # Collapse empty parens left over from URL removal: "Foo () bar" -> "Foo bar"
    s = re.sub(r"\(\s*\)", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    if s and s[-1] not in ".!?":
        s += "."
    # Trim to <= 320 chars for table / card rendering
    if len(s) > 320:
        s = s[:317].rsplit(" ", 1)[0] + "…"
    return s


# ---------------------------------------------------------------------------
# Install-method -> templated install block
# ---------------------------------------------------------------------------


def install_block(slug: str, method: str) -> str:
    """Render a short install section for the given install method.

    The output is intentionally short (≤5 lines) and matches the
    template in ``docs/catalog/_templates/integration-page.template.md``
    so a non-technical van owner can follow it.
    """

    slug_dashed = slug.replace("_", "-")
    repo_url = "https://raw.githubusercontent.com/roamcore/RoamCore/main"
    lines: list[str] = []

    if method == "one_click":
        lines.append("- Click **Add to my van** in the RoamCore dashboard (one-click install).")
    elif method == "one_line":
        lines.append(
            f"- Click **Add to my van** in the RoamCore dashboard, **or** run "
            f"`bash <(curl -sL {repo_url}/install.sh) --feature {slug_dashed}`."
        )
    elif method == "hacs":
        lines.append(
            f"- Add this repo as a **HACS custom repository** "
            f"(Category: *Integration*), then install **{slug_dashed}**."
        )
    elif method == "manual":
        lines.append(
            "- Follow the **Setup** steps in the recipe — this is a "
            "manual install that wires a few entities together."
        )
    else:
        lines.append(
            f"- Run `bash <(curl -sL {repo_url}/install.sh) --feature {slug_dashed}`."
        )

    lines.append("- Restart Home Assistant.")
    lines.append("- Done — the tiles appear under the relevant section in the dashboard.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Category mapping
# ---------------------------------------------------------------------------


def map_category(yaml_category: str) -> str:
    """Map the YAML category to a canonical catalog directory."""

    key = (yaml_category or "").strip().lower()
    if key in CATEGORY_MAP:
        return CATEGORY_MAP[key]
    # Try plural / singular / underscore variations
    key = key.replace("-", "_")
    if key in CATEGORY_MAP:
        return CATEGORY_MAP[key]
    return "misc"


# ---------------------------------------------------------------------------
# Tags / additional-hardware heuristics
# ---------------------------------------------------------------------------


def sensible_hardware_defaults(slug: str, title: str) -> list[str]:
    """Return a sensible list of optional additional-hardware items.

    The YAML files don't always list hardware; when they don't, we
    generate a short, cost-range-aware list from the slug / title so the
    catalog page isn't empty. This is the kind of thing Bernard will
    tweak by hand.
    """

    s = slug.lower()
    t = title.lower()
    defaults: list[str] = []

    if "fan" in s or "vent" in s:
        defaults += [
            "MaxxAir / Fan-Tastic rooftop vent fan ($250–$450)",
            "Generic 12 V circulation fan + Shelly 1 relay ($30–$80)",
        ]
    if "light" in s or "approach" in s:
        defaults += [
            "Zigbee / Z-Wave exterior light or relay ($20–$60)",
            "Shelly 1 / Shelly Plus 1 ($15–$25)",
        ]
    if "water" in s or "tank" in s:
        defaults += [
            "SeeLevel / Garnet tank sensor ($80–$200)",
            "12 V solenoid valve ($25–$60)",
        ]
    if "level" in s:
        defaults += [
            "Phone IMU (no cost — uses the HA Companion app)",
            "Dedicated MPU-6050 / BNO085 IMU module ($10–$40)",
        ]
    if "lock" in s or "deadbolt" in s:
        defaults += [
            "Z-Wave smart deadbolt (Yale / Schlage) ($120–$250)",
        ]
    if "remote" in s or "tailscale" in s or "networking" in s:
        defaults += [
            "Tailscale account (free for personal use)",
            "Cloudflare account for Cloudflare Tunnel (free tier)",
        ]
    if "smoke" in s or "co" in s or "gas" in s:
        defaults += [
            "Zigbee smoke / CO detector ($30–$80 each)",
        ]
    if "music" in s or "media" in s:
        defaults += [
            "Any AirPlay / Chromecast / Snapcast-capable speaker",
        ]
    if "traccar" in s or "map" in s or "gps" in s:
        defaults += [
            "Teltonika or other GPS tracker (often already in the LTE router)",
        ]

    # De-duplicate while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for h in defaults:
        if h not in seen:
            seen.add(h)
            out.append(h)
    return out


def sensible_tags(yaml_tags: list[str], slug: str, title: str) -> list[str]:
    """Return 3-5 searchable tags, deduped, lower-cased."""

    tags = [str(t).strip().lower() for t in (yaml_tags or []) if str(t).strip()]
    tags = [t for t in tags if t and not t.startswith("@")]
    tags = list(dict.fromkeys(tags))  # dedupe preserving order

    # Always include slug + title as tags so search works
    for extra in (slug.replace("_", "-"), title.lower()):
        if extra and extra not in tags:
            tags.append(extra)

    return tags[:6]


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def render_page(conn: Connection) -> str:
    """Render a single catalog page in IKEA style.

    Plain English. No frontmatter. No warnings. No tier letters.
    No status jargon. No Source manifest footer.
    """

    hardware_block = ""
    if conn.additional_hardware:
        hardware_block = "\n".join(f"- {h}" for h in conn.additional_hardware)

    install = install_block(conn.slug, conn.install_method).strip()

    body = f"""# {conn.title}

{conn.summary}

## What you need

{hardware_block or "- Nothing extra — uses what's already in the van."}

## Install

{install}

## What it shows on your dashboard

- A {conn.title} tile that updates automatically.
"""

    return body


# ---------------------------------------------------------------------------
# Loading + curating
# ---------------------------------------------------------------------------


def _tier_to_user(raw: str) -> str:
    raw = (raw or "").strip().lower()
    if raw in {"a", "b", "c", "d"}:
        return raw.upper()
    return "C"


def _install_method(raw_install: dict[str, Any], has_hacs: bool, config_flow: bool) -> str:
    """Decide the install method from the YAML's install block.

    Heuristic:

    * ``hacs: true``  → ``hacs`` (operator adds the repo as a HACS
      custom repository).
    * ``config_flow: true`` + has HACS URL or HACS custom repo →
      ``hacs`` (HA-integration style install).
    * ``config_flow: true`` (upstream-only) → ``one_line`` (operator
      runs the RoamCore installer CLI with the feature flag; the
      upstream HA integrations handle their own config_flow).
    * otherwise → ``manual`` (operator wires YAML / packages).
    """

    if has_hacs:
        return "hacs"
    if config_flow:
        # Upstream integrations auto-configure; RoamCore's recipe
        # lands via the installer CLI.
        return "one_line"
    return "manual"


def curate_connection(slug: str, raw: dict[str, Any], src_path: Path | None = None) -> Connection:
    """Parse one YAML into a curated :class:`Connection`."""

    raw_id = str(raw.get("id", slug)).strip()
    name_raw = str(raw.get("name", slug)).strip()
    title = extract_title(name_raw)
    yaml_category = str(raw.get("category", "misc")).strip()
    catalog_category = map_category(yaml_category)
    tier = _tier_to_user(raw.get("tier", "c"))
    status = str(raw.get("status", "beta")).strip()
    desc = str(raw.get("description", "")).strip()
    summary = humanize_summary(desc, title)
    tags = sensible_tags(raw.get("tags") or [], slug, title)
    install_block_raw = raw.get("install") or {}
    hacs = bool(install_block_raw.get("hacs", False)) if isinstance(install_block_raw, dict) else False
    config_flow = bool(install_block_raw.get("config_flow", False)) if isinstance(install_block_raw, dict) else False
    method = _install_method(install_block_raw if isinstance(install_block_raw, dict) else {}, hacs, config_flow)
    hardware = sensible_hardware_defaults(slug, title)

    return Connection(
        slug=slug,
        raw_id=raw_id,
        name_raw=name_raw,
        title=title,
        yaml_category=yaml_category,
        catalog_category=catalog_category,
        tier=tier,
        status=status,
        install_method=method,
        raw_description=desc,
        summary=summary,
        tags=tags,
        additional_hardware=hardware,
        install_instructions=install_block(slug, method),
        needs_curation_review=slug in {
            "mode",
            "demo-mode",
            "advanced-mode",
            "smart-automations",
            "map-dashboard",
            "motion-based-lighting",
            "bluetooth-wifi-presence",
            "hvac-basics",
            "electronic-valves",
            "music-assistant",
            "mqtt",
            "happijac",
            "heated-floors",
            "water-tanks",
            "mock-location-and-tracks",
            "timezone-geolocator",
            "in-cab-tablet-dashboard",
            "agent-actions-allowlist",
            "openclaw-api",
        },
        excluded=False,
        src_path=src_path,
    )


def discover_connections(
    connections_dir: Path,
    excludes: Iterable[str] = (),
) -> tuple[list[Connection], list[tuple[str, Path]]]:
    """Discover + parse every ``connections/*/connection.yml`` under ``connections_dir``.

    Returns ``(curated, skipped)`` where ``skipped`` is a list of
    ``(slug, path)`` tuples for any files that failed to parse.
    """

    excludes = set(excludes)
    curated: list[Connection] = []
    skipped: list[tuple[str, Path]] = []

    if not connections_dir.exists():
        return curated, skipped

    for path in sorted(connections_dir.glob("*/connection.yml")):
        slug = path.parent.name
        try:
            raw = load_yaml(path)
        except Exception as exc:  # noqa: BLE001
            skipped.append((slug, path))
            print(f"  ! could not parse {path}: {exc}")
            continue
        conn = curate_connection(slug, raw, src_path=path)
        if slug in excludes:
            conn.excluded = True
        curated.append(conn)

    return curated, skipped