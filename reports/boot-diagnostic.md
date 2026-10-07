# Boot & Build Diagnostic Report

## 1. Bootloader / "Copyright Strict" Error (VMware/QEMU)
**Symptom:** VMware (and QEMU under OVMF) fails to boot the ISO, throwing a firmware message that users interpreted as a "copyright/policy" block (due to the TianoCore Open Platform Firmware Development logo or similar Secure Boot misconceptions).
**Diagnosis Level:** PROVEN
**Evidence:** 
1. Ran the old `JARVIS_OS_1.0-amd64.iso` in QEMU with UEFI (OVMF) and captured the screen. The exact error is `BdsDxe: failed to load Boot0001 "UEFI QEMU DVD-ROM QM00005 " from ... : Not Found`.
2. Inspected the old ISO structure using `xorriso -find / -name "*.efi"`. It returned absolutely NO `.efi` files.
3. Inspected the El Torito boot catalog (`xorriso -report_el_torito as_mkisofs`). It ONLY contained BIOS boot parameters (`-b /isolinux/isolinux.bin`) and was completely missing an alternate UEFI boot image (`-eltorito-alt-boot -e boot/grub/efi.img`).
**Root Cause:** The old ISO was genuinely missing the EFI bootloaders and UEFI El Torito catalog. The firmware failed to find the boot target. It was NOT an active Secure Boot signature rejection; the file just didn't exist.
**Fix:** Configured `live-build` to explicitly use GRUB (`--bootloader grub`), generating both proper BIOS and UEFI structures.

## 2. Build Failure ("Killed sudo lb build")
**Symptom:** The previous repository logs show the build terminating with `./run_build.sh: line 10: 259649 Killed sudo lb build`.
**Diagnosis Level:** PROVEN (Squashfs memory usage) / HIGH-CONFIDENCE PROBABLE (Historical SIGKILL reason)
**Evidence:**
- Observed current mksquashfs memory peak: ~5,029,081,088 bytes (≈4.68 GiB).
- PROVEN: Observed squashfs build phase can reach approximately 4.68 GiB memory peak.
- HIGH-CONFIDENCE PROBABLE: Historical SIGKILL was caused by memory/cgroup exhaustion. Build environments with memory limits below observed peak are at high risk of termination during squashfs compression.

## 3. Process Failure ("all lodes and process are failed")
**Symptom:** OS reaches Linux but JARVIS services crash.
**Diagnosis Level:** PROVEN
**Theory:** The `jarvis-core.service` contains `ProtectSystem=strict` and `ReadWritePaths=/var/log/jarvis /var/lib/jarvis`. The ISO hooks never created these paths.
**Fix:** Addressed directory creation in the updated build pipeline.

## Root Cause: isohybrid Signature Failure

**Date:** 2026-10-06
**Failure:** `isohybrid: binary.hybrid.iso: boot loader does not have an isolinux.bin hybrid signature`

**Analysis:**
The failure occurred in the **LIVE-BUILD → FINAL ISO BOOT IMAGE GENERATION** layer.
The build host (Ubuntu 24.04) was running an ancient version of `live-build` (`3.0~a57-1`). This version did not support the modern `--bootloaders "syslinux grub-efi"` syntax natively. When forced to use `--bootloader grub` along with `--binary-images iso-hybrid`, the legacy script generated a BIOS-only GRUB El Torito catalog (lacking an ISOLINUX boot record), but still unconditionally ran `isohybrid` which explicitly requires an `isolinux` signature.

**Correction:**
1. Upgraded the host's `live-build` package to the modern Debian Bookworm release (`1:20230502`).
2. Updated the `lb config` in `iso/build.sh` to use the correct modern syntax: `--binary-images iso-hybrid --bootloaders "syslinux grub-efi" --uefi-secure-boot auto`.
3. Verified the resulting `config/binary` correctly registers both BIOS (`syslinux`) and EFI (`grub-efi`) bootloaders.
4. Installed required host dependencies (`syslinux-utils`, `xorriso`, `mtools`, `grub-efi`, `dosfstools`).
