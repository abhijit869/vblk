"""Multi-step Agent Engine for JARVIS."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal

from jarvis_core.ai_gateway import AIGateway, AIRequest, AIToolSpec, AIToolCall, AIToolOutput
from jarvis_core.tools import ToolRegistry, ToolRequest
from jarvis_core.protocol import RiskLevel
from jarvis_core.core import _tool_spec, _result_for_ai
from jarvis_core.rollback import SnapshotEngine


@dataclass
class TaskStep:
    description: str
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    result: str | None = None
    error: str | None = None


@dataclass
class TaskPlan:
    goal: str
    steps: list[TaskStep]
    status: Literal["pending", "running", "completed", "failed"] = "pending"


class AgentEngine:
    def __init__(self, ai: AIGateway, tools: ToolRegistry, max_risk: RiskLevel = RiskLevel.READ):
        self.ai = ai
        self.tools = tools
        self.max_risk = max_risk
        self.snapshot_engine = SnapshotEngine()

    def plan(self, goal: str) -> TaskPlan:
        submit_plan_tool = AIToolSpec(
            name="submit_plan",
            description="Submit the step-by-step plan.",
            parameters={
                "type": "object",
                "required": ["steps"],
                "properties": {
                    "steps": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Sequential steps to achieve the goal.",
                    }
                },
                "additionalProperties": False,
            },
        )
        
        request = AIRequest(
            prompt=f"Goal: {goal}\nCreate a concise, step-by-step plan to achieve this.",
            system_prompt="You are JARVIS Planner. Break down complex goals into simple steps.",
            tools=(submit_plan_tool,),
        )
        
        response = self.ai.complete(request)
        
        steps = []
        if response.tool_calls:
            for call in response.tool_calls:
                if call.tool == "submit_plan":
                    steps_list = call.arguments.get("steps", [])
                    steps = [TaskStep(description=s) for s in steps_list]
                    break
                    
        if not steps:
            steps = [TaskStep(description="Execute user request")]
            
        return TaskPlan(goal=goal, steps=steps)

    def execute_step(self, plan: TaskPlan, step_index: int) -> TaskStep:
        step = plan.steps[step_index]
        step.status = "running"
        
        context = [f"Goal: {plan.goal}", "Past Steps:"]
        for i in range(step_index):
            past = plan.steps[i]
            context.append(f"[{i+1}] {past.description} -> {past.status.upper()}: {past.result or past.error}")
            
        prompt = "\n".join(context) + f"\n\nCurrent Step: {step.description}"
        
        system_prompt = (
            "You are JARVIS Executor. Your job is to complete the 'Current Step'. "
            "Use the provided tools to inspect the system and perform actions. "
            "When you have completed the step or failed, return a natural language summary."
        )
        
        tool_specs = tuple(_tool_spec(d) for d in self.tools.definitions(self.max_risk))
        
        request = AIRequest(
            prompt=prompt,
            system_prompt=system_prompt,
            tools=tool_specs,
        )
        
        response = self.ai.complete(request)
        
        if not response.tool_calls:
            step.status = "completed" if not response.error else "failed"
            step.result = response.content
            if response.error:
                step.error = response.error
            return step
            
        outputs = []
        snapshot_id = None
        
        for call in response.tool_calls:
            # Check tool risk
            definition = next((d for d in self.tools.definitions(self.max_risk) if d.name == call.tool), None)
            if definition and definition.risk > RiskLevel.READ and snapshot_id is None:
                # High risk action detected! Take snapshot before execution.
                snapshot_id = self.snapshot_engine.create_snapshot(reason=f"step_{step_index}_{call.tool}")
                
            tool_req = ToolRequest(tool=call.tool, arguments=dict(call.arguments), max_risk=self.max_risk)
            result = self.tools.execute(tool_req)
            
            # Auto-rollback if a critical tool explicitly failed execution
            if result.status == "error" and snapshot_id:
                self.snapshot_engine.rollback(snapshot_id)
                step.status = "failed"
                step.error = f"Rollback triggered: {result.error}"
                return step
                
            outputs.append(AIToolOutput(call=call, content=_result_for_ai(result)))
            
        answer = self.ai.respond(request, outputs)
        step.status = "completed" if not answer.error else "failed"
        step.result = answer.content
        if answer.error:
            step.error = answer.error
            
        return step

    def run(self, goal: str) -> TaskPlan:
        plan = self.plan(goal)
        plan.status = "running"
        
        for i in range(len(plan.steps)):
            step = self.execute_step(plan, i)
            if step.status == "failed":
                plan.status = "failed"
                return plan
                
        plan.status = "completed"
        return plan
