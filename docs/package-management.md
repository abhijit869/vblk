# Package Management

## Primary Source
JARVIS OS relies on the **Debian Bookworm** repositories as the primary source of truth. All core system updates and standard applications are provided via APT.

## Secondary Source
**Flatpak** is used as an optional secondary source for desktop applications. Flatpak allows for isolated app installations with strict permission controls.

## Security Model
- Arbitrary PPAs and repositories are disabled by default.
- Ubuntu Snaps and Ubuntu App Center are strictly forbidden.
- Package installations go through the JARVIS Policy Engine to verify signatures, dependencies, and system impact.

## Update Policy
Updates are categorized into:
- Security Updates
- System Updates
- Application Updates
- Firmware Updates
- JARVIS Updates
