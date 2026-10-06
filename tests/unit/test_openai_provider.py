import unittest

from fake_openai import FakeOpenAIServer
from jarvis_core.ai_gateway import (
    AIGateway,
    AIRequest,
    AIToolCall,
    AIToolOutput,
    AIToolSpec,
    MockAIProvider,
    OpenAICompatibleProvider,
    ProviderError,
    ProviderStatus,
    encode_tool_name,
)
from jarvis_core.config import build_ai_gateway, load_ai_config

TOOLS = (
    AIToolSpec("system.cpu", "CPU"),
    AIToolSpec(
        "terminal.execute",
        "Terminal",
        {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    ),
)


def provider_for(
    server: FakeOpenAIServer, api_key: str | None = "sk-test-secret"
) -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        model="test-model", api_key=api_key, base_url=server.base_url, timeout_ms=5000
    )


def no_sleep(_: float) -> None:
    return None


class OpenAICompatibleProviderTests(unittest.TestCase):
    def test_tool_names_are_encoded_for_provider_pattern(self) -> None:
        self.assertEqual(encode_tool_name("system.cpu"), "system_cpu")
        self.assertRegex(encode_tool_name("a.b c/d"), r"^[a-zA-Z0-9_-]+$")

    def test_complete_sends_tools_and_maps_tool_calls_back(self) -> None:
        with FakeOpenAIServer() as server:
            server.enqueue_tool_calls(
                ("system_cpu", {}), ("terminal_execute", {"command": "uptime"})
            )
            response = provider_for(server).complete(
                AIRequest("check cpu", tools=TOOLS)
            )

        sent = server.requests[0]
        self.assertEqual(sent["model"], "test-model")
        self.assertEqual(
            [tool["function"]["name"] for tool in sent["tools"]],
            ["system_cpu", "terminal_execute"],
        )
        self.assertEqual(server.headers[0]["authorization"], "Bearer sk-test-secret")
        self.assertEqual(
            [call.tool for call in response.tool_calls],
            ["system.cpu", "terminal.execute"],
        )
        self.assertEqual(response.tool_calls[1].arguments, {"command": "uptime"})
        self.assertEqual(response.tool_calls[0].id, "call_0")
        self.assertEqual(response.usage.input_tokens, 100)

    def test_respond_sends_tool_results_with_matching_ids(self) -> None:
        call = AIToolCall("system.cpu", {}, id="call_abc")
        with FakeOpenAIServer() as server:
            server.enqueue_text("Your CPU is mostly idle.")
            response = provider_for(server).respond(
                AIRequest("check cpu", tools=TOOLS),
                [AIToolOutput(call, '{"status": "ok"}')],
            )

        messages = server.requests[0]["messages"]
        self.assertEqual(messages[2]["tool_calls"][0]["id"], "call_abc")
        self.assertEqual(messages[2]["tool_calls"][0]["function"]["name"], "system_cpu")
        self.assertEqual(
            messages[3],
            {"role": "tool", "tool_call_id": "call_abc", "content": '{"status": "ok"}'},
        )
        self.assertNotIn("tools", server.requests[0])
        self.assertEqual(response.content, "Your CPU is mostly idle.")

    def test_invalid_tool_arguments_are_captured_not_raised(self) -> None:
        with FakeOpenAIServer() as server:
            server.enqueue(
                {
                    "choices": [
                        {
                            "message": {
                                "tool_calls": [
                                    {
                                        "id": "c",
                                        "type": "function",
                                        "function": {
                                            "name": "system_cpu",
                                            "arguments": "{bad",
                                        },
                                    }
                                ]
                            }
                        }
                    ]
                }
            )
            response = provider_for(server).complete(AIRequest("cpu", tools=TOOLS))

        self.assertIn("_invalid_arguments", response.tool_calls[0].arguments)

    def test_http_errors_are_classified(self) -> None:
        with FakeOpenAIServer() as server:
            server.enqueue({"error": "bad key"}, status=401)
            server.enqueue({"error": "busy"}, status=429, headers={"Retry-After": "3"})
            provider = provider_for(server)
            with self.assertRaises(ProviderError) as unauthorized:
                provider.complete(AIRequest("cpu"))
            with self.assertRaises(ProviderError) as limited:
                provider.complete(AIRequest("cpu"))

        self.assertFalse(unauthorized.exception.retryable)
        self.assertTrue(limited.exception.retryable)
        self.assertEqual(limited.exception.retry_after_s, 3.0)

    def test_health_requires_model_and_remote_key(self) -> None:
        self.assertEqual(
            OpenAICompatibleProvider(model=None, api_key="k").health().status,
            ProviderStatus.UNAVAILABLE,
        )
        self.assertEqual(
            OpenAICompatibleProvider(model="m").health().status,
            ProviderStatus.UNAVAILABLE,
        )
        local = OpenAICompatibleProvider(
            model="m", base_url="http://localhost:11434/v1"
        )
        self.assertEqual(local.health().status, ProviderStatus.HEALTHY)

    def test_api_key_is_not_exposed_in_repr(self) -> None:
        provider = OpenAICompatibleProvider(model="m", api_key="sk-very-secret")
        config = load_ai_config(
            {"JARVIS_AI_API_KEY": "sk-very-secret", "JARVIS_AI_MODEL": "m"}
        )

        self.assertNotIn("sk-very-secret", repr(provider))
        self.assertNotIn("sk-very-secret", repr(config))


