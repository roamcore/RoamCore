"""Constants for the RoamCore AI Chat integration."""

DOMAIN = "roamcore_ai_chat"

# Bump ONLY on breaking schema changes. UI + agents rely on this number.
CONTRACT_VERSION = "1.0.0"

# Provider ids supported by the slice-1 view. Keep this boring + lowercase.
PROVIDER_ANTHROPIC = "anthropic"
PROVIDER_OPENAI = "openai"

SUPPORTED_PROVIDERS = (PROVIDER_ANTHROPIC, PROVIDER_OPENAI)

# Default model per provider (used when input_text.rc_ai_chat_model is empty
# or matches the provider-default placeholder).
DEFAULT_MODEL_BY_PROVIDER = {
    PROVIDER_ANTHROPIC: "claude-3-5-haiku-latest",
    PROVIDER_OPENAI: "gpt-4o-mini",
}

# Hard cap on the number of history turns we accept per request (defensive).
MAX_HISTORY_TURNS_HARD_CAP = 50

# Endpoint path. Keep stable; UI + agents depend on it.
URL_PATH = "/api/roamcore/ai_chat/message"