"""Application coordinator tying together Engine, Hotkeys, GUI, Tray, and Floating HUD."""

import os
import sys
import threading
import time

from .config import Config
from .engine import TTSEngine
from .hotkeys import HotkeyManager
from .hud import FloatingHUD
from .selection import get_selected_text
from .tray import TrayManager
from .ui import MainWindow


class SpeakThatApp:
    """Main application lifecycle controller."""

    def __init__(self):
        # 1. Config
        self.config = Config()

        # 2. TTS Engine
        self.engine = TTSEngine(
            voice=self.config.get("voice", "bf_isabella"),
            speed=float(self.config.get("speed", 1.05)),
            volume=float(self.config.get("volume", 1.0)),
        )

        # 3. Main GUI Window
        self.window = MainWindow(
            config=self.config,
            engine=self.engine,
            on_read_selection=self.read_selected_text,
            on_stop_reading=self.stop_reading,
            on_quit=self.shutdown
        )

        # 4. Floating Mini-HUD Bar
        self.hud = FloatingHUD(
            master=self.window,
            on_pause_toggle=self.toggle_pause,
            on_stop=self.stop_reading
        )

        # 5. System Tray Manager
        self.tray = TrayManager(
            config=self.config,
            on_read=self.read_selected_text,
            on_stop=self.stop_reading,
            on_show_window=self.show_window,
            on_exit=self.shutdown,
            on_voice_change=self.on_voice_change_tray,
            on_speed_change=self.on_speed_change_tray,
        )

        # 6. Global Hotkey Manager
        self.hotkeys = HotkeyManager(
            on_read_callback=self.read_selected_text,
            on_stop_callback=self.stop_reading
        )
        self.hotkeys.set_hotkeys(
            self.config.get("hotkey_read", "<ctrl>+<shift>+r"),
            self.config.get("hotkey_stop", "<ctrl>+<shift>+x")
        )

        # Connect engine callbacks
        self.engine.on_status_change = self._on_engine_status
        self.engine.on_sentence = self._on_engine_sentence
        self.engine.on_complete = self._on_engine_complete

    def start(self):
        print("[+] Starting system tray icon...", flush=True)
        self.tray.start()

        print("[+] Registering global hotkeys...", flush=True)
        self.hotkeys.start()

        print("[+] Launching SpeakThat Dashboard...", flush=True)
        print("    * Shortcut: [Ctrl + Shift + R] to read selected text", flush=True)
        print("    * Shortcut: [Ctrl + Shift + X] to stop reading", flush=True)
        print("===================================================\n", flush=True)

        if self.config.get("start_minimized", False):
            self.window.withdraw()
        else:
            self.show_window()

        try:
            self.window.mainloop()
        except KeyboardInterrupt:
            self.shutdown()

    def show_window(self):
        """Restore and focus the main settings dashboard window."""
        def _show():
            try:
                self.window.deiconify()
                self.window.lift()
                self.window.attributes("-topmost", True)
                self.window.after(250, lambda: self.window.attributes("-topmost", False))
                self.window.focus_force()
            except Exception:
                pass
        self.window.after(0, _show)

    def read_selected_text(self):
        """Action invoked when shortcut Ctrl+Shift+R is pressed."""
        fallback = self.config.get("fallback_to_clipboard", True)
        restore = self.config.get("restore_clipboard", False)

        print("[Hotkeys] Triggered: Capturing selected text...", flush=True)
        self.window.update_status("Capturing text...")

        text = get_selected_text(
            fallback_to_clipboard=fallback,
            restore_clipboard=restore
        )

        if text and text.strip():
            preview = text.strip().replace("\n", " ")
            if len(preview) > 50:
                preview = preview[:47] + "..."
            print(f"[Reader] Speaking ({len(text)} chars): \"{preview}\"", flush=True)

            # Show HUD if enabled
            if self.config.get("show_floating_hud", True):
                first_line = text.strip().split("\n")[0]
                self.window.after(0, lambda: self.hud.show(first_line))

            # Start reading
            self.engine.speak(text)
        else:
            print("[Reader] No text selected or on clipboard.", flush=True)
            self.window.update_status("Ready")
            def _flash_no_text():
                self.hud.show("No text selected. Highlight text and press Ctrl+Shift+R.")
                self.window.after(2500, self.hud.hide)
            self.window.after(0, _flash_no_text)

    def stop_reading(self):
        """Action invoked when shortcut Ctrl+Shift+X or Stop button is pressed."""
        self.engine.stop()
        self.window.after(0, self.hud.hide)
        self.window.update_status("Ready")
        self.tray.set_status("Ready")

    def toggle_pause(self):
        self.engine.toggle_pause()
        is_paused = self.engine.is_paused()
        self.hud.set_paused_state(is_paused)

    def on_voice_change_tray(self, voice_key):
        self.engine.set_voice(voice_key)
        self.window._load_config_to_ui()

    def on_speed_change_tray(self, speed_val):
        self.engine.set_speed(speed_val)
        self.window._load_config_to_ui()

    def _on_engine_status(self, status):
        self.window.update_status(status)
        self.tray.set_status(status)

    def _on_engine_sentence(self, sentence):
        self.window.update_sentence(sentence)
        if self.config.get("show_floating_hud", True):
            self.window.after(0, lambda: self.hud.update_sentence(sentence))

    def _on_engine_complete(self):
        self.window.update_status("Ready")
        self.tray.set_status("Ready")
        self.window.after(0, self.hud.hide)

    def shutdown(self):
        """Clean application termination."""
        print("[App] Shutting down SpeakThat...")
        self.hotkeys.stop()
        self.engine.stop()
        self.tray.stop()
        try:
            self.window.after(0, self.window.destroy)
            self.window.after(50, self.window.quit)
        except Exception:
            pass
        # Fallback exit after short grace period
        threading.Thread(target=lambda: (time.sleep(0.3), os._exit(0)), daemon=True).start()
