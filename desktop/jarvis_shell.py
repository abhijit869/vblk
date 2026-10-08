#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import time
import subprocess
import threading

try:
    import dbus
    DBUS_AVAILABLE = True
except ImportError:
    DBUS_AVAILABLE = False

class JarvisTopBar(tk.Toplevel):
    def __init__(self, master, iface):
        super().__init__(master)
        self.iface = iface
        self.overrideredirect(True)
        # Position at top
        screen_width = self.winfo_screenwidth()
        self.geometry(f"{screen_width}x30+0+0")
        self.configure(bg="#111827") # Dark navy/black
        
        # Keep on top and behave like a dock/panel
        self.attributes("-topmost", True)
        try:
            self.attributes("-type", "dock")
        except:
            pass

        # Left: Workspaces / Menu
        self.menu_btn = tk.Button(self, text=" 🔴 JARVIS ", bg="#1F2937", fg="#38BDF8", bd=0, font=("Helvetica", 11, "bold"), command=self.show_quick_settings)
        self.menu_btn.pack(side=tk.LEFT, padx=5, fill=tk.Y)
        
        # Center: Clock
        self.clock_lbl = tk.Label(self, text="", bg="#111827", fg="white", font=("Helvetica", 11))
        self.clock_lbl.pack(side=tk.LEFT, expand=True)

        # Right: System HUD (Network, Battery, Status)
        self.status_lbl = tk.Label(self, text="Core: Offline", bg="#111827", fg="#EF4444", font=("Helvetica", 10))
        self.status_lbl.pack(side=tk.RIGHT, padx=5)

        self.net_lbl = tk.Label(self, text="Net: UP", bg="#111827", fg="#A7F3D0", font=("Helvetica", 10))
        self.net_lbl.pack(side=tk.RIGHT, padx=5)
        
        self.bat_lbl = tk.Label(self, text="Bat: 100%", bg="#111827", fg="#A7F3D0", font=("Helvetica", 10))
        self.bat_lbl.pack(side=tk.RIGHT, padx=5)

        self.update_clock()
        self.update_status()

    def update_clock(self):
        t = time.strftime("%a %b %d  %H:%M:%S")
        self.clock_lbl.config(text=t)
        self.after(1000, self.update_clock)

    def update_status(self):
        if self.iface:
            try:
                st = self.iface.Status()
                self.status_lbl.config(text=f"Core: {st}", fg="#34D399")
            except Exception:
                self.status_lbl.config(text="Core: Error", fg="#EF4444")
        self.after(5000, self.update_status)

    def show_quick_settings(self):
        # Could launch jarvis_panel.py
        subprocess.Popen(["/usr/bin/python3", "/opt/jarvis/desktop/jarvis_panel.py"])


class JarvisDock(tk.Toplevel):
    def __init__(self, master, ai_surface):
        super().__init__(master)
        self.ai_surface = ai_surface
        self.overrideredirect(True)
        # Position at bottom center
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        width = 400
        height = 48
        x = (screen_width - width) // 2
        y = screen_height - height - 10
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.configure(bg="#1F2937")
        self.attributes("-topmost", True)
        try:
            self.attributes("-type", "dock")
        except:
            pass

        self.apps = [
            ("File Explorer", self.launch_explorer, "#3B82F6"),
            ("Terminal", self.launch_terminal, "#10B981"),
            ("AI Assistant", self.toggle_ai, "#8B5CF6")
        ]

        for text, cmd, color in self.apps:
            btn = tk.Button(self, text=text, bg=color, fg="white", bd=0, font=("Helvetica", 10, "bold"), command=cmd)
            btn.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=2, pady=2)

    def launch_explorer(self):
        subprocess.Popen(["/usr/bin/python3", "/opt/jarvis/desktop/file_explorer.py"])

    def launch_terminal(self):
        subprocess.Popen(["x-terminal-emulator"])

    def toggle_ai(self):
        if self.ai_surface.winfo_ismapped():
            self.ai_surface.withdraw()
        else:
            self.ai_surface.deiconify()
            self.ai_surface.focus_force()

class AICommandSurface(tk.Toplevel):
    def __init__(self, master, iface):
        super().__init__(master)
        self.iface = iface
        self.title("JARVIS AI Command Surface")
        self.overrideredirect(True)
        width, height = 500, 200
        x = (self.winfo_screenwidth() - width) // 2
        y = (self.winfo_screenheight() - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.configure(bg="#0F172A")
        self.attributes("-topmost", True)

        self.lbl = tk.Label(self, text="How can I help you?", bg="#0F172A", fg="#38BDF8", font=("Helvetica", 14, "bold"))
        self.lbl.pack(pady=(20, 10))

        self.entry = tk.Entry(self, font=("Helvetica", 12), bg="#1E293B", fg="white", insertbackground="white", bd=0)
        self.entry.pack(fill=tk.X, padx=20, pady=10)
        self.entry.bind("<Return>", self.handle_query)
        self.entry.focus()

        self.resp_lbl = tk.Label(self, text="", bg="#0F172A", fg="#A7F3D0", font=("Helvetica", 10), wraplength=460, justify=tk.LEFT)
        self.resp_lbl.pack(padx=20, fill=tk.BOTH, expand=True)

        self.bind("<Escape>", lambda e: self.withdraw())
        self.withdraw()

    def handle_query(self, event):
        query = self.entry.get()
        if not query.strip(): return
        self.entry.delete(0, tk.END)
        self.resp_lbl.config(text="Thinking...", fg="#94A3B8")
        
        def run():
            if not self.iface:
                self.resp_lbl.config(text="Error: D-Bus not connected", fg="#EF4444")
                return
            try:
                ans = self.iface.Ask("gui_session", query)
                self.resp_lbl.config(text=ans, fg="#A7F3D0")
            except Exception as e:
                self.resp_lbl.config(text=f"Error: {e}", fg="#EF4444")
        
        threading.Thread(target=run, daemon=True).start()

class JarvisShell(tk.Tk):
    def __init__(self):
        super().__init__()
        self.withdraw() # Hide root window
        
        self.bus = None
        self.jarvis_iface = None
        
        if DBUS_AVAILABLE:
            try:
                self.bus = dbus.SystemBus()
                proxy = self.bus.get_object("com.jarvis.Core", "/com/jarvis/Core")
                self.jarvis_iface = dbus.Interface(proxy, "com.jarvis.CoreInterface")
            except Exception:
                pass

        self.ai_surface = AICommandSurface(self, self.jarvis_iface)
        self.top_bar = JarvisTopBar(self, self.jarvis_iface)
        self.dock = JarvisDock(self, self.ai_surface)

if __name__ == "__main__":
    app = JarvisShell()
    app.mainloop()
