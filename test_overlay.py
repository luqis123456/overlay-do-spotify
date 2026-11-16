"""Automated test suite for the Spotify gaming overlay."""

import sys
import time
import tkinter as tk
import unittest

from spotify_overlay.config import DEFAULT_CONFIG, load_config, save_config
from spotify_overlay.mock_spotify import DEMO_TRACKS, MockSpotifyClient, generate_mock_cover
from spotify_overlay.spotify_client import SpotifyManager
from spotify_overlay.ui.components import ModernButton, ProgressBar, RoundedArtworkCanvas
from spotify_overlay.ui.overlay_window import SpotifyOverlayWindow
from spotify_overlay.utils import win32_helper


class TestConfig(unittest.TestCase):
    """Test configuration persistence and structure."""

    def test_default_config_structure(self):
        self.assertIn("spotify", DEFAULT_CONFIG)
        self.assertIn("overlay", DEFAULT_CONFIG)
        self.assertIn("client_id", DEFAULT_CONFIG["spotify"])
        self.assertIn("opacity", DEFAULT_CONFIG["overlay"])
        self.assertIn("locked", DEFAULT_CONFIG["overlay"])

    def test_load_and_save(self):
        cfg = load_config()
        self.assertIsInstance(cfg, dict)
        old_op = cfg.get("overlay", {}).get("opacity", 0.88)
        cfg["overlay"]["opacity"] = 0.95
        save_config(cfg)

        reloaded = load_config()
        self.assertEqual(reloaded["overlay"]["opacity"], 0.95)

        # Restore
        cfg["overlay"]["opacity"] = old_op
        save_config(cfg)


class TestMockSpotifyClient(unittest.TestCase):
    """Test mock playback logic and state progression."""

    def setUp(self):
        self.client = MockSpotifyClient()

    def test_initial_playback(self):
        state = self.client.get_current_playback()
        self.assertIsNotNone(state)
        self.assertEqual(state["title"], DEMO_TRACKS[0]["title"])
        self.assertTrue(state["is_playing"])
        self.assertTrue(state["is_mock"])

    def test_toggle_play_pause(self):
        self.assertTrue(self.client.is_playing)
        self.client.toggle_play_pause()
        self.assertFalse(self.client.is_playing)
        state = self.client.get_current_playback()
        self.assertFalse(state["is_playing"])

        self.client.toggle_play_pause()
        self.assertTrue(self.client.is_playing)

    def test_next_and_previous_track(self):
        initial_track = self.client.get_current_playback()["title"]
        self.client.next_track()
        next_track = self.client.get_current_playback()["title"]
        self.assertNotEqual(initial_track, next_track)

        self.client.previous_track()
        prev_track = self.client.get_current_playback()["title"]
        self.assertEqual(initial_track, prev_track)

    def test_artwork_generation(self):
        cover = generate_mock_cover(DEMO_TRACKS[0], size=64)
        self.assertEqual(cover.size, (64, 64))
        self.assertEqual(cover.mode, "RGBA")


class TestWin32Helper(unittest.TestCase):
    """Test Win32 API helper safety."""

    def test_dpi_init(self):
        # Should execute safely without raising exceptions
        win32_helper.init_dpi_awareness()

    def test_virtual_keys(self):
        self.assertEqual(win32_helper.VK_MEDIA_NEXT_TRACK, 0xB0)
        self.assertEqual(win32_helper.VK_MEDIA_PREV_TRACK, 0xB1)
        self.assertEqual(win32_helper.VK_MEDIA_PLAY_PAUSE, 0xB3)


class TestUIIntegration(unittest.TestCase):
    """Test that UI widgets render correctly and close cleanly."""

    def test_window_lifecycle(self):
        root = tk.Tk()
        client = MockSpotifyClient()
        app = SpotifyOverlayWindow(root, client)

        # Trigger initial UI updates
        root.update_idletasks()
        root.update()

        # Check widget instances
        self.assertIsInstance(app.artwork, RoundedArtworkCanvas)
        self.assertIsInstance(app.play_btn, ModernButton)
        self.assertIsInstance(app.progress_bar, ProgressBar)

        # Test toggle lock
        init_lock = app.is_locked
        app._on_toggle_lock()
        self.assertEqual(app.is_locked, not init_lock)
        app._on_toggle_lock()
        self.assertEqual(app.is_locked, init_lock)

        # Test button actions
        app._on_toggle_play()
        app._on_next_track()
        app._on_prev_track()
        root.update_idletasks()

        # Clean shutdown
        app.close()


def run_tests() -> bool:
    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestMockSpotifyClient))
    suite.addTests(loader.loadTestsFromTestCase(TestWin32Helper))
    suite.addTests(loader.loadTestsFromTestCase(TestUIIntegration))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
