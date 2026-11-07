"""Configuration manager for SpeakThat."""

import json
import os
import sys

DEFAULT_CONFIG = {
    "voice": "bf_isabella",
    "speed": 1.05,
    "volume": 1.0,
    "hotkey_read": "<ctrl>+<shift>+r",
    "hotkey_stop": "<ctrl>+<shift>+x",
    "restore_clipboard": False,
    "fallback_to_clipboard": True,
    "show_floating_hud": True,
    "minimize_to_tray_on_close": True,
    "start_minimized": False,
    "sound_feedback": True,
    "window_width": 1000,
    "window_height": 700,
}

VOICE_NAMES = {
    "bf_isabella": "Isabella (British Female)",
    "af_heart": "Heart (American Female)",
    "am_puck": "Puck (American Male)",
    "bm_fable": "Fable (British Male)",
}


class Config:
    def __init__(self, config_file=None):
        if config_file is None:
            # Prefer local config in project directory, fallback to AppData
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.config_path = os.path.join(base_dir, "config.json")
        else:
            self.config_path = config_file

        self.data = dict(DEFAULT_CONFIG)
        self.load()

    def load(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self.data.update(saved)
            except Exception as e:
                print(f"[Config] Error loading config: {e}")

    def save(self):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            print(f"[Config] Error saving config: {e}")

    def get(self, key, default=None):
        return self.data.get(key, default if default is not None else DEFAULT_CONFIG.get(key))

    def set(self, key, value):
        self.data[key] = value
        self.save()

