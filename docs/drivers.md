# Hardware and Drivers

JARVIS OS detects hardware automatically and provides relevant Debian firmware.

## Supported Firmware
- `firmware-linux`
- `firmware-amd-graphics`
- `firmware-iwlwifi` (Intel Wi-Fi)
- `firmware-brcm80211` (Broadcom)
- `firmware-realtek` (Realtek)
- `intel-microcode`, `amd64-microcode`

## Policy
Drivers are sourced exclusively from Debian repositories. The system avoids blindly installing unsupported or non-free drivers without explicit detection of hardware. NetworkManager is the exclusive authority for networking configurations.
