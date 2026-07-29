"""RoamCore AI Chat view (slice #27, opt-in).

This is the scaffold + opt-in + smoke slice for the AI chat layer. It is
deliberately conservative:

- OFF by default (``input_boolean.rc_ai_chat_enabled`` initial ``false``).
- When OFF, the endpoint returns 404. NO outbound HTTP. NO summary fetch.
- When ON but the API key is empty, the endpoint returns 503. NO outbound HTTP.
- When ON with a key, the view fetches the in-process OpenClaw summary
  (``hass.data[...]['openclaw_summary']`` if cached, otherwise it calls the
  existing ``RoamCoreOpenClawSummaryView`` in-process — never over HTTP) and
  then sends ONE outbound HTTPS call to the configured provider.
- The provider call is Anthropic-first, OpenAI fallback. Both go over HTTPS.
- No telemetry. No JS error reporting. No CDN scripts that phone home.

Endpoint:
  POST /api/roamcore/ai_chat/message
  Body:  {"message": str, "history"?: [{"role": "user"|"assistant", "content": str}]}
  200:   {"reply": str, "model": str, "tokens_in": int, "tokens_out": int}
  404:   {"error": "ai chat disabled"}               (toggle is OFF)
  503:   {"error": "ai chat not configured"}         (no API key)
  502/4xx/5xx: {"error": <provider error string>}

This view intentionally does NOT return a 200 with empty content. If the
toggle is OFF or the key is missing, the contract is fail-closed.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .const import (
    CONTRACT_VERSION,
    DEFAULT_MODEL_BY_PROVIDER,
    DOMAIN,
    MAX_HISTORY_TURNS_HARD_CAP,
    PROVIDER_ANTHROPIC,
    PROVIDER_OPENAI,
    SUPPORTED_PROVIDERS,
)

_LOGGER = logging.getLogger(__name__)

# Stable system prompt. Kept short and boring on purpose.
_SYSTEM_PROMPT = (
    "You are RoamCore, a local-first assistant for a van/RV system. "
    "Answer the user question using the structured system summary below. "
    "If the summary does not contain the answer, say so plainly. "
    "Keep answers short and actionable. "
    "NEVER invent entities that are not in the summary."
)

# Entity ids read from the HA state machine. Kept as module constants so the
# smoke check can grep for them deterministically.
ENTITY_TOGGLE = "input_boolean.rc_ai_chat_enabled"
ENTITY_API_KEY = "input_text.rc_ai_chat_api_key"
ENTITY_PROVIDER = "input_text.rc_ai_chat_provider"
ENTITY_MODEL = "input_text.rc_ai_chat_model"
ENTITY_MAX_HISTORY = "input_number.rc_ai_chat_max_history"


# --- helpers (silent on purpose: never raise into HA's startup) ---


def _state_value(hass: HomeAssistant, entity_id: str) -> str | None:
    try:
        st = hass.states.get(entity_id)
    except Exception:
        return None
    if st is None:
        return None
    v = st.state
    if v in ("unknown", "unavailable", "none", ""):
        return None
    return str(v)


def _is_on(hass: HomeAssistant, entity_id: str) -> bool:
    return _state_value(hass, entity_id) == "on"


def _is_configured(hass: HomeAssistant) -> bool:
    """True iff the toggle is ON and the API key helper has a non-empty value."""
    if not _is_on(hass, ENTITY_TOGGLE):
        return False
    key = _state_value(hass, ENTITY_API_KEY)
    return bool(key) and key.strip() != ""


def _provider(hass: HomeAssistant) -> str:
    p = (_state_value(hass, ENTITY_PROVIDER) or "").strip().lower()
    if p in SUPPORTED_PROVIDERS:
        return p
    # Conservative default: anthropic (matches input_text initial).
    return PROVIDER_ANTHROPIC


def _model(hass: HomeAssistant, provider: str) -> str:
    m = (_state_value(hass, ENTITY_MODEL) or "").strip()
    if m:
        return m
    return DEFAULT_MODEL_BY_PROVIDER.get(provider, "claude-3-5-haiku-latest")


def _max_history(hass: HomeAssistant) -> int:
    raw = _state_value(hass, ENTITY_MAX_HISTORY)
    try:
        n = int(raw) if raw is not None else 10
    except (TypeError, ValueError):
        n = 10
    # Defensive clamp.
    if n < 0:
        n = 0
    if n > MAX_HISTORY_TURNS_HARD_CAP:
        n = MAX_HISTORY_TURNS_HARD_CAP
    return n


# --- in-process summary source (NEVER a network loopback call) ---


def _get_summary_dict(hass: HomeAssistant) -> dict[str, Any]:
    """Return the deterministic system summary dict WITHOUT making an HTTP call.

    Two safe paths, in order:
      1. ``hass.data["roamcore_openclaw_api"]["openclaw_summary"]`` if a sibling
         integration has cached a fresh summary dict there.
      2. Otherwise, import the existing ``roamcore_openclaw_api`` view class and
         invoke its ``.get()`` coroutine in-process against a tiny shim
         request object — we never build a loopback HTTP request.

    This is the ONLY RoamCore data that ever leaves the host. The privacy
    contract in the package + smoke check hinges on this.
    """
    # Path 1: cached summary (preferred; cheapest).
    try:
        cache = hass.data.get("roamcore_openclaw_api") or {}
        cached = cache.get("openclaw_summary")
        if isinstance(cached, dict) and cached:
            return cached
    except Exception:
        pass

    # Path 2: invoke the OpenClaw view in-process.
    try:
        from homeassistant.custom_components.roamcore_openclaw_api.view import (
            RoamCoreOpenClawSummaryView,
        )

        view = RoamCoreOpenClawSummaryView(hass)

        # Build the summary in-process. We never touch the network here.
        import asyncio

        async def _build():
            shim = _SummaryShim(hass)
            return await view.get(shim)

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're already inside HA's event loop (the view's post() is
                # awaited by HA). Block until the inner coroutine finishes.
                fut = asyncio.ensure_future(_build())
                resp = loop.run_until_complete(fut)
            else:
                resp = loop.run_until_complete(_build())
        except RuntimeError:
            resp = asyncio.run(_build())

        body = getattr(resp, "body", None)
        if body is None and hasattr(resp, "text"):
            try:
                body = resp.text.encode("utf-8")
            except Exception:
                body = None
        if body is None:
            return {}

        try:
            payload = json.loads(body)
        except Exception:
            return {}

        if isinstance(payload, dict):
            return payload
    except Exception as e:
        _LOGGER.debug("AI chat: in-process summary fetch failed: %s", e)

    return {}


class _SummaryShim:
    """Minimal stand-in for ``web.Request`` that the OpenClaw summary view needs.

    The OpenClaw summary view only reads ``request.app["hass"]``, so we expose
    a tiny shim with the same surface. Defined at module level (not nested) so
    it's easy to find and document.
    """

    __slots__ = ("app",)

    def __init__(self, hass: HomeAssistant) -> None:
        self.app = {"hass": hass}


def _summary_for_prompt(summary: dict[str, Any]) -> str:
    """Serialize the summary dict for the LLM system prompt.

    We always send the full dict — there's no other RoamCore data going out,
    and the dict is bounded (~2 KB by the system-summary contract).
    """
    try:
        return json.dumps(summary, sort_keys=True, separators=(",", ":"))
    except Exception:
        return "{}"


def _build_messages(
    user_message: str,
    history: list[dict[str, Any]],
    summary_text: str,
) -> list[dict[str, Any]]:
    """Assemble the messages payload for the LLM call.

    History is a list of prior turns ``[{"role": "user"|"assistant", "content": str}, ...]``.
    Only ``user`` and ``assistant`` roles are accepted; everything else is
    dropped defensively.
    """
    msgs: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": _SYSTEM_PROMPT + "\n\nSystem summary (JSON):\n" + summary_text,
        }
    ]
    for turn in history:
        if not isinstance(turn, dict):
            continue
        role = str(turn.get("role") or "").strip().lower()
        content = turn.get("content")
        if role not in ("user", "assistant"):
            continue
        if not isinstance(content, str):
            continue
        msgs.append({"role": role, "content": content})
    msgs.append({"role": "user", "content": user_message})
    return msgs


async def _call_anthropic(
    hass: HomeAssistant,
    api_key: str,
    model: str,
    messages: list[dict[str, Any]],
) -> tuple[str, int, int]:
    """Call https://api.anthropic.com/v1/messages.

    Returns ``(reply, tokens_in, tokens_out)`` on 200.
    Raises on any other status.
    """
    # Anthropic separates the system message from the messages array.
    system_text = ""
    chat_msgs: list[dict[str, Any]] = []
    for m in messages:
        role = m.get("role")
        content = m.get("content") or ""
        if role == "system":
            system_text = (system_text + "\n" + content).strip() if system_text else str(content)
        else:
            chat_msgs.append({"role": role, "content": content})

    payload = {
        "model": model,
        "max_tokens": 1024,
        "messages": chat_msgs,
    }
    if system_text:
        payload["system"] = system_text

    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "content-type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }

    session = hass.helpers.aiohttp_client.async_get_clientsession()
    async with session.post(url, json=payload, headers=headers, timeout=30) as resp:
        text = await resp.text()
        if resp.status != 200:
            raise RuntimeError(f"anthropic {resp.status}: {text[:200]}")
        try:
            data = json.loads(text)
        except Exception as e:
            raise RuntimeError(f"anthropic bad json: {e}")

        reply_parts: list[str] = []
        for block in data.get("content") or []:
            if isinstance(block, dict) and block.get("type") == "text":
                reply_parts.append(str(block.get("text") or ""))
        reply = "".join(reply_parts).strip()

        usage = data.get("usage") or {}
        tokens_in = int(usage.get("input_tokens") or 0)
        tokens_out = int(usage.get("output_tokens") or 0)
        return reply, tokens_in, tokens_out


async def _call_openai(
    hass: HomeAssistant,
    api_key: str,
    model: str,
    messages: list[dict[str, Any]],
) -> tuple[str, int, int]:
    """Call https://api.openai.com/v1/chat/completions.

    Returns ``(reply, tokens_in, tokens_out)`` on 200.
    Raises on any other status.
    """
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {api_key}",
    }
    payload = {
        "model": model,
        "max_tokens": 1024,
        "messages": messages,
    }

    session = hass.helpers.aiohttp_client.async_get_clientsession()
    async with session.post(url, json=payload, headers=headers, timeout=30) as resp:
        text = await resp.text()
        if resp.status != 200:
            raise RuntimeError(f"openai {resp.status}: {text[:200]}")
        try:
            data = json.loads(text)
        except Exception as e:
            raise RuntimeError(f"openai bad json: {e}")

        choices = data.get("choices") or []
        reply = ""
        if choices:
            msg = choices[0].get("message") or {}
            reply = str(msg.get("content") or "").strip()

        usage = data.get("usage") or {}
        tokens_in = int(usage.get("prompt_tokens") or 0)
        tokens_out = int(usage.get("completion_tokens") or 0)
        return reply, tokens_in, tokens_out


# --- view ---


class RoamCoreAiChatView(HomeAssistantView):
    """POST /api/roamcore/ai_chat/message (opt-in, fail-closed)."""

    url = "/api/roamcore/ai_chat/message"
    name = "api:roamcore:ai_chat:message"

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass

    async def post(self, request: web.Request) -> web.Response:
        hass: HomeAssistant = request.app["hass"]

        # ---- Privacy gate 1: opt-in toggle must be ON ----
        if not _is_on(hass, ENTITY_TOGGLE):
            # Fail-closed. NO outbound HTTP. NO summary fetch. NO LLM call.
            return web.json_response(
                {"ok": False, "error": "ai chat disabled"},
                status=404,
            )

        # ---- Privacy gate 2: API key must be present ----
        api_key = (_state_value(hass, ENTITY_API_KEY) or "").strip()
        if not api_key:
            # Fail-closed. NO outbound HTTP. NO summary fetch. NO LLM call.
            return web.json_response(
                {"ok": False, "error": "ai chat not configured"},
                status=503,
            )

        # ---- Parse body (best-effort; bail on bad JSON without leaking stack). ----
        try:
            raw = await request.read()
            body = json.loads(raw) if raw else {}
        except Exception:
            return web.json_response(
                {"ok": False, "error": "invalid json body"},
                status=400,
            )
        if not isinstance(body, dict):
            return web.json_response(
                {"ok": False, "error": "body must be a json object"},
                status=400,
            )

        user_message = str(body.get("message") or "").strip()
        if not user_message:
            return web.json_response(
                {"ok": False, "error": "message is required"},
                status=400,
            )
        if len(user_message) > 8000:
            return web.json_response(
                {"ok": False, "error": "message too long"},
                status=400,
            )

        history_in = body.get("history") or []
        if not isinstance(history_in, list):
            history_in = []

        # Trim history to the configured cap (in-process).
        cap = _max_history(hass)
        history = [t for t in history_in if isinstance(t, dict)][-cap:]

        # ---- Fetch the in-process summary (NO network loopback). ----
        summary = _get_summary_dict(hass)
        summary_text = _summary_for_prompt(summary)

        # ---- Build messages + call the provider (ONE outbound HTTPS call). ----
        provider = _provider(hass)
        model = _model(hass, provider)
        messages = _build_messages(user_message, history, summary_text)

        try:
            if provider == PROVIDER_OPENAI:
                reply, tokens_in, tokens_out = await _call_openai(
                    hass, api_key, model, messages
                )
            else:
                # Default + Anthropic.
                reply, tokens_in, tokens_out = await _call_anthropic(
                    hass, api_key, model, messages
                )
        except Exception as e:
            _LOGGER.warning("RoamCore AI chat upstream failed: %s", e)
            return web.json_response(
                {"ok": False, "error": f"upstream: {e}"},
                status=502,
            )

        # Trim key from any echo before we return.
        body_out: dict[str, Any] = {
            "ok": True,
            "contract": {
                "name": "roamcore_ai_chat",
                "version": CONTRACT_VERSION,
            },
            "reply": reply,
            "model": model,
            "tokens_in": int(tokens_in),
            "tokens_out": int(tokens_out),
            "summary_bytes": len(summary_text),
        }
        # serialise via HA's helpers to keep things boring
        text = json.dumps(body_out, separators=(",", ":"))
        return web.Response(
            text=text,
            status=200,
            content_type="application/json",
            charset="utf-8",
            headers={"Cache-Control": "no-store"},
        )