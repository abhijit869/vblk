import unittest
from jarvis_core.tools import build_default_registry
from jarvis_core.protocol import ToolRequest, RiskLevel

class FileToolsTests(unittest.TestCase):
    def setUp(self):
        self.registry = build_default_registry()

    def test_unknown_tool(self):
        req = ToolRequest(tool="unknown.tool")
        res = self.registry.execute(req)
        self.assertEqual(res.status, "error")

    def test_malformed_arguments(self):
        req = ToolRequest(tool="file.read", arguments={"wrong": "arg"})
        res = self.registry.execute(req)
        self.assertEqual(res.status, "error")

    def test_authorization_required_for_write_tools(self):
        req = ToolRequest(tool="file.mkdir", arguments={"path": "/tmp/test"})
        res = self.registry.execute(req)
        self.assertEqual(res.status, "denied")

if __name__ == "__main__":
    unittest.main()
