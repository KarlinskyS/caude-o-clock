# Claude o'clock — dev notes

## Language

Respond to the user in this repo only in Russian, regardless of what
language they write in or what language this file is written in.

A macOS menu bar app showing Claude Code's 5-hour/weekly usage windows,
built from scratch on raw PyObjC/AppKit (no menu bar toolkit, no rumps).
User-facing description and setup steps are in `README.md` — this file is
for whoever (human or agent) touches the code next: architecture, and the
non-obvious reasons things are built the way they are.

## File map

| File | Responsibility |
|---|---|
| `ccusagebar.py` | App entry point + `AppDelegate`: status item, popover lifecycle, overlay/click-dismiss, timers, notifications. Everything UI-orchestration lives here. |
| `card_view.py` | Pure view-building: constructs the popover's NSView tree by hand (no xib/storyboard). `build_card()` is the entry point. |
| `ccusage_api.py` | Reads the OAuth token from Keychain, calls the usage endpoint, parses the response into `Usage`/`Window` dataclasses. |
| `local_stats.py` | Computes today's message/token counts by reading Claude Code's own local session logs (`~/.claude/projects/**/*.jsonl`) — no network call. |
| `formatting.py` | Locale-aware text formatting (relative/absolute reset times, token counts). |
| `i18n.py` | Language detection + string tables. All user-facing text goes through `t()`. |

## Data source: undocumented API, Keychain auth

`ccusage_api.fetch_usage()` calls `https://api.anthropic.com/api/oauth/usage`
— the same internal endpoint `claude.ai/settings/usage` uses. **This is not
a documented or officially supported endpoint.** It could change or
disappear without notice.

Auth: reads `Claude Code-credentials` from the macOS Keychain (the same
JSON `claude` the CLI itself writes after `claude login`) via `security
find-generic-password`. No browser cookies, no separate login flow — this
is the OAuth access token Claude Code already has, reused read-only.

**The endpoint has its own strict, unpublished rate limit**, unrelated to
your actual Claude usage — hit a 429 with `Retry-After: 234` during dev
just from restarting the app repeatedly while testing. Consequences baked
into the code:
- Poll every 5 minutes (`POLL_SECONDS` in `ccusagebar.py`), not more often.
- Opening the popover does **not** trigger a fetch — it shows whatever
  `refresh_()` last fetched (see "Popover performance" below).
- On a 429, `CredentialsError.retry_after` carries the `Retry-After` value;
  `refresh_()` schedules its next attempt at `retry_after + 20s` instead of
  the normal cadence, so a rate-limited window isn't hammered again
  immediately.

## Popover dismiss-on-outside-click: why it's two mechanisms, not one

This took several iterations; each one fixed one case and broke/missed
another, so the reasoning matters if you touch `toggle_`/`dismissPopover_`:

1. **`NSPopoverBehaviorTransient` alone** (AppKit's built-in "close me on
   outside click"): unreliable for accessory-policy (no Dock icon) apps —
   clicking outside just didn't close the popover at all.

2. **A plain `NSEvent` global monitor** (observe-only) calling
   `performClose_`: fixed dismissal, but global monitors can only *observe*
   clicks, never consume them. A click on empty desktop wallpaper still
   reached Finder underneath and triggered macOS Sonoma+'s "click wallpaper
   to reveal desktop" gesture (all windows sweep aside) — a real system
   feature (System Settings → Desktop & Dock), not something we can prevent
   once the click reaches the desktop layer.

3. **Current approach — a real screen-covering window (`ClickCatcherView`
   in `ccusagebar.py`)** sitting just behind the popover: a click on empty
   desktop now lands on *our* window instead of reaching Finder, so the
   reveal-desktop gesture never fires. Side effect (accepted trade-off,
   same as most popovers/dropdowns): clicking another app's window while
   our popover is open now only closes the popover on that first click,
   it doesn't also pass the click through to that app.

4. **But the overlay alone still isn't enough**: Dock, other apps' menu bar
   items, Spotlight etc. are owned by separate system processes rendered
   at window levels our overlay can't (and shouldn't try to) out-level.
   Clicking Dock left the popover stuck open. Fix: **also** keep the
   observe-only global monitor from step 2 (`dock_click_monitor`) purely to
   trigger `dismissPopover_` for those — it can't consume the click, but we
   don't need it to; Dock/Spotlight handle themselves fine either way.

