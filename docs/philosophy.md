# RoamCore Philosophy

RoamCore is building the open-source operating system for life on the road.

If you live in a van, boat, tiny house, cabin, or any off-grid setup, the *software* that runs your home should feel as intentional as the build itself: clean, reliable, and owned by you.

This document describes the direction of the project — not a detailed spec.

---

## The problem we’re solving

Most “van tech” ends up in one of two buckets:

- **Proprietary boxes** that are expensive, subscription-shaped, and closed.
- **DIY dashboards** that can be powerful, but often feel fragile and take weeks to assemble.

RoamCore is the third option: a system that’s **simple enough for non-technical owners**, but still **fully extensible** for enthusiasts.

---

## What “good” looks like

### 1) Local-first, offline-capable
Core monitoring and control must work without an internet connection.

### 2) No subscriptions for essentials
Battery, location, levelling, and safety shouldn’t be paywalled.

### 3) Premium feel, not DIY feel
Non-technical users can’t evaluate architecture — they evaluate whether it looks clean, deliberate, and trustworthy.
The UI matters as much as the code.

### 4) Fail softly
When a data source disappears, we prefer:

- showing the last known value with a subtle “last updated” timestamp, and
- clear status indicators,

instead of blank screens, spinners forever, or cryptic errors.

### 5) Novice-first by default, advanced mode when you want it
RoamCore should be easy on day one.

And if you want full control, you can go deeper — but that “advanced mode” should be clearly separated, documented, and recoverable.

### 6) Contract-first design
The dashboard should depend on a stable set of `rc_*` contract entities.
That lets us swap underlying vendors/integrations over time without breaking the user experience.

---

## The near-term focus

The beta focus is to deliver a small set of features that are *reliably valuable* out of the box:

- **Power** (starting with Victron)
- **Map + trip tracking**
- **Trip Wrapped** (shareable trip recap)
- **Weather + time** primitives for automations
- **OpenClaw-oriented API** for modern agent integrations

---

## The long-term direction

Over time, RoamCore aims to become a cohesive, modular platform:

- expanding into more systems (water, climate, vehicle diagnostics, safety)
- supporting plug-and-play hardware modules
- enabling simple setup flows and guided onboarding
- providing trustworthy summaries and “what-if” exploration (with safety as the #1 priority)

The goal is not “AI for the sake of AI”. It’s *clarity*, *confidence*, and *control*.

