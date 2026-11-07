# 🗣️ SpeakThat Windows

**SpeakThat** is a modern, ultra-fast Windows Text Reader desktop application powered by **Paradee 8M ONNX TTS** (distilled from Kokoro-82M). 

Whenever you highlight any text across any Windows application (browser, PDF reader, Word document, IDE, chat app) and press **`Ctrl + Shift + R`**, SpeakThat will instantly capture the selected text and read it aloud with natural, high-fidelity human speech.

---

## ✨ Features

- **Global Hotkey Reader**:
  - **`Ctrl + Shift + R`**: Reads currently selected text in any Windows software.
  - **`Ctrl + Shift + X`**: Instantly stops / cancels speech playback.
- **Paradee 8M TTS Engine**:
  - Tiny ~8.5 MB int8 quantized ONNX model.
  - Over **18x to 25x real-time speed** on standard CPU.
  - Generates crisp **24 kHz** audio waveforms.
  - Four distinct voice personas:
    - **`bf_isabella`** — Isabella (British Female, crisp & articulate)
    - **`af_heart`** — Heart (American Female, warm & expressive)
    - **`am_puck`** — Puck (American Male, casual & clear)
    - **`bm_fable`** — Fable (British Male, polished & narrative)
- **Zero-Latency Sentence Streaming**:
  - Splits text into natural sentence chunks and begins audio playback on the very first sentence within **~100ms**, synthesizing subsequent sentences in parallel.
- **Floating Mini-Player HUD**:
  - A sleek, draggable floating pill widget on screen showing current spoken sentence, with quick **Play / Pause (⏸)** and **Stop (⏹)** controls.
- **System Tray Integration**:
  - Lives quietly in the Windows notification area (System Tray).
  - Quick right-click menu to change voices, adjust speeds, read selection, or stop playback.
  - Minimizes cleanly to tray when closing the dashboard.
- **Clipboard Preservation**:
  - Safely preserves your existing clipboard history so reading selected text doesn't erase whatever you had previously copied.
  - Optional fallback to read existing clipboard text when no selection is highlighted.
- **Modern Settings Dashboard**:
  - Built with CustomTkinter (dark mode, rounded cards).
  - Real-time voice persona audition button.
  - Reading speed slider (0.7x to 2.0x).
  - Volume slider (0% to 100%).
  - Direct text reader box for typing or pasting manual text.
  - Persistent settings stored in `config.json`.

---

## 🚀 Quick Start

### 1. Run Directly

Double-click **`run.bat`** (or execute via command line):
```powershell
.\run.bat
```

To run silently in the background without a command prompt window, double-click:
```powershell
run_background.vbs
```

### 2. How to Use
1. Highlight any text in your browser, document, or application.
2. Press **`Ctrl + Shift + R`**.
3. SpeakThat will start reading the text aloud immediately.
4. Press **`Ctrl + Shift + X`** (or the Stop button on the floating HUD) at any time to cancel.

---

## 🛠️ Project Structure

```
E:\Speak-That-Windows\
├── assets\
│   ├── icon.ico            # Windows icon file
│   └── icon.png            # App logo
├── speak_that\
│   ├── __init__.py         # Package init
│   ├── app.py              # Application lifecycle coordinator
│   ├── config.py           # Settings manager & JSON persistence
│   ├── engine.py           # Paradee TTS engine with sentence streaming
│   ├── hotkeys.py          # Global hotkey manager (pynput)
│   ├── hud.py              # Floating mini-player HUD bar
│   ├── selection.py        # Windows selected text grabber & clipboard manager
│   ├── tray.py             # System tray icon and context menu (pystray)
│   └── ui.py               # CustomTkinter modern dashboard window
├── main.py                 # Application entry point
├── run.bat                 # One-click Windows batch launcher
├── run_background.vbs      # Silent background launcher
├── requirements.txt        # Dependencies
└── README.md               # Documentation
```

---

## ⚙️ Configuration (`config.json`)

Settings are automatically saved and reloaded:
```json
{
    "voice": "bf_isabella",
    "speed": 1.05,
    "volume": 1.0,
    "hotkey_read": "<ctrl>+<shift>+r",
    "hotkey_stop": "<ctrl>+<shift>+x",
    "restore_clipboard": true,
    "fallback_to_clipboard": true,
    "show_floating_hud": true,
    "minimize_to_tray_on_close": true,
    "start_minimized": false
}
```

---

## 📜 Credits & References
- **Paradee TTS**: [https://github.com/sahilmahendrakar/paradee](https://github.com/sahilmahendrakar/paradee)
- **Model**: [https://huggingface.co/sahilmahendrakar/Paradee-8M-v1.2](https://huggingface.co/sahilmahendrakar/Paradee-8M-v1.2)
- **Base Architecture**: Kokoro-82M / Misaki G2P
