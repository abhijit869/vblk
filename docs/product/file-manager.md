# JARVIS OS File Manager

## Purpose
The File Explorer (`desktop/file_explorer.py`) provides a dependency-free graphical interface for the JARVIS OS desktop environment, built with Tkinter.

## Two-Tier Security Model
The File Explorer complies with the JARVIS architecture's Two-Tier isolation model:
1. **Tier 1 (User Space):** The GUI runs under an unprivileged user (`jarvis`), communicating via D-Bus instead of using local raw `shutil` commands.
2. **Tier 2 (System Space):** The `com.jarvis.Core` daemon validates all operations. The `PathGuard` module intercepts operations, protecting Tier 2 directories like `/etc` and `/var/lib/jarvis` from write/tamper attempts.

## Allowed and Blocked Actions
- **Allowed:** Browsing local user directories, renaming files, trashing files (using freedesktop specification), creating folders.
- **Blocked:** Permanent deletion (no `unlink` or `rmtree`), executing `.desktop` files or binaries directly from the explorer, symlink escape attempts to restricted areas.

## D-Bus / Tool API
The File Manager operates via `com.jarvis.FilesInterface` exported by the Core daemon. It uses these methods:
- `List(path)`
- `Stat(path)`
- `Mkdir(path)`
- `Copy(src, dst)`
- `Move(src, dst)`
- `Rename(src, name)`
- `Trash(path)`
- `Search(root, query)`

## Adding New Desktop Apps
New desktop applications should replicate the `jarvis_panel.py` or `file_explorer.py` pattern:
1. Run as the unprivileged user.
2. Connect to the `com.jarvis.Core` SystemBus.
3. Expose functionality through D-Bus endpoints within `jarvis_core.dbus_service` (like `FilesInterface`).
4. Avoid any usage of `os.system` or `subprocess.run(shell=True)`.
