import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

from src.pipeline.grading.ast_adapter import find_parser_binary, parse_answer


def make_fake_binary(directory: Path, script_body: str) -> Path:
    path = directory / "fake-parser"
    path.write_text("#!/bin/sh\n" + script_body)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


class AstAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_success_payload_is_normalized(self):
        binary = make_fake_binary(
            self.tmp_path,
            "cat > /dev/null\n"
            "echo '{\"ok\": true, \"ast_version\": \"cambridge-pseudocode-ast/v1\", "
            "\"statements\": [{\"kind\": \"output\"}], \"diagnostics\": [], \"stdout\": \"\"}'\n",
        )

        result = parse_answer("OUTPUT 1", binary=binary)

        self.assertEqual(result["schema_version"], "parsed-answer/v1")
        self.assertTrue(result["parse"]["ok"])
        self.assertEqual(result["parse"]["ast"]["statements"], [{"kind": "output"}])
        self.assertEqual(result["runner"]["exit_code"], 0)
        self.assertIsNone(result["runner"]["error"])

    def test_parser_error_payload_keeps_diagnostics(self):
        binary = make_fake_binary(
            self.tmp_path,
            "cat > /dev/null\n"
            "echo '{\"ok\": false, \"statements\": [], \"diagnostics\": "
            "[{\"severity\": \"error\", \"message\": \"Expected ENDIF\", \"line\": 2, \"column\": 1}]}'\n",
        )

        result = parse_answer("IF x THEN", binary=binary)

        self.assertFalse(result["parse"]["ok"])
        self.assertEqual(
            result["parse"]["diagnostics"][0]["message"], "Expected ENDIF"
        )
        self.assertIsNone(result["runner"]["error"])

    def test_invalid_json_is_reported_not_raised(self):
        binary = make_fake_binary(self.tmp_path, "cat > /dev/null\necho 'not json'\n")

        result = parse_answer("OUTPUT 1", binary=binary)

        self.assertFalse(result["parse"]["ok"])
        self.assertEqual(result["runner"]["error"], "invalid_json")
        self.assertIn("invalid JSON", result["parse"]["diagnostics"][0]["message"])

    def test_timeout_is_reported_not_raised(self):
        binary = make_fake_binary(self.tmp_path, "sleep 5\n")

        result = parse_answer("OUTPUT 1", timeout=0.2, binary=binary)

        self.assertFalse(result["parse"]["ok"])
        self.assertEqual(result["runner"]["error"], "timeout")

    def test_missing_binary_is_reported_not_raised(self):
        result = parse_answer("OUTPUT 1", binary=self.tmp_path / "does-not-exist")

        self.assertFalse(result["parse"]["ok"])
        self.assertEqual(result["runner"]["error"], "binary_missing")

    def test_nonzero_exit_is_reported(self):
        binary = make_fake_binary(self.tmp_path, "cat > /dev/null\nexit 3\n")

        result = parse_answer("OUTPUT 1", binary=binary)

        self.assertFalse(result["parse"]["ok"])
        self.assertEqual(result["runner"]["error"], "nonzero_exit")
        self.assertEqual(result["runner"]["exit_code"], 3)

    def test_env_override_governs_binary_lookup(self):
        binary = make_fake_binary(self.tmp_path, "echo hi\n")
        old = os.environ.get("PSEUDOCODE_PARSER_BIN")
        os.environ["PSEUDOCODE_PARSER_BIN"] = str(binary)
        try:
            self.assertEqual(find_parser_binary(), binary)
        finally:
            if old is None:
                del os.environ["PSEUDOCODE_PARSER_BIN"]
            else:
                os.environ["PSEUDOCODE_PARSER_BIN"] = old

    def test_real_binary_roundtrip_if_built(self):
        real = None
        if os.environ.get("PSEUDOCODE_PARSER_BIN") is None:
            real = find_parser_binary()
        if real is None:
            self.skipTest("pseudocode-parser binary not built")
        result = parse_answer("OUTPUT 1", binary=real)
        self.assertTrue(result["parse"]["ok"], json.dumps(result, indent=2))
        self.assertEqual(
            result["parse"]["ast"]["statements"][0]["kind"], "output"
        )


if __name__ == "__main__":
    unittest.main()
