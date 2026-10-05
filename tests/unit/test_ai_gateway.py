import unittest

from jarvis_core.ai_gateway import AIGateway, AIRequest, MockAIProvider, ProviderStatus


class AIGatewayTests(unittest.TestCase):
    def test_mock_provider_selects_cpu_tool(self) -> None:
        response = AIGateway(MockAIProvider()).complete(AIRequest("check cpu usage"))

        self.assertEqual(response.provider, "mock")
        self.assertEqual(response.tool_calls[0].tool, "system.cpu")

    def test_unavailable_provider_returns_no_tool_calls(self) -> None:
        provider = MockAIProvider(status=ProviderStatus.UNAVAILABLE)
        response = AIGateway(provider).complete(AIRequest("check cpu usage"))

        self.assertEqual(response.tool_calls, [])
        self.assertIn("unavailable", response.content.lower())

    def test_mock_provider_adds_safe_terminal_command(self) -> None:
        response = AIGateway(MockAIProvider()).complete(AIRequest("run terminal command"))

        self.assertEqual(response.tool_calls[0].tool, "terminal.execute")
        self.assertEqual(response.tool_calls[0].arguments["command"], "pwd")


if __name__ == "__main__":
    unittest.main()