class GatewayRoutingTests(unittest.TestCase):
    def test_retries_transient_errors_then_succeeds(self) -> None:
        delays: list[float] = []
        with FakeOpenAIServer() as server:
            server.enqueue({"error": "oops"}, status=500)
            server.enqueue({"error": "busy"}, status=429, headers={"Retry-After": "1"})
            server.enqueue_tool_calls(("system_cpu", {}))
            gateway = AIGateway(
                provider_for(server),
                fallback=MockAIProvider(),
                max_retries=2,
                sleep=delays.append,
            )
            response = gateway.complete(AIRequest("cpu", tools=TOOLS))

        self.assertEqual(len(server.requests), 3)
        self.assertEqual(delays, [0.5, 1.0])
        self.assertIsNone(response.fallback_from)
        self.assertEqual(response.tool_calls[0].tool, "system.cpu")

    def test_non_retryable_error_falls_back_to_mock(self) -> None:
        with FakeOpenAIServer() as server:
            server.enqueue({"error": "bad key"}, status=401)
            gateway = AIGateway(
                provider_for(server), fallback=MockAIProvider(), sleep=no_sleep
            )
            response = gateway.complete(AIRequest("check cpu usage", tools=TOOLS))

        self.assertEqual(len(server.requests), 1)
        self.assertEqual(response.provider, "mock")
        self.assertEqual(response.fallback_from, "openai-compatible")
        self.assertIn("HTTP 401", response.error)
        self.assertNotIn("sk-test-secret", response.error)

    def test_unreachable_provider_falls_back_after_retries(self) -> None:
        provider = OpenAICompatibleProvider(
            model="m", base_url="http://127.0.0.1:9/v1", timeout_ms=500
        )
        gateway = AIGateway(
            provider, fallback=MockAIProvider(), max_retries=1, sleep=no_sleep
        )

        response = gateway.complete(AIRequest("check memory"))

        self.assertEqual(response.provider, "mock")
        self.assertIn("Connection failed", response.error)

    def test_unconfigured_provider_skips_network_and_falls_back(self) -> None:
        gateway = AIGateway(
            OpenAICompatibleProvider(model=None, api_key="k"), fallback=MockAIProvider()
        )

        response = gateway.complete(AIRequest("check cpu"))

        self.assertEqual(response.provider, "mock")
        self.assertIn("JARVIS_AI_MODEL", response.error)


class ConfigTests(unittest.TestCase):
    def test_defaults_to_mock_without_key(self) -> None:
        config = load_ai_config({})

        self.assertEqual(config.provider, "mock")
        self.assertIsInstance(build_ai_gateway(config).primary, MockAIProvider)

    def test_key_selects_openai_with_mock_fallback(self) -> None:
        config = load_ai_config(
            {
                "OPENAI_API_KEY": "k",
                "JARVIS_AI_MODEL": "m",
                "JARVIS_AI_MAX_RETRIES": "5",
            }
        )
        gateway = build_ai_gateway(config)

        self.assertEqual(config.provider, "openai")
        self.assertEqual(config.max_retries, 5)
        self.assertIsInstance(gateway.primary, OpenAICompatibleProvider)
        self.assertIsInstance(gateway.fallback, MockAIProvider)

    def test_rejects_unknown_provider(self) -> None:
        with self.assertRaises(ValueError):
            load_ai_config({"JARVIS_AI_PROVIDER": "skynet"})


if __name__ == "__main__":
    unittest.main()
