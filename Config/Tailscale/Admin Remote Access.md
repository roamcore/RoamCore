# Admin Remote Access

> Design overview for VanCore remote support using Tailscale clients + self-hosted Headscale

---

## 1. Goals

- Enable **secure, reliable remote access** to VanCore hubs (VP2430) and related boxes for:
  - Diagnostics
  - Configuration changes
  - Emergency fixes
- **Prevent any connectivity between customer systems**:
  - No van→van traffic
  - No customer→other customer traffic
- Ensure **customers cannot weaken the fleet’s security model**, even if they are “advanced” users.
- Keep **operational cost near zero**:
  - No per-device or per-user SaaS fees
  - Based on fully open-source components

---

## 2. High-Level Architecture

### Components

- **Headscale server (self-hosted)**
  - Runs on a VanCore-managed VPS.
  - Acts as the **control plane** for the mesh network.
  - Stores:
    - Nodes (hubs, support laptops)
    - Users
    - ACLs
    - Tags / namespaces
- **Tailscale clients**
  - Installed on:
    - Every VanCore hub (VP2430 main hub; possibly other boxes later).
    - VanCore support laptops/desktop machines.
  - Use `--login-server=https://headscale.vancore.net` to talk to **Headscale**, not Tailscale SaaS.

- **WireGuard**
  - Underlying encryption/transport for point-to-point links.
  - Managed automatically by Tailscale clients and Headscale.

### Network Topology

- **Hub-and-spoke model**:
  - **Support devices** = central hub.
  - **Van Hubs** = spokes.
- Each Van Hub:
  - Joins the Headscale tailnet.
  - Is reachable only from support devices, on a restricted set of ports.
- **No inter-spoke connectivity**:
  - Vans cannot talk to other vans.
  - Vans cannot talk to VanCore corporate infra directly (only what ACLs explicitly allow).

---

## 3. Identity & Tagging Model

### Node Types

- **Van Hubs**
  - Tailscale client installed on VP2430.
  - Tagged as `tag:van-hub`.
  - Named using a stable convention, e.g.:
    - `vc-<country>-<customer_id>-hub`
    - Optional suffixes for subsystem boxes: `-water`, `-electrical`, `-security`.

- **Support Devices**
  - Laptops/desktops used by VanCore staff.
  - Logged in as individual identities (no shared user accounts).
  - Tagged as `tag:support`.

### Users vs Devices

- **Users**:
  - One user per real human in the support team (e.g. `bernard@vancore`, `alex@vancore`).
  - Used for audit and revocation.
- **Devices**:
  - Each support machine + each van hub is a device in Headscale.
  - Devices are assigned tags (`tag:van-hub`, `tag:support`) server-side.

---

## 4. ACL & Isolation Design

### Core Principles

1. **Default deny**: No traffic allowed unless explicitly permitted.
2. **Support-only inbound access**:
   - Only `tag:support` → `tag:van-hub` flows are allowed.
3. **No lateral movement**:
   - No `van-hub` → `van-hub`.
   - No `van-hub` → corporate network, unless extremely constrained and necessary.

### Example ACL Policy (Conceptual)

- Allow:
  - `tag:support` → `tag:van-hub` on:
    - TCP 443 (VanCore/HA admin UI)
    - TCP 22 (SSH), only if enabled
    - Optional: an internal admin API port
- Deny:
  - `tag:van-hub` → `tag:van-hub`
  - Any other unlisted flows (default-deny)

### OS-Level Firewall on Hubs

- Restrict inbound to:
  - Tailscale interface only.
  - Specific ports (443, optional 22, etc.).
- (Optional) Restrict outbound from Tailscale interface:
  - Only to Headscale (for control) and support IPs if needed.
- No subnet routing by default:
  - The van’s LAN is not exposed onto the tailnet unless explicitly enabled per-case.

---

## 5. Customer Consent & Controls

### Remote Support Toggle

- VanCore UI includes a **“Remote Support”** toggle:
  - `Remote support: OFF / ON (temporary)`
- Behaviour:
  - When **ON**:
    - Indicates that VanCore support is allowed to connect.
    - May enable ACL rules or OS firewall rules that allow support access.
    - Optionally times out after a configurable period (e.g. 24–72 hours).
  - When **OFF**:
    - Support devices cannot access that hub (ACLs/firewall enforce this).

### Documentation & Terms

- Onboarding materials clearly state:
  - Remote access is **opt-in**.
  - It is used only for support/debugging with permission.
  - VanCore will not access systems without consent, except for any narrowly defined safety-critical exceptions (if you decide to allow that later).

---

## 6. Security & Threat Model

### What an Advanced User *Can* Do

- Stop or uninstall Tailscale client on their hub.
- Change local Tailscale config to point at their **own** Headscale/Tailscale.
- Gain root access to their own box and modify OS-level settings.

### What They **Cannot** Do (By Design)

- Modify **Headscale ACLs** or tags.
- Enable `van-hub` → `van-hub` or `van-hub` → VanCore corporate traffic.
- Use your tailnet to pivot into other customers’ devices.

### Kill Switches

- **Per-hub**:
  - Revoke a node’s keys in Headscale.
- **Fleet-wide emergency**:
  - Stop Headscale.
  - Push update to disable/uninstall Tailscale if ever required.

---

## 7. Operational Considerations

### Logging & Audit

- Headscale logs:
  - Which support user accessed which hub.
  - Connection timestamps.
- Support workflow links each session to a ticket/case.
- Logs retained 6–12 months.

### Naming & Discovery

- Maintain internal mapping of:
  - Customer name
  - Serial numbers
  - Node names
  - Install info

### Separation from Corporate Network

- Fleet tailnet is isolated from corporate networks.
- ACLs prevent vans from reaching anything except allowed support ports.

### Updates vs Remote Access

- Normal updates:
  - Outbound HTTPS to VanCore update server.
- VPN:
  - For diagnostics and manual fixes.

---

## 8. Deployment & Ops Plan (v1)

### Headscale Server

- Hosted on small VPS.
- MFA + SSH keys.
- Backups of Headscale DB.
- Process monitoring & alerts.

### Tailscale Clients on Hubs

- Installed during provisioning.
- Auto-join with preauth key.
- Tagged automatically.

### Support Devices

- Each support engineer has unique identity.
- ACLs + OS-level hardening.

---

## 9. Future Enhancements

- Per-customer namespaces.
- User-visible access logs.
- Remote-session logging.

---

## 10. Summary

- Remote support uses a **self-hosted Headscale control plane** with **Tailscale clients**.
- Strict **hub-and-spoke** ACL model:
  - Support → van allowed.
  - Van → van denied.
  - Van → support denied unless required.
- Customers cannot alter ACLs.
- Remote updates and diagnostics are secure, isolated, and low-cost.

