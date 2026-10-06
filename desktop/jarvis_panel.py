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
        
        self.create_widgets()
        self.connect_dbus()
        
    def connect_dbus(self):
        if dbus is None:
            self.status_label.config(text="Core Status: D-Bus library missing", foreground="red")
            return
            
        try:
            self.bus = dbus.SessionBus()
            proxy = self.bus.get_object("com.jarvis.Core", "/com/jarvis/Core")
            self.jarvis_iface = dbus.Interface(proxy, "com.jarvis.CoreInterface")
            status = self.jarvis_iface.Status()
            self.status_label.config(text=f"Core Status: {status}", foreground="green")
        except dbus.DBusException:
            self.status_label.config(text="Core Status: OFFLINE (Daemon not running)", foreground="red")
        except Exception as e:
            self.status_label.config(text=f"Core Status: Error", foreground="red")

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        ttk.Label(main_frame, text="Jarvis AI Controller", font=("Helvetica", 16, "bold")).pack(pady=(0, 15))
        
        # Status
        self.status_label = ttk.Label(main_frame, text="Core Status: Connecting...", font=("Helvetica", 10))
        self.status_label.pack(pady=(0, 15))
        
        # Mode
        mode_frame = ttk.LabelFrame(main_frame, text="Operation Mode", padding="10")
        mode_frame.pack(fill=tk.X, pady=5)
        self.mode_var = tk.StringVar(value="Manual")
        ttk.Radiobutton(mode_frame, text="Manual Mode (Require Approval)", variable=self.mode_var, value="Manual").pack(anchor=tk.W)
        ttk.Radiobutton(mode_frame, text="Auto Mode (Autonomous)", variable=self.mode_var, value="Auto").pack(anchor=tk.W)
        
        # Language
        lang_frame = ttk.LabelFrame(main_frame, text="Voice Language", padding="10")
        lang_frame.pack(fill=tk.X, pady=5)
        self.lang_var = tk.StringVar(value="English")
        ttk.Combobox(lang_frame, textvariable=self.lang_var, values=["English", "Bengali (বাংলা)", "Hindi (हिन्दी)"], state="readonly").pack(fill=tk.X)
        
        # Model
        model_frame = ttk.LabelFrame(main_frame, text="AI Model Provider", padding="10")
        model_frame.pack(fill=tk.X, pady=5)
        self.model_var = tk.StringVar(value="openai-compatible")
        ttk.Combobox(model_frame, textvariable=self.model_var, values=["openai-compatible", "gemini", "antigravity", "mock"], state="readonly").pack(fill=tk.X)
        
        # Apply button
        ttk.Button(main_frame, text="Apply Configuration", command=self.apply_settings).pack(pady=15)
        
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
