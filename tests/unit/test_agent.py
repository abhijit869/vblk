import unittest
from unittest.mock import MagicMock

from jarvis_core.agent import AgentEngine, TaskPlan, TaskStep
from jarvis_core.ai_gateway import AIGateway, AIResponse, AIToolCall
from jarvis_core.tools import build_default_registry


class AgentEngineTests(unittest.TestCase):
    def test_plan_generates_steps(self) -> None:
        mock_gateway = MagicMock(spec=AIGateway)
        mock_gateway.complete.return_value = AIResponse(
            request_id="test",
            provider="mock",
            model="mock",
            content="",
            tool_calls=[
                AIToolCall(
                    tool="submit_plan",
                    arguments={"steps": ["Check CPU", "Check Memory"]},
                )
            ],
        )

        agent = AgentEngine(ai=mock_gateway, tools=build_default_registry())
        plan = agent.plan("Diagnose system")

        self.assertEqual(plan.goal, "Diagnose system")
        self.assertEqual(len(plan.steps), 2)
        self.assertEqual(plan.steps[0].description, "Check CPU")
        self.assertEqual(plan.steps[1].description, "Check Memory")
        self.assertEqual(plan.status, "pending")

    def test_execute_step(self) -> None:
        mock_gateway = MagicMock(spec=AIGateway)

        # Complete returns a tool call to system.cpu
        mock_gateway.complete.return_value = AIResponse(
            request_id="test",
            provider="mock",
            model="mock",
            content="",
            tool_calls=[AIToolCall(tool="system.cpu", arguments={})],
        )
        # Respond returns the final natural language answer
        mock_gateway.respond.return_value = AIResponse(
            request_id="test",
            provider="mock",
            model="mock",
            content="CPU is at 10%",
            tool_calls=[],
        )

        agent = AgentEngine(ai=mock_gateway, tools=build_default_registry())
        plan = TaskPlan(goal="Check system", steps=[TaskStep(description="Check CPU")])

        step = agent.execute_step(plan, 0)

        self.assertEqual(step.status, "completed")
        self.assertEqual(step.result, "CPU is at 10%")
        self.assertIsNone(step.error)

    def test_run_completes_full_plan(self) -> None:
        mock_gateway = MagicMock(spec=AIGateway)

        # We need side_effects to return the plan first, then the tool calls, then responses
        # But wait, `plan` and `execute_step` use different mock methods.
        # plan uses `complete`, execute_step uses `complete` then `respond`.

        def mock_complete(request):
            if (
                "submit_plan" in request.prompt
                or "Goal:" in request.prompt
                and "Create a concise, step-by-step plan" in request.prompt
            ):
                return AIResponse(
                    request_id="test",
                    provider="mock",
                    model="mock",
                    content="",
                    tool_calls=[
                        AIToolCall(tool="submit_plan", arguments={"steps": ["Step 1"]})
                    ],
                )
            # Otherwise it's execution
            return AIResponse(
                request_id="test",
                provider="mock",
                model="mock",
                content="Done without tools",
                tool_calls=[],
            )

        mock_gateway.complete.side_effect = mock_complete

        agent = AgentEngine(ai=mock_gateway, tools=build_default_registry())
        plan = agent.run("Do a thing")

        self.assertEqual(plan.status, "completed")
        self.assertEqual(len(plan.steps), 1)
        self.assertEqual(plan.steps[0].status, "completed")
        self.assertEqual(plan.steps[0].result, "Done without tools")


if __name__ == "__main__":
    unittest.main()