So: overlay window = consumes desktop clicks (prevents the OS gesture).
Global monitor = catches system-UI clicks the overlay can't reach. Both are
needed; neither alone covers every case.

## Popover open/close performance

Also iterative — first pass just made dismissal *work*, a later pass had to
fix it *not being janky*:

- `toggle_()` does **not** rebuild the card view on every open. `_render()`
  (which reconstructs ~20 NSViews via `build_card()`) only runs from inside
  `refresh_()`, i.e. after an actual data fetch (launch, periodic timer, or
  explicit Refresh click). Opening the popover just re-shows whatever's
  already assigned. Rebuilding synchronously on every click was the main
  cause of a visibly janky open.
- The overlay window (`self.overlay`) is ordered into the window stack
  **exactly once**, at launch, and never ordered out again. Toggling
  `setIgnoresMouseEvents_` (cheap property flip) turns its click-catching
  on/off instead. Repeated `orderFront_`/`orderOut_` on a screen-covering
  window forces WindowServer to redo z-order compositing for the whole
  screen — that was the cause of jank on *both* open and close, not the
  popover's own animation.
- `self.popover.setAnimates_(False)` — deliberately no fade. Matches how
  most other menu bar utilities open/close (instant, not animated); a user
  call, not a technical requirement.
- The overlay's window level (needed so it sits below the popover but
  above everything else) is discovered lazily from `popover_window.level()`
  the first time the popover is shown, then cached in `self._overlay_level`
  — never recomputed after that.

## Icon can silently fail to appear at all (WindowServer exhaustion)

Separate from, and more serious than, the highlight cosmetics below: the
menu bar icon can simply **never appear**, with the app process alive,
no crash, no exception, no log output of any kind. User-facing guidance
is in the README ("If the icon doesn't appear in the menu bar"); this is
the technical story for whoever debugs it next.

**Root cause**: `NSStatusBar.systemStatusBar().statusItemWithLength_(-1)`
(the very first line of `applicationDidFinishLaunching_`) talks to
WindowServer over a CoreGraphics/SkyLight connection to actually register
the icon. On a Mac that's been up a long time and/or has accumulated a lot
of menu-bar-item create/destroy churn (many status-bar apps installed,
or -- as happened during this app's own development -- many rapid
restarts across many processes in one sitting), that connection can fail
to establish. Confirmed two ways during development:
- A native crash (`SIGABRT`) was captured in
  `~/Library/Logs/DiagnosticReports/`, with the crashing frame *inside*
  `-[NSStatusBar _statusItemWithLength:withPriority:]` → `CGSConnectionByID`
  → an assertion failure -- i.e. the crash was WindowServer's own code
  refusing to hand out a connection, not anything in this app's Python.
- The same failure can also happen *without* crashing: the call returns a
  perfectly valid-looking `NSStatusItem` object (no exception raised,
  nothing to catch), but WindowServer never actually composites anything
  on screen for it. Reproduced with a 15-line script containing nothing
  but a bare `NSStatusBar` call and no other app logic, ruling out
  anything specific to this codebase.
- A full reboot reliably cleared it in both forms observed.

**Why this app can't detect or route around it itself**: there is no
exception, no error code, and no reliable in-process signal that "the
icon didn't actually render" -- the object handed back is indistinguishable
from a working one. Querying via Accessibility (`System Events` /
`osascript`) to check from *outside* the process is unreliable here too
(permission-gated, and returned false negatives during investigation even
for icons later confirmed visible). There's nothing to retry: the launchd
agent's `KeepAlive` only restarts the process on a *crash*, and a process
that "succeeded" at this call (in the non-crashing failure mode above)
never exits, so `KeepAlive` never even sees a reason to intervene.

**Why other menu-bar apps don't seem to hit this**: probably mostly
because they aren't repeatedly creating and destroying status items across
many rapid app restarts the way this app's own development process did
in one sitting -- ordinary usage (install once, leave it running for
weeks) is a fundamentally different load pattern on whatever WindowServer
resource is getting exhausted, and likely far less likely to trip this in
practice. Not fully verified: whether a long-lived, well-behaved app is
literally immune to this given enough uptime on its own, or just far less
likely to encounter it than this app's own dev-session churn made it.

## Icon highlight while popover is open (known cosmetic bug, unresolved)

