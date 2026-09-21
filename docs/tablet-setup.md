# Putting the strip on an iPad or Android tablet

The strip (`/display`) is meant to sit on the same tablet as your mixer app and
stay visible while you mix. Nothing is installed on the tablet: it opens a web
page served by the computer with the microphone. This page covers how to make
that page look and behave like a small always-visible app.

The iPad workflow below is what the project was built around and has been used
at events. The Android notes are best-effort and have **not** been tested by the
project; treat them as a starting point and tell us what you find.

## The idea: overlap, don't split

The strip needs very little height (one row of numbers) but browsers will not
let a window shrink below a minimum size, and a side-by-side split wastes the
mixer app's screen. The workflow that works:

1. Open the strip in its own window and make that window as short as the
   system allows.
2. Put the strip window **behind** the mixer app, positioned so that only the
   strip peeks out (usually along the bottom or top edge).
3. Resize the mixer app's window to leave that edge uncovered.

The strip keeps updating while it is in the background; the mixer app keeps the
full width. Tap the strip's **•••** button to set the strip's own height, digit
size and position inside its window so it lines up with the uncovered edge.
Those settings are saved in that browser, per tablet.

## iPad

### Make it a menuless "app" (recommended)

Open the strip address in **Safari** (not Chrome; only Safari can create
standalone home-screen apps on iOS/iPadOS), then:

1. Tap the **Share** button (square with an arrow).
2. Tap **Add to Home Screen**.
3. Keep or edit the name, tap **Add**.

The new icon opens the strip full-screen with no address bar or tabs, because
the app declares itself as a standalone web app. Plain `http://` on your LAN is
fine for this on iPadOS. The home-screen app remembers its own strip settings,
separate from Safari's.

### Windowing

- **iPadOS 26 and later:** any app window, including the home-screen web app,
  can be resized by dragging its corner and freely overlapped. Shrink the strip
  window to its minimum height and place it along the bottom edge; then size
  the mixer app to stop just above it.
- **iPadOS 16–18 with Stage Manager** (M-series iPads and iPad Pro 2018 or
  later): turn on Stage Manager in Control Centre, then drag the window
  corner to resize and overlap the same way.
- **Older iPads / Stage Manager off:** use Split View. Give the strip the
  narrow side and set the strip to portrait-friendly sizing with **•••**. Slide
  Over also works but covers part of the mixer app.

The minimum window height is set by iPadOS, not by this app; it is larger than
the strip needs, which is why the overlap trick exists. Home-screen web apps
support Split View and windowing on current iPadOS; if yours will not resize,
open the strip in Safari instead and use that window.

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
  functionally the same as the iPad overlap, sometimes with the strip on top
  rather than behind. Minimum window sizes still apply.

If you get a clean Android setup working, please open an issue with the tablet,
Android version and browser so this page can be improved.

## Phone

A phone works as a second readout (for example in the operator's pocket) but not
as an overlay; just open the strip address and use **•••** to size it for the
phone's width.
