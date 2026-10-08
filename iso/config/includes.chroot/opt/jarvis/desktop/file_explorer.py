#!/usr/bin/env python3
"""JARVIS OS File Explorer."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Any, Dict, List

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

try:
    import dbus
    DBUS_AVAILABLE = True
except ImportError:
    dbus = None
    DBUS_AVAILABLE = False


APP_NAME = "JARVIS Files"
HOME = Path.home()


@dataclass
class ClipboardItem:
    path: Path
    cut: bool


class DBusFilesClient:
    def __init__(self):
        self.bus = None
        self.proxy = None
        self.iface = None
        if DBUS_AVAILABLE:
            try:
                self.bus = dbus.SystemBus()
                self.proxy = self.bus.get_object("com.jarvis.Core", "/com/jarvis/Files")
                self.iface = dbus.Interface(self.proxy, "com.jarvis.FilesInterface")
            except Exception as e:
                print(f"Warning: Could not connect to D-Bus com.jarvis.Core: {e}")
                
    def _call(self, method_name: str, *args) -> Dict[str, Any]:
        if not self.iface:
            return {"success": False, "error": "D-Bus service not available (Core offline)"}
        try:
            method = getattr(self.iface, method_name)
            res_str = method(*args)
            return json.loads(res_str)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_dir(self, path: str) -> Dict[str, Any]:
        return self._call("List", str(path))
        
    def stat(self, path: str) -> Dict[str, Any]:
        return self._call("Stat", str(path))

    def mkdir(self, path: str) -> Dict[str, Any]:
        return self._call("Mkdir", str(path))

    def copy(self, src: str, dst: str) -> Dict[str, Any]:
        return self._call("Copy", str(src), str(dst))

    def move(self, src: str, dst: str) -> Dict[str, Any]:
        return self._call("Move", str(src), str(dst))

    def rename(self, src: str, name: str) -> Dict[str, Any]:
        return self._call("Rename", str(src), name)

    def trash(self, path: str) -> Dict[str, Any]:
        return self._call("Trash", str(path))

    def search(self, root: str, query: str) -> Dict[str, Any]:
        return self._call("Search", str(root), query)


class FileExplorer(tk.Tk):
    """Small, functional desktop file manager for JARVIS OS."""

    def __init__(self, start_path: str | Path | None = None) -> None:
        super().__init__()

        self.title(APP_NAME)
        self.geometry("1050x680")
        self.minsize(760, 480)

        self.client = DBusFilesClient()

        self.current_path = self._safe_directory(start_path or HOME)
        self.history: list[Path] = [self.current_path]
        self.history_index = 0
        self.clipboard: list[ClipboardItem] = []
        self.show_hidden = False
        
        # Search state
        self.searching = False
        self.search_thread = None
        self.search_cancelled = False
        self.search_results = []
        
        self.sort_column = "name"
        self.sort_reverse = False

        self.address_var = tk.StringVar(value=str(self.current_path))
        self.search_var = tk.StringVar()
        self.status_var = tk.StringVar()

        self._build_ui()
        self._bind_shortcuts()
        self.refresh()

    def _build_ui(self) -> None:
        # Intentionally removed clam theme to use JARVIS OS system look
        
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

        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True, padx=8, pady=4)
        
        sidebar = ttk.Frame(paned)
        paned.add(sidebar, weight=0)
        
        ttk.Label(sidebar, text="Places", font=("", 10, "bold")).pack(anchor="w", pady=(0, 4))
        
        places = [
            ("Home", HOME),
            ("Documents", HOME / "Documents"),
            ("Downloads", HOME / "Downloads"),
            ("Trash", Path(os.environ.get("XDG_DATA_HOME", HOME / ".local" / "share")) / "Trash" / "files"),
            ("Root", Path("/")),
        ]
        
        for name, p in places:
            btn = ttk.Button(sidebar, text=name, command=lambda p=p: self.navigate(p))
            btn.pack(fill="x", pady=2)
            
        main_frame = ttk.Frame(paned)
        paned.add(main_frame, weight=1)

        columns = ("name", "type", "size", "modified")
        self.tree = ttk.Treeview(main_frame, columns=columns, show="headings", selectmode="extended")
        self.tree.heading("name", text="Name", command=lambda: self.sort_by("name"))
        self.tree.heading("type", text="Type", command=lambda: self.sort_by("type"))
        self.tree.heading("size", text="Size", command=lambda: self.sort_by("size"))
        self.tree.heading("modified", text="Modified", command=lambda: self.sort_by("modified"))
        self.tree.column("name", width=400, anchor="w")
        self.tree.column("type", width=100, anchor="w")
        self.tree.column("size", width=100, anchor="e")
        self.tree.column("modified", width=150, anchor="w")

        y_scroll = ttk.Scrollbar(main_frame, orient="vertical", command=self.tree.yview)
        x_scroll = ttk.Scrollbar(main_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        main_frame.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)

        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Return>", lambda _event: self.open_selected())
        self.tree.bind("<Button-3>", self.show_context_menu)
        
        # Guarded bindings: only on Treeview
        self.tree.bind("<Delete>", lambda _event: self.trash_selected())
        self.tree.bind("<Control-c>", lambda _event: self.copy_selected())
        self.tree.bind("<Control-x>", lambda _event: self.cut_selected())
        self.tree.bind("<Control-v>", lambda _event: self.paste())

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
        self.context_menu.add_command(label="Set as Wallpaper", command=self.set_as_wallpaper)
        self.context_menu.add_command(label="Add to Wallpaper Library", command=self.add_to_wallpaper_library)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Refresh", command=self.refresh)

        status_frame = ttk.Frame(self, padding=(8, 4))
        status_frame.pack(fill="x")
        
        self.breadcrumb_var = tk.StringVar()
        ttk.Label(status_frame, textvariable=self.breadcrumb_var, anchor="w").pack(side="left")
        ttk.Label(status_frame, text="  |  ").pack(side="left")
        ttk.Label(status_frame, textvariable=self.status_var, anchor="w").pack(side="left", fill="x", expand=True)

        self._build_menu()

    def _build_menu(self) -> None:
        menu_bar = tk.Menu(self)

        file_menu = tk.Menu(menu_bar, tearoff=False)
        file_menu.add_command(label="New Folder", command=self.create_folder, accelerator="Ctrl+Shift+N")
        file_menu.add_command(label="Rename", command=self.rename_selected, accelerator="F2")
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
        self.bind_all("<Control-Shift-N>", lambda _event: self.create_folder())
        self.bind_all("<F2>", lambda _event: self.rename_selected())
        self.bind_all("<F5>", lambda _event: self.refresh())
        self.bind_all("<Alt-Left>", lambda _event: self.go_back())
        self.bind_all("<Alt-Right>", lambda _event: self.go_forward())
        self.bind_all("<Alt-Up>", lambda _event: self.go_up())
        self.bind_all("<Escape>", lambda _event: self.cancel_search())

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
        if self.searching:
            self.cancel_search()
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
        else:
            messagebox.showerror(APP_NAME, f"Directory does not exist or is a file:\n{target}")

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
            
        self.breadcrumb_var.set(f"📍 {self.current_path}")

        if self.searching:
            return

        res = self.client.list_dir(str(self.current_path))
        if not res.get("success"):
            error = res.get("error", "Unknown error")
            if "NOT_ABSOLUTE_PATH" in error:
                pass
            self.status_var.set(f"Error: {error}")
            if "Core offline" in error:
                pass
            return

        entries = res.get("entries", [])
        if not self.show_hidden:
            entries = [e for e in entries if not e["name"].startswith(".")]

        rows = []
        for e in entries:
            p = self.current_path / e["name"]
            is_dir = e["is_dir"]
            type_name = "Folder" if is_dir else self._file_type(p)
            size_val = 0 if is_dir else e["size"]
            size_str = "—" if is_dir else self._format_size(size_val)
            mod_val = e["modified"]
            mod_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(mod_val))
            rows.append((p, (e["name"], type_name, size_str, mod_str), size_val, mod_val))
            
        rows.sort(key=self._sort_key, reverse=self.sort_reverse)

        for p, display_vals, size_val, mod_val in rows:
            self.tree.insert("", "end", iid=self._item_id(p), values=display_vals)

        if not rows:
            self.status_var.set(f"Folder is empty")
        else:
            self.status_var.set(f"{len(rows)} item(s)")
            
        self.address_var.set(str(self.current_path))
        self._update_navigation_state()

    def _file_type(self, path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix:
            return f"{suffix[1:].upper()} file"
        return "File"

    def _format_size(self, size: int) -> str:
        value = float(size)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if value < 1024 or unit == "TB":
                return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
            value /= 1024
        return f"{size} B"

    def _sort_key(self, row):
        p, display_vals, size_val, mod_val = row
        if self.sort_column == "size":
            return 0 if p.is_dir() else size_val
        if self.sort_column == "modified":
            return mod_val
        return display_vals[("name", "type", "size", "modified").index(self.sort_column)].casefold()

    def sort_by(self, column: str) -> None:
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column
            self.sort_reverse = False
        self.refresh()

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
        res = self.client.stat(str(path))
        if not res.get("success"):
            messagebox.showerror(APP_NAME, f"The file no longer exists or access denied:\n{path}")
            self.refresh()
            return
            
        is_dir = res.get("is_dir")
        if is_dir:
            self.navigate(path)
            return

        if path.suffix == ".desktop" or os.access(path, os.X_OK):
            messagebox.showinfo(APP_NAME, "Execution of desktop files and executables from file manager is blocked for security.")
            return

        try:
            subprocess.Popen(["xdg-open", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError as exc:
            messagebox.showerror(APP_NAME, f"Unable to open:\n{path}\n\n{exc}")

    def start_search(self) -> None:
        query = self.search_var.get().strip()
        if not query:
            self.clear_search()
            return
        self.searching = True
        self.search_cancelled = False
        self.status_var.set(f"Searching for '{query}'...")
        
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        def search_worker():
            try:
                needle = query.casefold()
                root = self.current_path.resolve()
                found = []
                for base, dirs, files in os.walk(root, topdown=True, followlinks=False):
                    if self.search_cancelled:
                        break
                    if not self.show_hidden:
                        dirs[:] = [d for d in dirs if not d.startswith(".")]
                        files = [f for f in files if not f.startswith(".")]
                    for name in [*dirs, *files]:
                        if needle in name.casefold():
                            found.append(Path(base) / name)
                            if len(found) >= 2000:
                                break
                    if len(found) >= 2000:
                        break
                self.search_results = found
            except Exception:
                pass

        self.search_thread = threading.Thread(target=search_worker)
        self.search_thread.start()
        self.after(100, self._poll_search)

    def _poll_search(self) -> None:
        if self.search_thread and self.search_thread.is_alive():
            self.after(100, self._poll_search)
        elif not self.search_cancelled:
            # Render results
            self._render_search_results()
            
    def _render_search_results(self):
        for p in self.search_results:
            st = self.client.stat(str(p))
            if st.get("success"):
                is_dir = st["is_dir"]
                type_name = "Folder" if is_dir else self._file_type(p)
                size_str = "—" if is_dir else self._format_size(st["size"])
                mod_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(st["modified"]))
                self.tree.insert("", "end", iid=self._item_id(p), values=(p.name, type_name, size_str, mod_str))
        self.status_var.set(f"Found {len(self.search_results)} item(s). Press Esc to clear.")
        
    def cancel_search(self) -> None:
        if self.searching:
            self.search_cancelled = True
            self.clear_search()

    def clear_search(self) -> None:
        self.search_var.set("")
        self.searching = False
        self.refresh()

    def toggle_hidden(self) -> None:
        self.show_hidden = bool(self.hidden_var.get())
        self.refresh()

    def create_folder(self) -> None:
        name = simpledialog.askstring(APP_NAME, "New folder name:", parent=self)
        if not name:
            return
        name = name.strip()
        target = self.current_path / name
        res = self.client.mkdir(str(target))
        if not res.get("success"):
            messagebox.showerror(APP_NAME, f"Could not create folder:\n{target}\n\n{res.get('error')}")
        else:
            self.refresh()

    def rename_selected(self) -> None:
        selected = self._selected_paths()
        if len(selected) != 1:
            return
        source = selected[0]
        name = simpledialog.askstring(APP_NAME, "New name:", initialvalue=source.name, parent=self)
        if not name:
            return
        name = name.strip()
        res = self.client.rename(str(source), name)
        if not res.get("success"):
            messagebox.showerror(APP_NAME, f"Could not rename:\n{source}\n\n{res.get('error')}")
        else:
            self.refresh()

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
            
            if item.cut:
                res = self.client.move(str(source), str(destination))
            else:
                res = self.client.copy(str(source), str(destination))
                
            if res.get("success"):
                moved_any = True
            else:
                messagebox.showerror(APP_NAME, f"Could not paste:\n{source}\n\n{res.get('error')}")

        if moved_any and any(item.cut for item in self.clipboard):
            self.clipboard = []
        self.refresh()

    @staticmethod
    def _unique_destination(destination: Path) -> Path:
        if not destination.exists() and not destination.is_symlink():
            return destination
        stem = destination.stem
        suffix = destination.suffix
        for index in range(1, 10000):
            candidate = destination.parent / f"{stem} ({index}){suffix}"
            if not candidate.exists() and not candidate.is_symlink():
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
            res = self.client.trash(str(path))
            if not res.get("success"):
                messagebox.showerror(APP_NAME, f"Could not move to Trash:\n{path}\n\n{res.get('error')}")
        self.refresh()

    @staticmethod
    def _item_id(path: Path) -> str:
        return os.path.abspath(str(path))

    def _update_navigation_state(self) -> None:
        self.back_button.configure(state="normal" if self.history_index > 0 else "disabled")
        self.forward_button.configure(
            state="normal" if self.history_index < len(self.history) - 1 else "disabled"
        )

    def set_as_wallpaper(self) -> None:
        selection = self.tree.selection()
        if not selection: return
        iid = selection[0]
        path = self.nodes.get(iid)
        if not path or not path.is_file(): return
        
        if DBUS_AVAILABLE:
            try:
                bus = dbus.SystemBus()
                proxy = bus.get_object("com.jarvis.Core", "/com/jarvis/Wallpaper")
                iface = dbus.Interface(proxy, "com.jarvis.WallpaperInterface")
                res_str = iface.AddWallpaper(str(path), path.name)
                res = json.loads(res_str)
                if res.get("success"):
                    wid = res["wallpaper"]["id"]
                    iface.SetCurrent(wid)
                    messagebox.showinfo("Wallpaper", "Wallpaper applied successfully.")
                else:
                    messagebox.showerror("Error", res.get("error", "Unknown error"))
            except Exception as e:
                messagebox.showerror("Error", f"Failed to set wallpaper: {e}")

    def add_to_wallpaper_library(self) -> None:
        selection = self.tree.selection()
        if not selection: return
        iid = selection[0]
        path = self.nodes.get(iid)
        if not path or not path.is_file(): return
        
        if DBUS_AVAILABLE:
            try:
                bus = dbus.SystemBus()
                proxy = bus.get_object("com.jarvis.Core", "/com/jarvis/Wallpaper")
                iface = dbus.Interface(proxy, "com.jarvis.WallpaperInterface")
                res_str = iface.AddWallpaper(str(path), path.name)
                res = json.loads(res_str)
                if res.get("success"):
                    messagebox.showinfo("Wallpaper", "Added to Wallpaper Library.")
                else:
                    messagebox.showerror("Error", res.get("error", "Unknown error"))
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add to library: {e}")

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
