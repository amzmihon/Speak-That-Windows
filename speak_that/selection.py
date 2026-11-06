"""Windows selected text grabber using keyboard emulation and clipboard capture."""

import ctypes
import time
import uuid
import pyperclip

# Virtual Key Codes
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12  # Alt key
VK_C = 0x43
VK_S = 0x53
KEYEVENTF_KEYUP = 0x0002

user32 = ctypes.windll.user32


def release_modifier_keys():
    """Ensure modifier keys are not physically/virtually held down before triggering Ctrl+C."""
    user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_SHIFT, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_S, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)


def send_ctrl_c():
    """Simulate Ctrl+C to copy current text selection to clipboard."""
    release_modifier_keys()
    time.sleep(0.04)

    # Press Ctrl + C
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    user32.keybd_event(VK_C, 0, 0, 0)
    time.sleep(0.03)
    user32.keybd_event(VK_C, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)


def get_selected_text(fallback_to_clipboard=True, restore_clipboard=True, max_wait_sec=0.35):
    """
    Captures currently selected text from active Windows application.

    1. Reads and saves current clipboard contents.
    2. Writes a unique sentinel token to clipboard.
    3. Simulates Ctrl+C.
    4. Polls clipboard to see if new text replaced the sentinel.
    5. Restores original clipboard if restore_clipboard is True.
    6. Falls back to original clipboard text if nothing was copied and fallback_to_clipboard is True.
    """
    old_clip = None
    try:
        old_clip = pyperclip.paste()
    except Exception:
        old_clip = ""

    # Unique token to distinguish new copy from old content
    token = f"__SPEAKTHAT_TOKEN_{uuid.uuid4().hex[:12]}__"
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
        result = old_clip.strip()

    # Restore original clipboard
    if restore_clipboard and old_clip is not None and old_clip != token:
        try:
            # Small delay so active app finished its paste/copy sequence
            time.sleep(0.05)
            pyperclip.copy(old_clip)
        except Exception:
            pass

    return result

