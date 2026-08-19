"""Quota-verdict handling in the Vercel Function.

The fixed-window arithmetic these tests used to cover now lives in
``consume_grading_quota()`` in supabase/migrations/, where it belongs: it needs
a row lock to be correct, and a lock is not something Python can hold on the
database's behalf.  See tests/test_grading_quota.sql for its coverage.

What remains testable here is how this side reads the database's verdict, which
is where a silent failure would be most costly - misreading "denied" as
"allowed" would uncap spend.
"""

import json
import unittest
import urllib.error
from unittest import mock

from api import _quota
from api._quota import QuotaUnavailable, RateLimitExceeded, interpret_quota_response


class InterpretQuotaResponseTests(unittest.TestCase):
    def test_allowed_returns_remaining(self):
        self.assertEqual(
            interpret_quota_response({"allowed": True, "remaining": 5}), 5
        )

    def test_allowed_with_zero_remaining_is_still_allowed(self):
        """The last request in a window is permitted; the next one is not."""
        self.assertEqual(
            interpret_quota_response({"allowed": True, "remaining": 0}), 0
        )

    def test_denied_raises_with_retry_and_limit(self):
        with self.assertRaises(RateLimitExceeded) as caught:
            interpret_quota_response(
                {"allowed": False, "limit": 8, "window": "burst",
                 "retry_after_seconds": 240}
            )
        self.assertEqual(caught.exception.retry_after, 240)
        self.assertEqual(caught.exception.limit, 8)

    def test_denied_without_a_usable_retry_still_backs_off(self):
        """A missing or nonsensical retry must not become "retry immediately"."""
        for payload in (
            {"allowed": False, "limit": 8},
            {"allowed": False, "limit": 8, "retry_after_seconds": 0},
            {"allowed": False, "limit": 8, "retry_after_seconds": "soon"},
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(RateLimitExceeded) as caught:
                    interpret_quota_response(payload)
                self.assertGreater(caught.exception.retry_after, 0)

    def test_missing_verdict_fails_closed(self):
        for payload in ({}, {"remaining": 3}, None, [], "allowed"):
            with self.subTest(payload=payload):
                with self.assertRaises(QuotaUnavailable):
                    interpret_quota_response(payload)

    def test_allowed_without_remaining_fails_closed(self):
        with self.assertRaises(QuotaUnavailable):
            interpret_quota_response({"allowed": True})


class ConsumeQuotaTransportTests(unittest.TestCase):
    """The RPC is called with the caller's token and never with a uid."""

    def _response(self, payload):
        response = mock.MagicMock()
        response.read.return_value = json.dumps(payload).encode("utf-8")
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        return response

    def test_sends_the_callers_token_and_the_anon_key(self):
        with mock.patch.object(_quota.urllib.request, "urlopen") as urlopen:
            urlopen.return_value = self._response({"allowed": True, "remaining": 7})
            self.assertEqual(_quota.consume_quota("token-abc"), 7)

        request = urlopen.call_args[0][0]
        self.assertEqual(request.get_header("Authorization"), "Bearer token-abc")
        self.assertEqual(request.get_header("Apikey"), _quota.SUPABASE_ANON_KEY)
        self.assertTrue(request.full_url.endswith("/rpc/consume_grading_quota"))
        # No uid travels with the request: the database derives it from the
        # token, so a caller cannot spend someone else's quota or reset its own.
        self.assertEqual(request.data, b"{}")

    def test_http_error_fails_closed(self):
        with mock.patch.object(_quota.urllib.request, "urlopen") as urlopen:
            urlopen.side_effect = urllib.error.HTTPError(
                _quota.CONSUME_QUOTA_URL, 403, "Forbidden", {}, None
            )
            with self.assertRaises(QuotaUnavailable):
                _quota.consume_quota("token-abc")

    def test_network_error_fails_closed(self):
        with mock.patch.object(_quota.urllib.request, "urlopen") as urlopen:
            urlopen.side_effect = urllib.error.URLError("connection refused")
            with self.assertRaises(QuotaUnavailable):
                _quota.consume_quota("token-abc")


if __name__ == "__main__":
    unittest.main()
