"""Claude o'clock — a from-scratch menu bar usage panel for Claude Code.

Not a clone of any existing app's code: custom AppKit popover (own layout,
own palette, own local-session stats section), built directly on PyObjC
rather than a menu-bar UI toolkit.

Run: ./.venv/bin/python ccusagebar.py
"""
from __future__ import annotations

import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

import objc
from AppKit import (
    NSApplication, NSApplicationActivationPolicyAccessory, NSStatusBar,
    NSViewController, NSPopover, NSPopoverBehaviorTransient, NSObject,
    NSWorkspace, NSURL, NSUserNotification, NSUserNotificationCenter,
    NSMakeRect, NSMinYEdge, NSView, NSWindow, NSScreen, NSColor,
    NSWindowStyleMaskBorderless, NSBackingStoreBuffered,
    NSWindowCollectionBehaviorCanJoinAllSpaces, NSWindowCollectionBehaviorStationary,
    NSWindowCollectionBehaviorIgnoresCycle, NSWindowCollectionBehaviorFullScreenAuxiliary,
    NSEvent, NSEventMaskLeftMouseDown, NSEventMaskRightMouseDown,
    NSImage, NSMakeSize, NSImageLeft,
)
from Foundation import NSTimer

from ccusage_api import fetch_usage, CredentialsError
from local_stats import today_stats
from formatting import format_updated_at
from card_view import build_card
from i18n import t as tr

# The usage endpoint is undocumented and enforces its own (fairly strict,
# unpublished) rate limit -- unrelated to your actual 5h/weekly Claude usage.
# Poll gently: on a 429 we saw Retry-After ~234s, so stay well above that,
# and don't fetch on every popover open (see toggle_ / _render_cached).
POLL_SECONDS = 300.0
MIN_RETRY_SECONDS = 60.0
THRESHOLDS = (50, 75, 90)
CLAUDE_USAGE_URL = "https://claude.ai/settings/usage"
MENUBAR_ICON_PATH = Path(__file__).resolve().parent / "assets" / "menubar-glyph.png"


def notify(title: str, subtitle: str, message: str):
    n = NSUserNotification.alloc().init()
    n.setTitle_(title)
    n.setSubtitle_(subtitle)
    n.setInformativeText_(message)
    NSUserNotificationCenter.defaultUserNotificationCenter().deliverNotification_(n)


