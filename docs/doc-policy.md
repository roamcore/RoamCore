# Documentation policy (VanCore)

## Goal

VanCore’s GitHub repository is intended to become **customer-facing**.

## Rules

1) **No secrets in GitHub**
- No tokens, passwords, API keys, credentials, or private keys.

2) **Customer docs vs internal ops**
- Customer-facing content should not include internal IPs/hostnames, port maps, backup locations, or any information that increases attack surface.

3) **Development logs stay local**
- Clawdbot records day-to-day engineering actions and context in local files on the Clawdbot host:
  - `memory/YYYY-MM-DD.md`
  - `MEMORY.md`

4) **Redaction/rewriting is expected**
- Internal runbooks may exist temporarily, but must be rewritten or migrated before the repo becomes public.

## Definitions

- **Customer-facing docs**: product usage, setup, troubleshooting, concepts, FAQs.
- **Internal runbooks**: operational procedures, infrastructure diagrams, IPs, backups/snapshots.
