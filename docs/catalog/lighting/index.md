# Lighting

Approach lights, underbody lights, and motion-based lighting recipes.

<div class="rc-card-grid">
  <a class="rc-card" href="approach-and-underbody-lights.md">
    <div class="rc-card__title">💡 Approach + underbody lights</div>
    <div class="rc-card__body">Welcome-home lighting: porch + underbody lights turn on when you arrive.</div>
  </a>
  <a class="rc-card" href="motion-based-lighting.md">
    <div class="rc-card__title">🏃 Motion-based lighting</div>
    <div class="rc-card__body">Lights turn on when you walk by, off when you leave. No switch hunting.</div>
  </a>
</div>

## How the recipe works

Both lighting tiles ride on the same `rc_lighting_*` contract layer,
so swapping from Shelly to Zooz to Hue is a config change, not a
code change.