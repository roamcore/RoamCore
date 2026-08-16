# RoamCore — Automated Acceptance Tests for Gate D (agent integration)

## §1 What this is

Every time someone pushes a change to RoamCore, an automatic check
runs that proves the helper app on your phone or laptop can still ask
your van "how are things going?" and get a safe answer — and that if
the helper tries to do anything more than read, the answer is
always "ask the owner first, and write down what happened." This is
the check that makes sure the helper app stays helpful and stays
out of trouble.

## §2 What you see

When everything is healthy, you see a green check mark on the
project's test page called "Acceptance — Gate D (agent
integration)". When something goes wrong with how the helper talks
to your van, that check turns red and you can click into the failed
run to see exactly what broke, in plain words.

There are twelve checks in this test, and each one prints a short
sentence when it runs. If a check fails, the sentence tells you
what went wrong in words a normal person can understand — not in a
wall of code or error numbers.

## §3 What you do

1. Push your change to the main branch, or open a code-review request.
2. Open the **Actions** tab at the top of the GitHub repository.
3. Click on the run called "Acceptance — Gate D (agent
   integration)".
4. If the run is green, you are done. If the run is red, click
   into the failed step to see which one broke and what it says.

## §4 What to do if it goes wrong

When the check fails, the failed step's plain-English message tells
you what is wrong and what to check first. The most common reasons
a step fails are:

- **The helper app cannot log in.** This usually means the access
  code in your Hub has changed, or has not been entered yet. Check
  the Hub's setup page and confirm the helper-app access code is
  active.
- **The helper app asked for something it should not be allowed to
  do.** This means one of the safety rails was tripped. The most
  common cause is a new helper-app recipe that tries to do
  something risky. Look at the recipe and confirm it only asks
  for things a person would expect a helper to do (turn on a
  light, check the battery) — not things a person would never
  ask (turn off power, factory reset, wipe storage, turn off the
  internet, hand over remote admin).
- **The recorded log of helper actions is missing or has been
  changed.** This is the safety net that catches a helper app
  doing something it shouldn't. If the log is missing or has been
  edited, the helper app cannot be trusted until the log is
  restored. Check the Hub's storage and confirm the log file
  exists and has not been edited.
- **The helper app crashed, and the van kept running.** This is
  the recovery test — and a green result here means the helper
  app can crash without taking your van down. If it failed, the
  helper app is too tightly coupled to the van. Check the
  helper-app's recovery automation and confirm it clears the
  failure state on its own.

If the plain-English message does not help, scroll down in the run
log to find the detailed report — every check in the test quotes
the specific thing it was checking, with a short explanation of
why that thing matters.

## §5 Useful links

- The full project plan that this check is testing against lives
  with your Hub's release notes.
- The recovery guide (the manual fallback if anything ever does go
  wrong on your Hub) lives in your Hub's settings page under
  "Get help". You do not need it for normal operation — the checks
  exist so you never need it — but it is there if you do.
- The support page has a glossary of plain-English explanations for
  the words the project uses. The short version: an "acceptance
  test" is an automatic check that proves a release works, and a
  "gate" is one of the checkpoints the checks are testing.

---

If a term in this runbook is unclear, the support page has a
glossary of plain-English explanations for the words RoamCore uses.
The short version: an "acceptance test" is an automatic check that
proves an install works, "CI" is the automatic system that runs
those checks, a "gate" is one of the checkpoints the checks are
testing, and a "sandbox" is the safe test environment where the
checks run before anything reaches your Hub.

| Operator term | What it means for you |
| --- | --- |
| acceptance test | automatic check that proves a release works |
| CI | the automatic system that runs those checks |
| gate | one of the checkpoints the checks are testing |
| sandbox | the safe test environment where the checks run |
| agent / helper app | the helper app that asks your van how things are going |
| confirmation | the system that asks the owner before doing anything risky |
| audit log | the written record of everything the helper app has done |
| tamper-evident chain | a special way of writing the log so any change is easy to spot |