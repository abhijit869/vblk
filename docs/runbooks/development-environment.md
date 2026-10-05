# Development Environment Runbook

## Current Workspace

This workspace contains a downloaded Debian ISO and an extracted installer tree for inspection. These are local artifacts and are intentionally ignored by Git.

## Safety Rules

Do not modify the host operating system while developing JARVIS OS.

Run system-level experiments in:

```text
VM
container
dedicated test machine
```

Use VM snapshots before destructive recovery tests.

## Dependency Strategy

Add dependencies only when needed by a concrete milestone. Prefer standard Linux interfaces and deterministic software before adding AI or large infrastructure.

## Testing Strategy

Start with local unit tests and integration tests that do not require root. Add VM-based recovery tests only after the recovery lab exists.

## ISO Strategy

Do not manually edit the extracted Debian ISO as the source of truth. Track overlays, packages, and build configuration in the repository, then generate a new ISO from those inputs.