Goal: the status bar icon should look "active" for as long as the popover
is open, the way a real `NSMenu` would automatically look. **Current
behavior: it blinks (on, briefly off, back on) on the first click, then
visibly double-blinks on every click after that, and does not reliably
stay highlighted while the popover is open.** This is understood to be
cosmetic only — the popover itself opens/closes correctly and reliably;
only the icon's own highlight is affected. Left as a known limitation
after an extensive, evidence-based investigation (below) rather than
reached for further increasingly invasive workarounds.

What was tried, in order, each confirmed (via temporary debug logging,
removed afterward) to change *something* but never fully fix it:

1. `setHighlighted_(True)` synchronously inside `toggle_()` — clobbered by
   the button cell's own mouseDown/mouseUp tracking loop, which resets
   `highlighted` on release regardless of what's set in between.
2. The same call deferred to the next runloop tick via a zero-interval
   `NSTimer` (`applyHighlight_`), to land after that reset — the icon does
   then stay highlighted, but visibly double-blinks first (native ON,
   native OFF, forced ON) instead of one clean transition.
3. `button.cell().setHighlightsBy_(0)`, meant to stop the cell resetting
   `highlighted` on its own — wrong property: `highlightsBy` picks *which
   visual style* the cell draws for a highlighted state, not whether it
   auto-highlights. With no style selected, nothing drew at all, ours
   included.
4. `setState_(1)`/`setState_(0)` instead of `highlighted` — persists
   independently of the tracking loop in principle, but didn't visibly
   hold in practice either.
5. Removing all manual highlight code, relying on `NSPopover` to highlight
   its own anchor view automatically (confirmed this is real, documented
   behavior: `davidcaddy/MenuBarPopoverExample`, the reference
   implementation Apple-adjacent tutorials for "menu bar icon + NSPopover"
   link to, calls nothing but `popover.show(relativeTo:of:preferredEdge:)`
   / `popover.performClose(_:)`, no highlight code anywhere) — the icon
   highlighted briefly then dropped out while the popover stayed open, so
   whatever's automatic didn't hold for us either.
