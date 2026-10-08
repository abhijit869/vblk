#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk
import subprocess
import json
import dbus

# --- THEME COLORS ---
BG_BASE = "#0B1120"      # Deepest background
BG_SURFACE = "#0F172A"   # Panel surface
BG_ELEVATED = "#1E293B"  # Elevated elements
ACCENT = "#00E5FF"       # Cyan accent
ACCENT_BLUE = "#3B82F6"  # Blue accent for active states
TEXT_MAIN = "#FFFFFF"
TEXT_MUTED = "#94A3B8"

class JarvisTopBar(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.overrideredirect(True)
        w = self.winfo_screenwidth()
        self.geometry(f"{w}x32+0+0")
        self.configure(bg=BG_BASE)
        self.attributes("-topmost", True)

        # Left side
        left_frame = tk.Frame(self, bg=BG_BASE)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        tk.Label(left_frame, text="⬡ JARVIS OS", fg=TEXT_MAIN, bg=BG_BASE, font=("Helvetica", 10, "bold")).pack(side=tk.LEFT, padx=10)
        
        # Desktops
        for i in range(1, 5):
            bg = ACCENT_BLUE if i == 1 else BG_BASE
            tk.Label(left_frame, text=str(i), fg=TEXT_MAIN, bg=bg, width=3).pack(side=tk.LEFT, padx=2)

        # Center
        center_frame = tk.Frame(self, bg=BG_BASE)
        center_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        tk.Label(center_frame, text="Mon, Aug 11, 2025   10:24 AM", fg=TEXT_MAIN, bg=BG_BASE, font=("Helvetica", 9)).pack(expand=True)

        # Right side
        right_frame = tk.Frame(self, bg=BG_BASE)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10)
        icons = ["🔍", "🔔", "ᛒ", "📶", "🔊", "🔋 100%"]
        for ic in icons:
            tk.Label(right_frame, text=ic, fg=TEXT_MAIN, bg=BG_BASE, font=("Helvetica", 10)).pack(side=tk.LEFT, padx=5)

class JarvisLeftDock(tk.Toplevel):
    def __init__(self, master, toggle_menu_cb):
        super().__init__(master)
        self.overrideredirect(True)
        h = self.winfo_screenheight() - 80
        self.geometry(f"64x{h}+10+40")
        self.configure(bg=BG_SURFACE)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.95)

        apps = [
            ("🏠", "Home"),
            ("📁", "Files"),
            ("🦊", "Browser"),
            (">_", "Terminal"),
            ("🤖", "JARVIS AI"),
            ("📝", "Code"),
            ("▶", "Media"),
            ("📄", "Office"),
            ("⚙", "Settings")
        ]
        
        for ic, name in apps:
            btn = tk.Button(self, text=ic, bg=BG_SURFACE, fg=ACCENT, bd=0, font=("Helvetica", 16), activebackground=BG_ELEVATED)
            btn.pack(pady=10, fill=tk.X)

        self.start_btn = tk.Button(self, text="⠿", bg=BG_SURFACE, fg=TEXT_MAIN, bd=0, font=("Helvetica", 18), command=toggle_menu_cb)
        self.start_btn.pack(side=tk.BOTTOM, pady=20, fill=tk.X)

class JarvisBottomDock(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.overrideredirect(True)
        w = 460
        x = (self.winfo_screenwidth() - w) // 2
        y = self.winfo_screenheight() - 60
        self.geometry(f"{w}x48+{x}+{y}")
        self.configure(bg=BG_SURFACE)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.95)
        
        icons = ["🦊", "📁", ">_", "📝", "🎵", "📄", "⚙", "🗑"]
        for ic in icons:
            btn = tk.Button(self, text=ic, bg=BG_SURFACE, fg=TEXT_MAIN, bd=0, font=("Helvetica", 18), activebackground=BG_ELEVATED)
            btn.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=2, pady=2)

