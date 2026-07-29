# RoamCore AI Chat (opt-in; API/Auth based)

The RoamCore AI Chat is a small, **opt-in** chat layer that consumes the
deterministic `/api/roamcore/system/summary` contract and produces a
plain-language answer using a cloud AI provider you choose (Anthropic or
OpenAI). It is the boring, conservative counterpart to "agents" — there is
no agent, no tool calls, and no actions. It only reads.

This is **slice #27 (first slice: scaffold + opt-in + smoke)**. The UX
polish (rich history, token usage display, streaming, voice) lands in
later slices.

## Hard privacy contract

1. `input_boolean.rc_ai_chat_enabled` defaults to **OFF**. Opt-in only.
2. When OFF, `POST /api/roamcore/ai_chat/message` returns **404**
   (`{"error": "ai chat disabled"}`). **No outbound HTTP. No LLM call.
   No summary fetch.**
3. When ON but `input_text.rc_ai_chat_api_key` is empty, the view returns
   **503** (`{"error": "ai chat not configured"}`). **No outbound HTTP.**
4. When ON with a key, the view fetches the **in-process** OpenClaw summary
   (never over the network) and sends **one** outbound HTTPS call to the
   configured provider. No other outbound calls. No telemetry. No analytics.
   No CDN scripts that phone home.
5. The system summary is the **only** RoamCore data sent to the LLM. No raw
   sensor history, no entity IDs outside the summary, no PII outside the
   summary.
6. Clearing the toggle stops all external calls within seconds (the gate
   is checked at request time, not at HA startup).

These rules are enforced statically by
`scripts/checks/ai-chat-smoke.sh`.

## Endpoint

```
POST /api/roamcore/ai_chat/message
```

Auth: standard Home Assistant bearer token / cookie.

Request body:

```json
{
  "message": "Do I have enough battery to run the heater tonight?",
  "history": [
    {"role": "user", "content": "Earlier question"},
    {"role": "assistant", "content": "Earlier answer"}
  ]
}
```

`history` is optional. It is capped at `input_number.rc_ai_chat_max_history`
turns (default 10, max 50).

Responses:

| Status | Body | Meaning |
| ------ | ---- | ------- |
| 200 | `{"ok": true, "reply": "...", "model": "...", "tokens_in": 12, "tokens_out": 87, "summary_bytes": 1842}` | OK |
| 400 | `{"ok": false, "error": "..."}` | Bad request (missing/empty/long message, bad JSON) |
| 404 | `{"ok": false, "error": "ai chat disabled"}` | Toggle is OFF |
| 503 | `{"ok": false, "error": "ai chat not configured"}` | Toggle is ON but API key is empty |
| 502 | `{"ok": false, "error": "upstream: <provider error>"}` | Provider call failed |

## Setup

1. Make sure the RoamCore packages are loaded (`!include_dir_named packages`).
   The new package `homeassistant/packages/roamcore_ai_chat.yaml` ships
   the input helpers it needs — no manual Helper creation required.
2. (Optional) Set the provider and model:

   - `input_text.rc_ai_chat_provider` → `anthropic` (default) or `openai`
   - `input_text.rc_ai_chat_model` → e.g. `claude-3-5-haiku-latest`
     (default) or `gpt-4o-mini`

3. Set `input_text.rc_ai_chat_api_key` to your provider's API key.
4. Turn the toggle **on**: `input_boolean.rc_ai_chat_enabled`.
5. Open the RoamCore dashboard → **AI Chat** page (or add a
   `custom:roamcore-ai-chat` Lovelace card).

That's it. Flipping the toggle off again makes the endpoint return 404
immediately.

## UI

The bundled card (`homeassistant/www/roamcore/roamcore-ai-chat.js`) renders
the privacy banner, the enable/setup instructions, and the chat log. The
card **never reaches the network itself** when the toggle is OFF — it
mirrors the entity state to decide which state to show.

## Provider notes

- **Anthropic** is the default. Endpoint:
  `https://api.anthropic.com/v1/messages` with header
  `x-api-key: <key>` and `anthropic-version: 2023-06-01`.
- **OpenAI** fallback. Endpoint:
  `https://api.openai.com/v1/chat/completions` with header
  `authorization: Bearer <key>`.

Both calls use `max_tokens: 1024`. We never retry; failures bubble back as
`502 upstream: <message>`.

## Troubleshooting

- **AI Chat is OFF** banner — toggle `input_boolean.rc_ai_chat_enabled` ON.
- **AI chat is on but no API key is set** — set
  `input_text.rc_ai_chat_api_key`. The view returns 503 until you do.
- **`upstream: anthropic 401 …`** — bad/expired API key, or the key was
  set in the wrong helper. Double-check `input_text.rc_ai_chat_api_key`.
- **`upstream: anthropic 429 …`** — provider rate-limit. Wait and retry, or
  pick a different model.
- **Empty reply** — provider returned no `text` block. Try again or switch
  provider/model.

## Rollback

This slice ships a single integration + one package + one card. To roll
back:

- Close PR #30 (the slice PR).
- Or, after merge: `git revert <merge-sha>`.

There is no HA-side state that needs cleaning up beyond removing the
package file.

## What this slice deliberately does NOT include

- No streaming responses (UI would need a different shape).
- No tool calls / agent actions (those belong to the Agent Actions
  Allowlist, which is a separate slice).
- No persistence of the chat history across reloads (memory is in-process
  only; the server forgets on restart).
- No provider abstraction beyond Anthropic + OpenAI.

These land in later slices.