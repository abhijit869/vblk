import unittest
from unittest.mock import MagicMock

from jarvis_core.protocol import RiskLevel, ToolResult
from jarvis_core.security import SecurityScanner
from jarvis_core.tools import ToolRegistry


class SecurityScannerTests(unittest.TestCase):
    def test_run_heuristics_scan(self) -> None:
        mock_registry = MagicMock(spec=ToolRegistry)

        # Mock the process list result
        mock_registry.execute.return_value = ToolResult(
            request_id="test",
            tool="process.list",
            status="ok",
            risk=RiskLevel.READ,
            duration_ms=10,
            data=[
                {"pid": 1, "command": "/sbin/init"},
                {"pid": 2, "command": "/tmp/malicious_miner --donate-level 1"},
                {"pid": 3, "command": "./xmrig -o stratum+tcp://pool.example.com"},
            ],
            redacted=False,
            truncated=False,
        )

        scanner = SecurityScanner(tools=mock_registry)
        report = scanner.run_heuristics_scan()

        self.assertEqual(report.scanned_processes, 3)
        self.assertEqual(report.status, "threats_found")
        self.assertEqual(len(report.detected_threats), 2)

        self.assertIn("volatile memory", report.detected_threats[0]["reason"])
        self.assertIn("cryptominer", report.detected_threats[1]["reason"])


if __name__ == "__main__":
    unittest.main()
