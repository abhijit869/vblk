#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk
import sys

BG_BASE = "#0B1120"
BG_SURFACE = "#0F172A"
BG_ELEVATED = "#1E293B"
ACCENT = "#00E5FF"
TEXT_MAIN = "#FFFFFF"
TEXT_MUTED = "#94A3B8"

class JarvisAISurface(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("JARVIS AI Command Surface")
        self.geometry("700x500")
        self.configure(bg=BG_BASE)
        self.attributes("-alpha", 0.95)

        # Header
        header = tk.Frame(self, bg=BG_SURFACE, height=60)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        tk.Label(header, text="🤖 JARVIS AI", bg=BG_SURFACE, fg=ACCENT, font=("Helvetica", 16, "bold")).pack(side=tk.LEFT, padx=20)
        
        status_frame = tk.Frame(header, bg=BG_SURFACE)
        status_frame.pack(side=tk.RIGHT, padx=20)
        tk.Label(status_frame, text="State: Local (Ready)", bg=BG_SURFACE, fg=TEXT_MUTED).pack(anchor="e")
        tk.Label(status_frame, text="Model: Qwen3 (1.7B)", bg=BG_SURFACE, fg=TEXT_MUTED).pack(anchor="e")

        # Conversation Area
        self.conv_frame = tk.Frame(self, bg=BG_BASE)
        self.conv_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        self.text_area = tk.Text(self.conv_frame, bg=BG_BASE, fg=TEXT_MAIN, bd=0, font=("Helvetica", 11), wrap=tk.WORD, state=tk.DISABLED)
        self.text_area.pack(fill=tk.BOTH, expand=True)

        # Input Area
        input_frame = tk.Frame(self, bg=BG_ELEVATED, height=60)
        input_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        input_frame.pack_propagate(False)

        tk.Label(input_frame, text=">", bg=BG_ELEVATED, fg=ACCENT, font=("Helvetica", 14, "bold")).pack(side=tk.LEFT, padx=15)
        
        self.input_var = tk.StringVar()
        entry = tk.Entry(input_frame, textvariable=self.input_var, bg=BG_ELEVATED, fg=TEXT_MAIN, bd=0, insertbackground=TEXT_MAIN, font=("Helvetica", 12))
        entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=10)
        entry.bind("<Return>", self.on_submit)
        
        self.append_message("System", "JARVIS OS AI Assistant is ready. How can I help you?", ACCENT)

    def append_message(self, sender, text, color):
        self.text_area.config(state=tk.NORMAL)
        self.text_area.insert(tk.END, f"{sender}:\n", ("sender",))
        self.text_area.insert(tk.END, f"{text}\n\n", ("text",))
        self.text_area.tag_config("sender", foreground=color, font=("Helvetica", 10, "bold"))
        self.text_area.tag_config("text", foreground=TEXT_MAIN)
        self.text_area.see(tk.END)
        self.text_area.config(state=tk.DISABLED)

    def on_submit(self, event):
        user_text = self.input_var.get().strip()
        if not user_text: return
        self.input_var.set("")
        self.append_message("You", user_text, TEXT_MUTED)
        
        # Simulate thinking and response
        self.after(500, lambda: self.append_message("JARVIS", f"Received your command: {user_text}\n(Tool execution would appear here.)", ACCENT))

if __name__ == "__main__":
    app = JarvisAISurface()
    app.mainloop()
