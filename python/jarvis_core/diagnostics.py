"""Diagnostics and Self-Healing Engine for JARVIS."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from jarvis_core.ai_gateway import AIGateway, AIRequest, AIToolSpec
from jarvis_core.agent import AgentEngine, TaskPlan


@dataclass
class RepairStep:
    action: str
    command_or_tool: str
    risk_level: str


@dataclass
class DiagnosisReport:
    issue_signature: str
    root_cause: str
    confidence: float
    recommended_repair: list[RepairStep] = field(default_factory=list)


class DiagnosisEngine:
    def __init__(self, ai: AIGateway, agent_engine: AgentEngine):
        self.ai = ai
        self.agent = agent_engine

    def diagnose_issue(self, issue_description: str) -> DiagnosisReport:
        """Diagnose a system issue and produce a structured report and repair plan."""
        
        # Tool definition to force the AI to return a structured diagnosis report
        submit_diagnosis_tool = AIToolSpec(
            name="submit_diagnosis",
            description="Submit the final diagnosis and repair plan.",
            parameters={
                "type": "object",
                "required": ["root_cause", "confidence", "repair_steps"],
                "properties": {
                    "root_cause": {"type": "string", "description": "Explanation of the root cause."},
                    "confidence": {"type": "number", "description": "Confidence score between 0.0 and 1.0."},
                    "repair_steps": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["action", "command_or_tool", "risk_level"],
                            "properties": {
                                "action": {"type": "string", "description": "Description of the repair step."},
                                "command_or_tool": {"type": "string", "description": "The specific tool or command to run."},
                                "risk_level": {"type": "string", "enum": ["READ", "MEDIUM", "HIGH"]},
                            },
                        },
                    },
                },
                "additionalProperties": False,
            },
        )
        
        system_prompt = (
            "You are the JARVIS Diagnosis Engine. Your job is to analyze system errors. "
            "You have access to a robust OS knowledge and logging environment. "
            "Analyze the given issue and output a structured diagnosis using the submit_diagnosis tool."
        )
        
        request = AIRequest(
            prompt=f"System Issue:\n{issue_description}\n\nDiagnose the root cause and provide a repair plan.",
            system_prompt=system_prompt,
            tools=(submit_diagnosis_tool,),
        )
        
        response = self.ai.complete(request)
        
        root_cause = "Unable to determine root cause."
        confidence = 0.0
        repair_steps = []
        
        if response.tool_calls:
            for call in response.tool_calls:
                if call.tool == "submit_diagnosis":
                    args = call.arguments
                    root_cause = args.get("root_cause", root_cause)
                    confidence = float(args.get("confidence", 0.0))
                    for step_data in args.get("repair_steps", []):
                        repair_steps.append(
                            RepairStep(
                                action=step_data.get("action", ""),
                                command_or_tool=step_data.get("command_or_tool", ""),
                                risk_level=step_data.get("risk_level", "HIGH"),
                            )
                        )
                    break

        return DiagnosisReport(
            issue_signature=issue_description,
            root_cause=root_cause,
            confidence=confidence,
            recommended_repair=repair_steps,
        )

    def generate_repair_plan(self, report: DiagnosisReport) -> TaskPlan:
        """Convert a diagnosis report into an executable TaskPlan for the AgentEngine."""
        goal = f"Repair issue: {report.issue_signature}\nRoot Cause: {report.root_cause}"
        plan = self.agent.plan(goal)
        
        # Override the AI's generated steps with our strictly approved repair steps if desired,
        # but for now, we rely on the agent to formulate the safe execution path based on the diagnosis.
        return plan
