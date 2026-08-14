import unittest

from functions.rate_limit import RateLimitExceeded, consume_quota


class RateLimitTests(unittest.TestCase):
    def setUp(self):
        self.policies = {
            "burst": {"limit": 2, "window_seconds": 60},
            "daily": {"limit": 4, "window_seconds": 86400},
        }

    def test_consumes_every_window_atomically(self):
        state, remaining = consume_quota(None, now=100, policies=self.policies)

        self.assertEqual(state["burst"], {"started_at": 100, "count": 1})
        self.assertEqual(state["daily"], {"started_at": 100, "count": 1})
        self.assertEqual(remaining, 1)

    def test_rejects_when_any_window_is_exhausted(self):
        state, _ = consume_quota(None, now=100, policies=self.policies)
        state, _ = consume_quota(state, now=110, policies=self.policies)

        with self.assertRaises(RateLimitExceeded) as caught:
            consume_quota(state, now=120, policies=self.policies)

        self.assertEqual(caught.exception.retry_after, 40)
        self.assertEqual(caught.exception.limit, 2)

    def test_expired_window_resets_without_resetting_long_window(self):
        state, _ = consume_quota(None, now=100, policies=self.policies)
        state, remaining = consume_quota(state, now=161, policies=self.policies)

        self.assertEqual(state["burst"], {"started_at": 161, "count": 1})
        self.assertEqual(state["daily"], {"started_at": 100, "count": 2})
        self.assertEqual(remaining, 1)


if __name__ == "__main__":
    unittest.main()
