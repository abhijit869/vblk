#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, messagebox

try:
    import dbus
except ImportError:
    dbus = None

class JarvisControlPanel(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Jarvis OS - Control Panel")
        self.geometry("420x400")
        self.resizable(False, False)
        
        self.bus = None
        self.jarvis_iface = None
        self.jarvis_diag = None
        
        self.create_widgets()
        self.connect_dbus()
        
    def connect_dbus(self):
        if dbus is None:
            self.status_label.config(text="Core Status: D-Bus library missing", foreground="red")
            return
            
        try:
            self.bus = dbus.SystemBus()
            proxy = self.bus.get_object("com.jarvis.Core", "/com/jarvis/Core")
            self.jarvis_iface = dbus.Interface(proxy, "com.jarvis.CoreInterface")
            dproxy = self.bus.get_object("com.jarvis.Core", "/com/jarvis/Diagnostics")
            self.jarvis_diag = dbus.Interface(dproxy, "com.jarvis.DiagnosticsInterface")
            status = self.jarvis_iface.Status()
            self.status_label.config(text=f"Core Status: {status}", foreground="green")
        except dbus.DBusException:
            self.status_label.config(text="Core Status: OFFLINE (Daemon not running)", foreground="red")
        except Exception as e:
            self.status_label.config(text=f"Core Status: Error", foreground="red")

    def create_widgets(self):
        # Header
        ttk.Label(self, text="Jarvis AI Controller", font=("Helvetica", 16, "bold")).pack(pady=(15, 5))
        
        # Status
        self.status_label = ttk.Label(self, text="Core Status: Connecting...", font=("Helvetica", 10))
        self.status_label.pack(pady=(0, 10))

        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        main_frame = ttk.Frame(notebook, padding="10")
        notebook.add(main_frame, text="General")
        
        appearance_frame = ttk.Frame(notebook, padding="10")
        notebook.add(appearance_frame, text="Appearance")
        
        # --- General Tab ---
        mode_frame = ttk.LabelFrame(main_frame, text="Operation Mode", padding="10")
        mode_frame.pack(fill=tk.X, pady=5)
        self.mode_var = tk.StringVar(value="Manual")
        ttk.Radiobutton(mode_frame, text="Manual Mode (Require Approval)", variable=self.mode_var, value="Manual").pack(anchor=tk.W)
        ttk.Radiobutton(mode_frame, text="Auto Mode (Autonomous)", variable=self.mode_var, value="Auto").pack(anchor=tk.W)
        
        lang_frame = ttk.LabelFrame(main_frame, text="Voice Language", padding="10")
        lang_frame.pack(fill=tk.X, pady=5)
        self.lang_var = tk.StringVar(value="English")
        ttk.Combobox(lang_frame, textvariable=self.lang_var, values=["English", "Bengali (বাংলা)", "Hindi (हिन्दी)"], state="readonly").pack(fill=tk.X)
        
        model_frame = ttk.LabelFrame(main_frame, text="AI Model Provider", padding="10")
        model_frame.pack(fill=tk.X, pady=5)
        self.model_var = tk.StringVar(value="openai-compatible")
        ttk.Combobox(model_frame, textvariable=self.model_var, values=["openai-compatible", "gemini", "antigravity", "mock"], state="readonly").pack(fill=tk.X)
        
        ttk.Button(main_frame, text="Apply Configuration", command=self.apply_settings).pack(pady=15)
        
        # --- Appearance Tab (Wallpaper) ---
        wp_frame = ttk.LabelFrame(appearance_frame, text="Wallpaper Settings", padding="10")
        wp_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.wp_listbox = tk.Listbox(wp_frame, height=8)
        self.wp_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        self.wp_listbox.bind('<<ListboxSelect>>', self.on_wp_select)
        
        self.wp_details_var = tk.StringVar(value="Select a wallpaper to preview")
        ttk.Label(wp_frame, textvariable=self.wp_details_var, justify=tk.CENTER).pack(pady=5)
        
        btn_frame = ttk.Frame(wp_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(btn_frame, text="Apply", command=self.apply_wallpaper).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Reset Default", command=self.reset_wallpaper).pack(side=tk.LEFT, padx=2)
        
        # --- Network Tab ---
        network_frame = ttk.Frame(notebook, padding="10")
        notebook.add(network_frame, text="Network")
        
        self.net_text = tk.Text(network_frame, height=15, width=45, bg="#111827", fg="#A7F3D0", font=("Consolas", 10))
        self.net_text.pack(fill=tk.BOTH, expand=True)
        ttk.Button(network_frame, text="Refresh Network", command=self.refresh_network).pack(pady=5)
        
        # --- System Monitor Tab ---
        monitor_frame = ttk.Frame(notebook, padding="10")
        notebook.add(monitor_frame, text="System Monitor")
        
        self.mon_text = tk.Text(monitor_frame, height=15, width=45, bg="#111827", fg="#38BDF8", font=("Consolas", 10))
        self.mon_text.pack(fill=tk.BOTH, expand=True)
        ttk.Button(monitor_frame, text="Refresh Monitor", command=self.refresh_monitor).pack(pady=5)
        
        self.wp_manager = None
        self.refresh_wallpapers()
        
        # Initial data fetch
        self.after(500, self.refresh_network)
        self.after(500, self.refresh_monitor)

    

    def refresh_network(self):
        self.net_text.delete(1.0, tk.END)
        self.net_text.insert(tk.END, "Loading network status...\n")
        self.update()
        if not self.jarvis_diag:
            self.net_text.insert(tk.END, "Error: D-Bus not connected")
            return
        try:
            import json
            res = json.loads(self.jarvis_diag.GetNetwork())
            if res.get('status') == 'ok':
                self.net_text.delete(1.0, tk.END)
                self.net_text.insert(tk.END, res['data'].get('interfaces', ''))
                self.net_text.insert(tk.END, "\n\nRoutes:\n")
                self.net_text.insert(tk.END, res['data'].get('routes', ''))
            else:
                self.net_text.insert(tk.END, "Error retrieving data")
        except Exception as e:
            self.net_text.insert(tk.END, f"Error: {e}")
        
    def refresh_monitor(self):
        self.mon_text.delete(1.0, tk.END)
        self.mon_text.insert(tk.END, "Loading system monitor...\n")
        self.update()
        if not self.jarvis_diag:
            self.mon_text.insert(tk.END, "Error: D-Bus not connected")
            return
        try:
            import json
            res = json.loads(self.jarvis_diag.GetSystem())
            if res.get('status') == 'ok':
                self.mon_text.delete(1.0, tk.END)
                self.mon_text.insert(tk.END, res['data'].get('memory', ''))
                self.mon_text.insert(tk.END, "\n\nCPU:\n")
                self.mon_text.insert(tk.END, res['data'].get('cpu', ''))
            else:
                self.mon_text.insert(tk.END, "Error retrieving data")
        except Exception as e:
            self.mon_text.insert(tk.END, f"Error: {e}")

    def refresh_wallpapers(self):
        if not dbus:
            return
        try:
            bus = dbus.SystemBus()
            proxy = bus.get_object("com.jarvis.Core", "/com/jarvis/Wallpaper")
            self.wp_manager = dbus.Interface(proxy, "com.jarvis.WallpaperInterface")
            
            import json
            wallpapers = json.loads(self.wp_manager.GetAll())
            self.wp_listbox.delete(0, tk.END)
            self.wp_data = {}
            for wp in wallpapers:
                fav_marker = "★ " if wp.get("favorite") else ""
                def_marker = " (Default)" if wp.get("default") else ""
                display = f"{fav_marker}{wp['name']}{def_marker}"
                self.wp_listbox.insert(tk.END, display)
                self.wp_data[display] = wp
        except Exception as e:
            self.wp_details_var.set(f"Could not load wallpapers: {e}")

    def on_wp_select(self, event):
        selection = self.wp_listbox.curselection()
        if not selection:
            return
        name = self.wp_listbox.get(selection[0])
        wp = self.wp_data.get(name)
        if wp:
            self.wp_details_var.set(f"ID: {wp['id']}\nCategory: {wp['category']}")
            
    def apply_wallpaper(self):
        selection = self.wp_listbox.curselection()
        if not selection or not self.wp_manager:
            return
        name = self.wp_listbox.get(selection[0])
        wp = self.wp_data.get(name)
        if wp:
            try:
                success = self.wp_manager.SetCurrent(wp["id"])
                if success:
                    messagebox.showinfo("Success", f"Wallpaper set to {wp['name']}")
                else:
                    messagebox.showerror("Error", "Failed to set wallpaper.")
            except Exception as e:
                messagebox.showerror("Error", f"D-Bus Error: {e}")

    def reset_wallpaper(self):
        if self.wp_manager:
            try:
                self.wp_manager.ResetDefault()
                messagebox.showinfo("Success", "Restored JARVIS Default Wallpaper")
                self.refresh_wallpapers()
            except Exception as e:
                messagebox.showerror("Error", f"D-Bus Error: {e}")
                
    def apply_settings(self):
        if not self.jarvis_iface:
            messagebox.showerror("Connection Error", "Not connected to Jarvis Core D-Bus service.")
            return
            
        try:
            mode = self.mode_var.get()
            lang = self.lang_var.get()
            model = self.model_var.get()
            response = self.jarvis_iface.UpdateSettings(model, lang, mode)
            messagebox.showinfo("Success", str(response))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update settings: {e}")

if __name__ == "__main__":
    app = JarvisControlPanel()
    app.mainloop()
