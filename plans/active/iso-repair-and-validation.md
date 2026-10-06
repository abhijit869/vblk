# ISO Repair and Validation Plan

## GOAL
Make the existing Debian-based JARVIS OS repository produce a genuinely bootable, testable ISO and validate that ISO in QEMU/VMware.

## STAGES
1. **INSPECT**: Understand the build pipeline and environment.
2. **DIAGNOSE**: Find root causes of boot failure ("copyright strict") and systemd crashes ("process failed").
3. **PLAN**: Fix GRUB/Secure Boot, fix systemd directory permissions, organize build scripts.
4. **FIX**: Applied in `1636b5c`.
5. **BUILD**: Executing clean build via `run_build_clean.sh` inside `/tmp/jarvis_build`.
6. **VERIFY ISO**: Inspect generated ISO layout.
7. **QEMU TEST**: Validate BIOS/UEFI boot and Linux userspace.
8. **VMWARE BOOT**: (Simulated via QEMU since VMware automation is unavailable).
9. **BOOT HEALTH**: Check systemd logs and services.
10. **SECURITY TEST**: Check sandbox capabilities.

## CURRENT STATUS
- Diagnosed and fixed UEFI bootloader misconfiguration and systemd directory dependencies.
- Build is running.

