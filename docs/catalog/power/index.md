# Power

Batteries, solar, shore power, and inverter control. See state of charge, how fast you're charging, and whether you need to plug in tonight.

<!-- RC_FEATURE_LIST_START -->

## Features

<div class="rc-feature-list">
  <a class="rc-feature" href="alternator-charge-control-wakespeed/"><div class="rc-feature-left"><div class="rc-feature-title">Alternator charge control (Wakespeed / smart regulator)</div><div class="rc-feature-sub">If your build uses a smart alternator regulator (e.g. Wakespeed), you can automate when alternator charging is allowed and how aggressively it charges — based o</div></div></a>
  <a class="rc-feature" href="inverter-idle-shutdown/"><div class="rc-feature-left"><div class="rc-feature-title">Inverter idle shutdown (automatic power safety)</div><div class="rc-feature-sub">Automatically turn off (or reduce) inverter usage when it’s been idle for a while, or when nobody is home — to prevent silent battery drain.</div></div></a>
  <a class="rc-feature" href="victron-auto-addon/"><div class="rc-feature-left"><div class="rc-feature-title">Victron Auto add-on (backend connector)</div><div class="rc-feature-sub">A Home Assistant add-on used by RoamCore to connect to Victron telemetry automatically and keep power entities up to date.</div></div></a>
  <a class="rc-feature" href="victron-mock-addon/"><div class="rc-feature-left"><div class="rc-feature-title">Victron Mock add-on (demo power data)</div><div class="rc-feature-sub">A demo/mock backend that generates Victron-like power telemetry for development and demos.</div></div></a>
  <a class="rc-feature" href="victron/"><div class="rc-feature-left"><div class="rc-feature-title">Victron power monitoring (GX + MQTT)</div><div class="rc-feature-sub">RoamCore includes a Victron integration path that turns your Victron GX + battery/solar system into clean Home Assistant entities (SOC, solar watts, etc.) and d</div></div></a>
</div>

<!-- RC_FEATURE_LIST_END -->

## Power connections (new format)

## [Alternator charge control](alternator-charge-control-wakespeed.md)

Show me at a glance whether my alternator is charging the house battery while I drive, and turn charging off on its own when it would do more harm than good.

<div class="rc-state-chip-row" data-connection-name="Alternator charge control">
  <span class="rc-state-chip rc-state-chip--available" title="Code is shipped and the device is ready to install.">Available</span>
  <span class="rc-tier rc-tier--verified rc-chip rc-chip--verified" title="A member of the community tested this on a real van.">Community Verified</span>
  <a class="rc-connect-button" href="alternator-charge-control/" title="Open the setup page for alternator-charge-control">Connect →</a>
</div>
