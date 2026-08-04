# AI

Conversational agents, mode switching, and the local JSON API the
OpenClaw agent uses to talk to your van.

<div class="rc-card-grid">
  <a class="rc-card" href="mode.md">
    <div class="rc-card__title">🤖 Mode switcher</div>
    <div class="rc-card__body">Quickly switch the van between common states (Auto / Travel / Camp / Stealth).</div>
  </a>
  <a class="rc-card" href="advanced-mode.md">
    <div class="rc-card__title">⚡ Advanced mode</div>
    <div class="rc-card__body">Power-user toggle that exposes the raw entity layer for advanced automations.</div>
  </a>
  <a class="rc-card" href="demo-mode.md">
    <div class="rc-card__title">🎭 Demo mode</div>
    <div class="rc-card__body">Safe demo values for showing off the dashboard without real sensors.</div>
  </a>
  <a class="rc-card" href="openclaw-json-api.md">
    <div class="rc-card__title">🔌 OpenClaw JSON API</div>
    <div class="rc-card__body">Local agent contract — the JSON API OpenClaw uses to read + write van state.</div>
  </a>
  <a class="rc-card" href="agent-actions-allowlist.md">
    <div class="rc-card__title">🛡 Agent actions allowlist</div>
    <div class="rc-card__body">Safety gateway that limits which actions the agent can trigger.</div>
  </a>
</div>

## What RoamCore does for AI

RoamCore ships no native LLM. It provides the contract layer + the
mode/automation-builder recipes that any agent (local or cloud) can
plug into. See the [OpenClaw skill](../../howto/openclaw-roamcore-skill.md)
for the canonical agent path.