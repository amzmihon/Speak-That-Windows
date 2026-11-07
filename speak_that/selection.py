"""Windows selected text grabber using keyboard emulation and clipboard capture."""

import ctypes
import time
import uuid
import pyperclip

# Virtual Key Codes
VK_SHIFT = 0x10
VK_LSHIFT = 0xA0
VK_RSHIFT = 0xA1
VK_CONTROL = 0x11
VK_MENU = 0x12       # Alt key
VK_LMENU = 0xA4      # Left Alt
VK_RMENU = 0xA5      # Right Alt
VK_C = 0x43
VK_R = 0x52
VK_S = 0x53
KEYEVENTF_KEYUP = 0x0002

user32 = ctypes.windll.user32


def wait_for_modifiers_released(timeout=0.6):
    """
    Waits until the user releases Shift, Alt, R, and S keys.
    Crucial for global hotkeys like Ctrl+Shift+R and Ctrl+Alt+S so that the subsequent Ctrl+C
    is not interpreted by Windows applications as Ctrl+Shift+C (Inspect) or Ctrl+Alt+C.
    """
    start = time.time()
    while time.time() - start < timeout:
        shift_down = bool(
            (user32.GetAsyncKeyState(VK_SHIFT) & 0x8000)
            or (user32.GetAsyncKeyState(VK_LSHIFT) & 0x8000)
            or (user32.GetAsyncKeyState(VK_RSHIFT) & 0x8000)
        )
        alt_down = bool(
            (user32.GetAsyncKeyState(VK_MENU) & 0x8000)
            or (user32.GetAsyncKeyState(VK_LMENU) & 0x8000)
            or (user32.GetAsyncKeyState(VK_RMENU) & 0x8000)
        )
        r_down = bool(user32.GetAsyncKeyState(VK_R) & 0x8000)
        s_down = bool(user32.GetAsyncKeyState(VK_S) & 0x8000)

        if not shift_down and not alt_down and not r_down and not s_down:
            break
        time.sleep(0.02)


def release_modifier_keys():
    """Ensure modifier keys are virtually released before sending Ctrl+C."""
    user32.keybd_event(VK_SHIFT, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_LSHIFT, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_RSHIFT, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_LMENU, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_RMENU, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_R, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_S, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)


def send_ctrl_c():
    """Simulate clean Ctrl+C to copy current text selection to clipboard."""
    # First wait for user to release hotkey modifiers
    wait_for_modifiers_released(timeout=0.4)
    release_modifier_keys()
    time.sleep(0.03)

    # Press Ctrl + C
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    user32.keybd_event(VK_C, 0, 0, 0)
    time.sleep(0.04)
    user32.keybd_event(VK_C, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)


def get_selected_text(fallback_to_clipboard=True, restore_clipboard=False, max_wait_sec=0.4):
    """
    Captures currently selected text from active Windows application.

    1. Reads and saves current clipboard contents.
    2. Writes a unique sentinel token to clipboard.
    3. Simulates clean Ctrl+C after releasing Alt/S.
    4. Polls clipboard to see if new text replaced the sentinel.
    5. Returns copied text, or falls back to existing clipboard content.
    """
    old_clip = None
    try:
        old_clip = pyperclip.paste()
    except Exception:
        old_clip = ""

    # Unique token to distinguish new copy from old content
    token = f"__SPEAKTHAT_{uuid.uuid4().hex[:8]}__"
    try:
        pyperclip.copy(token)
    except Exception:
        pass

    # Send Ctrl+C
    send_ctrl_c()

    # Poll clipboard for change
    start_time = time.time()
    copied_text = ""
    while time.time() - start_time < max_wait_sec:
        time.sleep(0.02)
        try:
            curr = pyperclip.paste()
            if curr != token:
                copied_text = curr
                break
        except Exception:
            pass

    result = None
    if copied_text and copied_text.strip() and copied_text != token:
        result = copied_text.strip()
    elif fallback_to_clipboard and old_clip and old_clip.strip() and old_clip != token:
        # Fall back to existing clipboard text
        result = old_clip.strip()
        try:
            pyperclip.copy(old_clip)
        except Exception:
            pass

    # Restore original clipboard only if requested
    if restore_clipboard and old_clip is not None and old_clip != token:
        try:
            time.sleep(0.05)
            pyperclip.copy(old_clip)
        except Exception:
            pass

    return result
