import unittest
from unittest.mock import MagicMock

from jarvis_core.diagnostics import DiagnosisEngine, DiagnosisReport
from jarvis_core.ai_gateway import AIGateway, AIResponse, AIToolCall
from jarvis_core.agent import AgentEngine
from jarvis_core.tools import build_default_registry


class DiagnosisEngineTests(unittest.TestCase):
    def test_diagnose_issue(self) -> None:
        mock_gateway = MagicMock(spec=AIGateway)
        mock_gateway.complete.return_value = AIResponse(
            request_id="test",
            provider="mock",
            model="mock",
            content="",
            tool_calls=[
                AIToolCall(
                    tool="submit_diagnosis",
                    arguments={
                        "root_cause": "Nginx configuration syntax error.",
                        "confidence": 0.95,
                        "repair_steps": [
                            {
                                "action": "Fix nginx.conf syntax",
                                "command_or_tool": "file.write",
                                "risk_level": "MEDIUM"
                            },
                            {
                                "action": "Restart nginx service",
                                "command_or_tool": "systemctl restart nginx",
                                "risk_level": "MEDIUM"
                            }
                        ]
                    },
                )
            ]
        )
        
        agent = AgentEngine(ai=mock_gateway, tools=build_default_registry())
        diag = DiagnosisEngine(ai=mock_gateway, agent_engine=agent)
        
        report = diag.diagnose_issue("nginx.service failed to start")
        
        self.assertEqual(report.issue_signature, "nginx.service failed to start")
        self.assertEqual(report.root_cause, "Nginx configuration syntax error.")
        self.assertEqual(report.confidence, 0.95)
        self.assertEqual(len(report.recommended_repair), 2)
        self.assertEqual(report.recommended_repair[0].command_or_tool, "file.write")

if __name__ == "__main__":
    unittest.main()
