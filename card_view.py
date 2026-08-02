"""Hand-built AppKit views for the usage popover card — no nib/xib, no
third-party UI toolkit. Layout is stacked top-to-bottom in a flipped view so
coordinates read naturally (y grows downward).
"""
from __future__ import annotations

import objc
from AppKit import (
    NSView, NSColor, NSBezierPath, NSTextField, NSFont, NSButton,
    NSMakeRect, NSAttributedString, NSForegroundColorAttributeName,
    NSFontAttributeName, NSCenterTextAlignment,
)

from i18n import t

CARD_WIDTH = 300
PAD_X = 18
BAR_HEIGHT = 6

COLOR_GOOD = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.29, 0.45, 0.94, 1.0)   # indigo
COLOR_WARN = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.92, 0.62, 0.13, 1.0)   # amber
COLOR_HOT = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.86, 0.29, 0.29, 1.0)    # red


def bar_color(percent: float) -> NSColor:
    if percent >= 90:
        return COLOR_HOT
    if percent >= 70:
        return COLOR_WARN
    return COLOR_GOOD


class FlippedView(NSView):
    def isFlipped(self):
        return True


class Divider(NSView):
    def drawRect_(self, rect):
        NSColor.separatorColor().setFill()
        NSBezierPath.fillRect_(self.bounds())


class ProgressBar(NSView):
    def initWithFrame_progress_color_(self, frame, progress, color):
        self = objc.super(ProgressBar, self).initWithFrame_(frame)
        if self is None:
            return None
        self._progress = max(0.0, min(1.0, progress))
        self._color = color
        return self

    def drawRect_(self, rect):
        bounds = self.bounds()
        radius = bounds.size.height / 2.0
        track = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(bounds, radius, radius)
        NSColor.quaternaryLabelColor().setFill()
        track.fill()
        if self._progress > 0:
            w = max(bounds.size.height, bounds.size.width * self._progress)
            fill_rect = NSMakeRect(0, 0, w, bounds.size.height)
            fill_path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(fill_rect, radius, radius)
            self._color.setFill()
            fill_path.fill()


class PillBadge(NSView):
    def initWithFrame_text_(self, frame, text):
        self = objc.super(PillBadge, self).initWithFrame_(frame)
        if self is None:
            return None
        self._text = text
        return self

    def drawRect_(self, rect):
        bounds = self.bounds()
        radius = bounds.size.height / 2.0
        path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(bounds, radius, radius)
        NSColor.controlAccentColor().colorWithAlphaComponent_(0.16).setFill()
        path.fill()
        attrs = {
            NSFontAttributeName: NSFont.boldSystemFontOfSize_(10),
            NSForegroundColorAttributeName: NSColor.controlAccentColor(),
        }
        s = NSAttributedString.alloc().initWithString_attributes_(self._text.upper(), attrs)
        size = s.size()
        x = (bounds.size.width - size.width) / 2.0
        y = (bounds.size.height - size.height) / 2.0
        s.drawAtPoint_((x, y))


def _label(text, size=13, weight="regular", color=None) -> NSTextField:
    field = NSTextField.labelWithString_(text)
    if weight == "bold":
        field.setFont_(NSFont.boldSystemFontOfSize_(size))
    elif weight == "semibold":
        field.setFont_(NSFont.systemFontOfSize_weight_(size, 0.3))
    else:
        field.setFont_(NSFont.systemFontOfSize_(size))
    field.setTextColor_(color or NSColor.labelColor())
    field.sizeToFit()
    return field


def _link_button(text, size, target, action) -> NSButton:
    btn = NSButton.alloc().initWithFrame_(NSMakeRect(0, 0, 10, 16))
    btn.setBordered_(False)
    btn.setButtonType_(1)  # NSButtonTypeMomentaryPushIn-ish, plain text
    attrs = {
        NSFontAttributeName: NSFont.systemFontOfSize_(size),
        NSForegroundColorAttributeName: NSColor.secondaryLabelColor(),
    }
    btn.setAttributedTitle_(NSAttributedString.alloc().initWithString_attributes_(text, attrs))
    btn.sizeToFit()
    btn.setTarget_(target)
    btn.setAction_(action)
    return btn


def _bordered_button(text, target, action, size=13, prominent=False, tooltip=None) -> NSButton:
    """A real bezeled push button -- for actions that deserve more visual
    weight than `_link_button`'s plain text link (e.g. recovering from an
    error, quitting)."""
    btn = NSButton.alloc().initWithFrame_(NSMakeRect(0, 0, 10, 30))
    btn.setBezelStyle_(1)  # NSBezelStyleRounded
    btn.setBordered_(True)
    font = NSFont.systemFontOfSize_(size)
    if prominent:
        btn.setBezelColor_(NSColor.controlAccentColor())
        attrs = {
            NSFontAttributeName: font,
            NSForegroundColorAttributeName: NSColor.whiteColor(),
        }
        btn.setAttributedTitle_(NSAttributedString.alloc().initWithString_attributes_(text, attrs))
    else:
        btn.setFont_(font)
        btn.setTitle_(text)
    if tooltip:
        btn.setToolTip_(tooltip)
    btn.setTarget_(target)
    btn.setAction_(action)
    btn.sizeToFit()
    frame = btn.frame()
    btn.setFrameSize_((max(frame.size.width, 40), max(frame.size.height, 28)))
    return btn


