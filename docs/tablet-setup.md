# Putting the strip on an iPad or Android tablet

The strip (`/display`) is meant to sit on the same tablet as your mixer app and
stay visible while you mix. Nothing is installed on the tablet: it opens a web
page served by the computer with the microphone. This page covers how to make
that page look and behave like a small always-visible app.

The iPad workflow below is what the project was built around and has been used
at events. The Android notes are best-effort and have **not** been tested by the
project; treat them as a starting point and tell us what you find.

## The idea: leave it behind the mixer app

The strip needs very little height (one row of numbers), but a tablet will not
let a window shrink that small, and a side-by-side split wastes the mixer app's
screen. So instead of splitting, you leave the strip **behind** the mixer app
and make the mixer app a little shorter so the strip shows above it.

## iPad

This is the setup the project was built around and uses at events.

1. Open the strip address in **Safari** (it has to be Safari; only Safari can
   create standalone home-screen apps on iPadOS). Tap the **Share** button
   (square with an arrow) → **Add to Home Screen** → **Add**. Plain `http://`
   on your LAN is fine for this.
2. Launch the new home-screen icon. It opens the strip full-screen with no
   address bar or tabs — a menuless app.
3. Open Mixing Station (or your mixer app). It comes to the front; the strip
   stays open behind it.
4. Resize Mixing Station so it leaves enough room at the top of the screen to
   see the strip above it. On iPadOS 26 drag the window's corner; on
   iPadOS 16–18 turn on Stage Manager (Control Centre) and do the same.
5. Tap the strip's **•••** button once to set its height, digit size and
   position so it lines up with the space you left. Those settings are saved
   on that iPad, separately for the home-screen app and for Safari.

The strip keeps updating while it is behind Mixing Station, and Mixing Station
keeps the full width. If you switch apps, bring Mixing Station back and the
arrangement is still there.

If your iPad cannot resize windows at all (older models without Stage Manager),
use Split View instead: give the strip the narrow side and size it with **•••**.

### Keeping it awake

Set **Settings → Display & Brightness → Auto-Lock** to Never (or use Guided
Access) for the event. The strip does not keep the screen awake by itself.

## Android

### Home-screen shortcut

Chrome, Edge, Samsung Internet and Firefox all offer **⋮ → Add to Home screen**.
The catch: Android only opens a page as a standalone, chrome-less app when it is
served over **HTTPS**. This app is served over plain HTTP on your LAN, so the
shortcut opens as a normal browser tab with the address bar visible. Options:

- Live with the address bar; Chrome hides it once you scroll, and in landscape
  it is small.
- Use a kiosk-style browser (for example "Fully Kiosk Browser") that can show a
  URL full-screen with no UI. This is a third-party app; the project has not
  tested it.
- Samsung tablets: Samsung Internet has a full-screen option in its menu.

### Windowing

- **Split screen:** open the mixer app, then from Recents choose *Split screen*
  and pick the browser. The divider is draggable but each pane has a minimum
  size, as on iPad, so the strip pane will be taller than the strip needs.
- **Pop-up / freeform windows:** Samsung's *Pop-up view* and the desktop-style
  windowing on recent Android tablets (Android 15/16 on Pixel Tablet, Samsung
  DeX) allow a small floating browser window that can sit over the mixer app —
  functionally the same as the iPad arrangement, sometimes with the strip on
  top rather than behind. Minimum window sizes still apply.

If you get a clean Android setup working, please open an issue with the tablet,
Android version and browser so this page can be improved.

## Phone

A phone works as a second readout (for example in the operator's pocket) but not
as an overlay; just open the strip address and use **•••** to size it for the
phone's width.
