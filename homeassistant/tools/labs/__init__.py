"""RoamCore Labs — share setups/dashboards (local-only).

This package is a *thin* stdlib-only helper that the custom-component
service handlers and the headless CLI scripts both call. The slice
(privacy-by-default) refuses to touch the network: no HTTP, no DNS,
no third-party imports. The CLI surface is intentionally narrow:
``--help`` and ``--dry-run`` plus the bare-minimum inputs.

Slice: Wave 2 #32 — RoamCore Labs (share setups/dashboards)
Tier: b (community-supported)
"""
