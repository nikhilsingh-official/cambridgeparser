import unittest

from api._quota import RateLimitExceeded, next_quota_state


class RateLimitTests(unittest.TestCase):
    def setUp(self):
        self.policies = {
            "burst": {"limit": 2, "window_ms": 60_000},
            "daily": {"limit": 4, "window_ms": 86_400_000},
        }

    def test_consumes_every_window_atomically(self):
        state, remaining = next_quota_state(
            None, now_ms=100_000, policies=self.policies
        )

        self.assertEqual(state["burst"], {"startedAt": 100_000, "count": 1})
        self.assertEqual(state["daily"], {"startedAt": 100_000, "count": 1})
        self.assertEqual(remaining, 1)

    def test_rejects_when_any_window_is_exhausted(self):
        state, _ = next_quota_state(None, now_ms=100_000, policies=self.policies)
        state, _ = next_quota_state(
            state, now_ms=110_000, policies=self.policies
        )

        with self.assertRaises(RateLimitExceeded) as caught:
            next_quota_state(state, now_ms=120_000, policies=self.policies)

        self.assertEqual(caught.exception.retry_after, 40)
        self.assertEqual(caught.exception.limit, 2)

    def test_expired_window_resets_without_resetting_long_window(self):
        state, _ = next_quota_state(None, now_ms=100_000, policies=self.policies)
        state, remaining = next_quota_state(
            state, now_ms=161_000, policies=self.policies
        )

        self.assertEqual(state["burst"], {"startedAt": 161_000, "count": 1})
        self.assertEqual(state["daily"], {"startedAt": 100_000, "count": 2})
        self.assertEqual(remaining, 1)


if __name__ == "__main__":
    unittest.main()
