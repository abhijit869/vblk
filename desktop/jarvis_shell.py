import tkinter as tk
from tkinter import ttk, messagebox
import time
import subprocess
import threading
import json

try:
    import dbus
    DBUS_AVAILABLE = True
except ImportError:
    DBUS_AVAILABLE = False

BG_COLOR = "#0A0F1C"
PANEL_BG = "#12182B"
TEXT_COLOR = "#E2E8F0"
ACCENT_COLOR = "#0EA5E9"

class JarvisTopBar(tk.Toplevel):
    def __init__(self, master, iface):
        super().__init__(master)
        self.iface = iface
        self.overrideredirect(True)
        w = self.winfo_screenwidth()
        self.geometry(f"{w}x24+0+0")
        self.configure(bg=PANEL_BG)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.85)

        # Left: Branding & Workspaces
        left_frame = tk.Frame(self, bg=PANEL_BG)
        left_frame.pack(side=tk.LEFT, padx=10)
        tk.Label(left_frame, text="JARVIS OS", bg=PANEL_BG, fg=ACCENT_COLOR, font=("Helvetica", 10, "bold")).pack(side=tk.LEFT)
        tk.Label(left_frame, text=" | 1  2  3  4", bg=PANEL_BG, fg=TEXT_COLOR, font=("Helvetica", 9)).pack(side=tk.LEFT)

        # Center: Clock
        self.clock_lbl = tk.Label(self, text="", bg=PANEL_BG, fg=TEXT_COLOR, font=("Helvetica", 9))
        self.clock_lbl.pack(side=tk.LEFT, expand=True)

        # Right: Tray
        self.status_lbl = tk.Label(self, text="Status: Checking...", bg=PANEL_BG, fg=TEXT_COLOR, font=("Helvetica", 9))
        self.status_lbl.pack(side=tk.RIGHT, padx=10)

        self.update_clock()
        self.update_status()

    def update_clock(self):
        self.clock_lbl.config(text=time.strftime("%a, %b %d, %Y  %I:%M %p"))
        self.after(1000, self.update_clock)

    def update_status(self):
        if self.iface:
            try:
                st = self.iface.Status()
                self.status_lbl.config(text=f"Core: {st}", fg="#10B981")
            except:
                self.status_lbl.config(text="Core: Offline", fg="#EF4444")
        self.after(5000, self.update_status)

class JarvisLeftDock(tk.Toplevel):
    def __init__(self, master, shell_app):
        super().__init__(master)
        self.shell_app = shell_app
        self.overrideredirect(True)
        h = self.winfo_screenheight() - 24
        self.geometry(f"48x{h}+0+24")
        self.configure(bg=PANEL_BG)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.85)

        apps = [
            ("Home", shell_app.launch_explorer),
            ("Files", shell_app.launch_explorer),
            ("Terminal", shell_app.launch_terminal),
            ("AI", shell_app.toggle_ai),
            ("Settings", shell_app.launch_settings)
        ]
        
        for name, cmd in apps:
            btn = tk.Button(self, text=name[:2], bg="#1E293B", fg="white", bd=0, command=cmd)
            btn.pack(pady=10, padx=4, fill=tk.X)
            
        # Grid/Start Menu button at bottom
        self.start_btn = tk.Button(self, text=":::", bg=ACCENT_COLOR, fg="white", bd=0, font=("Helvetica", 14), command=shell_app.toggle_launcher)
        self.start_btn.pack(side=tk.BOTTOM, pady=20, fill=tk.X)

class JarvisBottomDock(tk.Toplevel):
    def __init__(self, master, shell_app):
        super().__init__(master)
        self.shell_app = shell_app
        self.overrideredirect(True)
        w = 400
        x = (self.winfo_screenwidth() - w) // 2
        y = self.winfo_screenheight() - 50
        self.geometry(f"{w}x40+{x}+{y}")
        self.configure(bg=PANEL_BG)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.9)

        apps = [
            ("Web", shell_app.launch_browser),
            ("Files", shell_app.launch_explorer),
            ("Term", shell_app.launch_terminal),
            ("Code", shell_app.launch_code),
            ("Settings", shell_app.launch_settings)
        ]
        
        for name, cmd in apps:
            btn = tk.Button(self, text=name, bg="#1E293B", fg="white", bd=0, command=cmd)
            btn.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=2, pady=2)

