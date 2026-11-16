"""Desktop Spotify Gaming Overlay - Main Entry Point."""

import argparse
import sys
import tkinter as tk

from spotify_overlay.config import DEFAULT_CONFIG, load_config, save_config
from spotify_overlay.mock_spotify import MockSpotifyClient
from spotify_overlay.spotify_client import SpotifyManager
from spotify_overlay.ui.overlay_window import SpotifyOverlayWindow
from spotify_overlay.utils import win32_helper


def main() -> None:
    parser = argparse.ArgumentParser(description="Lightweight Desktop Spotify Overlay for PC Gaming.")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run in interactive Demo / Mock mode without requiring Spotify API credentials.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset overlay position and configuration back to defaults.",
    )
    args = parser.parse_args()

    # Step 1: Initialize razor-sharp Win32 DPI awareness before creating Tk
    win32_helper.init_dpi_awareness()

    if args.reset:
        save_config(DEFAULT_CONFIG)
        print("[Config] Configuration reset to default values.")

    config = load_config()
    sp_cfg = config.get("spotify", {})
    client_id = sp_cfg.get("client_id", "").strip()
    client_secret = sp_cfg.get("client_secret", "").strip()

    # Step 2: Determine client backend
    if args.demo:
        print("[Mode] Starting in interactive DEMO mode with simulated gaming tracks...")
        client = MockSpotifyClient()
    elif client_id and client_secret:
        print("[Mode] Connecting to Spotify Web API...")
        client = SpotifyManager(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=sp_cfg.get("redirect_uri", "http://127.0.0.1:8888/callback"),
            scope=sp_cfg.get("scope", "user-read-playback-state user-modify-playback-state"),
        )
        if not client.connect():
            print("[Warning] Could not connect to Spotify Web API. Falling back to Demo mode.")
            client = MockSpotifyClient()
    else:
        print(
            "\n[Notice] No Spotify API credentials found in config.json or environment.\n"
            "Starting in DEMO mode so you can test the overlay immediately.\n"
            "To connect real Spotify, click the ⚙ (gear) icon on the overlay or set SPOTIPY_CLIENT_ID in .env.\n"
        )
        client = MockSpotifyClient()

    # Step 3: Launch Tkinter application
    root = tk.Tk()
    app = SpotifyOverlayWindow(root, client)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\nExiting Spotify Overlay...")
        app.close()
    except Exception as e:
        print(f"Error in main loop: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

