"""Shared pytest fixtures + skip markers for connections/openwrt/tests/.

Defines the `requires_aiohttp` marker + `aiohttp_present`
fixture for the integration HTTP probe test. Pattern is
skip-when-missing: tests that require aiohttp are
skipped at collection time if aiohttp is not installed.
"""

from __future__ import annotations

import pytest

try:
    import aiohttp  # noqa: F401
    _AIOHTTP_AVAILABLE = True
except ImportError:
    _AIOHTTP_AVAILABLE = False


def pytest_configure(config: pytest.Config) -> None:
    """Register the `requires_aiohttp` marker."""
    config.addinivalue_line(
        "markers",
        "requires_aiohttp: mark test as requiring aiohttp "
        "(skipped at collection time if aiohttp is not "
        "installed).",
    )


@pytest.fixture
def aiohttp_present() -> bool:
    """Return True iff aiohttp is importable."""
    return _AIOHTTP_AVAILABLE