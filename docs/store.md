# JARVIS Software Store

The JARVIS Software Store provides a secure, intuitive graphical interface for managing applications on JARVIS OS. 

## Features
- Native application management through Debian APT
- Optional Flatpak support for sandboxed applications
- Unified metadata and app discovery
- Offline support (cached metadata and local packages)
- Strict policy enforcement (no raw sudo/apt access for GUI)

## Architecture
GUI (JARVIS Store) -> JARVIS Software Service (DBus) -> Tool Registry -> Policy Engine -> Package Backend (APT/Flatpak)

## Supported Profiles
- Targets a 2GB RAM / 2vCPU baseline
- Fast, local-first search
