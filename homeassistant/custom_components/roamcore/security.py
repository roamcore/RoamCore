"""RoamCore-owned service handler for the Security Review surface.

Phase 7 — Wave 9 #123.c Security Review slice.

This module is the canonical umbrella for the security-review surface.
It exposes three stdlib-only Python classes (no HA imports required)
that the helper package at
`homeassistant/packages/roamcore_security_review.yaml` + the pytest rig
at `homeassistant/packages/tests/test_security_review.py` + the bash
smoke at `scripts/checks/security-review-smoke.sh` can call:

  - `RCApiTokenManager` — rotate + age the `RC_API_TOKEN`
    (the OpenClaw agent interface token) with backup-before-mutate
    discipline (writes a backup to
    `/config/.storage/.roamcore_security_backup.jsonl` BEFORE
    rotating the token, then updates
    `/config/.storage/roamcore_security.json` with
    `{last_rotation_at, last_rotation_reason, rotation_count}`).

  - `SSHAuditReader` — read-only audit of `/etc/ssh/sshd_config`
    (parses `PasswordAuthentication` + `PermitRootLogin` +
    `PubkeyAuthentication` + `Port` + `PermitEmptyPasswords`,
    then surfaces plain-English warnings like "Your SSH allows
    password login — switch to keys for safety" via
    `find_risky_settings()`).

  - `FirewallAuditReader` — read-only audit of `/etc/nftables.conf`
    + `iptables-save` output (parses both nft + iptables rule
    lists, then surfaces plain-English warnings like
    "Port 22 (SSH) is open to the whole internet — restrict to
    your IP range" via `find_risky_rules()`).

The service handler is bench-tested by the pytest rig at
`homeassistant/packages/tests/test_security_review.py` (20 tests
covering the 3 services + the 4 helper entities + the 4 template
sensors + the 4 §8 MANDATORY automations + the rc-entity-naming
compliance + the idempotency guarantees + the secrets-leak guard).
The bash smoke at `scripts/checks/security-review-smoke.sh`
enforces 10 cross-cutting YAML / secrets-leak / idempotency
assertions.

Anti-patterns avoided:
  - No hardcoded URLs, no hardcoded passwords, no
    `/home/<user>` paths (the secrets-leak guard is real;
    see `test_secrets_leak_guard` in the pytest rig).
  - No HA imports in the core class bodies — stdlib only so
    the pytest rig can import the module without spinning up
    HA (the bench test mocks the .storage/ files + the
    sshd_config + the nft files).
  - SSH + firewall audit is READ-ONLY by design — no
    mutation of `/etc/ssh/sshd_config` or
    `/etc/nftables.conf` from this module (the audit
    surfaces plain-English warnings; the operator decides
    what to do with them).
  - RC_API_TOKEN rotation writes the backup BEFORE
    updating .storage/ — backup-before-mutate discipline
    (verified by the `test_rotate_writes_backup_before_updating`
    pytest).
  - Idempotent: re-running `rotate_token()` reuses the
    backup file (does NOT overwrite the previous backup
    unless the caller explicitly passes `force=True`).

Plain-English philosophy (per Bernard 2026-08-04):
  - "Your access codes are 95 days old — rotate soon"
    NOT "Token age > 90d threshold violated".
  - "Your SSH config allows password login — switch to keys"
    NOT "PasswordAuthentication yes".
  - "Port 22 (SSH) is open to the whole internet — restrict
    to your IP range" NOT "INPUT ACCEPT tcp dport 22".

Vendor-neutral: the SSH + firewall audit is file-based (no
specific firewall / SSH server implementation) — it works
with any nft / iptables / sshd setup.
"""

from __future__ import annotations

import json
import os
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Optional


# ---------------------------------------------------------------------------
# Module-level constants — exported for the audit + the helper package +
# the pytest rig + the bash smoke.
# ---------------------------------------------------------------------------

SECURITY_TILE_PREFIX = "rc_security_review_"

# Default storage paths (overridable via constructor for testing).
DEFAULT_STORAGE_PATH = "/config/.storage/roamcore_security.json"
DEFAULT_BACKUP_PATH = "/config/.storage/.roamcore_security_backup.jsonl"

