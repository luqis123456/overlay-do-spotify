"""Quick graphical setup dialog for configuring Spotify Web API credentials."""

import tkinter as tk
from tkinter import messagebox
import webbrowser
from typing import Callable, Optional

from spotify_overlay.config import load_config, save_config


class SetupDialog(tk.Toplevel):
    """Configuration dialog for entering Spotify Client ID and Client Secret."""

    def __init__(self, parent, on_save_callback: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self.on_save_callback = on_save_callback
        self.title("Spotify Overlay Setup")
        self.geometry("440x360")
        self.resizable(False, False)
        self.configure(bg="#181818")

        # Keep on top of parent
        self.transient(parent)
        self.grab_set()

        self.config = load_config()
        self._build_ui()

    def _build_ui(self) -> None:
        title_lbl = tk.Label(
            self,
            text="Spotify Overlay Configuration",
            font=("Segoe UI", 12, "bold"),
            fg="#FFFFFF",
            bg="#181818",
        )
        title_lbl.pack(pady=(16, 6))

        desc_lbl = tk.Label(
            self,
            text="Connect your Spotify Developer App for in-game control.\nNeed a Client ID? Click the button below.",
            font=("Segoe UI", 9),
            fg="#A7A7A7",
            bg="#181818",
            justify="center",
        )
        desc_lbl.pack(pady=(0, 12))

        dev_btn = tk.Button(
            self,
            text="🌐 Open Spotify Developer Dashboard",
            command=self._open_dashboard,
            bg="#282828",
            fg="#1DB954",
            activebackground="#333333",
            activeforeground="#1ED760",
            relief="flat",
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=4,
            cursor="hand2",
        )
        dev_btn.pack(pady=(0, 14))

        # Form container
        form_frame = tk.Frame(self, bg="#181818")
        form_frame.pack(fill="x", padx=30)

        # Client ID
        id_lbl = tk.Label(
            form_frame,
            text="Client ID:",
            font=("Segoe UI", 9, "bold"),
            fg="#FFFFFF",
            bg="#181818",
            anchor="w",
        )
        id_lbl.pack(fill="x")

        self.id_entry = tk.Entry(
            form_frame,
            font=("Consolas", 10),
            bg="#282828",
            fg="#FFFFFF",
            insertbackground="#1DB954",
            relief="flat",
        )
        self.id_entry.pack(fill="x", pady=(2, 10), ipady=3)
        self.id_entry.insert(0, self.config.get("spotify", {}).get("client_id", ""))

        # Client Secret
        secret_lbl = tk.Label(
            form_frame,
            text="Client Secret:",
            font=("Segoe UI", 9, "bold"),
            fg="#FFFFFF",
            bg="#181818",
            anchor="w",
        )
        secret_lbl.pack(fill="x")

        self.secret_entry = tk.Entry(
            form_frame,
            font=("Consolas", 10),
            show="•",
            bg="#282828",
            fg="#FFFFFF",
            insertbackground="#1DB954",
            relief="flat",
        )
        self.secret_entry.pack(fill="x", pady=(2, 6), ipady=3)
        self.secret_entry.insert(0, self.config.get("spotify", {}).get("client_secret", ""))

        # Note about redirect uri
        uri_note = tk.Label(
            form_frame,
            text="App Redirect URI in Dashboard: http://127.0.0.1:8888/callback",
            font=("Segoe UI", 8),
            fg="#888888",
            bg="#181818",
            anchor="w",
        )
        uri_note.pack(fill="x", pady=(0, 14))

        # Action Buttons
        btn_frame = tk.Frame(self, bg="#181818")
        btn_frame.pack(fill="x", padx=30, pady=(4, 16))

        save_btn = tk.Button(
            btn_frame,
            text="Save & Connect",
            command=self._save_credentials,
            bg="#1DB954",
            fg="#FFFFFF",
            activebackground="#1ED760",
            activeforeground="#FFFFFF",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
        )
        save_btn.pack(side="right", padx=(6, 0))

        cancel_btn = tk.Button(
            btn_frame,
            text="Close",
            command=self.destroy,
            bg="#282828",
            fg="#CCCCCC",
            activebackground="#333333",
            activeforeground="#FFFFFF",
            font=("Segoe UI", 9),
            relief="flat",
            padx=12,
            pady=6,
            cursor="hand2",
        )
        cancel_btn.pack(side="right")

    def _open_dashboard(self) -> None:
        webbrowser.open("https://developer.spotify.com/dashboard")

    def _save_credentials(self) -> None:
        cid = self.id_entry.get().strip()
        csecret = self.secret_entry.get().strip()

        if not cid or not csecret:
            messagebox.showwarning(
                "Missing Credentials",
                "Please enter both your Spotify Client ID and Client Secret.",
                parent=self,
            )
            return

        self.config["spotify"]["client_id"] = cid
        self.config["spotify"]["client_secret"] = csecret
        save_config(self.config)

        messagebox.showinfo(
            "Saved",
            "Spotify credentials saved successfully!\nThe overlay will now connect to Spotify.",
            parent=self,
        )
        if self.on_save_callback:
            self.on_save_callback()
        self.destroy()

