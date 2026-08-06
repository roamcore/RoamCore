"""Shared helpers for the RoamCore OpenClaw API views.

The `X-RoamCore-Contract` header is the canonical contract-v-bump
canary. Every RoamCore API response emits it (the agent checks the
header BEFORE parsing the body so it can detect a contract bump
before downstream code paths can deserialize incorrectly-shaped data).

The helper `apply_contract_header(response)` mutates an aiohttp
`web.Response` to set the header. It is a no-op if the response is
None (some views return early on the disabled/error path) and
idempotent (safe to call multiple times on the same response).
"""

from __future__ import annotations

from aiohttp import web

from .const import DEFAULT_CONTRACT_VERSION, ROAMCORE_CONTRACT_HEADER


def apply_contract_header(
    response: web.Response | web.StreamResponse,
    version: int = DEFAULT_CONTRACT_VERSION,
) -> web.Response | web.StreamResponse:
    """Set the `X-RoamCore-Contract` header on the response.

    Returns the same response (mutated) for chaining. The header
    must be emitted on every RoamCore API response — the agent
    uses it as the contract-bump canary.
    """
    if response is None:
        return response
    response.headers[ROAMCORE_CONTRACT_HEADER] = str(version)
    return response
