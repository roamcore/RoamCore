# RutOS (Teltonika) inspiration notes for RoamCore netstack

These notes capture useful, public RutOS concepts we can mirror in RoamCore’s OpenWrt-based MVP.

## Source docs
- Teltonika Wiki: RUT241 Failover
  - https://wiki.teltonika-networks.com/view/RUT241_Failover
- Teltonika Wiki: RUT240 Failover
  - https://wiki.teltonika-networks.com/view/RUT240_Failover

## Concepts worth copying

### 1) Simple priority model (metrics)
RutOS expresses WAN priority via interface ordering / metrics.

Key idea:
- “Use the interface with the highest priority as long as it’s available; otherwise fall back.”

RoamCore mapping:
- mwan3 members already support this via `metric` (lower metric = higher priority in our conventions).
- Expose a single “preferred WAN” control (Starlink vs LTE) that rewrites metrics:
  - primary metric = 10
  - backup metric = 20

### 2) Per-interface health check configuration
RutOS has an “Interface configuration” page that controls how it determines an interface is up/down:
- interval
- failure threshold
- action on connect/disconnect (flush connections)

RoamCore mapping:
- mwan3 provides similar knobs:
  - `track_ip` list
  - `reliability`
  - `interval`, `down`, `up`
  - `flush_conntrack` (if we choose to use it)

We should define sane defaults in netstack scripts:
- WAN (Starlink): track 1.1.1.1 + 8.8.8.8, interval 5s, down 3, up 3
- LTE: same, but allow a slightly longer interval to reduce data churn

### 3) Mutually exclusive modes (failover vs load-balance)
RutOS makes it explicit:
- Failover and load balancing aren’t used at the same time.

RoamCore mapping:
- Keep MVP as **failover-first**.
- Add an optional “balanced” mode later (mwan3 `balanced` policy) with clear UX.

## Practical UX takeaway
The RutOS UI pushes the user toward:
- a single priority decision
- transparent health checks
- quick visibility of which WAN is active

RoamCore should mirror this in the HA dashboard:
- Active WAN
- Preferred WAN
- Per-WAN state (online/offline)
- LTE SIM state + registration

