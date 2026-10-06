import unittest
from unittest.mock import MagicMock

from jarvis_core.shell import JarvisShell


class JarvisShellTests(unittest.TestCase):
    def test_default_command_calls_core(self) -> None:
        mock_core = MagicMock()
        mock_core.handle_text.return_value = {
            "answer": "CPU is 10%",
            "session_id": "test_session",
            "selected_tools": ["system.cpu"],
        }

        shell = JarvisShell(core=mock_core)
        shell.default("What is my CPU?")

        mock_core.handle_text.assert_called_with("What is my CPU?", None)
        self.assertEqual(shell.session_id, "test_session")

    def test_exit_commands(self) -> None:
        shell = JarvisShell()
        self.assertTrue(shell.do_exit(""))
        self.assertTrue(shell.do_quit(""))


if __name__ == "__main__":
    unittest.main()
