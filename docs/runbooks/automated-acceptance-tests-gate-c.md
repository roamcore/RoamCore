# RoamCore — Automated Acceptance Tests for Gate C (dashboard reliability)

## §1 What this is

An automated test that proves the dashboard on your Hub stays the
same shape on your phone (any screen 480 pixels wide or smaller)
as on your tablet, that the readings update on their own without
you doing anything, that a control you tap in the app actually
flips the real switch in the van, and that anything you have added
to the dashboard stays put even when the Hub restarts. The whole
point of this test is so you can trust what you see on the
screen, no matter which screen you look at.

## §2 What you see

When RoamCore is healthy, you see a green check mark called
"Acceptance — Gate C (dashboard reliability)" in the build
status that the team watches. When something is wrong, that
check is red and the team gets a plain-English message telling
them which part of the dashboard is misbehaving — for example
"the dashboard tile did not update within five seconds, check
the recorder". You never have to read that message yourself;
the team sees it before any release reaches your Hub.

There are twelve short checks in this test. Each one checks
one promise RoamCore makes about the dashboard, and each one
prints what it found in plain English.

## §3 What you do

1. Nothing on your normal day. The tests run automatically every
   time the team finishes a change, and the result is either
   "good to go" or "fix this before shipping".
2. If you want to peek, open the website where the team's
   release status lives and look for the green badge next to
   the latest release.
3. If a release you were about to install shows a red instead
   of a green, do not install it yet. Wait for the next
   release — the website will turn the badge back to green
   when the team has fixed it.

## §4 What to do if it goes wrong

If the dashboard ever stops showing live data on your Hub, the
first thing to try is the same thing you would try for any
"stuck" reading on the Hub: open the Home Assistant app, go to
the Settings screen, find the device or sensor that is not
updating, and tap "Reload". Wait ten seconds, then look at the
dashboard again. If it is still stuck, follow the plain-English
recovery hint the test gives — most often that will say "go to
Setup" and the next step is to open the Setup screen and let
RoamCore re-detect the device for you.

If a tile ever disappears from your dashboard after a restart,
the test verifies that your own added tiles always come back.
Open the dashboard and tap the small "Refresh" button at the
top. If your added tiles still do not come back, send the
support bundle from the Hub's Settings screen to support and
include a short note describing which tile went missing.

If a control in the app (a switch, a slider, anything you can
tap) does not seem to flip the real thing in the van, the first
thing to try is opening the device's own app (the one made by
the maker of that piece of hardware) and confirming the
device is reachable there. If the device's own app says the
device is offline, the dashboard cannot reach it either, and
the fix is the device-side one — not a RoamCore issue. If the
device's own app says the device is online, send the support
bundle from the Hub's Settings screen to support.

## §5 Useful links

- The full list of what RoamCore promises to do (the release
  plan the tests check against) lives in the product guide
  that ships with your Hub.
- The other automated tests, one for each part of RoamCore,
  live in the same release status page next to this one.
- The support page on the RoamCore website has the latest
  update notes and a short note about which release is
  currently green.
- The recovery guide (the manual fallback if anything ever
  does go wrong on your Hub) lives in your Hub's Settings
  page under "Get help".

---

If a term in this runbook is unclear, the support page has a
glossary of plain-English explanations for the words RoamCore
uses. The short version: a "tile" is one of the small panels
on your dashboard (one tile for battery, one tile for water,
one tile for lights), the "dashboard" is the whole screen
made up of all those tiles, a "control" is anything on the
dashboard you can tap to change something in the van (a
switch, a slider, a button), the "phone" form factor is
anything with a screen 480 pixels wide or smaller, a "reboot"
is when the Hub restarts itself, and a "release" is one
shipped update of the software on your Hub.
