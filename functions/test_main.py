import unittest
from unittest import mock

try:
    from . import main
except ImportError:  # Firebase emulator / direct discovery
    import main


class FakeRequest:
    method = "POST"
    content_length = 2
    headers = {"Authorization": "Bearer test-token"}

    def __init__(self, payload):
        self.payload = payload

    def get_json(self, **_kwargs):
        return self.payload


class GradeApiBoundaryTests(unittest.TestCase):
    def test_rejects_anonymous_request(self):
        request = FakeRequest({})
        request.headers = {}

        response = main.api(request)

        self.assertEqual(response.status_code, 401)
        self.assertIn("Sign in is required", response.get_data(as_text=True))

    @mock.patch.object(main, "_consume_account_quota")
    @mock.patch.object(main, "_authenticated_uid", return_value="user-1")
    def test_non_object_json_does_not_consume_quota(self, _auth, consume):
        response = main.api(FakeRequest([]))

        self.assertEqual(response.status_code, 400)
        self.assertIn("must be an object", response.get_data(as_text=True))
        consume.assert_not_called()

    @mock.patch.object(main, "_consume_account_quota")
    @mock.patch.object(main, "_load_record", return_value=None)
    @mock.patch.object(main, "_authenticated_uid", return_value="user-1")
    def test_unknown_record_does_not_consume_quota(self, _auth, _record, consume):
        response = main.api(FakeRequest({"record_id": 999999, "source": "", "parse": {}}))

        self.assertEqual(response.status_code, 400)
        consume.assert_not_called()

    @mock.patch.object(
        main,
        "_consume_account_quota",
        side_effect=main.RateLimitExceeded(37, 8, 600),
    )
    @mock.patch.object(main, "_load_record", return_value={"id": 1})
    @mock.patch.object(main, "_authenticated_uid", return_value="user-1")
    def test_exhausted_quota_returns_429_with_retry_after(
        self, _auth, _record, _consume
    ):
        request = FakeRequest({"record_id": 1, "source": "OUTPUT 1", "parse": {}})

        response = main.api(request)

        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers["Retry-After"], "37")
        self.assertEqual(response.headers["Cache-Control"], "no-store")


if __name__ == "__main__":
    unittest.main()
