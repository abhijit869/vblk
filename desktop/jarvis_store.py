#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, messagebox
import json

try:
    import dbus
    DBUS_AVAILABLE = True
except ImportError:
    DBUS_AVAILABLE = False

BG_BASE = "#0B1120"
BG_SURFACE = "#0F172A"
BG_ELEVATED = "#1E293B"
ACCENT = "#00E5FF"
ACCENT_BLUE = "#3B82F6"
TEXT_MAIN = "#FFFFFF"
TEXT_MUTED = "#94A3B8"

class JarvisStore(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("JARVIS Store")
        self.geometry("900x600")
        self.configure(bg=BG_BASE)
        
        self.dbus_iface = None
        if DBUS_AVAILABLE:
            try:
                bus = dbus.SystemBus()
                proxy = bus.get_object("com.jarvis.Core", "/com/jarvis/Store")
                self.dbus_iface = dbus.Interface(proxy, "com.jarvis.StoreInterface")
            except Exception as e:
                print(f"Warning: Could not connect to Store D-Bus: {e}")
        
        self.create_widgets()

    def create_widgets(self):
        # Top bar
        top = tk.Frame(self, bg=BG_SURFACE, height=60)
        top.pack(side=tk.TOP, fill=tk.X)
        
        self.online = self.check_network()
        status_text = "⬡ JARVIS Store" if self.online else "⬡ JARVIS Store (Offline)"
        status_color = TEXT_MAIN if self.online else "orange"
        
        self.title_label = tk.Label(top, text=status_text, fg=status_color, bg=BG_SURFACE, font=("Helvetica", 16, "bold"))
        self.title_label.pack(side=tk.LEFT, padx=20, pady=15)
        
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(top, textvariable=self.search_var, bg=BG_ELEVATED, fg=TEXT_MAIN, insertbackground=TEXT_MAIN, font=("Helvetica", 12), relief=tk.FLAT, width=40)
        search_entry.pack(side=tk.LEFT, padx=20, pady=15, ipady=5)
        
        search_btn = tk.Button(top, text="Search", bg=ACCENT_BLUE, fg=TEXT_MAIN, relief=tk.FLAT, command=self.do_search, font=("Helvetica", 10, "bold"))
        search_btn.pack(side=tk.LEFT, padx=5, pady=15, ipadx=10, ipady=3)
        
        # Left sidebar
        sidebar = tk.Frame(self, bg=BG_SURFACE, width=200)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        
        categories = ["Featured", "All Applications", "Internet", "Office", "Development", "AI", "Graphics", "Multimedia", "Games", "System", "Updates"]
        for cat in categories:
            btn = tk.Button(sidebar, text=cat, bg=BG_SURFACE, fg=TEXT_MAIN, relief=tk.FLAT, anchor="w", font=("Helvetica", 11), activebackground=BG_ELEVATED, activeforeground=ACCENT)
            if cat == "Updates":
                btn.config(command=self.show_updates)
            elif cat == "Featured":
                btn.config(command=self.show_featured)
            else:
                btn.config(command=lambda c=cat: self.show_category(c))
            btn.pack(fill=tk.X, padx=10, pady=2, ipadx=10, ipady=5)
        
        # Main content
        self.content = tk.Frame(self, bg=BG_BASE)
        self.content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        self.results_frame = tk.Frame(self.content, bg=BG_BASE)
        self.results_frame.pack(fill=tk.BOTH, expand=True)
        
        self.show_featured()

    def check_network(self):
        import subprocess
        try:
            res = subprocess.run(["ping", "-c", "1", "8.8.8.8"], capture_output=True, timeout=2)
            return res.returncode == 0
        except Exception:
            return False

    def show_updates(self):
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        tk.Label(self.results_frame, text="JARVIS Updates", fg=TEXT_MAIN, bg=BG_BASE, font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        update_cats = ["Security Updates", "System Updates", "Application Updates", "Firmware Updates", "JARVIS Updates"]
        for u in update_cats:
            tk.Label(self.results_frame, text=f"• {u}: System up to date.", fg=TEXT_MUTED, bg=BG_BASE, font=("Helvetica", 11)).pack(anchor="w", pady=5)
            
    def show_category(self, cat):
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        tk.Label(self.results_frame, text=cat, fg=TEXT_MAIN, bg=BG_BASE, font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        self.create_app_card(f"Example {cat} App", "Description", cat, "Debian")

    def show_featured(self):
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        
        tk.Label(self.results_frame, text="Featured Applications", fg=TEXT_MAIN, bg=BG_BASE, font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        apps = [
            ("Firefox ESR", "Web Browser", "Internet"),
            ("LibreOffice", "Office Suite", "Office"),
            ("VLC", "Media Player", "Multimedia"),
            ("Qwen3", "Local AI Model", "AI")
        ]
        
        for name, desc, cat in apps:
            self.create_app_card(name, desc, cat, "Debian")

    def create_app_card(self, name, desc, cat, source, app_id=None):
        card = tk.Frame(self.results_frame, bg=BG_ELEVATED, padx=15, pady=15)
        card.pack(fill=tk.X, pady=5)
        
        info = tk.Frame(card, bg=BG_ELEVATED)
        info.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Label(info, text=name, fg=TEXT_MAIN, bg=BG_ELEVATED, font=("Helvetica", 12, "bold")).pack(anchor="w")
        tk.Label(info, text=desc, fg=TEXT_MUTED, bg=BG_ELEVATED, font=("Helvetica", 10)).pack(anchor="w")
        source_lbl = f"{cat} • Source: {source}"
        if source == "Flatpak":
            source_lbl += " (Sandboxed)"
        tk.Label(info, text=source_lbl, fg=ACCENT, bg=BG_ELEVATED, font=("Helvetica", 9)).pack(anchor="w", pady=(5,0))
        
        btn = tk.Button(card, text="Install", bg=ACCENT_BLUE, fg=TEXT_MAIN, relief=tk.FLAT, font=("Helvetica", 10, "bold"), command=lambda n=(app_id if app_id else name), s=source: self.install_app(n, s))
        btn.pack(side=tk.RIGHT, ipadx=15, ipady=5)

    def do_search(self):
        query = self.search_var.get()
        if not query:
            return
            
        for widget in self.results_frame.winfo_children():
            widget.destroy()
            
        tk.Label(self.results_frame, text=f"Search Results for '{query}'", fg=TEXT_MAIN, bg=BG_BASE, font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        if self.dbus_iface:
            try:
                res_str = self.dbus_iface.Search(query)
                res = json.loads(res_str)
                if isinstance(res, dict) and "data" in res:
                    for pkg in res["data"]:
                        self.create_app_card(pkg["name"], pkg.get("description", ""), "Application", pkg.get("source", "Debian"))
                else:
                    for pkg in res:
                        if isinstance(pkg, dict):
                            self.create_app_card(pkg.get("name", ""), pkg.get("description", ""), "Application", pkg.get("source", "Debian"))
            except Exception as e:
                tk.Label(self.results_frame, text=f"APT Search failed: {e}", fg="red", bg=BG_BASE).pack(anchor="w")

            if self.online:
                try:
                    fp_str = self.dbus_iface.SearchFlatpak(query)
                    fp_res = json.loads(fp_str)
                    if isinstance(fp_res, dict) and "data" in fp_res:
                        for pkg in fp_res["data"]:
                            self.create_app_card(pkg["name"], pkg.get("description", ""), "Application", "Flatpak", pkg.get("application_id"))
                    else:
                        for pkg in fp_res:
                            if isinstance(pkg, dict):
                                self.create_app_card(pkg.get("name", ""), pkg.get("description", ""), "Application", "Flatpak", pkg.get("application_id"))
                except Exception as e:
                    tk.Label(self.results_frame, text=f"Flatpak Search failed: {e}", fg="red", bg=BG_BASE).pack(anchor="w")
        else:
            # Mock results
            self.create_app_card(query, f"Package matching {query}", "System", "Debian")

    def install_app(self, name, source="Debian"):
        if messagebox.askyesno("Install", f"Do you want to install {name} via {source}?"):
            if self.dbus_iface:
                try:
                    if source == "Flatpak":
                        res_str = self.dbus_iface.InstallFlatpak(name)
                    else:
                        res_str = self.dbus_iface.Install(name)
                    res = json.loads(res_str)
                    if isinstance(res, dict) and "data" in res:
                        inner = res["data"]
                        if inner.get("status") == "ok":
                            messagebox.showinfo("Success", inner.get("message"))
                        else:
                            messagebox.showerror("Error", inner.get("message"))
                    else:
                        messagebox.showerror("Error", str(res))
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to install: {e}")
            else:
                messagebox.showinfo("Success", f"Simulated install of {name} (No D-Bus)")

if __name__ == "__main__":
    app = JarvisStore()
    app.mainloop()
