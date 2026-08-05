# Connection state chip — reference

The state chip is the small colour-coded pill at the top of every connection page in the catalog. It tells you, at a glance, where the connection is in its lifecycle and what you (or RoamCore) needs to do next.

This page is the IKEA-style 5-step reference for the state chip primitive. If you want to add a state chip to a connection page, follow steps 1–5. No prior CSS knowledge required.

## What this is

A connection-state chip is a tiny HTML snippet (`<span class="rc-state-chip ready-to-connect">…</span>`) that the catalog renders at the top of every connection page alongside a tier pill (RoamCore Certified / Community Verified / Experimental) and a Connect button. The chip colour tells you the state; the optional one-line `state_reason` subtitle tells you why. The full set of 10 states comes from the [product directive §"Connection states are standardized"](../reference/rc-entity-naming.md) — the directive is the single source of truth, this page is just the user-facing cheat sheet.

## When you see a state chip

There are exactly 10 states. Each one has a colour and a plain-English meaning.

| State | Colour | Plain-English meaning |
|---|---|---|
| `Available` | neutral gray | Listed in the catalog, but nothing is detected on the LAN yet. You can browse it. |
| `Detected` | light teal | RoamCore sees the device on the network but hasn't wired it up. One click from ready. |
| `Ready to connect` | teal accent | Everything is in place — recipe shipped, docs published. Tap **Connect** and you're live. |
| `Connecting` | animated teal pulse | You tapped **Connect** and RoamCore is in the middle of the install flow. Don't tap twice. |
| `Connected` | green accent | Live on the dashboard. The tile is showing real values. |
| `Needs information` | yellow | RoamCore is ready, but you owe 1–2 answers (an IP, a serial port, a vendor choice). |
| `Needs attention` | orange | Something is wrong but recoverable. Look soon. |
| `Unsupported` | gray + diagonal stripes | This combination of hardware + vendor + recipe isn't tested together. Informational only. |
| `Offline` | red | The device / connection is down. The tile is currently missing from the dashboard. |
| `Update available` | purple | Works fine. A newer recipe or upstream integration exists; tap **Connect** to upgrade. |

## How to add a state chip to a connection page

Five steps. Each step has a copy-pastable code snippet.

### Step 1 — Pick the right state

Open `connections/<your-slug>/connection.yml` and set the `state:` field to one of the 10 values from the table above. The literal string matters — lowercase, plural, or synonym forms are rejected at pytest time so the catalog never renders a misstyled chip.

```yaml
state: Ready to connect
```

If the state isn't `Connected`, add a one-line `state_reason:` explaining why the connection is in this state (e.g. "3-path recipe shipped; awaiting operator pick of Path A / B / C"). The catalog auditor surfaces this copy in the tooltip.

```yaml
state: Ready to connect
state_reason: '3-path recipe shipped; operator picks Path A / B / C to go live.'
```

### Step 2 — Open the connection page

The connection's user-facing page lives at `docs/catalog/<category>/<slug>.md`. Open it in your editor.

### Step 3 — Add the inline HTML row at the top

Right after the H1 (`# Starlink` and similar), drop this raw-HTML block. MkDocs is configured with the `md_in_html` extension (see `mkdocs.yml`) so the HTML passes through unchanged.

```markdown
# Starlink

<div class="rc-state-chip-row">
  <strong>Starlink</strong>
  <span class="rc-state-chip ready-to-connect">Ready to connect</span>
  <span class="rc-tier verified">Community Verified</span>
  <a class="rc-connect-button" href="/connections/starlink/connect">Connect</a>
</div>

Starlink is a self-hosted mobile-internet terminal (Gen-2/Gen-3 dish + router)…
```

Swap the kebab-case class on the chip (`ready-to-connect`) to match your connection's declared state. Swap the tier pill class (`verified`) to `certified` for a RoamCore-shipped integration, or `experimental` for a DIY / community recipe. Swap the Connect button label to one of the per-state verbs below.

### Step 4 — Pick the right Connect-button label

The default label is `Connect`. Override per-state to match what the operator needs to do next.

| Connection state | Suggested label |
|---|---|
| `Available`, `Detected`, `Ready to connect` | `Connect` (default) |
| `Connecting` | `Connecting…` |
| `Connected` | `Reconnect` |
| `Needs information` | `Set up` |
| `Needs attention` | `Reconnect` |
| `Update available` | `Update` |
| `Unsupported` | `Learn more` |
| `Offline` | `Reconnect` |

### Step 5 — Verify locally

Run the two checks before you push:

```bash
bash scripts/checks/catalog-state-chip-smoke.sh
python3 -m pytest homeassistant/packages/tests/test_connection_card.py -v
```

The smoke check confirms your `state:` value has a matching CSS class in `docs/styles/rc.css` and the pytest suite pins the helper's contract (10 states × tier vocabulary × Connect button). Both must be green before the catalog rebuild runs.

## Why the colours matter

The colour palette is deliberate. Green = good (everything works). Yellow / orange = the operator owes action. Teal accent = you can do this now (the brightest "go" signal in the palette). Red = something is broken right now (reserved for `Offline`, never decorative). Gray = informational, not for you. Purple = newer / optional (`Update available`). The full set is documented at the top of `docs/styles/rc.css` under the "Connection-state chips (Wave 9 #118)" header — if you add a new state, add the colour rule alongside it.

## Tier chips (RoamCore Certified / Community Verified / Experimental)

The support-level pill next to the state chip uses the **full-word vocabulary** introduced in the Wave 9 #117 rebrand. The legacy `tier: a|b|c` letter sort key survives in YAML for programmatic sorting; what you (and the operator) see on the catalog row is one of:

- `<span class="rc-tier certified">RoamCore Certified</span>` — RoamCore ships and maintains the integration code. Bench-tested.
- `<span class="rc-tier verified">Community Verified</span>` — A well-understood recipe over upstream Home Assistant core + HACS add-ons. Setup required.
- `<span class="rc-tier experimental">Experimental</span>` — DIY / community inspiration. No support.

The helper at `scripts/connection_card.py::format_tier_chip` accepts both forms (`a|b|c` letters and `certified|verified|experimental` full-word) so legacy catalog pages and future pages both render correctly. See the [Wave 9 #117 PR](https://github.com/roamcore/RoamCore/pull/117) for the full rebrand context.