class JarvisAppLauncher(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.overrideredirect(True)
        w, h = 650, 480
        x = 84
        y = self.winfo_screenheight() - h - 60
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.configure(bg=BG_BASE)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.95)

        left = tk.Frame(self, bg=BG_SURFACE, width=180)
        left.pack(side=tk.LEFT, fill=tk.Y)
        left.pack_propagate(False)
        
        cats = [
            ("⭐", "Favorites", ACCENT_BLUE),
            ("⛶", "All Applications", BG_SURFACE),
            ("👨‍💻", "Development", BG_SURFACE),
            ("🌐", "Internet", BG_SURFACE),
            ("▶", "Multimedia", BG_SURFACE),
            ("📄", "Office", BG_SURFACE),
            ("🖥", "System", BG_SURFACE),
            ("⚙", "Settings", BG_SURFACE),
            ("🔧", "Utilities", BG_SURFACE),
            ("🤖", "JARVIS AI", BG_SURFACE)
        ]
        
        for ic, text, bg in cats:
            btn = tk.Button(left, text=f" {ic}  {text}", bg=bg, fg=TEXT_MAIN, bd=0, anchor="w", font=("Helvetica", 10))
            btn.pack(fill=tk.X, pady=2)

        right = tk.Frame(self, bg=BG_BASE)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        search_frame = tk.Frame(right, bg=BG_ELEVATED)
        search_frame.pack(fill=tk.X, padx=20, pady=20)
        tk.Label(search_frame, text="🔍 Search apps, files, settings...", bg=BG_ELEVATED, fg=TEXT_MUTED, anchor="w").pack(fill=tk.X, padx=10, pady=8)

        grid = tk.Frame(right, bg=BG_BASE)
        grid.pack(fill=tk.BOTH, expand=True, padx=20)
        
        apps = [
            ("Firefox\nWeb Browser", "🦊"), ("Files\nFile Manager", "📁"), ("Terminal\nCommand Line", ">_"),
            ("Code\nCode Editor", "📝"), ("JARVIS AI\nLocal Assistant", "🤖"), ("LibreOffice\nOffice Suite", "📄"),
            ("Settings\nSystem Settings", "⚙"), ("Software\nInstall Software", "👜"), ("Text Editor\nEdit Files", "📝")
        ]
        
        for i, (name, ic) in enumerate(apps):
            f = tk.Frame(grid, bg=BG_BASE)
            f.grid(row=i//3, column=i%3, padx=15, pady=15, sticky="nsew")
            grid.grid_columnconfigure(i%3, weight=1)
            
            tk.Label(f, text=ic, bg=BG_BASE, fg=ACCENT, font=("Helvetica", 24)).pack()
            tk.Label(f, text=name, bg=BG_BASE, fg=TEXT_MAIN, font=("Helvetica", 9), justify=tk.CENTER).pack()

        self.bind("<FocusOut>", lambda e: self.withdraw())
        self.withdraw()

class JarvisWidgets(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.overrideredirect(True)
        w = 260
        h = self.winfo_screenheight() - 80
        x = self.winfo_screenwidth() - w - 20
        y = 40
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.configure(bg=BG_BASE)
        # Transparent background trick for toplevel if possible, otherwise use BG_BASE
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.95)

        # Sys Monitor
        sys_f = tk.Frame(self, bg=BG_SURFACE)
        sys_f.pack(fill=tk.X, pady=(0, 15))
        tk.Label(sys_f, text="↓ System Monitor", bg=BG_SURFACE, fg=TEXT_MUTED, anchor="w").pack(fill=tk.X, padx=10, pady=5)
        
        sys_rings = tk.Frame(sys_f, bg=BG_SURFACE)
        sys_rings.pack(fill=tk.X, pady=10)
        for stat, val in [("CPU", "12%"), ("RAM", "19%"), ("Disk", "18%")]:
            sf = tk.Frame(sys_rings, bg=BG_SURFACE)
            sf.pack(side=tk.LEFT, expand=True)
            tk.Label(sf, text=val, bg=BG_SURFACE, fg=ACCENT, font=("Helvetica", 12, "bold")).pack()
            tk.Label(sf, text=stat, bg=BG_SURFACE, fg=TEXT_MUTED, font=("Helvetica", 8)).pack()
            
        # JARVIS AI
        ai_f = tk.Frame(self, bg=BG_SURFACE)
        ai_f.pack(fill=tk.X, pady=15)
        tk.Label(ai_f, text="🤖 JARVIS AI (Qwen3)\nReady - Local Inference", bg=BG_SURFACE, fg=ACCENT, anchor="w", justify=tk.LEFT).pack(fill=tk.X, padx=10, pady=10)
        
        for action in ["💬 Chat with JARVIS", "✨ Create Code", "📄 Analyze Files", "🖼 Generate Images", "🌐 Browse the Web"]:
            tk.Label(ai_f, text=f"{action}  >", bg=BG_ELEVATED, fg=TEXT_MAIN, anchor="w").pack(fill=tk.X, padx=10, pady=2, ipady=4)

        # Network
        net_f = tk.Frame(self, bg=BG_SURFACE)
        net_f.pack(fill=tk.X, pady=15)
        tk.Label(net_f, text="⊕ Network", bg=BG_SURFACE, fg=TEXT_MUTED, anchor="w").pack(fill=tk.X, padx=10, pady=5)
        nf = tk.Frame(net_f, bg=BG_SURFACE)
        nf.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(nf, text="Download\n125 KB/s", bg=BG_SURFACE, fg=TEXT_MAIN, justify=tk.LEFT).pack(side=tk.LEFT, expand=True)
        tk.Label(nf, text="Upload\n48 KB/s", bg=BG_SURFACE, fg=TEXT_MAIN, justify=tk.LEFT).pack(side=tk.RIGHT, expand=True)

        # Storage
        stor_f = tk.Frame(self, bg=BG_SURFACE)
        stor_f.pack(fill=tk.X, pady=15)
        tk.Label(stor_f, text="⛁ Storage", bg=BG_SURFACE, fg=TEXT_MUTED, anchor="w").pack(fill=tk.X, padx=10, pady=5)
        tk.Label(stor_f, text="Root (/)              23 GB / 100 GB", bg=BG_SURFACE, fg=TEXT_MAIN, font=("Helvetica", 9)).pack(anchor="w", padx=10)
        tk.Label(stor_f, text="Data (/home)        120 GB / 500 GB", bg=BG_SURFACE, fg=TEXT_MAIN, font=("Helvetica", 9)).pack(anchor="w", padx=10, pady=(5,0))

class JarvisDesktopApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.withdraw()
        
        self.top_bar = JarvisTopBar(self)
        self.launcher = JarvisAppLauncher(self)
        self.left_dock = JarvisLeftDock(self, self.toggle_menu)
        self.bottom_dock = JarvisBottomDock(self)
        self.widgets = JarvisWidgets(self)

    def toggle_menu(self):
        if self.launcher.winfo_ismapped():
            self.launcher.withdraw()
        else:
            self.launcher.deiconify()
            self.launcher.focus_force()

if __name__ == "__main__":
    app = JarvisDesktopApp()
    app.mainloop()
