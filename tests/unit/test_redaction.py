import unittest

from jarvis_core.redaction import redact_data, redact_text


class RedactionTests(unittest.TestCase):
    def test_redacts_assignment_and_preserves_separator(self) -> None:
        self.assertEqual(redact_text("API_KEY=abc123")[0], "API_KEY=[REDACTED]")
        self.assertEqual(redact_text("password: hunter2")[0], "password: [REDACTED]")
        self.assertEqual(redact_text("export GITHUB_TOKEN=ghp_x")[0], "export GITHUB_TOKEN=[REDACTED]")

    def test_redacts_json_and_bearer(self) -> None:
        text, changed = redact_text('{"token": "abc", "user": "me"}')
        self.assertTrue(changed)
        self.assertEqual(text, '{"token": "[REDACTED]", "user": "me"}')
        self.assertEqual(redact_text("Authorization: Bearer abc.def")[0], "Authorization: Bearer [REDACTED]")

    def test_redacts_private_key_block(self) -> None:
        text, changed = redact_text("x\n-----BEGIN RSA PRIVATE KEY-----\nMIIE\n-----END RSA PRIVATE KEY-----\ny")
        self.assertTrue(changed)
        self.assertEqual(text, "x\n[REDACTED]\ny")

    def test_leaves_normal_text_alone(self) -> None:
        self.assertEqual(redact_text("load average: 0.1 0.2"), ("load average: 0.1 0.2", False))

    def test_redacts_nested_data_and_secret_keys(self) -> None:
        data, changed = redact_data({"env": {"api_key": "xyz"}, "lines": ["SECRET=1", "ok"], "count": 3})

        self.assertTrue(changed)
        self.assertEqual(data, {"env": {"api_key": "[REDACTED]"}, "lines": ["SECRET=[REDACTED]", "ok"], "count": 3})


if __name__ == "__main__":
    unittest.main()
