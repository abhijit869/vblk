# JARVIS File Explorer - Reconnaissance Report

## Ground Truth & Baseline
- Extracted `desktop/file_explorer.py` from `downloads/jarvis-os-file-explorer-final.zip` (it is 626 lines, Tkinter).
- Baseline Tests: Ran `PYTHONPATH=python python3 -m unittest discover -s tests`. Output was 70 tests passed (`OK`), 0 errors. The expected `KeyError: 'ip_address'` in `test_security_block_ip` did not occur on my system (which seems to be due to environmental differences; no tests were weakened).

## What Exists
- `desktop/jarvis_panel.py` and `desktop/jarvis-panel.desktop` exist and show the D-Bus frontend integration pattern.
- The `iso/build.sh` script copies system files. There is a noted hazard regarding `iso/config/includes.chroot/opt/jarvis/**` files drifting from the `python/` directory.
- D-Bus is configured with `dbus.SessionBus()` in `python/jarvis_core/dbus_service.py` despite `jarvis-core.service` running as a system service.
- The current tool registry (`python/jarvis_core/tools.py`) implements `file.read` and `file.search` but lacks write/mutation file tools.
- Openbox `autostart` and `systemd` services point to different python environments (e.g. `/opt/jarvis/bin/python3` vs `/usr/bin/python3`).

## What is Missing
- **Path Policy:** `python/jarvis_core/pathguard.py` does not exist.
- **File Service:** `python/jarvis_core/files.py` does not exist.
- **File Tools:** `file.list`, `file.stat`, `file.mkdir`, `file.copy`, `file.rename`, `file.move`, `file.trash` are missing from the tool registry.
- **D-Bus File API:** `FilesInterface` is missing in `python/jarvis_core/dbus_service.py`.
- **D-Bus Security:** No `/etc/dbus-1/system.d/com.jarvis.Core.conf` exists to secure the bus name.
- **File Explorer Desktop Integration:** No `.desktop` launcher, SVG icon, or MIME type associations exist for `file_explorer.py`.
- **AST Security Scanner:** `tests/security/test_file_boundary.py` is missing.
- **Autologin/Display Manager:** Noted by the instructions; might need a manual `startx` workaround during boot testing.

## What I Will Change
1. **Security & Core (Phase 1 & 3):** Implement `PathGuard` with Tier 1/Tier 2 isolation. Implement `FileService`. Add new Tools into the registry (`file.mkdir`, etc.). Add `FilesInterface` to D-Bus and secure it using a D-Bus policy file. Modify `start_dbus_service` to run/adapt correctly.
2. **Refactor GUI (Phase 2):** Strip macOS/Win32 branches from `file_explorer.py`. Fix GUI bugs (symlinks, event binds, thread blocking, NUL validation, `shutil.copytree` recursions, etc.). Fix the f-string issue.
3. **Desktop Wiring (Phase 4):** Create `jarvis-files.desktop` and a minimal SVG icon. Update MIME associations.
4. **ISO Build (Phase 5):** Remove or fix the duplicate chroot tracking in Git to prevent drift. Sync `python3` paths. Add `jarvis-files.desktop` and default app settings via ISO hooks.
5. **Testing (Phase 6):** Add unit tests for `PathGuard`, `FileService`, tool registry boundaries, and the AST scan boundary for `desktop/` scripts.
6. **Boot Test & Validation (Phase 7):** Generate the ISO, boot VM (2GB & 4GB), and run all specified validations, recording OOM/RSS logs.
