from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch

from ccusage_api import Usage, Window
from ccusagebar import AppDelegate, THRESHOLDS


def usage(percent: float, resets_at: datetime) -> Usage:
    return Usage(
        five_hour=Window(percent=percent, resets_at=resets_at, active=True),
        seven_day=Window(percent=0, resets_at=None, active=True),
        plan="Pro",
    )


class ResetNotificationTest(unittest.TestCase):
    def setUp(self):
        self.delegate = AppDelegate.alloc().init()
        self.reset_at = datetime(2026, 8, 2, 19, tzinfo=timezone.utc)

    def test_does_not_notify_for_subsecond_reset_time_jitter(self):
        self.delegate._last_five_hour_percent = 100
        self.delegate._last_resets_at = self.reset_at - timedelta(milliseconds=326)
        self.delegate._notified_thresholds = set(THRESHOLDS)

        with patch("ccusagebar.notify") as notify_mock:
            self.delegate._maybe_notify(usage(100, self.reset_at + timedelta(milliseconds=180)))

        notify_mock.assert_not_called()
        self.assertEqual(self.delegate._notified_thresholds, set(THRESHOLDS))

    def test_does_not_notify_for_reset_time_moving_less_than_a_minute(self):
        self.delegate._last_five_hour_percent = 100
        self.delegate._last_resets_at = self.reset_at
        self.delegate._notified_thresholds = set(THRESHOLDS)

        with patch("ccusagebar.notify") as notify_mock:
            self.delegate._maybe_notify(usage(100, self.reset_at + timedelta(seconds=59)))

        notify_mock.assert_not_called()
        self.assertEqual(self.delegate._notified_thresholds, set(THRESHOLDS))

    def test_notifies_when_reset_boundary_moves_by_more_than_tolerance(self):
        self.delegate._last_five_hour_percent = 100
        self.delegate._last_resets_at = self.reset_at
        self.delegate._notified_thresholds = set(THRESHOLDS)

        with patch("ccusagebar.notify") as notify_mock:
            self.delegate._maybe_notify(usage(100, self.reset_at + timedelta(minutes=2)))

        self.assertEqual(notify_mock.call_count, 1)
        self.assertEqual(self.delegate._notified_thresholds, set())

    def test_notifies_after_new_window_boundary_and_usage_drop(self):
        self.delegate._last_five_hour_percent = 100
        self.delegate._last_resets_at = self.reset_at
        self.delegate._notified_thresholds = set(THRESHOLDS)

        with patch("ccusagebar.notify") as notify_mock:
            self.delegate._maybe_notify(usage(0, self.reset_at + timedelta(hours=5)))

        self.assertEqual(notify_mock.call_count, 1)
        self.assertEqual(self.delegate._notified_thresholds, set())


if __name__ == "__main__":
    unittest.main()
