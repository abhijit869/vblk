import unittest

from jarvis_core.ai_gateway import OpenAICompatibleProvider
from jarvis_core.config import AIConfig, build_ai_gateway, load_ai_config


class ConfigTests(unittest.TestCase):
    def test_load_mock_provider(self):
        config = load_ai_config({"JARVIS_AI_PROVIDER": "mock"})
        self.assertEqual(config.provider, "mock")

    def test_build_mock_primary(self):
        config = AIConfig(provider="mock")
        gateway = build_ai_gateway(config)
        self.assertEqual(gateway.primary.name, "mock")


if __name__ == "__main__":
    unittest.main()
