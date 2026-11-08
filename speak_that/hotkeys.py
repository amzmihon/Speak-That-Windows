"""Global hotkey listener using pynput."""

import re
import threading
from pynput import keyboard


def normalize_hotkey(hotkey_str):
    """
    Normalizes human-friendly hotkey strings into pynput format.
    E.g. 'Ctrl+Alt+S' -> '<ctrl>+<alt>+s'
         'Ctrl+Shift+R' -> '<ctrl>+<shift>+r'
    """
    if not hotkey_str:
        return "<ctrl>+<alt>+s"

    s = hotkey_str.strip().lower()
    # Replace common words
    parts = re.split(r'[\+\s]+', s)
    norm_parts = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if p in ("ctrl", "control"):
            norm_parts.append("<ctrl>")
        elif p in ("alt", "menu"):
            norm_parts.append("<alt>")
        elif p in ("shift",):
            norm_parts.append("<shift>")
        elif p in ("cmd", "win", "super", "windows"):
            norm_parts.append("<cmd>")
        elif p in ("esc", "escape"):
            norm_parts.append("<esc>")
        elif p in ("space",):
            norm_parts.append("<space>")
        else:
            if not p.startswith("<") and len(p) == 1:
                norm_parts.append(p)
            elif not p.startswith("<"):
                norm_parts.append(f"<{p}>")
            else:
                norm_parts.append(p)

    return "+".join(norm_parts)


def format_hotkey_for_display(hotkey_str):
    """Converts internal pynput hotkey string (<ctrl>+<shift>+r) into readable 'Ctrl + Shift + R'."""
    if not hotkey_str:
        return ""
    parts = hotkey_str.lower().replace("<", "").replace(">", "").split("+")
    display_parts = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if p in ("ctrl", "control"):
            display_parts.append("Ctrl")
        elif p in ("alt", "menu"):
            display_parts.append("Alt")
        elif p == "shift":
            display_parts.append("Shift")
        elif p in ("cmd", "win", "windows", "super"):
            display_parts.append("Win")
        elif p == "space":
            display_parts.append("Space")
        elif p in ("esc", "escape"):
            display_parts.append("Esc")
        elif p.startswith("f") and p[1:].isdigit():
            display_parts.append(p.upper())
        else:
            display_parts.append(p.upper())
    return " + ".join(display_parts)


def validate_hotkey(hotkey_str):
    """Validates if a hotkey string can be registered with pynput.GlobalHotKeys."""
    if not hotkey_str or not hotkey_str.strip():
        return False, "Shortcut cannot be empty."
    norm = normalize_hotkey(hotkey_str)
    try:
        from pynput import keyboard
        _ = keyboard.GlobalHotKeys({norm: lambda: None})
        return True, norm
    except Exception as e:
        return False, f"Invalid shortcut combination: {e}"


class HotkeyManager:
    """Manages global Windows hotkeys for reading and stopping speech."""

    def __init__(self, on_read_callback=None, on_stop_callback=None):
        self.on_read = on_read_callback
        self.on_stop = on_stop_callback

        self.hotkey_read_str = "<ctrl>+<shift>+r"
        self.hotkey_stop_str = "<ctrl>+<shift>+x"

        self._hotkeys = None
        self._lock = threading.RLock()

    def set_hotkeys(self, read_str, stop_str):
        with self._lock:
            self.hotkey_read_str = normalize_hotkey(read_str)
            self.hotkey_stop_str = normalize_hotkey(stop_str)
            if self._hotkeys is not None:
                self.start()

    def start(self):
        with self._lock:
            if self._hotkeys is not None:
                try:
                    self._hotkeys.stop()
                except Exception:
                    pass
                self._hotkeys = None
            try:
                mapping = {}
                if self.on_read and self.hotkey_read_str:
                    mapping[self.hotkey_read_str] = self._handle_read

                if self.on_stop and self.hotkey_stop_str:
                    mapping[self.hotkey_stop_str] = self._handle_stop

                self._hotkeys = keyboard.GlobalHotKeys(mapping)
                self._hotkeys.daemon = True
                self._hotkeys.start()
                print(f"[Hotkeys] Registered: Read={self.hotkey_read_str}, Stop={self.hotkey_stop_str}")
            except Exception as e:
                print(f"[Hotkeys] Failed to bind global hotkeys: {e}")

    def stop(self):
        with self._lock:
            if self._hotkeys is not None:
                try:
                    self._hotkeys.stop()
                except Exception:
                    pass
                self._hotkeys = None

    def _handle_read(self):
        if self.on_read:
            # Run callback in worker thread so hotkey hook is never blocked
            threading.Thread(target=self.on_read, daemon=True).start()

    def _handle_stop(self):
        if self.on_stop:
            threading.Thread(target=self.on_stop, daemon=True).start()

