# Documentation policy (customer/production-facing)

## Rule 0: assume this repo will be public

Write everything as if it will be read by customers and attackers.

## Never include

- Secrets (tokens/passwords/API keys)
- Private keys
- Internal IPs/hostnames
- Detailed network topology of private environments
- Backup vault paths or snapshot schedules

## Prefer

- Conceptual architecture that is environment-agnostic
- Configuration examples with placeholders
- Clear upgrade/rollback guidance that doesn’t leak internal layout

## Internal documentation

Internal engineering runbooks and day-to-day development logs must live outside this repo.
Recommended location: private internal repo and/or local agent memory files.
