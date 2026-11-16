import json
import os
from pathlib import Path
from typing import Any, Dict

CONFIG_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = CONFIG_DIR / "config.json"
ENV_FILE = CONFIG_DIR / ".env"

DEFAULT_CONFIG: Dict[str, Any] = {
    "spotify": {
        "client_id": "",
        "client_secret": "",
        "redirect_uri": "http://127.0.0.1:8888/callback",
        "scope": "user-read-playback-state user-modify-playback-state user-read-currently-playing",
    },
    "overlay": {
        "x": 60,
        "y": 60,
        "width": 360,
        "height": 78,
        "opacity": 0.88,
        "locked": False,
        "compact_mode": False,
        "poll_active_ms": 1500,
        "poll_idle_ms": 4000,
        "always_on_top": True,
    },
}


def load_env_file() -> None:
    """Manually parse .env without external dotenv dependency if present."""
    if not ENV_FILE.exists():
        return

    try:
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip("\"'")
                if key and not os.environ.get(key):
                    os.environ[key] = val
    except Exception as e:
        print(f"[Config] Error reading .env: {e}")


def load_config() -> Dict[str, Any]:
    """Load config.json merged with environment variables and defaults."""
    load_env_file()
    config = json.loads(json.dumps(DEFAULT_CONFIG))  # deep copy

    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                if "spotify" in saved:
                    config["spotify"].update(saved["spotify"])
                if "overlay" in saved:
                    config["overlay"].update(saved["overlay"])
        except Exception as e:
            print(f"[Config] Warning: Failed to read {CONFIG_FILE}: {e}")

    # Environment variables take precedence if present
    env_id = os.environ.get("SPOTIPY_CLIENT_ID")
    env_secret = os.environ.get("SPOTIPY_CLIENT_SECRET")
    env_redirect = os.environ.get("SPOTIPY_REDIRECT_URI")

    if env_id:
        config["spotify"]["client_id"] = env_id
    if env_secret:
        config["spotify"]["client_secret"] = env_secret
    if env_redirect:
        config["spotify"]["redirect_uri"] = env_redirect

    return config


def save_config(config: Dict[str, Any]) -> bool:
    """Save config safely to config.json."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        print(f"[Config] Failed to save config to {CONFIG_FILE}: {e}")
        return False

