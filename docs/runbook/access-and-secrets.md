# Access and secrets (VanCore)

This document defines how credentials are stored and how operators/automation should access VanCore systems.

## Principles

- **Never commit secrets** (tokens, passwords, credentials, SSH private keys) to GitHub.
- GitHub contains **paths, runbooks, and procedures**, not secret material.
- Prefer **tokens** over passwords.
- Prefer **SSH keys** over password SSH.

## Home Assistant

- URL: `http://192.168.1.67:8123`
- HA API token is stored locally on the Clawdbot host:
  - `~/.clawdbot/secrets/homeassistant.token` (mode `600`)

## Proxmox (VP2430)

- SSH: `root@192.168.1.10`
- Access via SSH key (private key stored locally; do not commit).

## Google Drive backups (rclone)

- rclone remote name: `gdrive:`
- Backup folder: `gdrive:VanCore-Backups/`

> Encryption is optional. Current baseline is unencrypted Drive storage (owner-only).

## Clawdbot browser

- Automation browser: Google Chrome installed on Clawdbot host.
- Clawdbot browser profile data lives under:
  - `~/.clawdbot/browser/clawd/user-data`

## Local secrets directory

Standard location for local secrets on the Clawdbot host:

- `~/.clawdbot/secrets/`

Rules:
- directory mode `700`
- individual secret files mode `600`

