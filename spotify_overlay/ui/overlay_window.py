"""Main desktop Spotify overlay window with topmost persistence and drag/lock support."""

import threading
import time
import tkinter as tk
from typing import Any, Dict, Optional

from spotify_overlay.config import load_config, save_config
from spotify_overlay.mock_spotify import MockSpotifyClient
from spotify_overlay.spotify_client import SpotifyManager
from spotify_overlay.ui.components import ModernButton, ProgressBar, RoundedArtworkCanvas
from spotify_overlay.ui.setup_dialog import SetupDialog
from spotify_overlay.utils import win32_helper


class SpotifyOverlayWindow:
    """Horizontal, translucent, unobtrusive gaming overlay for Spotify."""

    def __init__(self, root: tk.Tk, client: Any):
        self.root = root
        self.client = client
        self.config = load_config()

        # Window settings
        ov_cfg = self.config.get("overlay", {})
        self.pos_x = ov_cfg.get("x", 60)
        self.pos_y = ov_cfg.get("y", 60)
        self.width = ov_cfg.get("width", 360)
        self.height = ov_cfg.get("height", 78)
        self.opacity = ov_cfg.get("opacity", 0.88)
        self.is_locked = ov_cfg.get("locked", False)
        self.compact_mode = ov_cfg.get("compact_mode", False)
        self.poll_active_ms = ov_cfg.get("poll_active_ms", 1500)
        self.poll_idle_ms = ov_cfg.get("poll_idle_ms", 4000)

        # Drag state
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._hwnd = 0

        # Current playback cache
        self._current_track: Dict[str, Any] = {}
        self._is_polling = True
        self._poll_lock = threading.Lock()

        self._configure_root()
        self._build_layout()
        self._bind_events()

        # Initialize Win32 styles
        self.root.after(100, self._apply_win32_attributes)

        # Start playback polling
        self.root.after(200, self._poll_playback)

        # Periodic topmost assertion for borderless games
        self.root.after(3000, self._ensure_topmost)

    def _configure_root(self) -> None:
        """Apply frameless, topmost, and alpha attributes."""
        self.root.title("Spotify Game Overlay")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", self.opacity)

        # Clamp position to screen dimensions
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        self.pos_x = max(0, min(self.pos_x, screen_w - 100))
        self.pos_y = max(0, min(self.pos_y, screen_h - 60))

        actual_h = 44 if self.compact_mode else self.height
        actual_w = 260 if self.compact_mode else self.width
        self.root.geometry(f"{actual_w}x{actual_h}+{self.pos_x}+{self.pos_y}")
        self.root.configure(bg="#141414")

    def _apply_win32_attributes(self) -> None:
        """Apply native Windows extended styles (ToolWindow & HWND_TOPMOST)."""
        self._hwnd = win32_helper.get_window_handle(self.root)
        if self._hwnd:
            win32_helper.set_tool_window_style(self._hwnd)
            win32_helper.set_topmost(self._hwnd)

    def _ensure_topmost(self) -> None:
        """Periodically assert topmost z-order to guarantee visibility over game windows."""
        if self._hwnd:
            win32_helper.set_topmost(self._hwnd)
        self.root.attributes("-topmost", True)
        self.root.after(3000, self._ensure_topmost)

    def _build_layout(self) -> None:
        """Create the horizontal miniplayer UI."""
        # Main outer container with subtle border
        self.main_frame = tk.Frame(self.root, bg="#141414", highlightbackground="#282828", highlightthickness=1)
        self.main_frame.pack(fill="both", expand=True)

        # Top row: Artwork + Info + Controls
        self.content_frame = tk.Frame(self.main_frame, bg="#141414")
        self.content_frame.pack(fill="both", expand=True, padx=8, pady=(6, 2))

        # Album Artwork (Left)
        art_size = 32 if self.compact_mode else 54
        self.artwork = RoundedArtworkCanvas(self.content_frame, size=art_size, radius=6, bg_color="#141414")
        self.artwork.pack(side="left", padx=(0, 8))

        # Center track info (Title, Artist)
        self.info_frame = tk.Frame(self.content_frame, bg="#141414")
        self.info_frame.pack(side="left", fill="both", expand=True)

        self.title_label = tk.Label(
            self.info_frame,
            text="Spotify Overlay",
            font=("Segoe UI", 9 if self.compact_mode else 10, "bold"),
            fg="#FFFFFF",
            bg="#141414",
            anchor="w",
        )
        self.title_label.pack(fill="x", pady=(2 if self.compact_mode else 4, 0))

        self.artist_label = tk.Label(
            self.info_frame,
            text="Ready to play",
            font=("Segoe UI", 8),
            fg="#A7A7A7",
            bg="#141414",
            anchor="w",
        )
        self.artist_label.pack(fill="x")

        # Right Action & Playback Controls
        self.controls_frame = tk.Frame(self.content_frame, bg="#141414")
        self.controls_frame.pack(side="right", fill="y", padx=(4, 0))

        btn_size = 24 if self.compact_mode else 28

        # Previous Track Button
        self.prev_btn = ModernButton(
            self.controls_frame,
            text="⏮",
            command=self._on_prev_track,
            width=btn_size,
            height=btn_size,
            font=("Segoe UI Symbol", 10),
            container_bg="#141414",
            tooltip="Previous Track",
        )
        self.prev_btn.pack(side="left", padx=2)

        # Play / Pause Button
        self.play_btn = ModernButton(
            self.controls_frame,
            text="▶",
            command=self._on_toggle_play,
            width=btn_size + 4,
            height=btn_size,
            bg_color="#1DB954",
            hover_color="#1ED760",
            active_color="#1DB954",
            text_color="#FFFFFF",
            font=("Segoe UI Symbol", 11, "bold"),
            container_bg="#141414",
            tooltip="Play / Pause",
        )
        self.play_btn.pack(side="left", padx=2)

        # Next Track Button
        self.next_btn = ModernButton(
            self.controls_frame,
            text="⏭",
            command=self._on_next_track,
            width=btn_size,
            height=btn_size,
            font=("Segoe UI Symbol", 10),
            container_bg="#141414",
            tooltip="Next Track",
        )
        self.next_btn.pack(side="left", padx=2)

        # Utility Buttons (Lock, Compact, Settings, Close)
        self.util_frame = tk.Frame(self.controls_frame, bg="#141414")
        self.util_frame.pack(side="left", padx=(6, 0))

        # Position Lock Button
        lock_icon = "🔒" if self.is_locked else "🔓"
        self.lock_btn = ModernButton(
            self.util_frame,
            text=lock_icon,
            command=self._on_toggle_lock,
            width=22,
            height=btn_size,
            bg_color="#332222" if self.is_locked else "#222222",
            hover_color="#443333" if self.is_locked else "#333333",
            font=("Segoe UI Emoji", 9),
            container_bg="#141414",
            tooltip="Lock Screen Position",
        )
        self.lock_btn.pack(side="left", padx=1)

        # Compact Mode Toggle
        self.compact_btn = ModernButton(
            self.util_frame,
            text="🗕" if not self.compact_mode else "🗖",
            command=self._on_toggle_compact,
            width=20,
            height=btn_size,
            font=("Segoe UI Symbol", 9),
            container_bg="#141414",
            tooltip="Compact Mode",
        )
        self.compact_btn.pack(side="left", padx=1)

        # Settings Gear
        self.settings_btn = ModernButton(
            self.util_frame,
            text="⚙",
            command=self._open_settings,
            width=20,
            height=btn_size,
            font=("Segoe UI Symbol", 9),
            container_bg="#141414",
            tooltip="Settings",
        )
        self.settings_btn.pack(side="left", padx=1)

        # Close Button
        self.close_btn = ModernButton(
            self.util_frame,
            text="✕",
            command=self.close,
            width=20,
            height=btn_size,
            hover_color="#E81123",
            font=("Segoe UI", 9, "bold"),
            container_bg="#141414",
            tooltip="Close Overlay",
        )
        self.close_btn.pack(side="left", padx=1)

        # Bottom Progress Bar
        self.progress_bar = ProgressBar(
            self.main_frame,
            width=self.width,
            height=3,
            bg_color="#262626",
            fill_color="#1DB954",
            container_bg="#141414",
        )
        self.progress_bar.pack(fill="x", side="bottom")

    def _bind_events(self) -> None:
        """Bind drag-and-drop and hotkeys."""
        # Window drag bindings on background frames and labels
        drag_targets = [self.main_frame, self.content_frame, self.info_frame, self.title_label, self.artist_label]
        for w in drag_targets:
            w.bind("<Button-1>", self._on_drag_start)
            w.bind("<B1-Motion>", self._on_drag_motion)
            w.bind("<ButtonRelease-1>", self._on_drag_stop)
            # Adjust opacity with mouse wheel on overlay background
            w.bind("<MouseWheel>", self._on_mouse_wheel)

        # Global Hotkey listeners when overlay is focused
        self.root.bind("<Escape>", lambda e: self.close())
        self.root.bind("<space>", lambda e: self._on_toggle_play())
        self.root.bind("<Right>", lambda e: self._on_next_track())
        self.root.bind("<Left>", lambda e: self._on_prev_track())

    def _on_mouse_wheel(self, event) -> None:
        """Adjust transparency dynamically using mouse scroll."""
        delta = 0.05 if event.delta > 0 else -0.05
        new_op = max(0.35, min(1.0, round(self.opacity + delta, 2)))
        if new_op != self.opacity:
            self.opacity = new_op
            self.root.attributes("-alpha", self.opacity)
            self.config["overlay"]["opacity"] = self.opacity
            save_config(self.config)

    def _on_drag_start(self, event) -> None:
        if self.is_locked:
            return
        self._drag_start_x = event.x_root - self.root.winfo_x()
        self._drag_start_y = event.y_root - self.root.winfo_y()

    def _on_drag_motion(self, event) -> None:
        if self.is_locked:
            return
        new_x = event.x_root - self._drag_start_x
        new_y = event.y_root - self._drag_start_y

        # Clamp inside screen boundaries
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        w = self.root.winfo_width()
        h = self.root.winfo_height()

        new_x = max(0, min(new_x, screen_w - w))
        new_y = max(0, min(new_y, screen_h - h))

        self.pos_x = new_x
        self.pos_y = new_y
        self.root.geometry(f"+{new_x}+{new_y}")

    def _on_drag_stop(self, event) -> None:
        if not self.is_locked:
            self.config["overlay"]["x"] = self.pos_x
            self.config["overlay"]["y"] = self.pos_y
            save_config(self.config)

    def _on_toggle_lock(self) -> None:
        """Lock or unlock screen position."""
        self.is_locked = not self.is_locked
        self.lock_btn.set_text("🔒" if self.is_locked else "🔓")
        self.lock_btn.current_bg = "#3A2222" if self.is_locked else "#222222"
        self.lock_btn.render()
        self.config["overlay"]["locked"] = self.is_locked
        save_config(self.config)

    def _on_toggle_compact(self) -> None:
        """Toggle between full miniplayer and slim compact bar."""
        self.compact_mode = not self.compact_mode
        self.config["overlay"]["compact_mode"] = self.compact_mode
        save_config(self.config)

        # Destroy and rebuild layout with new dimensions
        for widget in self.root.winfo_children():
            widget.destroy()

        actual_h = 44 if self.compact_mode else self.height
        actual_w = 260 if self.compact_mode else self.width
        self.root.geometry(f"{actual_w}x{actual_h}+{self.pos_x}+{self.pos_y}")
        self._build_layout()
        self._bind_events()
        self._update_ui_state(self._current_track)

    def _open_settings(self) -> None:
        """Open settings dialog."""
        SetupDialog(self.root, on_save_callback=self._on_settings_saved)

    def _on_settings_saved(self) -> None:
        """Reload configuration and reconnect."""
        self.config = load_config()
        sp_cfg = self.config.get("spotify", {})
        if sp_cfg.get("client_id") and sp_cfg.get("client_secret"):
            self.client = SpotifyManager(
                client_id=sp_cfg["client_id"],
                client_secret=sp_cfg["client_secret"],
                redirect_uri=sp_cfg.get("redirect_uri", "http://127.0.0.1:8888/callback"),
            )
            self.client.connect()
        self._trigger_immediate_poll()

    def _on_toggle_play(self) -> None:
        """Toggle playback and poll immediately."""
        self.client.toggle_play_pause()
        self.root.after(100, self._trigger_immediate_poll)

    def _on_next_track(self) -> None:
        """Skip track and poll immediately."""
        self.client.next_track()
        self.root.after(200, self._trigger_immediate_poll)

    def _on_prev_track(self) -> None:
        """Previous track and poll immediately."""
        self.client.previous_track()
        self.root.after(200, self._trigger_immediate_poll)

    def _trigger_immediate_poll(self) -> None:
        """Worker thread fetch for instantaneous responsiveness."""
        threading.Thread(target=self._fetch_and_update, daemon=True).start()

    def _poll_playback(self) -> None:
        """Periodic background poll."""
        if not self._is_polling:
            return

        threading.Thread(target=self._fetch_and_update, daemon=True).start()

        interval = self.poll_active_ms if self._current_track.get("is_playing") else self.poll_idle_ms
        self.root.after(interval, self._poll_playback)

    def _fetch_and_update(self) -> None:
        """Run network query off the UI thread and push results safely to Tkinter."""
        with self._poll_lock:
            try:
                state = self.client.get_current_playback()
                if state:
                    self.root.after(0, lambda: self._update_ui_state(state))
            except Exception as e:
                print(f"[Overlay] Error fetching playback: {e}")

    def _update_ui_state(self, state: Dict[str, Any]) -> None:
        """Update label texts, icons, progress, and artwork."""
        if not state:
            return
        self._current_track = state

        # Title truncation
        title = state.get("title", "Unknown Title")
        max_title_len = 22 if self.compact_mode else 30
        display_title = (title[:max_title_len] + "…") if len(title) > max_title_len else title
        self.title_label.config(text=display_title)

        # Artist
        artist = state.get("artist", "")
        max_artist_len = 20 if self.compact_mode else 28
        display_artist = (artist[:max_artist_len] + "…") if len(artist) > max_artist_len else artist
        self.artist_label.config(text=display_artist)

        # Play/Pause button symbol
        is_playing = state.get("is_playing", False)
        self.play_btn.set_text("⏸" if is_playing else "▶")

        # Artwork
        pil_img = state.get("cached_pil_image")
        img_id = state.get("image_url") or state.get("title", "")
        self.artwork.update_artwork(pil_img, img_id)

        # Progress bar
        curr_ms = state.get("progress_ms", 0)
        tot_ms = state.get("duration_ms", 0)
        self.progress_bar.set_progress(curr_ms, tot_ms)

    def close(self) -> None:
        """Clean shutdown and persist state."""
        self._is_polling = False
        self.config["overlay"]["x"] = self.pos_x
        self.config["overlay"]["y"] = self.pos_y
        self.config["overlay"]["locked"] = self.is_locked
        self.config["overlay"]["opacity"] = self.opacity
        self.config["overlay"]["compact_mode"] = self.compact_mode
        save_config(self.config)
        self.root.destroy()

