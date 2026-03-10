# Contributing to RoamCore

Thanks for your interest in contributing to RoamCore. Whether you're fixing a bug, improving documentation, suggesting a feature, or testing the system in your van — every contribution helps move the project forward.

This document explains how to get involved, what we're looking for, and how we work.

---

## Before You Start

RoamCore is in active beta development. Things change frequently, and some areas of the codebase are more stable than others. Before diving into a large contribution, please open an issue or start a discussion to check that your idea aligns with the project direction. This saves everyone time and ensures your work has the best chance of being merged.

Read the [ROADMAP.md](ROADMAP.md) to understand where the project is heading and what's currently being prioritised.

---

## Ways to Contribute

### Report Bugs

Found something broken? Open an issue with:

- A clear description of what you expected to happen and what actually happened.
- Steps to reproduce the problem.
- Your setup: which install path you're using (RoamCore OS or standalone HA config), your hardware, and your Home Assistant version.
- Relevant logs or screenshots if available.

Please check existing issues before opening a new one to avoid duplicates.

### Test in Your Van

The single most valuable contribution right now is real-world testing. Install RoamCore in your vehicle, use it on a trip, and tell us what works and what doesn't. Edge cases that only appear on the road — intermittent connectivity, power fluctuations, GPS dropouts in valleys — are things we can't find at a desk.

If you're testing, even a short write-up of your experience (what hardware you're using, what worked, what was confusing, what broke) is enormously helpful. Post it in Discussions or open an issue.

### Improve Documentation

Documentation is never finished. If something was unclear when you set up RoamCore, there's a good chance other people will hit the same confusion. Improvements to install guides, configuration explanations, hardware compatibility notes, and troubleshooting guides are always welcome.

### Contribute Code

We welcome pull requests for bug fixes, feature improvements, and new integrations. See the workflow section below for how to submit code.

### Suggest Features

Have an idea for something RoamCore should do? Open a Discussion thread. Describe the use case — what problem does it solve, and who benefits? Feature suggestions grounded in real vanlife/off-grid experience are especially valuable.

---

## What We're Looking For

Contributions that align with these priorities are most likely to be reviewed and merged quickly:

- **Bug fixes** for existing MVP features (power, map, level, weather, dashboard, setup wizard).
- **Dashboard improvements** — better cards, more responsive layouts, accessibility.
- **Integration refinements** — improving reliability of Victron pairing, Traccar data flow, GPS accuracy.
- **Documentation** — install guides, hardware compatibility, troubleshooting, how-tos.
- **Testing reports** — real-world usage feedback from different hardware and vehicle setups.

We're less likely to merge contributions that:

- Add features not on the roadmap without prior discussion.
- Introduce cloud dependencies or require paid API keys for core functionality.
- Add dependencies with restrictive licenses (GPL, AGPL) without prior approval.
- Significantly increase complexity without a clear user benefit.

When in doubt, open an issue first.

---

## Development Workflow

### Setting Up Your Environment

1. Fork the repository and clone your fork locally.
2. Follow the install guide in the README for your chosen install path.
3. Make your changes on a feature branch, not on `main`.

### Commit Messages

Write clear, descriptive commit messages. Use the present tense and keep the first line under 72 characters.

```
Add cell tower fallback to GPS parser service

When the LTE modem loses GPS fix for more than 60 seconds, the parser
now queries cell tower info and performs an OpenCelliD lookup to
maintain approximate position reporting.
```

### Pull Requests

1. **One concern per PR.** Don't bundle unrelated changes. A bug fix and a new feature should be separate PRs.
2. **Describe what and why.** Explain what your PR does, why it's needed, and how you tested it.
3. **Reference related issues.** Link to any relevant issue or discussion thread.
4. **Keep it reviewable.** Smaller PRs get reviewed faster. If your change is large, consider breaking it into a series of smaller PRs.
5. **Test your changes.** If you're modifying dashboard YAML, verify it renders correctly on mobile and desktop. If you're modifying automations or scripts, confirm they execute as expected. If you're modifying integrations, test with real hardware if possible.

### Code Style

- **YAML:** Follow Home Assistant's conventions. Use 2-space indentation. Comment non-obvious configuration choices.
- **Python:** Follow PEP 8. Use type hints where practical.
- **JavaScript:** If contributing custom Lovelace cards, use ES6+ and keep dependencies minimal.
- **General:** Favour readability over cleverness. The next person reading your code might be a van-dwelling contributor debugging at a campsite on their phone.

---

## Project Structure

The repo is organised to support both install paths:

- **HA configuration** (dashboard YAML, automations, scripts, integrations, packages) lives in a clearly separated directory that can be used independently of the full RoamCore OS stack.
- **RoamCore OS configuration** (Proxmox setup, OpenWrt config, VM provisioning) lives in its own directory and is only relevant for the full-stack install path.
- **Documentation** lives in `docs/`.

If you're unsure where something belongs, check existing files for precedent or ask in an issue.

---

## Licensing

RoamCore is released under a permissive open-source license (see LICENSE in the repo root). By submitting a contribution, you agree that your work will be released under the same license.

Do not introduce dependencies with licenses that are incompatible with the project license. When in doubt, ask.

---

## Code of Conduct

Be respectful, be constructive, and assume good faith. RoamCore is built by people who live in vans, work on the road, and care about making off-grid life better. Treat every contributor — whether they're submitting their first typo fix or redesigning the dashboard — with the same respect.

We don't have a formal code of conduct document yet. For now: don't be a jerk, help where you can, and remember that everyone's time is volunteered.

---

## Questions?

If something in this guide is unclear, or you're not sure how to get started, open a Discussion thread. We'd rather answer a question than lose a potential contributor to confusion.