def log_error(context: str, exc: Exception):
    print(f"[{datetime.now().isoformat()}] {context}: {exc}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)


class ClickCatcherView(NSView):
    """Invisible, screen-covering view shown behind the popover while it's
    open. A regular NSEvent monitor can only *observe* outside clicks, not
    consume them -- so a click on empty desktop still reaches the Finder
    layer underneath and triggers macOS's "click wallpaper to reveal
    desktop" gesture. This view is a real window that physically sits in
    front of the desktop, so the click lands on *us* instead and never
    reaches the desktop at all.
    """

    def initWithFrame_target_(self, frame, target):
        self = objc.super(ClickCatcherView, self).initWithFrame_(frame)
        if self is None:
            return None
        self._target = target
        return self

    def mouseDown_(self, event):
        self._target.dismissPopover_(event)

    def rightMouseDown_(self, event):
        self._target.dismissPopover_(event)

    def acceptsFirstMouse_(self, event):
        # Without this, the very first click after our overlay appears can
        # be swallowed as a plain "activate this window" click instead of
        # being delivered to mouseDown_.
        return True


class AppDelegate(NSObject):

    def init(self):
        self = objc.super(AppDelegate, self).init()
        if self is None:
            return None
        self._last_five_hour_percent = None
        self._last_resets_at = None
        self._notified_thresholds = set()
        self._timer = None
        self._usage = None
        self._today = None
        self._last_error = None
        self._overlay_level = None
        return self

    def applicationDidFinishLaunching_(self, notification):
        self._menubar_icon = NSImage.alloc().initByReferencingFile_(str(MENUBAR_ICON_PATH))
        self._menubar_icon.setTemplate_(True)
        self._menubar_icon.setSize_(NSMakeSize(18, 18))

        self.status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(-1)
        button = self.status_item.button()
        button.setImage_(self._menubar_icon)
        button.setImagePosition_(NSImageLeft)
        button.setTitle_(" …")
        button.setTarget_(self)
        button.setAction_(objc.selector(self.toggle_, signature=b"v@:@"))

        self.popover = NSPopover.alloc().init()
        self.popover.setBehavior_(NSPopoverBehaviorTransient)
        self.popover.setAnimates_(False)
        self.view_controller = NSViewController.alloc().init()
        self.popover.setContentViewController_(self.view_controller)

        # NSPopoverBehaviorTransient's built-in outside-click dismissal is
        # unreliable for accessory-policy (menu-bar-only, no Dock icon) apps,
        # and a plain NSEvent monitor can only observe clicks, not consume
        # them -- so a click on empty desktop would still trigger macOS's
        # "click wallpaper to reveal desktop" gesture underneath. Instead we
        # show a real, invisible, screen-covering window (see
        # ClickCatcherView) behind the popover to physically catch the click.
        #
        # It's ordered into the window stack exactly once, here, and stays
        # there permanently. Repeatedly calling orderFront_/orderOut_ on a
        # screen-covering window on every single popover open/close forces
        # WindowServer to redo z-order compositing for the whole screen each
        # time -- that was the actual cause of the janky open/close, not the
        # popover animation itself. Toggling ignoresMouseEvents_ instead is a
        # cheap property flip with no compositing cost.
        self.overlay = self.buildOverlay()
        self.overlay.setIgnoresMouseEvents_(True)
        self.overlay.orderFront_(None)

        # The overlay only catches clicks below its own window level, which
        # sits just under the popover -- it can't out-level system UI like
        # the Dock or other apps' menu bar items (those are owned by other
        # processes at very high levels and would otherwise leave the
        # popover stuck open). A global monitor sees those regardless of
        # level -- it can't consume the click (so Dock clicks still work
        # normally), but that's fine here, we only need it to close us.
        self.dock_click_monitor = NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
            NSEventMaskLeftMouseDown | NSEventMaskRightMouseDown, self.handleOutsideClick_
        )

        NSUserNotificationCenter.defaultUserNotificationCenter().setDelegate_(self)

        self.refresh_(None)

    def userNotificationCenter_didActivateNotification_(self, center, notification):
        if not self.popover.isShown():
            self.toggle_(None)

    def userNotificationCenter_shouldPresentNotification_(self, center, notification):
        return True

    def allScreensFrame(self):
        screens = NSScreen.screens()
        if not screens:
            return NSMakeRect(0, 0, 1920, 1080)
        x0 = min(s.frame().origin.x for s in screens)
        y0 = min(s.frame().origin.y for s in screens)
        x1 = max(s.frame().origin.x + s.frame().size.width for s in screens)
        y1 = max(s.frame().origin.y + s.frame().size.height for s in screens)
        return NSMakeRect(x0, y0, x1 - x0, y1 - y0)

    def buildOverlay(self):
        frame = self.allScreensFrame()
        win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            frame, NSWindowStyleMaskBorderless, NSBackingStoreBuffered, False
        )
        win.setOpaque_(False)
        win.setBackgroundColor_(NSColor.clearColor())
        win.setHasShadow_(False)
        win.setReleasedWhenClosed_(False)
        win.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces
            | NSWindowCollectionBehaviorStationary
            | NSWindowCollectionBehaviorIgnoresCycle
            | NSWindowCollectionBehaviorFullScreenAuxiliary
        )
        win.setContentView_(ClickCatcherView.alloc().initWithFrame_target_(frame, self))
        return win

    def showOverlay(self):
        # The window is already in the stack (ordered once, at launch) --
        # just need it interactive. Level only needs figuring out once: the
        # popover's own window doesn't exist until the first time it's been
        # shown, so we discover the level lazily and cache it, rather than
        # re-querying/re-setting it (itself not free) on every open.
        if self._overlay_level is None:
            popover_window = self.popover.contentViewController().view().window()
            if popover_window is not None:
                self._overlay_level = popover_window.level() - 1
                self.overlay.setLevel_(self._overlay_level)
        self.overlay.setIgnoresMouseEvents_(False)

    def hideOverlay(self):
        self.overlay.setIgnoresMouseEvents_(True)

    def dismissPopover_(self, sender):
        if self.popover.isShown():
            self.popover.performClose_(None)
        self.hideOverlay()
        self.status_item.button().setHighlighted_(False)

    def handleOutsideClick_(self, event):
        if self.popover.isShown():
            self.dismissPopover_(event)

    def toggle_(self, sender):
        if self.popover.isShown():
            self.dismissPopover_(sender)
            return
        if self._usage is None and self._last_error is None:
            self.refresh_(None)  # first-ever open before any data arrived
        # Otherwise: don't rebuild. refresh_() already built and assigned the
        # current card the last time it ran (launch or periodic timer), so
        # the popover's content is already up to date. Rebuilding ~20 views
        # again here, synchronously, right as the popover opens, was pure
        # redundant work that made the open feel janky.
        self.popover.showRelativeToRect_ofView_preferredEdge_(
            self.status_item.button().bounds(), self.status_item.button(), NSMinYEdge
        )
        # Called after showRelativeToRect: the popover's own backing window
        # doesn't exist until it's been shown at least once, and showOverlay
        # needs that window (to read its level) the first time it runs.
        self.showOverlay()
        # The button's own mouseDown tracking loop resets highlighted=NO as
        # it wraps up *after* this action method returns, so setting it here
        # directly gets immediately overwritten. Defer to the next runloop
        # tick, once that tracking loop has actually finished.
        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.0, self, objc.selector(self.applyHighlight_, signature=b"v@:@"), None, False
        )

    def applyHighlight_(self, timer):
        if self.popover.isShown():
            self.status_item.button().setHighlighted_(True)

    def refresh_(self, sender):
        if self._timer is not None:
            self._timer.invalidate()
            self._timer = None

        next_delay = POLL_SECONDS
        try:
            self._usage = fetch_usage()
            self._today = today_stats()
            self._last_error = None
            self._maybe_notify(self._usage)
            self._last_five_hour_percent = self._usage.five_hour.percent
            self._last_resets_at = self._usage.five_hour.resets_at
        except CredentialsError as e:
            log_error("fetch_usage failed", e)
            self._last_error = str(e)
            retry_after = getattr(e, "retry_after", None)
            next_delay = max(retry_after + 20, MIN_RETRY_SECONDS) if retry_after else MIN_RETRY_SECONDS
        except Exception as e:
            log_error("fetch_usage failed (unexpected)", e)
            self._last_error = tr("err_unexpected", err=e)
            next_delay = MIN_RETRY_SECONDS

        self._render()
        self._timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            next_delay, self, objc.selector(self.refresh_, signature=b"v@:@"), None, False
        )

    def _render(self):
        if self._last_error is not None:
            button = self.status_item.button()
            button.setImage_(None)
            button.setTitle_("⚠️")
            self._render_error(self._last_error)
            return

        usage, today = self._usage, self._today
        button = self.status_item.button()
        button.setImage_(self._menubar_icon)
        button.setTitle_(f" {usage.five_hour.percent:.0f}%")
        card = build_card(
            usage, today,
            format_updated_at(datetime.now(timezone.utc)),
            usage.plan,
            self,
            objc.selector(self.refresh_, signature=b"v@:@"),
            objc.selector(self.openBrowser_, signature=b"v@:@"),
            objc.selector(self.quit_, signature=b"v@:@"),
        )
        self.view_controller.setView_(card)
        self.popover.setContentSize_(card.frame().size)

    def _render_error(self, message: str):
        from card_view import _label, FlippedView
        from AppKit import NSMakeRect, NSColor
        view = FlippedView.alloc().initWithFrame_(NSMakeRect(0, 0, 300, 70))
        label = _label(message, size=12, color=NSColor.secondaryLabelColor())
        label.setFrameOrigin_((18, 18))
        label.setFrame_(NSMakeRect(18, 18, 264, 40))
        view.addSubview_(label)
        self.view_controller.setView_(view)
        self.popover.setContentSize_(view.frame().size)

    def _maybe_notify(self, usage):
        five = usage.five_hour
        if self._last_five_hour_percent is not None and five.percent < self._last_five_hour_percent - 20:
            self._notified_thresholds.clear()

        for threshold in THRESHOLDS:
            if five.percent >= threshold and threshold not in self._notified_thresholds:
                self._notified_thresholds.add(threshold)
                notify(
                    tr("notif_title"),
                    tr("notif_threshold_subtitle", pct=round(five.percent)),
                    tr("notif_threshold_message"),
                )

        if (
            self._last_resets_at is not None
            and five.resets_at is not None
            and five.resets_at > self._last_resets_at
        ):
            self._notified_thresholds.clear()
            notify(tr("notif_title"), tr("notif_reset_subtitle"), tr("notif_reset_message"))

    def openBrowser_(self, sender):
        NSWorkspace.sharedWorkspace().openURL_(NSURL.URLWithString_(CLAUDE_USAGE_URL))

    def quit_(self, sender):
        self.hideOverlay()
        if getattr(self, "dock_click_monitor", None) is not None:
            NSEvent.removeMonitor_(self.dock_click_monitor)
            self.dock_click_monitor = None
        NSApplication.sharedApplication().terminate_(self)


def main():
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)
    app.run()


if __name__ == "__main__":
    main()
