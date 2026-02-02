#!/usr/bin/env bash
set -euo pipefail

echo "== Clawdbot host =="
hostname
uname -a

echo

echo "== Proxmox (pve) =="
ssh root@192.168.1.10 'hostname; pveversion -v | head -n 5; qm list'

echo

echo "== Home Assistant VM =="
ssh hassio@192.168.1.67 'hostname; uname -a; cat /etc/os-release 2>/dev/null || true; ls -la /config 2>/dev/null | head -n 30 || true'
