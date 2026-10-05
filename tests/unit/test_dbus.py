import unittest
from unittest.mock import MagicMock
from jarvis_core.dbus_service import JarvisDBusService


class JarvisDBusServiceTests(unittest.TestCase):
    def test_status_returns_online(self) -> None:
        mock_core = MagicMock()
        service = JarvisDBusService(core=mock_core)
        self.assertEqual(service.Status(), "ONLINE")

    def test_ask_processes_prompt(self) -> None:
        mock_core = MagicMock()
        mock_core.handle_text.return_value = {"answer": "System is nominal."}
        
        service = JarvisDBusService(core=mock_core)
        answer = service.Ask("session_123", "What is the status?")
        
        mock_core.handle_text.assert_called_with("What is the status?", "session_123")
        self.assertEqual(answer, "System is nominal.")

    def test_ask_handles_exceptions(self) -> None:
        mock_core = MagicMock()
        mock_core.handle_text.side_effect = ValueError("AI failed")
        
        service = JarvisDBusService(core=mock_core)
        answer = service.Ask("", "Break it")
        
        self.assertIn("Error: AI failed", answer)

if __name__ == "__main__":
    unittest.main()
