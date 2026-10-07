# ISO Repair and Validation Plan

## GOAL
Make the existing Debian-based JARVIS OS repository produce a genuinely bootable, testable ISO and validate that ISO in QEMU/VMware.

## STAGES
1. **INSPECT**: Understand the build pipeline and environment.
2. **DIAGNOSE**: Find root causes of boot failure ("copyright strict") and systemd crashes ("process failed").
3. **PLAN**: Fix GRUB/Secure Boot, fix systemd directory permissions, organize build scripts.
4. **FIX**: Applied in `1636b5c`.
5. **BUILD**: Executing clean build via `build-iso.sh` inside `/tmp/jarvis_build`.
6. **VERIFY ISO**: Inspect generated ISO layout.
7. **QEMU TEST**: Validate BIOS/UEFI boot and Linux userspace.
8. **VMWARE BOOT**: (Simulated via QEMU since VMware automation is unavailable).
9. **BOOT HEALTH**: Check systemd logs and services.
10. **SECURITY TEST**: Check sandbox capabilities.

## CURRENT STATUS
- Diagnosed UEFI bootloader misconfiguration (missing UEFI El Torito catalog) and systemd directory dependencies.
- **BUILD FAILED**: The final `scripts/build/build-iso.sh` terminated with exit code 1. The `isohybrid` stage failed with `boot loader does not have an isolinux.bin hybrid signature` because live-build was configured to use `--bootloader grub` but `isohybrid` requires ISOLINUX or explicit UEFI args for hybrid images.
- **VALIDATION BLOCKED**: Stages 6 through 10 (Verify ISO, QEMU boot, Boot health, Security test, etc.) are strictly BLOCKED until the build pipeline is corrected to successfully emit `JARVIS-OS-1.0-amd64.iso`.

### LIVE-BUILD BOOTLOADER REPAIR (COMPLETED)
- **Root Cause Identified:** `isohybrid expected an ISOLINUX hybrid boot structure, but the selected GRUB-only build did not provide the required isolinux hybrid signature.` (LIVE-BUILD → FINAL ISO BOOT IMAGE GENERATION layer).
- **Fix Applied:** Upgraded host `live-build` to Debian 12 version (`1:20230502`) to unlock support for `--bootloaders "syslinux grub-efi"` and `--uefi-secure-boot auto`. Reconfigured `iso/build.sh` to use these parameters alongside `--binary-images iso-hybrid`.
- **Validation:** Clean config generated correctly showing both BIOS and EFI bootloaders.