def build_card(usage, today, updated_text, plan_label, target,
                refresh_action, open_action, quit_action):
    """Builds and returns the full card NSView. `target` is the NSObject that
    owns the action selectors (refresh_action / open_action / quit_action)."""
    root = FlippedView.alloc().initWithFrame_(NSMakeRect(0, 0, CARD_WIDTH, 10))
    y = 18

    # --- Header -------------------------------------------------------
    title = _label(t("app_name"), size=14, weight="bold")
    title.setFrameOrigin_((PAD_X, y))
    root.addSubview_(title)

    badge_w, badge_h = 48, 18
    badge = PillBadge.alloc().initWithFrame_text_(
        NSMakeRect(CARD_WIDTH - PAD_X - badge_w, y - 2, badge_w, badge_h), plan_label
    )
    root.addSubview_(badge)
    y += 28

    y = _add_window_section(root, y, f"⏱  {t('five_hour')}", usage.five_hour.percent,
                             _relative_reset(usage.five_hour.minutes_to_reset))
    y = _add_divider(root, y)
    y = _add_window_section(root, y, f"📅  {t('weekly')}", usage.seven_day.percent,
                             _weekday_reset(usage.seven_day.resets_at))
    y = _add_divider(root, y)

    # --- Today ----------------------------------------------------------
    header = _label(t("today_header"), size=10, weight="bold", color=NSColor.tertiaryLabelColor())
    header.setFrameOrigin_((PAD_X, y))
    root.addSubview_(header)
    y += 20

    y = _add_kv_row(root, y, t("messages"), str(today.messages))
    y = _add_kv_row(root, y, t("tokens"), _fmt_tokens(today.tokens))
    y += 4
    y = _add_divider(root, y)

    # --- Footer -----------------------------------------------------------
    # Quit's geometry decides Retry's -- Retry sits centered directly above
    # it, not pinned to the card's right edge (that reads lopsided once the
    # icon is narrower than the "Quit" button beneath it).
    quit_btn = _bordered_button(t("quit"), target, quit_action, size=13)
    quit_x = CARD_WIDTH - PAD_X - quit_btn.frame().size.width
    quit_center_x = quit_x + quit_btn.frame().size.width / 2

    refresh_btn = _link_button("⟳", 20, target, refresh_action)
    refresh_btn.setToolTip_(t("refresh"))
    refresh_btn.setFrameOrigin_((quit_center_x - refresh_btn.frame().size.width / 2, y))

    updated = _label(updated_text, size=11, color=NSColor.tertiaryLabelColor())
    updated.setFrameOrigin_((PAD_X, y + (refresh_btn.frame().size.height - updated.frame().size.height) / 2))
    root.addSubview_(updated)
    root.addSubview_(refresh_btn)
    y += refresh_btn.frame().size.height + 10

    # Row 2: Open Claude (link) and Quit (bordered), directly under Retry.
    open_btn = _link_button(t("open_claude"), 11, target, open_action)
    open_btn.setFrameOrigin_((PAD_X, y + (quit_btn.frame().size.height - open_btn.frame().size.height) / 2))
    quit_btn.setFrameOrigin_((quit_x, y))
    root.addSubview_(open_btn)
    root.addSubview_(quit_btn)

    y += quit_btn.frame().size.height + 10

    root.setFrame_(NSMakeRect(0, 0, CARD_WIDTH, y))
    return root


def _add_window_section(root, y, label_text, percent, reset_text):
    label = _label(label_text, size=13)
    label.setFrameOrigin_((PAD_X, y))
    root.addSubview_(label)

    pct = _label(f"{percent:.0f}%", size=15, weight="bold")
    pct.sizeToFit()
    pct.setFrameOrigin_((CARD_WIDTH - PAD_X - pct.frame().size.width, y - 1))
    root.addSubview_(pct)
    y += 24

    bar = ProgressBar.alloc().initWithFrame_progress_color_(
        NSMakeRect(PAD_X, y, CARD_WIDTH - 2 * PAD_X, BAR_HEIGHT),
        percent / 100.0, bar_color(percent),
    )
    root.addSubview_(bar)
    y += BAR_HEIGHT + 8

    sub = _label(reset_text, size=11, color=NSColor.secondaryLabelColor())
    sub.setFrameOrigin_((PAD_X, y))
    root.addSubview_(sub)
    y += 24
    return y


def _add_kv_row(root, y, key, value):
    k = _label(key, size=12, color=NSColor.secondaryLabelColor())
    k.setFrameOrigin_((PAD_X, y))
    root.addSubview_(k)

    v = _label(value, size=12, weight="bold")
    v.sizeToFit()
    v.setFrameOrigin_((CARD_WIDTH - PAD_X - v.frame().size.width, y))
    root.addSubview_(v)
    y += 20
    return y


def _add_divider(root, y):
    y += 8
    line = Divider.alloc().initWithFrame_(NSMakeRect(PAD_X, y, CARD_WIDTH - 2 * PAD_X, 1))
    root.addSubview_(line)
    y += 13
    return y


def _relative_reset(minutes):
    from formatting import format_relative_reset
    return format_relative_reset(minutes)


def _weekday_reset(dt):
    from formatting import format_weekday_reset
    return format_weekday_reset(dt)


def _fmt_tokens(n):
    from formatting import format_tokens
    return format_tokens(n)
