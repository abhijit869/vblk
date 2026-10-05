import unittest

from jarvis_core.protocol import ToolRequest
from jarvis_core.tools import build_default_registry
from jarvis_core import tools


class ToolRegistryTests(unittest.TestCase):
    def test_system_cpu_tool_returns_read_result(self) -> None:
        result = build_default_registry().execute(ToolRequest(tool="system.cpu"))

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.risk.name, "READ")
        self.assertIsInstance(result.data, dict)
        self.assertIn("cpu_count", result.data)

    def test_unknown_tool_returns_error(self) -> None:
        result = build_default_registry().execute(ToolRequest(tool="missing.tool"))

        self.assertEqual(result.status, "error")
        self.assertIsNotNone(result.error)
        self.assertEqual(result.error.code, "unknown_tool")

    def test_process_list_tool_returns_processes(self) -> None:
        result = build_default_registry().execute(ToolRequest(tool="process.list"))

        self.assertEqual(result.status, "ok")
        self.assertIsInstance(result.data, list)
        self.assertGreater(len(result.data), 0)
        self.assertIn("pid", result.data[0])

    def test_terminal_execute_denies_high_risk_command(self) -> None:
        result = build_default_registry().execute(
            ToolRequest(tool="terminal.execute", arguments={"command": "rm -rf /tmp/example"})
        )

        self.assertEqual(result.status, "denied")
        self.assertEqual(result.error.code, "command_risk_exceeds_limit")
        self.assertIsInstance(result.data, dict)
        self.assertEqual(result.data["risk"], "HIGH")
        self.assertIsNone(result.data["exit_code"])

    def test_process_command_is_redacted_and_capped(self) -> None:
        original_limit = tools.PROCESS_COMMAND_LIMIT
        tools.PROCESS_COMMAND_LIMIT = 40
        try:
            command = tools._parse_proc_command(  # noqa: SLF001
                process_path=FakeProcessPath(b"python API_KEY=abc123 with extra words"),
                stat="1 (python) S 0",
            )
        finally:
            tools.PROCESS_COMMAND_LIMIT = original_limit

        self.assertIn("API_KEY=[REDACTED]", command)
        self.assertIn("[TRUNCATED]", command)
        self.assertNotIn("abc123", command)


class FakeProcessPath:
    def __init__(self, cmdline: bytes) -> None:
        self._cmdline = cmdline

    def __truediv__(self, _: str) -> "FakeProcessPath":
        return self

    def read_bytes(self) -> bytes:
        return self._cmdline


if __name__ == "__main__":
    unittest.main()
