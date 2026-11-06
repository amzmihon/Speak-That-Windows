"""System tray icon integration using pystray."""

import os
import threading
from PIL import Image
import pystray
from pystray import MenuItem as item, Menu

from .config import VOICE_NAMES


class TrayManager:
    """Manages the Windows system tray notification icon and quick context menu."""

    def __init__(self, config, on_read=None, on_stop=None, on_show_window=None, on_exit=None, on_voice_change=None, on_speed_change=None):
        self.config = config
        self.on_read = on_read
        self.on_stop = on_stop
        self.on_show_window = on_show_window
        self.on_exit = on_exit
        self.on_voice_change = on_voice_change
        self.on_speed_change = on_speed_change

        self.icon = None
        self._status_text = "Ready"
        self._thread = None

    def _get_icon_image(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        png_path = os.path.join(base_dir, "assets", "icon.png")
        if os.path.exists(png_path):
            try:
                return Image.open(png_path)
            except Exception:
                pass

        # Fallback generated icon
        img = Image.new("RGBA", (64, 64), color=(67, 97, 238, 255))
        return img

    def _create_menu(self):
        # Voice submenu
        voice_items = []
        for voice_key, voice_label in VOICE_NAMES.items():
            def make_voice_handler(vk):
                return lambda icon, item: self._handle_voice_change(vk)

            def make_voice_checker(vk):
                return lambda item: self.config.get("voice") == vk

            voice_items.append(
                item(voice_label, make_voice_handler(voice_key), checked=make_voice_checker(voice_key), radio=True)
            )

        # Speed submenu
        speed_items = []
        for spd in [0.8, 1.0, 1.1, 1.25, 1.5, 1.75]:
            def make_speed_handler(s):
                return lambda icon, item: self._handle_speed_change(s)

            def make_speed_checker(s):
                return lambda item: abs(self.config.get("speed", 1.0) - s) < 0.05

            speed_items.append(
                item(f"{spd:.1f}x", make_speed_handler(spd), checked=make_speed_checker(spd), radio=True)
            )

        return Menu(
            item(f"SpeakThat ({self._status_text})", lambda: None, enabled=False),
            Menu.SEPARATOR,
            item("Read Selected Text (Ctrl+Alt+S)", lambda icon, it: self.on_read() if self.on_read else None, default=True),
            item("Stop Reading (Ctrl+Alt+X)", lambda icon, it: self.on_stop() if self.on_stop else None),
            Menu.SEPARATOR,
            item("Voice", Menu(*voice_items)),
            item("Speed", Menu(*speed_items)),
            Menu.SEPARATOR,
            item("Open Settings Dashboard", lambda icon, it: self.on_show_window() if self.on_show_window else None),
            item("Exit SpeakThat", lambda icon, it: self._handle_exit()),
        )

    def _handle_voice_change(self, voice_key):
        self.config.set("voice", voice_key)
        if self.on_voice_change:
            self.on_voice_change(voice_key)
        self.update_menu()

    def _handle_speed_change(self, speed_val):
        self.config.set("speed", speed_val)
        if self.on_speed_change:
            self.on_speed_change(speed_val)
        self.update_menu()

    def _handle_exit(self):
        self.stop()
        if self.on_exit:
            self.on_exit()

    def set_status(self, status):
        self._status_text = status
        if self.icon:
            self.icon.title = f"SpeakThat - {status}"
            self.update_menu()

    def update_menu(self):
        if self.icon:
            try:
                self.icon.menu = self._create_menu()
            except Exception:
                pass

    def start(self):
        image = self._get_icon_image()
        self.icon = pystray.Icon(
            "SpeakThat",
            image,
            f"SpeakThat - {self._status_text}",
            menu=self._create_menu()
        )
        self._thread = threading.Thread(target=self.icon.run, daemon=True)
        self._thread.start()

    def stop(self):
        if self.icon:
            try:
                self.icon.stop()
            except Exception:
                pass
            self.icon = None

