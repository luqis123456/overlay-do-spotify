"""Mock Spotify client for immediate out-of-the-box testing and offline demo mode."""

import io
import time
from typing import Any, Dict, List, Optional
from PIL import Image, ImageDraw, ImageFont

DEMO_TRACKS: List[Dict[str, Any]] = [
    {
        "title": "Legends Never Die",
        "artist": "Against The Current",
        "album": "League of Legends Worlds",
        "duration_ms": 235000,
        "color1": (220, 50, 40),
        "color2": (20, 20, 40),
        "symbol": "⚔️",
    },
    {
        "title": "Warriors",
        "artist": "Imagine Dragons",
        "album": "Warriors (2014)",
        "duration_ms": 171000,
        "color1": (230, 150, 20),
        "color2": (40, 30, 20),
        "symbol": "🛡️",
    },
    {
        "title": "Enemy",
        "artist": "Imagine Dragons, JID",
        "album": "Arcane League of Legends",
        "duration_ms": 173000,
        "color1": (160, 40, 200),
        "color2": (20, 10, 35),
        "symbol": "⚡",
    },
    {
        "title": "Awaken",
        "artist": "Valerie Broussard",
        "album": "Awaken (Season 2019)",
        "duration_ms": 204000,
        "color1": (30, 160, 230),
        "color2": (10, 25, 50),
        "symbol": "✨",
    },
    {
        "title": "STAR WALKIN'",
        "artist": "Lil Nas X",
        "album": "Worlds 2022",
        "duration_ms": 210000,
        "color1": (30, 215, 96),
        "color2": (18, 18, 18),
        "symbol": "🌟",
    },
]


def generate_mock_cover(track_info: Dict[str, Any], size: int = 120) -> Image.Image:
    """Generate a clean procedural album cover for the track."""
    img = Image.new("RGBA", (size, size), track_info["color2"])
    draw = ImageDraw.Draw(img)

    # Draw gradient or styled background circles
    c1 = track_info["color1"]
    c2 = track_info["color2"]

    for i in range(size):
        ratio = i / float(size)
        r = int(c1[0] * (1 - ratio) + c2[0] * ratio)
        g = int(c1[1] * (1 - ratio) + c2[1] * ratio)
        b = int(c1[2] * (1 - ratio) + c2[2] * ratio)
        draw.line([(0, i), (size, i)], fill=(r, g, b, 255))

    # Center decorative shape / vignette
    margin = size // 6
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=size // 10,
        outline=(255, 255, 255, 120),
        width=2,
    )

    # Monogram or musical icon in center
    text = track_info["title"][:2].upper()
    try:
        font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text(
            ((size - tw) // 2, (size - th) // 2),
            text,
            fill=(255, 255, 255, 240),
            font=font,
        )
    except Exception:
        draw.text((size // 3, size // 3), text, fill=(255, 255, 255, 240))

    return img


class MockSpotifyClient:
    """Simulates the SpotifyManager interface without requiring credentials or network access."""

    def __init__(self):
        self.is_mock = True
        self.track_index = 0
        self.is_playing = True
        self.progress_ms = 45000
        self.last_update_time = time.time()
        self._cover_cache: Dict[int, Image.Image] = {}

    def get_current_playback(self) -> Dict[str, Any]:
        """Return simulated current track metadata and progressive playback timestamp."""
        now = time.time()
        track = DEMO_TRACKS[self.track_index]

        if self.is_playing:
            delta_ms = int((now - self.last_update_time) * 1000)
            self.progress_ms += delta_ms
            if self.progress_ms >= track["duration_ms"]:
                # Auto loop or next
                self.progress_ms = 0
                self.track_index = (self.track_index + 1) % len(DEMO_TRACKS)
                track = DEMO_TRACKS[self.track_index]

        self.last_update_time = now

        if self.track_index not in self._cover_cache:
            self._cover_cache[self.track_index] = generate_mock_cover(track)

        return {
            "title": track["title"],
            "artist": track["artist"],
            "album": track["album"],
            "duration_ms": track["duration_ms"],
            "progress_ms": self.progress_ms,
            "is_playing": self.is_playing,
            "is_active": True,
            "image_url": f"mock://cover/{self.track_index}",
            "cached_pil_image": self._cover_cache[self.track_index],
            "is_mock": True,
        }

    def toggle_play_pause(self) -> bool:
        """Toggle playback state."""
        self.last_update_time = time.time()
        self.is_playing = not self.is_playing
        return True

    def next_track(self) -> bool:
        """Advance to next track."""
        self.track_index = (self.track_index + 1) % len(DEMO_TRACKS)
        self.progress_ms = 0
        self.last_update_time = time.time()
        return True

    def previous_track(self) -> bool:
        """Return to previous track or start of current track."""
        if self.progress_ms > 4000:
            self.progress_ms = 0
        else:
            self.track_index = (self.track_index - 1) % len(DEMO_TRACKS)
            self.progress_ms = 0
        self.last_update_time = time.time()
        return True

