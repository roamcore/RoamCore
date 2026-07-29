"""Tests for scripts/audit_connections.py.

These run as part of `python -m pytest scripts/tests/` and verify the
audit behaves correctly on both happy-path and adversarial inputs.

Run locally:
    cd scripts && python -m pytest tests/test_audit_connections.py -v
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "audit_connections.py"


def _run_audit(workspace: Path, *args: str) -> subprocess.CompletedProcess:
    """Run audit_connections.py against an isolated workspace."""
    # Symlink the script rather than copying so we test the real one
    script_dst = workspace / "audit_connections.py"
    if script_dst.exists() or script_dst.is_symlink():
        script_dst.unlink()
    script_dst.symlink_to(SCRIPT)
    return subprocess.run(
        [sys.executable, "audit_connections.py", "--root", str(workspace), *args],
        cwd=workspace,
        capture_output=True,
        text=True,
    )


def _make_workspace(tmp_path: Path, name: str = "connections") -> Path:
    """Build an isolated workspace that mirrors the real repo layout:
    ws/connections/_schema/connection.schema.json + ws/docs/{catalog,connections}/.
    The script's --root flag points at ws so it ignores the real repo.
    """
    ws = tmp_path / "ws"
    ws.mkdir()
    # Layout the script expects
    (ws / name).mkdir()
    (ws / name / "_schema").mkdir()
    (ws / name / "_schema" / "connection.schema.json").write_bytes(
        (REPO / "connections" / "_schema" / "connection.schema.json").read_bytes()
    )
    (ws / "docs" / "catalog").mkdir(parents=True)
    (ws / "docs" / "connections").mkdir(parents=True)
    return ws


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    return _make_workspace(tmp_path)


def _valid_a_tier_manifest() -> str:
    return """
id: test-connection
name: Test Connection
tier: a
category: power
status: shipped
version: 1.0.0
description: A valid tier-a manifest for testing.
wizard:
  connection_kind: mqtt
  one_tap: true
install:
  ha_integration_domain: test
  config_flow: true
tests:
  - tests/test_x.py
tier_requirements:
  - working_config_flow
  - integration_test_passes
  - no_manual_yaml_required
"""


def test_empty_workspace_passes(workspace: Path) -> None:
    result = _run_audit(workspace)  # without --quiet so the 'audit clean' line shows
    assert result.returncode == 0, result.stdout + result.stderr
    assert "audit clean" in result.stdout


def test_valid_tier_a_passes(workspace: Path) -> None:
    (workspace / "connections" / "test-connection").mkdir()
    (workspace / "connections" / "test-connection" / "connection.yml").write_text(
        _valid_a_tier_manifest()
    )
    # Create the test file so the audit doesn't warn
    (workspace / "connections" / "test-connection" / "tests").mkdir()
    (workspace / "connections" / "test-connection" / "tests" / "test_x.py").write_text("# test")
    result = _run_audit(workspace)
    assert result.returncode == 0, result.stdout + result.stderr
    # Registry should be written
    reg = json.loads((workspace / "connections" / "registry.json").read_text())
    assert reg["count"] == 1
    assert reg["connections"][0]["id"] == "test-connection"


def test_tier_a_without_config_flow_fails(workspace: Path) -> None:
    bad = _valid_a_tier_manifest().replace("config_flow: true", "config_flow: false")
    (workspace / "connections" / "test-connection").mkdir()
    (workspace / "connections" / "test-connection" / "connection.yml").write_text(bad)
    result = _run_audit(workspace)
    assert result.returncode == 1
    assert "config_flow" in result.stdout.lower()


def test_tier_a_without_one_tap_fails(workspace: Path) -> None:
    bad = _valid_a_tier_manifest().replace("one_tap: true", "one_tap: false")
    (workspace / "connections" / "test-connection").mkdir()
    (workspace / "connections" / "test-connection" / "connection.yml").write_text(bad)
    result = _run_audit(workspace)
    assert result.returncode == 1
    assert "one_tap" in result.stdout.lower()


def test_tier_a_without_tests_fails(workspace: Path) -> None:
    bad = "\n".join(
        line for line in _valid_a_tier_manifest().splitlines()
        if not line.startswith("  - tests/")
    )
    (workspace / "connections" / "test-connection").mkdir()
    (workspace / "connections" / "test-connection" / "connection.yml").write_text(bad)
    result = _run_audit(workspace)
    assert result.returncode == 1
    assert "tests" in result.stdout.lower()


def test_id_must_match_folder_name(workspace: Path) -> None:
    (workspace / "connections" / "wrong-folder").mkdir()
    (workspace / "connections" / "wrong-folder" / "connection.yml").write_text(
        _valid_a_tier_manifest().replace("id: test-connection", "id: not-the-same")
    )
    result = _run_audit(workspace)
    assert result.returncode == 1
    assert "does not match folder name" in result.stdout


def test_invalid_yaml_fails(workspace: Path) -> None:
    (workspace / "connections" / "broken").mkdir()
    (workspace / "connections" / "broken" / "connection.yml").write_text(
        "id: broken\nname: [unclosed"
    )
    result = _run_audit(workspace)
    assert result.returncode == 1
    assert "yaml" in result.stdout.lower()


def test_tier_b_requires_docs_recipe_published(workspace: Path) -> None:
    bad = _valid_a_tier_manifest().replace("tier: a", "tier: b")
    bad = bad.replace("one_tap: true", "one_tap: false")
    bad = bad.replace("config_flow: true", "config_flow: false")
    bad = bad.replace(
        "  - working_config_flow\n  - integration_test_passes\n  - no_manual_yaml_required",
        "  - integration_test_passes",
    )
    (workspace / "connections" / "test-connection").mkdir()
    (workspace / "connections" / "test-connection" / "connection.yml").write_text(bad)
    result = _run_audit(workspace)
    assert result.returncode == 1
    assert "docs_recipe_published" in result.stdout


def test_registry_only_contains_valid_manifests(workspace: Path) -> None:
    """Invalid manifests must NOT appear in registry.json."""
    # Good one
    (workspace / "connections" / "good").mkdir()
    (workspace / "connections" / "good" / "connection.yml").write_text(
        _valid_a_tier_manifest().replace("id: test-connection", "id: good")
    )
    (workspace / "connections" / "good" / "tests").mkdir()
    (workspace / "connections" / "good" / "tests" / "t.py").write_text("#")
    # Bad one
    bad = _valid_a_tier_manifest().replace("id: test-connection", "id: bad")
    bad = bad.replace("config_flow: true", "config_flow: false")
    (workspace / "connections" / "bad").mkdir()
    (workspace / "connections" / "bad" / "connection.yml").write_text(bad)

    result = _run_audit(workspace)
    assert result.returncode == 1  # bad one fails the audit
    reg = json.loads((workspace / "connections" / "registry.json").read_text())
    ids = {c["id"] for c in reg["connections"]}
    assert "good" in ids
    assert "bad" not in ids
