# Milestone 003: JARVIS v0.3

## Goal

Introduce the AI Agent Engine capable of multi-step planning and execution.

```text
Goal
  ↓
Planner
  ↓
Tool Execution
  ↓
Observer (Verify)
  ↓
Result
```

## Requirements

1. **Agent Planner**: Given a complex goal, break it down into steps.
2. **Executor**: Run steps securely (reusing JARVIS Core's tool execution).
3. **Observer/Verifier**: Evaluate the output of a tool to see if the step succeeded.
4. **Task Manager**: Maintain state of the plan (pending, in-progress, completed, failed).
5. **Controlled Terminal Automation**: Allow chained terminal commands to achieve a verified state.

## Current State

v0.2 is complete, featuring robust single-turn tool execution, redaction, safety checks, SQLite memory, and an initial system snapshot capability.

## Next Work

1. Define the `Agent` protocol and `Task` models.
2. Implement `Planner` that calls the AI Gateway to generate a step-by-step JSON plan.
3. Implement `Executor` that iterates through the plan.
4. Integrate the existing `ToolRegistry` and `MemoryEngine`.
