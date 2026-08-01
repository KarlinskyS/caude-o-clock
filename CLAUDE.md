# Caude o'clock — dev notes

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

## Icon highlight while popover is open

`NSStatusBarButton` doesn't automatically stay highlighted for a
manually-managed popover the way it would for a real `NSMenu`. We call
`setHighlighted_(True)` ourselves — but doing it synchronously inside
`toggle_()` gets immediately overwritten, because `toggle_()` runs *from
inside* the button's own mouseDown tracking loop, which resets
`highlighted=NO` as it wraps up *after* the action method returns. Fix:
defer the `setHighlighted_(True)` call to the next runloop tick via a
zero-interval `NSTimer` (`applyHighlight_`), so it runs after that tracking
loop has actually finished.

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
- **Reset**: detected by `resets_at` moving to a later timestamp than the
  previously observed one (not by any "is_active" field in the API
  response — that field's semantics turned out to mean something else,
  not "this window is fresh"). Clears the threshold-notified set so they
  can refire in the new window.
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
