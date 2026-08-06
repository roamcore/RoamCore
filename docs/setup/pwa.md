# RoamCore on your phone

This shows you how to put RoamCore on your phone's home screen, so you
can open it with one tap — even when your van is out of LTE range or
parked somewhere with no signal at all.

## 1. What this is

RoamCore is a small installable app for your phone. It looks like a
regular app icon, but it doesn't need to be downloaded from an app
store. Your phone quietly keeps a copy of the dashboard so the last
screen you saw is still there when the internet is gone.

## 2. What you see

After you install it, you'll have an RoamCore icon on your home screen
next to your other apps. When you tap it, the app opens full-screen —
no browser bar, no address line, no "which tab was that?" confusion.
You'll see:

- Your van's dashboard.
- A small **Online** or **Offline** tag at the top right. Honest, not
  decorative — it tells you whether RoamCore can actually reach your
  van right now.
- The last-known state of your van if the Hub is unreachable, with a
  "Couldn't reach your van" message instead of a blank screen.

## 3. What you do

You install it once. After that, it works by itself.

**On Android (Chrome):**

1. Open RoamCore in Chrome on your phone.
2. Wait a couple of seconds — a small banner appears at the bottom of
   the screen saying **Add RoamCore to your home screen**.
3. Tap **Install**. The RoamCore icon appears on your home screen.

**On iPhone or iPad (Safari):**

1. Open RoamCore in Safari.
2. Tap the **Share** button (the square with an arrow pointing up).
3. Scroll the menu and tap **Add to Home Screen**.
4. Tap **Add**. The RoamCore icon appears on your home screen.

If you ever tap **Not now** on the install banner, it won't ask again on
that phone. You can still install it later by following the steps above.

## 4. What to do if it goes wrong

If RoamCore can't reach your van, you'll see a page titled **Couldn't
reach your van**. That page is honest — it tells you when your Hub was
last heard from, instead of pretending everything is fine.

Try these, in order:

1. **Pull down** on the page (or tap **Try again**) to retry the
   connection.
2. **Check your phone's connection.** Your phone may be on Wi-Fi that
   has no internet, or you may be out of LTE range. The RoamCore icon
   stays on your home screen either way — your phone keeps the last
   screen you saw.
3. **Check your van's power.** If your van's battery is dead or solar
   is shaded, the Hub goes quiet. The app will come back to life the
   moment the Hub is reachable again.
4. **Still stuck?** Open the regular Home Assistant app on your phone.
   If RoamCore can reach Home Assistant from there but not from the
   installed icon, reinstall RoamCore by removing it from your home
   screen and following the steps above.

You won't lose any data — RoamCore stores nothing on its own. Everything
lives on your Hub, and your phone keeps only the parts of the dashboard
you've already opened.

## 5. FAQ

**Will RoamCore send me notifications?**

Not by itself. RoamCore can show you notifications when your Hub asks
it to — for example, "fresh water below 20%". To turn this on, you need
to add a small access code from your notification provider in RoamCore
settings. RoamCore never sends notifications on its own, and never
sends any data off your phone without you asking.

**Why is this a "PWA" and not a real app from the store?**

A PWA — "installable web app" — gives you the same one-tap home-screen
experience without needing an app store, an account, or a download. It
works on Android, iPhone, iPad, and any laptop browser. Updates land
automatically the next time you open RoamCore — no "update available"
popup, no app store approval. The trade-off is that some phone features
(like background GPS) are limited; if you need those, use the Home
Assistant Companion app instead.

**When should I use the Home Assistant app instead?**

Use the Home Assistant Companion app when you want background location,
phone sensor integration (battery, motion), or push notifications that
wake your phone up. Use RoamCore (this PWA) when you want the
RoamCore-specific dashboard on your home screen, even when the
Companion app is signed out or your Hub is unreachable.
