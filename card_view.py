"""Hand-built AppKit views for the usage popover card — no nib/xib, no
third-party UI toolkit. Layout is stacked top-to-bottom in a flipped view so
coordinates read naturally (y grows downward).
"""
from __future__ import annotations

import objc
from AppKit import (
    NSView, NSColor, NSBezierPath, NSTextField, NSFont, NSButton,
    NSMakeRect, NSAttributedString, NSForegroundColorAttributeName,
    NSFontAttributeName, NSCenterTextAlignment, NSImage, NSImageView,
    NSImageSymbolConfiguration, NSUnderlineStyleAttributeName,
    NSUnderlineStyleSingle,
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


class PillBadge(NSButton):
    def initWithFrame_text_target_action_(self, frame, text, target, action):
        self = objc.super(PillBadge, self).initWithFrame_(frame)
        if self is None:
            return None
        self._text = text
        self.setBordered_(False)
        self.setTitle_("")
        self.setTarget_(target)
        self.setAction_(action)
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
            NSUnderlineStyleAttributeName: NSUnderlineStyleSingle,
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


def _link_button(text, size, target, action, underline=False) -> NSButton:
    btn = NSButton.alloc().initWithFrame_(NSMakeRect(0, 0, 10, 16))
    btn.setBordered_(False)
    btn.setButtonType_(1)  # NSButtonTypeMomentaryPushIn-ish, plain text
    attrs = {
        NSFontAttributeName: NSFont.systemFontOfSize_(size),
        NSForegroundColorAttributeName: NSColor.secondaryLabelColor(),
    }
    if underline:
        attrs[NSUnderlineStyleAttributeName] = NSUnderlineStyleSingle
    btn.setAttributedTitle_(NSAttributedString.alloc().initWithString_attributes_(text, attrs))
    btn.sizeToFit()
    btn.setTarget_(target)
    btn.setAction_(action)
    return btn


def _sf_symbol(name, point_size, color=None) -> NSImageView:
    """Standard macOS SF Symbol (e.g. "alarm", "calendar"), tinted to match
    surrounding label text instead of the system's default multicolor
    rendering."""
    image = NSImage.imageWithSystemSymbolName_accessibilityDescription_(name, None)
    config = NSImageSymbolConfiguration.configurationWithPointSize_weight_(point_size, 0)
    image = image.imageWithSymbolConfiguration_(config)
    size = image.size()
    iv = NSImageView.alloc().initWithFrame_(NSMakeRect(0, 0, size.width, size.height))
    iv.setImage_(image)
    iv.setContentTintColor_(color or NSColor.labelColor())
    return iv


def _symbol_button(symbol, target, action, tooltip, point_size=13) -> NSButton:
    """Compact native-style icon button backed by an SF Symbol."""
    image = NSImage.imageWithSystemSymbolName_accessibilityDescription_(symbol, tooltip)
    config = NSImageSymbolConfiguration.configurationWithPointSize_weight_(point_size, 0)
    btn = NSButton.alloc().initWithFrame_(NSMakeRect(0, 0, 28, 28))
    btn.setBordered_(False)
    btn.setImage_(image.imageWithSymbolConfiguration_(config))
    btn.setToolTip_(tooltip)
    btn.setAccessibilityLabel_(tooltip)
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


def build_card(usage, today, updated_text, plan_label, target, open_action, quit_action):
    """Builds and returns the full card NSView. `target` is the NSObject that
    owns the action selectors (open_action / quit_action)."""
    root = FlippedView.alloc().initWithFrame_(NSMakeRect(0, 0, CARD_WIDTH, 10))
    y = 18

    # --- Header -------------------------------------------------------
    title = _label(t("app_name"), size=14, weight="bold")
    title.setFrameOrigin_((PAD_X, y))
    root.addSubview_(title)

    badge_w, badge_h = 64, 18
    quit_btn = _symbol_button("power", target, quit_action, t("quit"))
    quit_x = CARD_WIDTH - PAD_X - quit_btn.frame().size.width
    badge_x = quit_x - 6 - badge_w
    badge = PillBadge.alloc().initWithFrame_text_target_action_(
        NSMakeRect(badge_x, y - 2, badge_w, badge_h), f"{plan_label.upper()} ↗", target, open_action,
    )
    badge.setToolTip_(t("open_claude"))
    badge.setAccessibilityLabel_(t("open_claude"))
    root.addSubview_(badge)

    quit_btn.setFrameOrigin_((quit_x, y - 7))
    root.addSubview_(quit_btn)
    y += 28

    y = _add_window_section(root, y, "alarm", t('five_hour'), usage.five_hour.percent,
                             _relative_reset(usage.five_hour.minutes_to_reset))
    y = _add_divider(root, y)
    y = _add_window_section(root, y, "calendar", t('weekly'), usage.seven_day.percent,
                             _weekday_reset(usage.seven_day.resets_at))
    y = _add_divider(root, y)

    # --- Today ----------------------------------------------------------
    header = _label(t("today_header"), size=10, weight="bold", color=NSColor.tertiaryLabelColor())
    header.setFrameOrigin_((PAD_X, y))
    root.addSubview_(header)
    y += 20

    y = _add_kv_row(root, y, t("messages"), str(today.messages))
    y = _add_kv_row(root, y, t("tokens"), _fmt_tokens(today.tokens))
    y = _add_divider(root, y, before=4, after=6)

    # --- Footer -----------------------------------------------------------
    updated = _label(updated_text, size=11, color=NSColor.tertiaryLabelColor())
    updated.setFrameOrigin_(((CARD_WIDTH - updated.frame().size.width) / 2, y))
    root.addSubview_(updated)
    y += updated.frame().size.height + 10

    root.setFrame_(NSMakeRect(0, 0, CARD_WIDTH, y))
    return root


def _add_window_section(root, y, icon_symbol, label_text, percent, reset_text):
    icon = _sf_symbol(icon_symbol, point_size=13)
    icon_w = icon.frame().size.width
    icon.setFrameOrigin_((PAD_X, y + 2))
    root.addSubview_(icon)

    label = _label(label_text, size=13)
    label.setFrameOrigin_((PAD_X + icon_w + 6, y))
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


def _add_divider(root, y, before=8, after=13):
    y += before
    line = Divider.alloc().initWithFrame_(NSMakeRect(PAD_X, y, CARD_WIDTH - 2 * PAD_X, 1))
    root.addSubview_(line)
    y += after
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
