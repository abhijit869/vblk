#!/usr/bin/env python3
"""JARVIS OS File Explorer.

A dependency-free (standard-library only) graphical file manager for the
JARVIS desktop. It talks directly to the normal Linux filesystem through
Python's filesystem APIs and intentionally keeps AI/tool-routing concerns
outside this GUI application.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import uuid
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk


APP_NAME = "JARVIS Files"
HOME = Path.home()


@dataclass
class ClipboardItem:
    path: Path
    cut: bool


class FileExplorer(tk.Tk):
    """Small, functional desktop file manager for JARVIS OS."""

    def __init__(self, start_path: str | Path | None = None) -> None:
        super().__init__()

        self.title(APP_NAME)
        self.geometry("1050x680")
        self.minsize(760, 480)

        self.current_path = self._safe_directory(start_path or HOME)
        self.history: list[Path] = [self.current_path]
        self.history_index = 0
        self.clipboard: list[ClipboardItem] = []
        self.show_hidden = False
        self.searching = False
        self.sort_column = "name"
        self.sort_reverse = False

        self.address_var = tk.StringVar(value=str(self.current_path))
        self.search_var = tk.StringVar()
        self.status_var = tk.StringVar()

        self._build_ui()
        self._bind_shortcuts()
        self.refresh()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        toolbar = ttk.Frame(self, padding=(8, 8, 8, 4))
        toolbar.pack(fill="x")

        self.back_button = ttk.Button(toolbar, text="←", width=3, command=self.go_back)
        self.back_button.pack(side="left", padx=(0, 3))
        self.forward_button = ttk.Button(toolbar, text="→", width=3, command=self.go_forward)
        self.forward_button.pack(side="left", padx=(0, 3))
        ttk.Button(toolbar, text="↑", width=3, command=self.go_up).pack(side="left", padx=(0, 8))
        ttk.Button(toolbar, text="Home", command=self.go_home).pack(side="left", padx=(0, 8))

        address = ttk.Frame(toolbar)
        address.pack(side="left", fill="x", expand=True)
        self.address_entry = ttk.Entry(address, textvariable=self.address_var)
        self.address_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(address, text="Go", command=self.go_address).pack(side="left", padx=(5, 0))

        ttk.Button(toolbar, text="Refresh", command=self.refresh).pack(side="left", padx=(8, 0))

        search = ttk.Frame(self, padding=(8, 4))
        search.pack(fill="x")
        ttk.Label(search, text="Search:").pack(side="left", padx=(0, 6))
        search_entry = ttk.Entry(search, textvariable=self.search_var)
        search_entry.pack(side="left", fill="x", expand=True)
        search_entry.bind("<Return>", lambda _event: self.start_search())
        ttk.Button(search, text="Find", command=self.start_search).pack(side="left", padx=(5, 0))
        ttk.Button(search, text="Clear", command=self.clear_search).pack(side="left", padx=(5, 0))

        frame = ttk.Frame(self, padding=(8, 4, 8, 4))
        frame.pack(fill="both", expand=True)

        columns = ("name", "type", "size", "modified")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="extended")
        self.tree.heading("name", text="Name", command=lambda: self.sort_by("name"))
        self.tree.heading("type", text="Type", command=lambda: self.sort_by("type"))
        self.tree.heading("size", text="Size", command=lambda: self.sort_by("size"))
        self.tree.heading("modified", text="Modified", command=lambda: self.sort_by("modified"))
        self.tree.column("name", width=470, anchor="w")
        self.tree.column("type", width=130, anchor="w")
        self.tree.column("size", width=110, anchor="e")
        self.tree.column("modified", width=190, anchor="w")

        y_scroll = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        x_scroll = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Return>", lambda _event: self.open_selected())
        self.tree.bind("<Button-3>", self.show_context_menu)

        self.context_menu = tk.Menu(self, tearoff=False)
        self.context_menu.add_command(label="Open", command=self.open_selected)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Copy", command=self.copy_selected)
        self.context_menu.add_command(label="Cut", command=self.cut_selected)
        self.context_menu.add_command(label="Paste", command=self.paste)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="New Folder", command=self.create_folder)
        self.context_menu.add_command(label="Rename", command=self.rename_selected)
        self.context_menu.add_command(label="Move to Trash", command=self.trash_selected)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Refresh", command=self.refresh)

        status = ttk.Frame(self, padding=(8, 4))
        status.pack(fill="x")
        ttk.Label(status, textvariable=self.status_var, anchor="w").pack(side="left", fill="x", expand=True)

        self._build_menu()

    def _build_menu(self) -> None:
        menu_bar = tk.Menu(self)

        file_menu = tk.Menu(menu_bar, tearoff=False)
        file_menu.add_command(label="New Folder", command=self.create_folder, accelerator="Ctrl+Shift+N")
        file_menu.add_command(label="Rename", command=self.rename_selected, accelerator="F2")
        file_menu.add_separator()
        file_menu.add_command(label="Copy", command=self.copy_selected, accelerator="Ctrl+C")
        file_menu.add_command(label="Cut", command=self.cut_selected, accelerator="Ctrl+X")
        file_menu.add_command(label="Paste", command=self.paste, accelerator="Ctrl+V")
        file_menu.add_separator()
        file_menu.add_command(label="Move to Trash", command=self.trash_selected, accelerator="Delete")
        file_menu.add_separator()
        file_menu.add_command(label="Close", command=self.destroy, accelerator="Alt+F4")
        menu_bar.add_cascade(label="File", menu=file_menu)

        view_menu = tk.Menu(menu_bar, tearoff=False)
        self.hidden_var = tk.BooleanVar(value=False)
        view_menu.add_checkbutton(
            label="Show Hidden Files",
            variable=self.hidden_var,
            command=self.toggle_hidden,
        )
        view_menu.add_command(label="Refresh", command=self.refresh, accelerator="F5")
        menu_bar.add_cascade(label="View", menu=view_menu)

        go_menu = tk.Menu(menu_bar, tearoff=False)
        go_menu.add_command(label="Back", command=self.go_back, accelerator="Alt+Left")
        go_menu.add_command(label="Forward", command=self.go_forward, accelerator="Alt+Right")
        go_menu.add_command(label="Up", command=self.go_up, accelerator="Alt+Up")
        go_menu.add_command(label="Home", command=self.go_home)
        menu_bar.add_cascade(label="Go", menu=go_menu)

        self.config(menu=menu_bar)

    def _bind_shortcuts(self) -> None:
        self.bind_all("<Control-c>", lambda _event: self.copy_selected())
        self.bind_all("<Control-x>", lambda _event: self.cut_selected())
        self.bind_all("<Control-v>", lambda _event: self.paste())
        self.bind_all("<Control-Shift-N>", lambda _event: self.create_folder())
        self.bind_all("<F2>", lambda _event: self.rename_selected())
        self.bind_all("<F5>", lambda _event: self.refresh())
        self.bind_all("<Delete>", lambda _event: self.trash_selected())
        self.bind_all("<Alt-Left>", lambda _event: self.go_back())
        self.bind_all("<Alt-Right>", lambda _event: self.go_forward())
        self.bind_all("<Alt-Up>", lambda _event: self.go_up())
        self.bind_all("<Escape>", lambda _event: self.clear_search())

    # ------------------------------------------------------------------
    # Navigation and listing
    # ------------------------------------------------------------------
    @staticmethod
    def _safe_directory(path: str | Path) -> Path:
        candidate = Path(path).expanduser()
        try:
            candidate = candidate.resolve()
        except OSError:
            candidate = HOME.resolve()
        if not candidate.is_dir():
            return HOME.resolve()
        return candidate

    def navigate(self, path: str | Path, *, add_history: bool = True) -> None:
        target = self._safe_directory(path)
        if add_history and target != self.current_path:
            self.history = self.history[: self.history_index + 1]
            self.history.append(target)
            self.history_index += 1
        self.current_path = target
        self.address_var.set(str(target))
        self.search_var.set("")
        self.searching = False
        self.refresh()

    def go_address(self) -> None:
        raw = self.address_var.get().strip()
        if not raw:
            return
        target = Path(raw).expanduser()
        if target.is_dir():
            self.navigate(target)
        elif target.exists():
            self._open_path(target)
        else:
            messagebox.showerror(APP_NAME, f"Path does not exist:\n{target}")

    def go_back(self) -> None:
        if self.history_index <= 0:
            return
        self.history_index -= 1
        self.current_path = self.history[self.history_index]
        self.address_var.set(str(self.current_path))
        self.refresh()

    def go_forward(self) -> None:
        if self.history_index >= len(self.history) - 1:
            return
        self.history_index += 1
        self.current_path = self.history[self.history_index]
        self.address_var.set(str(self.current_path))
        self.refresh()

    def go_up(self) -> None:
        parent = self.current_path.parent
        if parent != self.current_path:
            self.navigate(parent)

    def go_home(self) -> None:
        self.navigate(HOME)

    def refresh(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            paths = list(self._iter_directory(self.current_path))
        except PermissionError:
            self.status_var.set("Permission denied")
            messagebox.showerror(APP_NAME, f"Permission denied:\n{self.current_path}")
            return
        except OSError as exc:
            self.status_var.set(f"Unable to read directory: {exc}")
            return

        if self.searching and self.search_var.get().strip():
            paths = self._search_paths(self.current_path, self.search_var.get().strip())
        else:
            self.searching = False

        rows = [self._row_for_path(path) for path in paths]
        rows.sort(key=self._sort_key, reverse=self.sort_reverse)

        for path, row in rows:
            self.tree.insert("", "end", iid=self._item_id(path), values=row)

        self.address_var.set(str(self.current_path))
        self._update_navigation_state()
        self.status_var.set(f"{len(rows)} item(s)   •   {self.current_path}")

    def _iter_directory(self, path: Path) -> Iterable[Path]:
        entries = path.iterdir()
        for entry in entries:
            if not self.show_hidden and entry.name.startswith("."):
                continue
            yield entry

    def _search_paths(self, root: Path, query: str) -> list[Path]:
        needle = query.casefold()
        matches: list[Path] = []
        try:
            for base, dirs, files in os.walk(root, topdown=True, followlinks=False):
                if not self.show_hidden:
                    dirs[:] = [d for d in dirs if not d.startswith(".")]
                    files = [f for f in files if not f.startswith(".")]
                for name in [*dirs, *files]:
                    if needle in name.casefold():
                        matches.append(Path(base) / name)
        except (PermissionError, OSError):
            pass
        return matches

    def _row_for_path(self, path: Path) -> tuple[Path, tuple[str, str, str, str]]:
        is_dir = path.is_dir()
        type_name = "Folder" if is_dir else self._file_type(path)
        size = "—" if is_dir else self._format_size(self._safe_stat(path).st_size)
        modified = time.strftime("%Y-%m-%d %H:%M", time.localtime(self._safe_stat(path).st_mtime))
        return path, (path.name, type_name, size, modified)

    @staticmethod
    def _safe_stat(path: Path):
        try:
            return path.stat()
        except OSError:
            class Fallback:
                st_size = 0
                st_mtime = 0
            return Fallback()

    @staticmethod
    def _file_type(path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix:
            return f"{suffix[1:].upper()} file"
        return "File"

    @staticmethod
    def _format_size(size: int) -> str:
        value = float(size)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if value < 1024 or unit == "TB":
                return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
            value /= 1024
        return f"{size} B"

    def _sort_key(self, row: tuple[Path, tuple[str, str, str, str]]):
        path, values = row
        if self.sort_column == "size":
            return 0 if path.is_dir() else self._safe_stat(path).st_size
        if self.sort_column == "modified":
            return self._safe_stat(path).st_mtime
        return values[("name", "type", "size", "modified").index(self.sort_column)].casefold()

    def sort_by(self, column: str) -> None:
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column
            self.sort_reverse = False
        self.refresh()

    # ------------------------------------------------------------------
    # Selection / opening
    # ------------------------------------------------------------------
    def _selected_paths(self) -> list[Path]:
        return [Path(iid) for iid in self.tree.selection()]

    def open_selected(self) -> None:
        selected = self._selected_paths()
        if len(selected) != 1:
            return
        self._open_path(selected[0])

    def on_double_click(self, _event: tk.Event) -> None:
        self.open_selected()

    def _open_path(self, path: Path) -> None:
        if path.is_dir():
            self.navigate(path)
            return
        if not path.exists():
            messagebox.showerror(APP_NAME, f"The file no longer exists:\n{path}")
            self.refresh()
            return

        try:
            if sys.platform.startswith("linux"):
                subprocess.Popen(["xdg-open", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            elif sys.platform == "win32":
                os.startfile(str(path))  # type: ignore[attr-defined]
            else:
                webbrowser.open(path.as_uri())
        except (OSError, subprocess.SubprocessError) as exc:
            messagebox.showerror(APP_NAME, f"Unable to open:\n{path}\n\n{exc}")

    # ------------------------------------------------------------------
    # Search / hidden files
    # ------------------------------------------------------------------
    def start_search(self) -> None:
        query = self.search_var.get().strip()
        if not query:
            self.clear_search()
            return
        self.searching = True
        self.refresh()

    def clear_search(self) -> None:
        self.search_var.set("")
        self.searching = False
        self.refresh()

    def toggle_hidden(self) -> None:
        self.show_hidden = bool(self.hidden_var.get())
        self.refresh()

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------
    def create_folder(self) -> None:
        name = simpledialog.askstring(APP_NAME, "New folder name:", parent=self)
        if not name:
            return
        name = name.strip()
        if not name or name in {".", ".."} or "/" in name:
            messagebox.showerror(APP_NAME, "Please enter a valid folder name.")
            return

        target = self.current_path / name
        if target.exists():
            messagebox.showerror(APP_NAME, f"Already exists:\n{target}")
            return
        try:
            target.mkdir()
            self.refresh()
        except OSError as exc:
            messagebox.showerror(APP_NAME, f"Could not create folder:\n{target}\n\n{exc}")

    def rename_selected(self) -> None:
        selected = self._selected_paths()
        if len(selected) != 1:
            return
        source = selected[0]
        name = simpledialog.askstring(APP_NAME, "New name:", initialvalue=source.name, parent=self)
        if not name:
            return
        name = name.strip()
        if not name or name in {".", ".."} or "/" in name:
            messagebox.showerror(APP_NAME, "Please enter a valid name.")
            return

        target = source.with_name(name)
        if target.exists() and target != source:
            messagebox.showerror(APP_NAME, f"Already exists:\n{target}")
            return
        try:
            source.rename(target)
            self.refresh()
        except OSError as exc:
            messagebox.showerror(APP_NAME, f"Could not rename:\n{source}\n\n{exc}")

    def copy_selected(self) -> None:
        paths = self._selected_paths()
        if not paths:
            return
        self.clipboard = [ClipboardItem(path=p, cut=False) for p in paths]
        self.status_var.set(f"Copied {len(paths)} item(s)")

    def cut_selected(self) -> None:
        paths = self._selected_paths()
        if not paths:
            return
        self.clipboard = [ClipboardItem(path=p, cut=True) for p in paths]
        self.status_var.set(f"Ready to move {len(paths)} item(s)")

    def paste(self) -> None:
        if not self.clipboard:
            return

        moved_any = False
        for item in list(self.clipboard):
            source = item.path
            destination = self._unique_destination(self.current_path / source.name)
            try:
                if item.cut:
                    shutil.move(str(source), str(destination))
                elif source.is_dir():
                    shutil.copytree(source, destination)
                else:
                    shutil.copy2(source, destination)
                moved_any = True
            except OSError as exc:
                messagebox.showerror(APP_NAME, f"Could not paste:\n{source}\n\n{exc}")

        if moved_any and any(item.cut for item in self.clipboard):
            self.clipboard = []
        self.refresh()

    @staticmethod
    def _unique_destination(destination: Path) -> Path:
        if not destination.exists():
            return destination
        stem = destination.stem
        suffix = destination.suffix
        for index in range(1, 10000):
            candidate = destination.parent / f"{stem} ({index}){suffix}"
            if not candidate.exists():
                return candidate
        return destination.parent / f"{stem}-{uuid.uuid4().hex[:8]}{suffix}"

    def trash_selected(self) -> None:
        paths = self._selected_paths()
        if not paths:
            return

        answer = messagebox.askyesno(
            APP_NAME,
            f"Move {len(paths)} item(s) to Trash?",
            parent=self,
        )
        if not answer:
            return

        for path in paths:
            try:
                self._move_to_trash(path)
            except OSError as exc:
                messagebox.showerror(APP_NAME, f"Could not move to Trash:\n{path}\n\n{exc}")
        self.refresh()

    @staticmethod
    def _move_to_trash(path: Path) -> None:
        """Use the desktop Trash when available, with a freedesktop fallback."""
        if sys.platform.startswith("linux"):
            gio = shutil.which("gio")
            if gio:
                result = subprocess.run([gio, "trash", str(path)], capture_output=True, text=True)
                if result.returncode == 0:
                    return

            trash_put = shutil.which("trash-put")
            if trash_put:
                result = subprocess.run([trash_put, str(path)], capture_output=True, text=True)
                if result.returncode == 0:
                    return

            trash_root = Path(os.environ.get("XDG_DATA_HOME", HOME / ".local/share")) / "Trash"
            files_dir = trash_root / "files"
            info_dir = trash_root / "info"
            files_dir.mkdir(parents=True, exist_ok=True)
            info_dir.mkdir(parents=True, exist_ok=True)

            destination = files_dir / FileExplorer._unique_destination(files_dir / path.name).name
            shutil.move(str(path), str(destination))

            info_name = destination.name + ".trashinfo"
            original = path.resolve().as_uri()
            deletion_date = time.strftime("%Y-%m-%dT%H:%M:%S")
            (info_dir / info_name).write_text(
                "[Trash Info]\n"
                f"Path={original}\n"
                f"DeletionDate={deletion_date}\n",
                encoding="utf-8",
            )
            return

        # macOS / Windows: prefer the platform's built-in file manager API.
        if sys.platform == "darwin":
            subprocess.run(["osascript", "-e", f'tell application "Finder" to delete POSIX file "{path}"'])
            return
        if sys.platform == "win32":
            from ctypes import windll, wintypes

            # SHFileOperation with FOF_ALLOWUNDO sends the item to Recycle Bin.
            class SHFILEOPSTRUCT(wintypes.Structure):
                _fields_ = [
                    ("hwnd", wintypes.HWND),
                    ("wFunc", wintypes.UINT),
                    ("pFrom", wintypes.LPCWSTR),
                    ("pTo", wintypes.LPCWSTR),
                    ("fFlags", wintypes.WORD),
                    ("fAnyOperationsAborted", wintypes.BOOL),
                    ("hNameMappings", wintypes.LPVOID),
                    ("lpszProgressTitle", wintypes.LPCWSTR),
                ]

            struct = SHFILEOPSTRUCT()
            struct.wFunc = 3  # FO_DELETE
            struct.pFrom = str(path) + "\\0"
            struct.fFlags = 0x0040  # FOF_ALLOWUNDO
            result = windll.shell32.SHFileOperationW(struct)
            if result != 0:
                raise OSError(f"Recycle Bin operation failed with code {result}")
            return

        path.unlink() if path.is_file() or path.is_symlink() else shutil.rmtree(path)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _item_id(path: Path) -> str:
        return str(path.resolve())

    def _update_navigation_state(self) -> None:
        self.back_button.configure(state="normal" if self.history_index > 0 else "disabled")
        self.forward_button.configure(
            state="normal" if self.history_index < len(self.history) - 1 else "disabled"
        )

    def show_context_menu(self, event: tk.Event) -> None:
        row = self.tree.identify_row(event.y)
        if row:
            if row not in self.tree.selection():
                self.tree.selection_set(row)
            self.context_menu.tk_popup(event.x_root, event.y_root)
        else:
            self.tree.selection_remove(self.tree.selection())
            self.context_menu.tk_popup(event.x_root, event.y_root)


def main() -> None:
    start = sys.argv[1] if len(sys.argv) > 1 else None
    app = FileExplorer(start)
    app.mainloop()


if __name__ == "__main__":
    main()
