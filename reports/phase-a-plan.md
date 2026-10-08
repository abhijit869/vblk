# Phase A Findings and Implementation Plan

## 4. Stale Files Identified
- Various `*.ppm` and `*.png` screen captures (`vm_screen*.ppm`, `vm_screen*.png`, `qemu_bios_screen.png`)
- Various log files (`llama_2048.log`, `llama_4096.log`, `server.log`, `build_mem.log`, `full_build_output.log`)
- Stale PID files (`llama_server.pid`, `server.pid`)
- Temporary patch scripts (`patch_*.py`, `fix_*.py`, `super_patch.py`)
- Temporary JSON and command files (`qmp_cmd.json`, `qmp.cmds`, `qmp_cmd_tmp.json`)
- Stray test/dummy files (`empty_file`, `empty_dir`, `dummy`, `bootlogo.cpio`)

## 5. Source/Runtime Mismatches
- Legacy ISO builder scripts (`iso/build.sh`) are mixed with new build scripts (`scripts/build/build-iso.sh`).
- llama.cpp build caching allows bypass without verifying staging (`scripts/build/build-llama-cpp.sh`).
- AI Gateway and Local AI use arbitrary port checking rather than systemd-native readiness dependencies.

## 6. Security Boundary Violations
- D-Bus prototype currently uses SessionBus rather than SystemBus, allowing UI direct access to privileged components.
- Root shell commands executed from UI/Agent without sufficient PathGuard restrictions.
- Weak capabilities isolation on `systemd/jarvis-local-ai.service` and `jarvis-core.service`.
- In-memory prototype audit log does not persist data securely.

## 7. Current Validated Features That Must Not Regress
- Bootable ISO generation (BIOS & UEFI).
- Successful loading of `Qwen3` via `llama-server`.
- Core JARVIS services (EventBus, Tools, Policy).
- PathGuard preventing basic path traversal.
- 2GB/4GB memory profiles.

## 8. Exact Implementation Plan

### Phase B: Make build/runtime consistent
- Delete stale generated artifacts (logs, images, PID files, patch scripts).
- Update `scripts/build/build-llama-cpp.sh` to be fully idempotent, checking SHA256 and enforcing correct permissions.
- Ensure `scripts/build/build-iso.sh` fails immediately if mandatory artifacts are missing.

### Phase C: Local AI + systemd + D-Bus
- Standardize systemd dependencies (`jarvis-local-ai.service` -> `jarvis-core.service` -> `jarvis-eventbus.service`).
- Switch D-Bus to `SystemBus` (`com.jarvis.Core`) with explicit authorization.
- Remove infinite shell loops; use real readiness probes.

### Phase D: Security control plane
- Upgrade Audit log to persistent, append-only disk storage.
- Minimize systemd service capabilities (e.g., `NoNewPrivileges`, `ProtectSystem`).
- Enforce strict PathGuard validation against symlinks and traversals.

### Phase E: Desktop shell
- Stabilize window management.
- Develop JARVIS Shell, Top Bar, Dock, System HUD.

### Phase F: File Explorer + Wallpaper
- Import themes and assets from the ZIP archive safely.
- Link File Explorer and Wallpaper changes to Policy Engine and authorized APIs.

### Phase G: Launcher + Settings + Network + Monitor
- Implement Application Launcher sourcing `.desktop` files.
- Implement Setting panels mapping to real backend state.
- Implement Network and System Monitor UIs leveraging deterministic JARVIS tools.

### Phase H: Diagnostics + Recovery + Memory
- Create deterministic diagnostic routines.
- Upgrade `rollback.py` to support real filesystem/config snapshot/rollback.
- Integrate SQLite for separated memory types.

### Phase I: Installer + Update + Recovery environment
- Evaluate if a real installer is provided; if so, validate against disposable virtual disks.

### Phase J: Production validation
- Complete all Layer A (Automated) and Layer B (Visual) tests.
- Produce `reports/final-system-audit.md`.
