from __future__ import annotations

from datetime import datetime

from i18n import t, weekday_name, USES_12H_CLOCK


def format_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def _format_clock(local_dt: datetime) -> str:
    if USES_12H_CLOCK:
        return local_dt.strftime("%-I:%M %p")
    return local_dt.strftime("%H:%M")


def _format_clock_with_seconds(local_dt: datetime) -> str:
    if USES_12H_CLOCK:
        return local_dt.strftime("%-I:%M:%S %p")
    return local_dt.strftime("%H:%M:%S")


def format_relative_reset(minutes: int | None) -> str:
    if minutes is None:
        return "—"
    h, m = divmod(minutes, 60)
    if h:
        return t("resets_in", h=h, m=m)
    return t("resets_in_short", m=m)


def format_weekday_reset(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    local = dt.astimezone()
    return t("resets_on", weekday=weekday_name(local.weekday()), time=_format_clock(local))


def format_updated_at(dt: datetime) -> str:
    local = dt.astimezone()
    return t("updated", time=_format_clock_with_seconds(local))
