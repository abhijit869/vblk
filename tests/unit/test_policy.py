import unittest

from jarvis_core.policy import PolicyEngine
from jarvis_core.protocol import RiskLevel, ToolDefinition, ToolRequest


class PolicyEngineTests(unittest.TestCase):
    def test_policy_allows_read_tool(self) -> None:
        definition = ToolDefinition(
            "system.cpu", 1, RiskLevel.READ, False, 2000, 32768, "CPU"
        )
        request = ToolRequest(tool="system.cpu", max_risk=RiskLevel.READ)

        decision = PolicyEngine().authorize(request, definition)

        self.assertTrue(decision.allowed)
        self.assertIsNone(decision.error)

    def test_policy_denies_risk_above_request_limit(self) -> None:
        definition = ToolDefinition(
            "service.restart", 1, RiskLevel.MEDIUM, True, 5000, 32768, "Restart service"
        )
        request = ToolRequest(tool="service.restart", max_risk=RiskLevel.READ)

        decision = PolicyEngine().authorize(request, definition)

        self.assertFalse(decision.allowed)
        self.assertIsNotNone(decision.error)
        self.assertEqual(decision.error.code, "risk_exceeds_request_limit")


if __name__ == "__main__":
    unittest.main()
