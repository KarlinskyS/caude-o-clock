import os
import unittest
from unittest.mock import patch

from ccusage_api import CredentialsError, fetch_usage
from i18n import t


class FetchUsageTest(unittest.TestCase):
    def test_raises_rate_limit_error_when_429_mock_is_enabled(self):
        with patch.dict(os.environ, {"CCUSAGE_MOCK_429": "234"}):
            with self.assertRaises(CredentialsError) as context:
                fetch_usage()

        self.assertEqual(context.exception.retry_after, 234)
        self.assertIn("429", str(context.exception))

    def test_raises_not_signed_in_error_when_no_auth_mock_is_enabled(self):
        with patch.dict(os.environ, {"CCUSAGE_MOCK_NO_AUTH": "1"}):
            with self.assertRaises(CredentialsError) as context:
                fetch_usage()

        self.assertEqual(str(context.exception), t("err_no_creds"))
        self.assertEqual(context.exception.title, t("err_no_creds_title"))
        self.assertEqual(context.exception.detail, t("err_no_creds_detail"))


if __name__ == "__main__":
    unittest.main()
