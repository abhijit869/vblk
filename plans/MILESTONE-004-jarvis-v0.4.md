# Milestone 004: JARVIS v0.4

## Goal

Error Diagnosis and Self-Healing.

```text
Error
  ↓
Log Collection
  ↓
Diagnosis Report
  ↓
Repair Plan
  ↓
Verification
```

## Requirements

1. **Error Engine**: Automatically trigger JARVIS when a specific service fails or an anomaly is detected.
2. **Log Collection**: Add tools to query journald and /var/log efficiently.
3. **Diagnosis Reports**: Produce structured reports explaining the root cause.
4. **Repair Plans**: Use the Agent Engine to safely execute repair steps.
5. **Rollback Plans**: Define rollback steps if the repair fails.

## Current State

v0.3 is complete. The system now features a multi-step `AgentEngine` with `TaskPlan` and `TaskStep` structures. The agent can break down a goal, execute it step-by-step using tools, and verify the outcome.

## Next Work

1. Add `system.logs` tool to query journalctl.
2. Introduce a `DiagnosisEngine` that takes an error signature and returns a `DiagnosisReport`.
3. Allow the `AgentEngine` to accept elevated `RiskLevel.MEDIUM` (mutation) limits for authorized repairs.