# Default file paths for the SSH + firewall audit (overridable).
DEFAULT_SSHD_CONFIG_PATH = "/etc/ssh/sshd_config"
DEFAULT_NFTABLES_PATH = "/etc/nftables.conf"
DEFAULT_IPTABLES_SAVE_PATH = "/etc/iptables.save"

# Token rotation policy (RC_API_TOKEN should be rotated every 90 days).
TOKEN_ROTATION_THRESHOLD_DAYS = 90
TOKEN_ROTATION_WARN_DAYS = 75  # Warn at 75 days (2 weeks before threshold).

# Status codes (mapped to plain-English via `plain_english_status`).
STATUS_SECURE = "secure"
STATUS_NEEDS_ROTATION = "needs_rotation"
STATUS_SSH_RISK = "ssh_risk"
STATUS_FIREWALL_RISK = "firewall_risk"
STATUS_UNKNOWN = "unknown"

# Plain-English strings surfaced on the dashboard tile + in OpenClaw
# queries. Each entry is keyed by status_code.
_PLAIN_ENGLISH = {
    STATUS_SECURE: "Your van is locked down — access codes fresh, SSH key-only, firewall tight.",
    STATUS_NEEDS_ROTATION: (
        "Your access codes are {age_days} days old — rotate soon "
        "(RoamCore will do it automatically when they hit {threshold} days)."
    ),
    STATUS_SSH_RISK: (
        "Your SSH settings aren't locked down: {ssh_warnings}. "
        "Check the runbook for the safe settings."
    ),
    STATUS_FIREWALL_RISK: (
        "Your firewall has open doors: {firewall_warnings}. "
        "Check the runbook for the recommended rules."
    ),
    STATUS_UNKNOWN: "Security review hasn't run yet — check back tomorrow.",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc_now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _coerce_int(value: Any, default: int = 0) -> int:
    """Best-effort int coercion (HA service-call fields arrive as str)."""
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def plain_english_status(
    status_code: str,
    *,
    age_days: Optional[int] = None,
    ssh_warnings: Optional[Iterable[str]] = None,
    firewall_warnings: Optional[Iterable[str]] = None,
) -> str:
    """Map a status code (+ optional context) to a plain-English string.

    The dashboard tile + the OpenClaw query response surface this string
    verbatim. The status mapper prefers plain-English over raw codes —
    per the Bernard 2026-08-04 doctrine ("Token age > 90d threshold
    violated" → "Your access codes are 95 days old — rotate soon").
    """
    template = _PLAIN_ENGLISH.get(status_code, _PLAIN_ENGLISH[STATUS_UNKNOWN])
    ssh_warnings_list = list(ssh_warnings) if ssh_warnings else []
    firewall_warnings_list = list(firewall_warnings) if firewall_warnings else []
    ssh_warnings_str = "; ".join(ssh_warnings_list) if ssh_warnings_list else "none"
    firewall_warnings_str = (
        "; ".join(firewall_warnings_list) if firewall_warnings_list else "none"
    )
    return template.format(
        age_days=age_days if age_days is not None else "?",
        threshold=TOKEN_ROTATION_THRESHOLD_DAYS,
        ssh_warnings=ssh_warnings_str,
        firewall_warnings=firewall_warnings_str,
    )


def _generate_token() -> str:
    """Generate a fresh 32-byte URL-safe token (256 bits of entropy)."""
    return secrets.token_urlsafe(32)


def _read_json_file(path: str) -> dict:
    """Read a JSON file from disk; return {} if the file doesn't exist or
    is unparseable (best-effort — the security review must not block the
    operator if the .storage/ file is missing).
    """
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        return data
    except (OSError, json.JSONDecodeError):
        return {}


def _write_json_atomic(path: str, data: dict) -> None:
    """Write a JSON file atomically (write to .tmp + os.replace).

    Atomic writes protect against partial writes if the Hub crashes
    mid-rotation. The audit + the helper package + the pytest rig all
    depend on .storage/ files being either fully-written or absent —
    never partially-written.
    """
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    os.replace(tmp_path, path)


def _append_backup_record(backup_path: str, record: dict) -> None:
    """Append a single record to the JSONL backup file.

    JSONL (one JSON object per line) is used because it's append-only
    + append-friendly — no need to read + rewrite the whole file on
    every rotation. The audit can parse the backup file to recover any
    historical state without losing previous rotations.
    """
    directory = os.path.dirname(backup_path) or "."
    os.makedirs(directory, exist_ok=True)
    with open(backup_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")


# ---------------------------------------------------------------------------
# RCApiTokenManager — rotates + ages the RC_API_TOKEN (the OpenClaw agent
# interface token).
# ---------------------------------------------------------------------------


@dataclass
class TokenRecord:
    """Lightweight in-memory representation of a token rotation record."""

    token: str
    last_rotation_at: str
    last_rotation_reason: str
    rotation_count: int


class RCApiTokenManager:
    """Manages the RC_API_TOKEN rotation lifecycle.

    The .storage/ file (`roamcore_security.json`) is the canonical
    runtime location. The backup file (`.roamcore_security_backup.jsonl`)
    is the canonical recovery location — every successful rotation
    appends a record BEFORE updating the .storage/ file.

    Backup-before-mutate discipline:
      - `rotate_token(reason)` first appends the CURRENT state to
        the backup file (so the operator can roll back if needed),
        THEN updates the .storage/ file with the NEW state.
      - The audit + the helper package + the pytest rig all assert
        this order via `test_rotate_writes_backup_before_updating`.

    Idempotency:
      - `rotate_token(reason, force=False)` reuses the backup file
        if the caller has not explicitly requested a force rotation
        (i.e., repeated rotations append to the same backup file
        instead of overwriting it).
      - The .storage/ file is updated atomically (write to .tmp +
        os.replace), so a crash mid-rotation leaves the previous
        token in place.
    """

    def __init__(
        self,
        storage_path: str = DEFAULT_STORAGE_PATH,
        backup_path: str = DEFAULT_BACKUP_PATH,
        threshold_days: int = TOKEN_ROTATION_THRESHOLD_DAYS,
    ) -> None:
        self.storage_path = storage_path
        self.backup_path = backup_path
        self.threshold_days = threshold_days

    # -- Public API --------------------------------------------------------

    def read_state(self) -> dict:
        """Read the current state from the .storage/ file.

        Returns an empty dict if the file is missing or unparseable —
        the operator hasn't rotated yet (rotation_count=0,
        last_rotation_at=None).
        """
        return _read_json_file(self.storage_path)

    def read_token_age_days(self) -> int:
        """Return the age of the current token in whole days.

        Returns -1 if the token has never been rotated
        (`last_rotation_at` is missing).
        Returns 0 if the token was rotated today.
        """
        state = self.read_state()
        last_rotation = state.get("last_rotation_at")
        if not last_rotation:
            return -1
        try:
            rotated_at = datetime.fromisoformat(last_rotation)
        except (TypeError, ValueError):
            return -1
        if rotated_at.tzinfo is None:
            rotated_at = rotated_at.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = now - rotated_at
        return max(0, int(delta.total_seconds() // 86400))

    def backup_exists(self) -> bool:
        """Return True if the backup file exists AND is parseable.

        The audit + the pytest rig both check this — if the backup
        file is missing or corrupt, the rotation history is at risk.
        """
        if not os.path.isfile(self.backup_path):
            return False
        try:
            with open(self.backup_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    json.loads(line)
            return True
        except (OSError, json.JSONDecodeError):
            return False

    def rotate_token(
        self,
        reason: str = "manual",
        *,
        force: bool = False,
    ) -> TokenRecord:
        """Rotate the RC_API_TOKEN.

        Backup-before-mutate:
          1. Read the current state from .storage/.
          2. Append the CURRENT state to the backup file
             (with timestamp + reason + previous rotation_count).
          3. Generate a new token.
          4. Update .storage/ with the NEW state
             (last_rotation_at + last_rotation_reason +
              rotation_count + previous_token for rollback).

        Idempotency: when `force=False`, the rotation reuses the backup
        file (appends) instead of overwriting it. The audit + the pytest
        rig + the bash smoke all verify the backup-before-mutate order.

        Returns:
            A TokenRecord with the new token + the updated metadata.

        Raises:
            OSError: if the .storage/ directory cannot be created or
                the backup file cannot be written.
        """
        current_state = self.read_state()
        rotation_count = _coerce_int(current_state.get("rotation_count"), 0)
        previous_token = current_state.get("token")
        rotated_at = _utc_now_iso()

        # Step 1: write backup BEFORE rotating.
        backup_record = {
            "rotated_at": rotated_at,
            "reason": reason,
            "previous_token": previous_token,
            "previous_rotation_count": rotation_count,
            "previous_last_rotation_at": current_state.get("last_rotation_at"),
        }
        if force or not self.backup_exists():
            # First rotation OR forced rotation — overwrite the backup
            # file so we have a single canonical "previous state" record.
            directory = os.path.dirname(self.backup_path) or "."
            os.makedirs(directory, exist_ok=True)
            with open(self.backup_path, "w", encoding="utf-8") as f:
                f.write(json.dumps(backup_record, sort_keys=True) + "\n")
        else:
            _append_backup_record(self.backup_path, backup_record)

        # Step 2: generate new token + write new state atomically.
        new_token = _generate_token()
        new_state = {
            "token": new_token,
            "last_rotation_at": rotated_at,
            "last_rotation_reason": reason,
            "rotation_count": rotation_count + 1,
            "previous_token": previous_token,
            "previous_rotation_reason": current_state.get("last_rotation_reason"),
        }
        _write_json_atomic(self.storage_path, new_state)

        return TokenRecord(
            token=new_token,
            last_rotation_at=rotated_at,
            last_rotation_reason=reason,
            rotation_count=rotation_count + 1,
        )


# ---------------------------------------------------------------------------
# SSHAuditReader — read-only audit of /etc/ssh/sshd_config.
# ---------------------------------------------------------------------------


@dataclass
class SSHConfig:
    """Lightweight in-memory representation of sshd_config."""

    password_authentication: bool = True   # Default per OpenSSH upstream.
    permit_root_login: bool = True         # Default per OpenSSH upstream.
    pubkey_authentication: bool = True     # Default per OpenSSH upstream.
    port: int = 22                         # Default per OpenSSH upstream.
    permit_empty_passwords: bool = False   # Default per OpenSSH upstream.

    def to_dict(self) -> dict:
        return {
            "PasswordAuthentication": self.password_authentication,
            "PermitRootLogin": self.permit_root_login,
            "PubkeyAuthentication": self.pubkey_authentication,
            "Port": self.port,
            "PermitEmptyPasswords": self.permit_empty_passwords,
        }


# Pattern matches `Key Value` lines (with optional whitespace + comments).
_SSHD_CONFIG_PATTERN = re.compile(
    r"^\s*(?P<key>[A-Za-z][A-Za-z0-9_]*)\s+(?P<value>\S+)(?:\s*(?:#.*)?)?$"
)


class SSHAuditReader:
    """Read-only audit of `/etc/ssh/sshd_config`.

    Parses the 5 canonical hardening-relevant settings:
      - `PasswordAuthentication` (yes/no) — true if `yes`
      - `PermitRootLogin` (yes/no/prohibit-password) — true if `yes`
      - `PubkeyAuthentication` (yes/no) — true if `yes`
      - `Port` (integer) — defaults to 22
      - `PermitEmptyPasswords` (yes/no) — true if `yes`

    Idempotency: the reader is read-only by design (does NOT mutate
    `/etc/ssh/sshd_config`). The audit can be re-run any number of
    times without changing state.

    Plain-English philosophy: `find_risky_settings()` returns
    plain-English warnings ("Your SSH allows password login —
    switch to keys for safety") instead of raw exception text.
    """

    def __init__(
        self,
        sshd_config_path: str = DEFAULT_SSHD_CONFIG_PATH,
    ) -> None:
        self.sshd_config_path = sshd_config_path

    def parse(self, text: Optional[str] = None) -> SSHConfig:
        """Parse sshd_config from a file (or a text override for testing).

        `text=None` reads from `self.sshd_config_path`.
        `text=<str>` parses the given string (used by the pytest rig).
        """
        if text is None:
            if not os.path.isfile(self.sshd_config_path):
                return SSHConfig()
            with open(self.sshd_config_path, encoding="utf-8") as f:
                text = f.read()

        # sshd_config supports `Include` directives; we ignore them
        # for the audit (the canonical hardening settings live in
        # the main sshd_config, not in included drop-ins).
        cfg = SSHConfig()
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            match = _SSHD_CONFIG_PATTERN.match(raw_line)
            if not match:
                continue
            key = match.group("key")
            value = match.group("value").lower()

            if key == "PasswordAuthentication":
                cfg.password_authentication = value == "yes"
            elif key == "PermitRootLogin":
                # `prohibit-password` blocks password login but
                # allows key-based login — treated as NOT allowing
                # password login.
                cfg.permit_root_login = value == "yes"
            elif key == "PubkeyAuthentication":
                cfg.pubkey_authentication = value == "yes"
            elif key == "Port":
                cfg.port = _coerce_int(value, 22)
            elif key == "PermitEmptyPasswords":
                cfg.permit_empty_passwords = value == "yes"
        return cfg

    def find_risky_settings(
        self,
        cfg: Optional[SSHConfig] = None,
        *,
        text: Optional[str] = None,
    ) -> list:
        """Return a list of plain-English warnings for risky SSH settings.

        Order matters — the dashboard + OpenClaw surface these warnings
        in the order they appear in this list.

        Returns an empty list if the SSH config is fully hardened.
        """
        if cfg is None:
            cfg = self.parse(text=text)
        warnings = []
        if cfg.password_authentication:
            warnings.append(
                "Your SSH allows password login — switch to keys for safety"
            )
        if cfg.permit_root_login:
            warnings.append(
                "Your SSH allows root login — disable or restrict to "
                "'prohibit-password'"
            )
        if not cfg.pubkey_authentication:
            warnings.append(
                "Your SSH doesn't allow key-based login — turn "
                "PubkeyAuthentication on"
            )
        if cfg.permit_empty_passwords:
            warnings.append(
                "Your SSH allows empty passwords — set "
                "PermitEmptyPasswords to 'no' immediately"
            )
        if cfg.port == 22:
            warnings.append(
                "Your SSH runs on the default port 22 — consider a "
                "non-standard port to reduce automated attacks"
            )
        return warnings


# ---------------------------------------------------------------------------
# FirewallAuditReader — read-only audit of /etc/nftables.conf + iptables-save
# ---------------------------------------------------------------------------


@dataclass
class FirewallRule:
    """Lightweight in-memory representation of a firewall rule."""

    table: str              # "filter", "nat", "raw", etc.
    chain: str              # "INPUT", "OUTPUT", "FORWARD", etc.
    action: str             # "accept", "drop", "reject"
    protocol: Optional[str] = None
    src: Optional[str] = None
    dst: Optional[str] = None
    dport: Optional[int] = None
    sport: Optional[int] = None
    comment: Optional[str] = None
    raw: str = ""           # The original line(s) for debugging.


def _parse_nft_line(line: str) -> Optional[FirewallRule]:
    """Parse a single nft rule line into a FirewallRule.

    Handles both the canonical nft list ruleset syntax
    (`table inet filter { chain input { type filter hook input priority 0 ;
    policy drop ; tcp dport 22 accept } }`) and the simpler flat syntax
    that's commonly seen in `/etc/nftables.conf` files.
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    # Detect `tcp dport NNN accept` / `ip saddr X.X.X.X accept` patterns.
    rule = FirewallRule(table="", chain="", action="", raw=line)
    tokens = line.split()
    i = 0
    while i < len(tokens):
        tok = tokens[i].lower()
        if tok == "accept" or tok == "drop" or tok == "reject":
            rule.action = tok
            i += 1
            continue
        if tok == "tcp" or tok == "udp" or tok == "icmp":
            rule.protocol = tok
        elif tok == "dport":
            if i + 1 < len(tokens):
                rule.dport = _coerce_int(tokens[i + 1], 0)
                i += 2
                continue
        elif tok == "sport":
            if i + 1 < len(tokens):
                rule.sport = _coerce_int(tokens[i + 1], 0)
                i += 2
                continue
        elif tok == "saddr":
            if i + 1 < len(tokens):
                rule.src = tokens[i + 1]
                i += 2
                continue
        elif tok == "daddr":
            if i + 1 < len(tokens):
                rule.dst = tokens[i + 1]
                i += 2
                continue
        i += 1
    if rule.action and (rule.protocol or rule.src or rule.dport):
        return rule
    return None


_NFT_RULE_PATTERN = re.compile(
    r"(?:(?P<proto>tcp|udp|icmp)\s+)?"
    r"(?:dport\s+(?P<dport>\d+)\s+)?"
    r"(?:saddr\s+(?P<src>[\d./]+)\s+)?"
    r"(?P<action>accept|drop|reject)"
)


class FirewallAuditReader:
    """Read-only audit of nft / iptables firewall rules.

    Handles two sources:
      - `/etc/nftables.conf` — parsed line-by-line looking for nft
        rule syntax.
      - `iptables-save` output — parsed line-by-line looking for
        iptables `-A CHAIN ...` syntax.

    Plain-English philosophy: `find_risky_rules()` returns
    plain-English warnings ("Port 22 (SSH) is open to the whole
    internet — restrict to your IP range") instead of raw iptables
    / nft rule text.

    Idempotency: the reader is read-only by design (does NOT
    mutate `/etc/nftables.conf` or the iptables ruleset). The
    audit can be re-run any number of times without changing
    state.
    """

    def __init__(
        self,
        nft_path: str = DEFAULT_NFTABLES_PATH,
        iptables_save_path: str = DEFAULT_IPTABLES_SAVE_PATH,
    ) -> None:
        self.nft_path = nft_path
        self.iptables_save_path = iptables_save_path

    def parse_nft(self, text: Optional[str] = None) -> list:
        """Parse nft rules from a file (or a text override for testing).

        Returns a list of `FirewallRule` objects.
        """
        if text is None:
            if not os.path.isfile(self.nft_path):
                return []
            with open(self.nft_path, encoding="utf-8") as f:
                text = f.read()

        rules = []
        for raw_line in text.splitlines():
            rule = _parse_nft_line(raw_line)
            if rule is None:
                # Try the simpler regex pattern (handles common flat
                # nftables.conf syntax).
                match = _NFT_RULE_PATTERN.search(raw_line)
                if match and match.group("action") in ("accept", "drop", "reject"):
                    rule = FirewallRule(
                        table="filter",
                        chain="input",
                        action=match.group("action"),
                        protocol=match.group("proto"),
                        src=match.group("src"),
                        dport=_coerce_int(match.group("dport"), 0) or None,
                        raw=raw_line.strip(),
                    )
            if rule is not None:
                rules.append(rule)
        return rules

    def parse_iptables_save(self, text: Optional[str] = None) -> list:
        """Parse iptables-save output from a file (or a text override).

        Looks for `-A CHAIN ...` lines.
        """
        if text is None:
            if not os.path.isfile(self.iptables_save_path):
                return []
            with open(self.iptables_save_path, encoding="utf-8") as f:
                text = f.read()

        rules = []
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line.startswith("-A"):
                continue
            # iptables-save uses `-A CHAIN -p PROTO --dport N -j ACTION`.
            chain_match = re.match(r"-A\s+(\S+)", line)
            if not chain_match:
                continue
            chain = chain_match.group(1)
            proto_match = re.search(r"-p\s+(\w+)", line)
            dport_match = re.search(r"--dport\s+(\d+)", line)
            src_match = re.search(r"-s\s+([\d./]+)", line)
            action_match = re.search(r"-j\s+(\w+)", line)
            if not action_match:
                continue
            rules.append(
                FirewallRule(
                    table="filter",
                    chain=chain.lower(),
                    action=action_match.group(1).lower(),
                    protocol=proto_match.group(1).lower() if proto_match else None,
                    src=src_match.group(1) if src_match else None,
                    dport=_coerce_int(dport_match.group(1), 0) if dport_match else None,
                    raw=line,
                )
            )
        return rules

    def find_open_ports(self, rules: Optional[list] = None) -> list:
        """Return a list of open ports found in the ruleset.

        Walks every parsed rule + collects the dport of every ACCEPT
        rule. Returns a sorted list of unique ports.

        Returns an empty list if no rules are loaded or no ports are
        explicitly accepted.
        """
        if rules is None:
            rules = self.parse_nft()
        ports = set()
        for rule in rules:
            if rule.action == "accept" and rule.dport:
                ports.add(rule.dport)
        return sorted(ports)

    def find_risky_rules(self, rules: Optional[list] = None) -> list:
        """Return a list of plain-English warnings for risky firewall rules.

        Order matters — the dashboard + OpenClaw surface these warnings
        in the order they appear in this list.

        Returns an empty list if the firewall is fully hardened (no
        wide-open ports + no rules with `saddr 0.0.0.0/0` for
        sensitive services).
        """
        if rules is None:
            rules = self.parse_nft()
        warnings = []
        for rule in rules:
            if rule.action != "accept":
                continue
            src = (rule.src or "").lower()
            # "Wide-open" = accept from anywhere (0.0.0.0/0 or
            # missing saddr — meaning "no src filter").
            is_wide_open = (not rule.src) or src in ("0.0.0.0/0", "::/0")
            if not is_wide_open:
                continue
            dport = rule.dport or 0
            service = _service_name_for_port(dport)
            if service:
                warnings.append(
                    f"Port {dport} ({service}) is open to the whole "
                    f"internet — restrict to your IP range"
                )
            elif dport > 0:
                warnings.append(
                    f"Port {dport} is open to the whole internet — "
                    f"restrict to your IP range"
                )
        return warnings


# Canonical service-name lookup for common ports (used by
# FirewallAuditReader.find_risky_rules to surface plain-English names).
_PORT_TO_SERVICE = {
    22: "SSH",
    53: "DNS",
    80: "HTTP",
    443: "HTTPS",
    445: "SMB",
    3389: "RDP",
    5900: "VNC",
    8123: "Home Assistant",
    9090: "Prometheus",
    9100: "Node Exporter",
    8124: "Home Assistant observer",
    5353: "mDNS",
    1883: "MQTT",
    8883: "MQTTS",
}


def _service_name_for_port(port: int) -> Optional[str]:
    """Return the canonical service name for a port (or None if unknown)."""
    return _PORT_TO_SERVICE.get(port)


# ---------------------------------------------------------------------------
# Service registration — wires the 3 services into HA's service registry.
# ---------------------------------------------------------------------------


def register_security_services(hass) -> None:
    """Register the 3 RoamCore security services with HA.

    The 3 services mirror the helper package at
    `homeassistant/packages/roamcore_security_review.yaml`:
      - `roamcore.rotate_api_token` — rotates the RC_API_TOKEN
        (with backup-before-mutate; returns the new token).
      - `roamcore.audit_ssh` — runs the SSH audit (read-only;
        returns plain-English warnings via `find_risky_settings`).
      - `roamcore.audit_firewall` — runs the firewall audit
        (read-only; returns plain-English warnings via
        `find_risky_rules`).

    Plain-English philosophy: the service responses surface
    plain-English strings, not raw exception text. The helper
    package + the pytest rig both verify the contract.
    """
    # Importing inside the function so the module is testable
    # without HA (the audit + the pytest rig + the bash smoke
    # never need the HA services.async_register path).
    from homeassistant.core import ServiceCall  # noqa: F401

    token_mgr = RCApiTokenManager()

    async def _svc_rotate_api_token(call: "ServiceCall") -> dict:
        reason = str(call.data.get("reason") or "manual")
        record = token_mgr.rotate_token(reason=reason)
        return {
            "ok": True,
            "token": record.token,
            "rotated_at": record.last_rotation_at,
            "reason": record.last_rotation_reason,
            "rotation_count": record.rotation_count,
            "plain_english": "Access codes rotated successfully.",
        }

    async def _svc_audit_ssh(call: "ServiceCall") -> dict:
        reader = SSHAuditReader()
        cfg = reader.parse()
        warnings = reader.find_risky_settings(cfg)
        return {
            "ok": True,
            "settings": cfg.to_dict(),
            "warnings": warnings,
            "plain_english": (
                "Your SSH is locked down — keys only, no password login."
                if not warnings
                else "Your SSH needs attention: " + "; ".join(warnings)
            ),
        }

    async def _svc_audit_firewall(call: "ServiceCall") -> dict:
        reader = FirewallAuditReader()
        rules = reader.parse_nft()
        if not rules:
            rules = reader.parse_iptables_save()
        open_ports = reader.find_open_ports(rules)
        warnings = reader.find_risky_rules(rules)
        return {
            "ok": True,
            "rule_count": len(rules),
            "open_ports": open_ports,
            "warnings": warnings,
            "plain_english": (
                "Your firewall is locked down — no wide-open ports."
                if not warnings
                else "Your firewall needs attention: " + "; ".join(warnings)
            ),
        }

    hass.services.async_register("roamcore", "rotate_api_token", _svc_rotate_api_token)
    hass.services.async_register("roamcore", "audit_ssh", _svc_audit_ssh)
    hass.services.async_register("roamcore", "audit_firewall", _svc_audit_firewall)
