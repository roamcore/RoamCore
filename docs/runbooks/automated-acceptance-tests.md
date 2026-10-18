# Automated acceptance tests

Every new release of RoamCore is tested automatically before it goes out, so you never receive an update that breaks your install. Here's what those tests check and how to read the results.

## §1 What this is

Every time the RoamCore team finishes a change, an automated test runs to prove the change did not break the part of the system you rely on. There is one test for each of the things RoamCore promises to do — that a fresh Hub boots cleanly, that supported devices still connect, that the dashboard still works, that your remote access still works, and that you can always recover if something goes wrong.

You never see these tests. They run in the background, on computers that look exactly like your Hub, and the result is either "good to go" or "fix this before shipping". If a test ever fails on a release that was about to come to you, the team catches it before you ever see the update — your Hub never receives a broken install.

## §2 What you see

When a new release is ready, the result of these tests is one of two things: green or red. Green means the release is safe to ship — every test passed. Red means the team fixes the issue before the release reaches you, so you never see a red on your Hub.

You might see a small badge on the project's website that says something like "all checks passed". That badge is the public summary of these tests. If you see "all checks passed" next to a release, you can install it knowing the install has been proven clean.

## §3 What you do

Nothing. The tests run automatically. You do not need to download anything extra, configure anything, or read any logs. The tests are part of how RoamCore is built — not something you opt into.

If you are curious about a specific release, the website shows the test results for that release right next to the download link. Green means you can install with confidence. If the team needs to delay a release because a test did not pass, they tell you on the same page.

## §4 What to do if it goes wrong

You cannot make these tests fail from your Hub. They run before the release reaches you, on computers the RoamCore team controls. If a test ever fails on your Hub in a way that prevents install, that is a different problem (a hardware issue, a network issue, or an incompatibility with your specific van setup) — and the support team handles it through the normal support channel, not through this test system.

If you are reading the test results on the website and you see a red next to a release you were about to install, the simple answer is: do not install it yet. The team will publish a fixed release soon. The website tells you when the next green release is available.

## §5 Useful links

- The full list of what RoamCore promises to do (the release plan the tests check against) lives in the product guide that ships with your Hub.
- The support page on the RoamCore website has the latest update notes, with a note about which release is currently green.
- If you want to see the test results for yourself, the project's public test page (linked from the website) shows green or red for every release, with a plain-English note explaining what each test is checking.
- The recovery guide (the manual fallback if anything ever does go wrong on your Hub) lives in your Hub's settings page under "Get help". You do not need it for normal operation — the tests exist so you never need it — but it is there if you do.

---

If a term in this runbook is unclear, the support page has a glossary of plain-English explanations for the words RoamCore uses. The short version: an "acceptance test" is an automatic check that proves an install works, "CI" is the automatic system that runs those checks, a "gate" is one of the checkpoints the checks are testing, and a "sandbox" is the safe test environment where the checks run before anything reaches your Hub.