6. `sendActionOn_` was firing `toggle_` on `NSEventMaskLeftMouseDown`
   rather than the default mouseUp (added for right-click support).
   Theory: NSPopover's anchor-highlight logic assumes the button's own
   mouseDown/mouseUp tracking loop has already finished by the time the
   popover appears, which mouseDown breaks (popover opens *mid*-tracking-
   loop; the loop's eventual mouseUp reset lands after and wins). Switched
   to `NSEventMaskLeftMouseUp | NSEventMaskRightMouseUp` -- no change.
7. Asymmetric `sendActionOn_` (`LeftMouseDown | RightMouseUp`), per a
   documented *different* NSStatusItem highlight bug and its workaround
   (Jesse Squires, jessesquires.com/blog/2019/08/16/workaround-highlight-
   bug-nsstatusitem/, about right-click leaving the icon stuck highlighted
   until a second click) — kept as the current trigger mask since it's a
   real fix for that separate, related failure mode, but confirmed via
   logging that it does not affect the double-blink here.
8. Re-added (2) on top of (6)/(7) — the icon does stay highlighted this
   way, but the double blink from (2) is back. **This is current code.**

Debug logging at every step (comparing `isHighlighted()` before/after each
call, across both rapid and deliberately slow ~2-3s-spaced clicks)
consistently showed the *logical* state transitions are single and
correct on every click — exactly one highlight-on per open, one
highlight-off per close, no duplicate or dropped calls. The visible
double-blink persisted regardless, which points to the actual remaining
issue being at the WindowServer/compositing layer, not in call ordering
we control from Python -- consistent with this Mac's independently
documented WindowServer flakiness (see the icon-registration issue above).

Not attempted: swizzling `-[NSWindow canBecomeKeyWindow]` on the private
`NSStatusBarWindow` class, per Shaheen Gandhi's deeper dive into
NSPopover/NSStatusBarWindow key-window conflicts
(shaheengandhi.com/using-nspopover-with-nsstatusitem/).
Deliberately not pursued: relies on an undocumented private class (could
break on any macOS update), requires runtime method-implementation
swapping (a real crash risk if the signature/calling convention is off),
and addresses a documented symptom (text fields not becoming first
responder, double-click-to-activate when inactive) that isn't obviously
the same root cause as this one -- for a purely cosmetic payoff.

## PyObjC method-naming gotcha (caused several crashes during dev)

Any method defined in an `NSObject` subclass gets scanned into an
Objective-C selector **at class-definition time**, whether or not you ever
intend to call it via objc dispatch. The expected argument count is
inferred from underscores in the name:

> `expected_args = (total underscores in the name) - (1 if the name starts
> with a single leading underscore, else 0)`

A leading underscore is treated as a "this is private" marker and doesn't
count as a keyword separator; every other underscore does. Concretely:
- `refresh_(self, sender)` → 1 trailing underscore, 1 extra arg. OK.
- `_render(self)` → 1 underscore total, all leading → subtract 1 → 0
  expected args. OK (0 extra args).
- `_maybe_notify(self, usage)` → 2 underscores (leading + 1 internal) → 1
  expected. OK (1 extra arg).
- `_closePopoverIfShown(self, event)` → 1 underscore, all leading → 0
  expected, but the method takes 1 extra arg → **`objc.BadPrototypeError`
  at class-definition time.** Fix was renaming to `closePopoverIfShown_`
  (1 trailing underscore, no leading one → 1 expected, matches).
- `handleClick(self, event)` (no underscores at all) → 0 expected, 1
  actual → same crash.

Practical rule used throughout this codebase: for any new method with args,
use the standard trailing-underscore Cocoa style (`name_`, `name_arg2_`,
...) — sidesteps the leading-underscore special case entirely. Private
zero-arg helpers can use a plain `_camelCaseName` (no other underscores).

## i18n

`i18n.py` picks a language from macOS's **ordered** preferred-languages
list (`NSLocale.preferredLanguages()`), not just the first entry — falls
back to English if none of the supported codes match. Override for testing
without touching System Settings: `CCUSAGE_LANG=ja ./.venv/bin/python
ccusagebar.py`. Supported: en, ru, es, de, fr, pt, ja, zh. To add a
language, add a block to `_STRINGS` in `i18n.py` with the same keys as the
`"en"` entry (nothing else needs to change — `card_view.py`,
`ccusagebar.py`, `ccusage_api.py` all just call `t("key", ...)`).

Time formatting (`formatting.py`) uses 12h AM/PM only for `en`
(`USES_12H_CLOCK`), 24h for everything else — a simplification, not
locale-perfect (e.g. UK commonly prefers 24h too), but a reasonable
default.

## Notification logic (`_maybe_notify` in `ccusagebar.py`)

Two kinds, both scoped to the 5-hour window only (not weekly):
- **Threshold crossing** (`THRESHOLDS = (50, 75, 90)`): fires once when
  `five.percent` first crosses each threshold; shows the actual live
  percent (`round(five.percent)`), not the threshold value itself — an
  earlier version accidentally showed the fixed threshold number, which
  looked "hardcoded" since it never matched the real number in the popup.
- **Reset**: detected only when `resets_at` moves more than one minute later
  than the previously observed value. The endpoint returns sub-second clock
  jitter around the same boundary, so treating any later timestamp as a reset
  creates false notifications. This does not use the API's `is_active` field:
  its semantics mean something else, not "this window is fresh". A detected
  reset clears the threshold-notified set so thresholds can refire in the new
  window.
- Dedup state (`self._notified_thresholds`, `self._last_five_hour_percent`)
  lives **only in memory** — resets on every app restart, so a
  already-crossed threshold can renotify after a restart. Not currently
  persisted to disk; acceptable since the app is meant to run continuously
  for the life of a login session, not be restarted often.

## Local dev workflow

```bash
./.venv/bin/python -m py_compile ccusagebar.py   # syntax
./.venv/bin/python -c "import ccusagebar"        # catches objc.BadPrototypeError
                                                  # (class-definition-time selector
                                                  # validation) without launching

# Restart the running instance (it's loaded as a launchd agent):
launchctl bootout gui/$(id -u)/com.ieffai.ccusagebar 2>/dev/null
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.ieffai.ccusagebar.plist
tail -f ccusagebar.err.log   # runtime errors land here, not on screen
```

## Known limitations / possible future work

- Notification dedup state not persisted across restarts (see above).
- No handling for actual macOS display/screen changes after launch — the
  overlay's screen-covering frame is computed once at startup
  (`allScreensFrame()`); connecting/disconnecting a monitor while the app
  is running won't resize it (edge case, not yet hit in practice).
- No automatic token refresh handling beyond what Claude Code's CLI itself
  does — we just re-read the Keychain value on every fetch, so as long as
  the CLI keeps it fresh, we're fine.
