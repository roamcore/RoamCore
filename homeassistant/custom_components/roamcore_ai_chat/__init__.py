"""RoamCore AI Chat (opt-in) — integration entrypoint.

Slice #27 — scaffold + opt-in + smoke.

Endpoint (POST):
  /api/roamcore/ai_chat/message

Privacy contract (enforced here + in ``view.py``):
  - When ``input_boolean.rc_ai_chat_enabled`` is OFF, the view returns 404.
  - When ON but ``input_text.rc_ai_chat_api_key`` is empty, the view returns 503.
  - When ON with a key, the view fetches the in-process OpenClaw summary
    and sends ONE outbound HTTPS call to the configured provider.
  - No telemetry. No analytics. No CDN scripts that phone home.
"""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .view import RoamCoreAiChatView


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the integration from configuration.yaml.

    The view is always registered; gating happens inside the view at request
    time so users can flip the toggle without restarting Home Assistant.
    """
    hass.http.register_view(RoamCoreAiChatView(hass))
    return True