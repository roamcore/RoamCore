# RoamCore Agent Engineering System (Clawdbot Upgrade)

## Purpose
This document defines how to upgrade the existing Clawdbot/OpenClaw agent setup into a structured, multi-agent engineering system.

This is **NOT** a rebuild. It is an overlay system that:
- improves output quality
- reduces hand-holding
- structures development like a real engineering team

---

## 1. Existing System (Baseline)

Current setup already provides:
- Clawdbot agent (main)
- Direct GitHub repo access
- SSH access to dev environment
- Ability to edit files and run commands
- Session memory and tooling
- Telegram interface

This is sufficient.

We are **NOT** adding:
- new infrastructure
- new deployment layers
- complex orchestration frameworks

---

## 2. Objective

Transform the single-agent workflow into:

> A structured, role-based engineering team simulation

Where:
- one agent orchestrates
- multiple agents specialise
- tasks are decomposed properly
- outputs are validated before returning

---

## 3. Core Concept

Instead of:

> User → Agent → Code

We move to:

> User → CTO Agent → Task Breakdown → Specialist Agents → Validation → Output

---

## 4. Architecture (Within Clawdbot)

### 4.1 Single Runtime, Multiple Roles

We **DO NOT** run multiple agents physically. We simulate them using:
- role prompts
- structured task execution
- internal delegation

### 4.2 Role Simulation Model

Each task is executed in stages:
1. CTO Agent (planner)
2. Architect Agent (design)
3. Engineer Agent (implementation)
4. QA Agent (testing)
5. Reviewer Agent (alignment)

Each stage is:
- explicit
- structured
- required

---

## 5. Required Files

### 5.1 GOLDEN.md

Defines:
- principles
- constraints
- product direction

This **MUST** be referenced in every task.

### 5.2 SYSTEM.md

This document. Defines:
- how the system works
- how agents behave

### 5.3 Agent Role Definitions

Create:

```
/agents/roles/
  cto.md
  architect.md
  engineer.md
  qa.md
  reviewer.md
```

---

## 6. Role Definitions (Behaviour)

### CTO Agent Responsibilities
- interpret user request
- break into structured tasks
- define success criteria

Output:
- clear task list
- ordered execution plan

### Architect Agent Responsibilities
- define system design
- define interfaces and structure
- prevent poor architectural decisions

### Engineer Agent Responsibilities
- implement code
- follow architecture strictly
- keep changes minimal and clean

### QA Agent Responsibilities
- test behaviour
- identify edge cases
- detect regressions

### Reviewer Agent Responsibilities
- check against GOLDEN.md
- reject over-complex or fragile solutions

---

## 7. Execution Flow (MANDATORY)

Every task **MUST** follow this flow:

### Step 1: Planning (CTO)
Output:
- problem breakdown
- task list
- risks

### Step 2: Design (Architect)
Output:
- system structure
- file changes
- data flow

### Step 3: Implementation (Engineer)
Output:
- actual code
- commits
- explanation

### Step 4: Testing (QA)
Output:
- test cases
- failure points
- validation status

### Step 5: Review (Reviewer)
Output:
- alignment with GOLDEN.md
- simplification suggestions
- approval/rejection

---

## 8. Prompting Strategy (Critical)

The main agent prompt must enforce:
- role-based execution
- step-by-step progression
- structured outputs

Required instruction:

> You are not a single agent. You are a team of specialised agents:
> - CTO
> - Architect
> - Engineer
> - QA
> - Reviewer
>
> For every request:
> 1. Plan (CTO)
> 2. Design (Architect)
> 3. Implement (Engineer)
> 4. Test (QA)
> 5. Review (Reviewer)
>
> Do not skip steps. Do not jump straight to implementation.
> All decisions must align with GOLDEN.md.

---

## 9. Git Workflow (Keep Simple)

- Work on current branch
- Make small commits
- Avoid massive changes

---

## 10. Token Efficiency Improvements

- Avoid repeated corrections
- Reduce failed implementations
- Improve first-pass quality

---

## 11. What We Are NOT Doing

- No full multi-process orchestration
- No Kubernetes-style agent systems
- No over-engineered frameworks

---

## 12. Success Criteria

System is working when:
- outputs require minimal correction
- agent explains reasoning clearly
- fewer back-and-forth iterations
- code quality improves noticeably

---

## 13. Immediate Implementation Steps

1. Add GOLDEN.md to repo
2. Add this SYSTEM.md to repo
3. Create /agents/roles/ files
4. Update Clawdbot system prompt
5. Start using structured workflow

---

## 14. Future Upgrades (Optional)

- Git worktrees per task
- Parallel subagent execution
- Automated testing scripts
- CI pipeline integration

---

## 15. Final Principle

This system works ONLY if:
- roles are respected
- steps are followed
- GOLDEN.md is enforced

If the agent skips structure:
→ The system collapses.

