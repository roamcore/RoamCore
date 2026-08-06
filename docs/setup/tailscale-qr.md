# Show this QR code on your phone — RoamCore Tailscale wizard

## §1 What this is

RoamCore draws a small square picture on your dashboard that you scan with the Tailscale app on your phone, so you don't have to type a long secret code by hand.

## §2 What you see

When RoamCore is ready for you to connect, you'll see a small black-and-white square on your dashboard under the Tailscale card, with a one-line message above it that says **"Show this to your phone"**. Below the square is a short web address — that's your one-tap backup if your phone can't read the square for any reason.

## §3 What you do

1. Open the Tailscale app on your phone. (You can get it from your phone's app store — search for "Tailscale".)
2. On your van's dashboard, find the Tailscale card. You'll see the small black-and-white square.
3. Tap the in-app camera button in Tailscale and point your phone at the square on your dashboard screen. Tailscale reads the square in about a second.
4. The Tailscale app asks "do you want to connect?" — tap **Approve**.
5. RoamCore's status line changes from **"Show this to your phone"** to **"Already paired"**. You're done — your van is now reachable from your phone wherever you have signal.

If you ever change the secret code, tap **Regenerate** on the dashboard card before you scan again — the square updates and the address below it changes too.

## §4 What to do if it goes wrong

- **"Your phone can't see this QR code — copy this URL instead"** — open the web address shown below the square in any browser on your phone. The Tailscale app picks up the connection automatically.
- **"Waiting for Tailscale account"** — RoamCore doesn't have your secret code yet. Open the Tailscale card and check that the long code field is filled in.
- **"Already paired" but you want to start over** — tap **Regenerate** on the dashboard card, then scan the new square with your phone.
- The square is just a friendly shortcut — if it ever looks broken, blurry, or missing, the web address below it does the same job in a more old-fashioned way.

## §5 Useful links

- For the integration developer / advanced user — see `homeassistant/packages/roamcore_tailscale_qr.yaml` for the raw helper definitions, `homeassistant/packages/scripts/qr_generator.py` for the small generator that draws the square (no extra software needed), and `homeassistant/packages/tests/test_tailscale_qr.py` for the tests that guard the contract.
- The QR code uses a "tailscale login" web address of the form `https://login.tailscale.com/a/<your-secret-key>`. Your phone's Tailscale app reads this and connects you automatically.
- If you want to understand the wizard as a whole (not just the QR step), see [Guided remote access setup](guided-remote-access.md).