class JarvisAppLauncher(tk.Toplevel):
    def __init__(self, master, shell_app):
        super().__init__(master)
        self.shell_app = shell_app
        self.overrideredirect(True)
        w, h = 600, 450
        x = 55  # Next to left dock
        y = self.winfo_screenheight() - h - 50
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.configure(bg=PANEL_BG)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.95)

        # Simple split layout
        left = tk.Frame(self, bg="#0F172A", width=150)
        left.pack(side=tk.LEFT, fill=tk.Y)
        left.pack_propagate(False)
        
        tk.Label(left, text="Favorites", bg="#0F172A", fg="white", font=("Helvetica", 10)).pack(pady=10, anchor="w", padx=10)
        tk.Label(left, text="All Applications", bg="#0F172A", fg="#94A3B8", font=("Helvetica", 10)).pack(pady=5, anchor="w", padx=10)

        right = tk.Frame(self, bg=PANEL_BG)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(right, text="Search apps...", bg="#1E293B", fg="#94A3B8", anchor="w").pack(fill=tk.X, padx=20, pady=20, ipady=5)

        grid = tk.Frame(right, bg=PANEL_BG)
        grid.pack(fill=tk.BOTH, expand=True, padx=20)
        
        apps = [
            ("Firefox", shell_app.launch_browser),
            ("Files", shell_app.launch_explorer),
            ("Terminal", shell_app.launch_terminal),
            ("Settings", shell_app.launch_settings)
        ]
        
        for i, (name, cmd) in enumerate(apps):
            btn = tk.Button(grid, text=name, bg="#1E293B", fg="white", bd=0, width=15, height=3, command=cmd)
            btn.grid(row=i//3, column=i%3, padx=10, pady=10)

        self.bind("<FocusOut>", lambda e: self.withdraw())
        self.withdraw()

class JarvisWidgets(tk.Toplevel):
    def __init__(self, master, diag_iface):
        super().__init__(master)
        self.diag_iface = diag_iface
        self.overrideredirect(True)
        w = 300
        h = self.winfo_screenheight() - 100
        x = self.winfo_screenwidth() - w - 20
        y = 40
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.configure(bg=PANEL_BG)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.9)
        self.attributes("-transparentcolor", PANEL_BG) # If supported

        # Stacked widgets
        self.sys_widget = tk.Frame(self, bg="#1E293B", height=120)
        self.sys_widget.pack(fill=tk.X, pady=(0, 15))
        tk.Label(self.sys_widget, text="System Monitor", bg="#1E293B", fg="white").pack(anchor="nw", padx=10, pady=5)
        self.cpu_lbl = tk.Label(self.sys_widget, text="CPU: --%", bg="#1E293B", fg=ACCENT_COLOR)
        self.cpu_lbl.pack(pady=5)

        self.ai_widget = tk.Frame(self, bg="#1E293B", height=200)
        self.ai_widget.pack(fill=tk.X, pady=15)
        tk.Label(self.ai_widget, text="JARVIS AI (Qwen3)", bg="#1E293B", fg="white").pack(anchor="nw", padx=10, pady=5)
        
        self.net_widget = tk.Frame(self, bg="#1E293B", height=100)
        self.net_widget.pack(fill=tk.X, pady=15)
        tk.Label(self.net_widget, text="Network", bg="#1E293B", fg="white").pack(anchor="nw", padx=10, pady=5)
        self.net_lbl = tk.Label(self.net_widget, text="Loading...", bg="#1E293B", fg=ACCENT_COLOR)
        self.net_lbl.pack(pady=5)

        self.update_widgets()

    def update_widgets(self):
        if self.diag_iface:
            try:
                res_sys = json.loads(self.diag_iface.GetSystem())
                if res_sys.get("status") == "ok":
                    cpu = res_sys["data"].get("cpu", "").split("\\n")[0]
                    self.cpu_lbl.config(text=cpu[:30])
                    
                res_net = json.loads(self.diag_iface.GetNetwork())
                if res_net.get("status") == "ok":
                    net = res_net["data"].get("interfaces", "").split("\\n")[0]
                    self.net_lbl.config(text=net[:30])
            except:
                pass
        self.after(5000, self.update_widgets)

class JarvisShell(tk.Tk):
    def __init__(self):
        super().__init__()
        self.withdraw()
        
        self.bus = None
        self.jarvis_iface = None
        self.diag_iface = None
        
        if DBUS_AVAILABLE:
            try:
                self.bus = dbus.SystemBus()
                proxy = self.bus.get_object("com.jarvis.Core", "/com/jarvis/Core")
                self.jarvis_iface = dbus.Interface(proxy, "com.jarvis.CoreInterface")
                
                dproxy = self.bus.get_object("com.jarvis.Core", "/com/jarvis/Diagnostics")
                self.diag_iface = dbus.Interface(dproxy, "com.jarvis.DiagnosticsInterface")
            except Exception:
                pass

        self.top_bar = JarvisTopBar(self, self.jarvis_iface)
        self.left_dock = JarvisLeftDock(self, self)
        self.bottom_dock = JarvisBottomDock(self, self)
        self.launcher = JarvisAppLauncher(self, self)
        self.widgets = JarvisWidgets(self, self.diag_iface)

    def launch_explorer(self):
        self.launcher.withdraw()
        subprocess.Popen(["/usr/bin/python3", "/opt/jarvis/desktop/file_explorer.py"])

    def launch_terminal(self):
        self.launcher.withdraw()
        subprocess.Popen(["x-terminal-emulator"])

    def launch_settings(self):
        self.launcher.withdraw()
        subprocess.Popen(["/usr/bin/python3", "/opt/jarvis/desktop/jarvis_panel.py"])

    def launch_browser(self):
        self.launcher.withdraw()
        subprocess.Popen(["firefox"])

    def launch_code(self):
        self.launcher.withdraw()
        subprocess.Popen(["code"])

    def toggle_ai(self):
        self.launcher.withdraw()
        # Trigger JARVIS AI command surface if implemented separately
        pass

    def toggle_launcher(self):
        if self.launcher.winfo_ismapped():
            self.launcher.withdraw()
        else:
            self.launcher.deiconify()
            self.launcher.focus_force()

if __name__ == "__main__":
    app = JarvisShell()
    app.mainloop()
