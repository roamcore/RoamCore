"""RoamCore custom-component unit tests (pytest).

Run:
    cd /home/bernard/clawd/RoamCore
    source .venv/bin/activate
    pytest homeassistant/custom_components/roamcore/tests/ -v

All tests are designed to be runnable WITHOUT a live Home Assistant
instance. Where aiohttp or Home Assistant modules are not available,
tests skip cleanly (so ``check.sh --core-only`` stays green on hosts
without those packages).
"""