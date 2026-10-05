import unittest

from jarvis_core.protocol import RiskLevel
from jarvis_core.terminal import TerminalEngine, classify_command


class TerminalEngineTests(unittest.TestCase):
    def test_classifies_read_only_command(self) -> None:
        self.assertEqual(classify_command(["ls", "-la"]), RiskLevel.READ)

    def test_classifies_destructive_command_high(self) -> None:
        self.assertEqual(classify_command(["rm", "-rf", "/tmp/example"]), RiskLevel.HIGH)

    def test_denies_command_above_max_risk(self) -> None:
        result = TerminalEngine().execute(["rm", "-rf", "/tmp/example"], max_risk=RiskLevel.READ)

        self.assertEqual(result.risk, RiskLevel.HIGH)
        self.assertIsNone(result.exit_code)
        self.assertIn("Denied", result.stderr)

    def test_executes_read_only_command(self) -> None:
        result = TerminalEngine().execute(["pwd"], max_risk=RiskLevel.READ)

        self.assertEqual(result.risk, RiskLevel.READ)
        self.assertEqual(result.exit_code, 0)
        self.assertTrue(result.stdout.strip())

    def test_redacts_secret_output(self) -> None:
        result = TerminalEngine().execute(
            ["echo", "API_KEY=abc123"],
            max_risk=RiskLevel.MEDIUM,
        )

        self.assertTrue(result.redacted)
        self.assertIn("API_KEY=[REDACTED]", result.stdout)
        self.assertNotIn("abc123", result.stdout)

    def test_truncates_output(self) -> None:
        result = TerminalEngine().execute(
            ["head", "-c", "100", "/dev/zero"],
            max_risk=RiskLevel.MEDIUM,
            output_limit_bytes=10,
        )

        self.assertTrue(result.truncated)
        self.assertIn("[TRUNCATED]", result.stdout)


if __name__ == "__main__":
    unittest.main()
