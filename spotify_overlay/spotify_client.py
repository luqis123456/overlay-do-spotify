"""Spotify Web API manager with token persistence, image caching, and Win32 fallback."""

import io
import time
from pathlib import Path
from typing import Any, Dict, Optional
from PIL import Image
import requests
import spotipy
from spotipy.exceptions import SpotifyException
from spotipy.oauth2 import SpotifyOAuth

from spotify_overlay.utils import win32_helper

CACHE_PATH = Path(__file__).resolve().parent.parent / ".spotify_cache"


class SpotifyManager:
    """Manages connection to Spotify Web API with intelligent fallback."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str = "http://127.0.0.1:8888/callback",
        scope: str = "user-read-playback-state user-modify-playback-state user-read-currently-playing",
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scope = scope
        self.is_mock = False

        self._sp: Optional[spotipy.Spotify] = None
        self._oauth: Optional[SpotifyOAuth] = None
        self._image_cache: Dict[str, Image.Image] = {}
        self._last_state: Optional[Dict[str, Any]] = None
        self._last_error_message: str = ""

    def connect(self) -> bool:
        """Authenticate or refresh credentials."""
        if not self.client_id or not self.client_secret:
            self._last_error_message = "Missing Spotify Client ID or Client Secret"
            return False

        try:
            self._oauth = SpotifyOAuth(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=self.redirect_uri,
                scope=self.scope,
                cache_path=str(CACHE_PATH),
                open_browser=True,
            )
            self._sp = spotipy.Spotify(auth_manager=self._oauth)
            return True
        except Exception as e:
            self._last_error_message = str(e)
            print(f"[Spotify] Authentication failed: {e}")
            return False

    def is_authenticated(self) -> bool:
        """Check if access token is available and valid."""
        if not self._oauth:
            return False
        try:
            token_info = self._oauth.validate_token(self._oauth.cache_handler.get_cached_token())
            return token_info is not None
        except Exception:
            return False

    def get_current_playback(self) -> Optional[Dict[str, Any]]:
        """Fetch current playback metadata from Spotify API."""
        if not self._sp:
            if not self.connect():
                return None

        try:
            playback = self._sp.current_playback()
            if not playback or not playback.get("item"):
                # No active track playing
                return {
                    "title": "No Song Playing",
                    "artist": "Open Spotify and press play",
                    "album": "",
                    "duration_ms": 0,
                    "progress_ms": 0,
                    "is_playing": False,
                    "is_active": False,
                    "image_url": "",
                    "cached_pil_image": None,
                    "is_mock": False,
                }

            item = playback["item"]
            title = item.get("name", "Unknown Title")
            artists = ", ".join([a["name"] for a in item.get("artists", [])]) or "Unknown Artist"
            album = item.get("album", {}).get("name", "")
            duration_ms = item.get("duration_ms", 0)
            progress_ms = playback.get("progress_ms", 0)
            is_playing = playback.get("is_playing", False)

            images = item.get("album", {}).get("images", [])
            image_url = images[0]["url"] if images else ""

            pil_img = None
            if image_url:
                pil_img = self._get_cached_artwork(image_url)

            state = {
                "title": title,
                "artist": artists,
                "album": album,
                "duration_ms": duration_ms,
                "progress_ms": progress_ms,
                "is_playing": is_playing,
                "is_active": True,
                "image_url": image_url,
                "cached_pil_image": pil_img,
                "is_mock": False,
            }
            self._last_state = state
            return state

        except SpotifyException as e:
            print(f"[Spotify] API error during get_current_playback: {e}")
            return None
        except Exception as e:
            print(f"[Spotify] Unexpected error: {e}")
            return None

    def _get_cached_artwork(self, url: str) -> Optional[Image.Image]:
        """Download and cache album artwork in memory."""
        if url in self._image_cache:
            return self._image_cache[url]

        try:
            res = requests.get(url, timeout=3.0)
            if res.status_code == 200:
                img = Image.open(io.BytesIO(res.content)).convert("RGBA")
                self._image_cache[url] = img
                # Keep cache bounded to 40 covers
                if len(self._image_cache) > 40:
                    oldest_key = next(iter(self._image_cache))
                    del self._image_cache[oldest_key]
                return img
        except Exception as e:
            print(f"[Spotify] Artwork download failed for {url}: {e}")
        return None

    def toggle_play_pause(self) -> bool:
        """Toggle play/pause with automatic Win32 media key fallback."""
        if self._sp and self._last_state and self._last_state.get("is_active"):
            try:
                if self._last_state.get("is_playing"):
                    self._sp.pause_playback()
                    self._last_state["is_playing"] = False
                else:
                    self._sp.start_playback()
                    self._last_state["is_playing"] = True
                return True
            except SpotifyException as e:
                # 403 occurs on Spotify Free tier ("Player command failed: Premium required")
                # or 404 when no active connect device is active
                print(f"[Spotify] Web API playback control failed ({e.http_status}). Falling back to Windows media key.")
            except Exception as e:
                print(f"[Spotify] Error toggling playback: {e}")

        # Fallback to native Windows media key
        return win32_helper.send_media_key(win32_helper.VK_MEDIA_PLAY_PAUSE)

    def next_track(self) -> bool:
        """Skip to next track with automatic Win32 media key fallback."""
        if self._sp and self._last_state and self._last_state.get("is_active"):
            try:
                self._sp.next_track()
                return True
            except SpotifyException as e:
                print(f"[Spotify] Web API next_track failed ({e.http_status}). Falling back to Windows media key.")
            except Exception as e:
                print(f"[Spotify] Error next_track: {e}")

        # Fallback
        return win32_helper.send_media_key(win32_helper.VK_MEDIA_NEXT_TRACK)

    def previous_track(self) -> bool:
        """Skip to previous track with automatic Win32 media key fallback."""
        if self._sp and self._last_state and self._last_state.get("is_active"):
            try:
                self._sp.previous_track()
                return True
            except SpotifyException as e:
                print(f"[Spotify] Web API previous_track failed ({e.http_status}). Falling back to Windows media key.")
            except Exception as e:
                print(f"[Spotify] Error previous_track: {e}")

        # Fallback
        return win32_helper.send_media_key(win32_helper.VK_MEDIA_PREV_TRACK)

