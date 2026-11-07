# 🗣️ SpeakThat Windows

**SpeakThat** is a modern, ultra-fast Windows Text Reader desktop application powered by **Paradee 8M ONNX TTS** (distilled from Kokoro-82M). 

Whenever you highlight any text across any Windows application (browser, PDF reader, Word document, IDE, chat app) and press **`Ctrl + Shift + R`**, SpeakThat instantly captures the selected text and reads it aloud with natural, high-fidelity human speech.

Designed following the **Microsoft WinUI 3 Fluent Design System** ([microsoft-ui-xaml](https://github.com/microsoft/microsoft-ui-xaml)), SpeakThat features native Windows 11 DWM hardware rounded corners, semi-transparent frosted Acrylic backdrops, smooth pill capsules, and Segoe Fluent Icons.

---

## 📦 Download & Installation

SpeakThat is distributed as a completely standalone Windows application. **No Python installation or command-line setup is required.**

| Package | Format | Description |
| :--- | :--- | :--- |
| **`SpeakThat-Setup.exe`** | **Single-file GUI Installer** | Recommended for most users. Automatically installs to `%LOCALAPPDATA%\Programs\SpeakThat` and creates Start Menu and Desktop shortcuts. |
| **`SpeakThat-v1.2-Windows-x64.zip`** | **Portable Archive** | Extract anywhere (e.g. `C:\SpeakThat` or USB drive) and double-click `SpeakThat.exe`. Includes `Install.bat` for optional one-click shortcut creation. |
| **Source (`run.bat`)** | **Developer Launch** | For Python developers: automatically sets up the `.venv` virtual environment and boots the app. |

### System Requirements
- **OS**: Windows 10 (1809+) or Windows 11 (64-bit x64).
- **RAM**: 200 MB free memory.
- **CPU**: Standard x64 processor (Paradee runs on CPU with ~20x real-time speed, no GPU required).
- **Network**: **100% Offline** (the ONNX model is pre-bundled in the package).

---

## ⌨️ Global Shortcuts

| Shortcut | Action | Description |
| :---: | :--- | :--- |
| **`Ctrl + Shift + R`** | **Read Selection** | Instantly grabs highlighted text in any window and streams natural speech audio in ~100ms. |
| **`Ctrl + Shift + X`** | **Stop Playback** | Immediately stops / cancels speech playback and hides the floating HUD. |

*Note: You can customize hotkeys and toggles in the Settings dashboard at any time.*

---

## ✨ Key Highlights

- **WinUI 3 Fluent Design & Frosted Glass**:
  - Borderless, semi-transparent floating HUD capsule with smooth 26px rounded pill corners.
  - Transparent color-keying (`-transparentcolor`) eliminates all rectangular box artifacts on Windows DWM.
  - Official Microsoft `Segoe Fluent Icons` / `Segoe MDL2 Assets` for native Pause (`\uE769`), Play (`\uE768`), and Stop (`\uE71A`).
  - Animated 3-bar sinusoidal neural waveform badge indicating real-time voice synthesis.
  - Windows 11 DWM hardware corner rounding (`DWMWCP_ROUND`) and GPU-accelerated Acrylic backdrop.

- **Paradee 8M TTS Engine**:
  - Ultra-compact ~8.5 MB int8 quantized ONNX model.
  - **18x to 25x real-time generation speed** on standard multi-core CPUs.
  - Generates crisp **24 kHz** audio waveforms.
  - Four distinct voice personas:
    - **`bf_isabella`** — Isabella (British Female, crisp & articulate)
    - **`af_heart`** — Heart (American Female, warm & expressive)
    - **`am_puck`** — Puck (American Male, casual & clear)
    - **`bm_fable`** — Fable (British Male, polished & narrative)

- **Zero-Latency Sentence Streaming**:
  - Splits text into natural sentence boundaries and begins audio playback on the very first sentence within **~100ms**, synthesizing subsequent sentences asynchronously in parallel.

- **Clipboard Preservation**:
  - Automatically snapshots and restores your existing clipboard history so reading selected text never overwrites your copied data.
  - Smart fallback reads clipboard content if no text is currently highlighted.

- **Studio Dashboard & System Tray**:
  - Two-column Fluent navigation rail (Studio Reader, Voice Personas, Shortcuts & Behavior, Model & Benchmark).
  - Lives quietly in the Windows notification area (System Tray) with right-click menu controls.
  - Adaptive resolution clamping (up to 1400x900) with zero scrollbars at default size.

---

## 🚀 Running from Source

If you prefer running from Python source:

1. **Clone the repository:**
   ```powershell
   git clone https://github.com/mohammadrabiulhasan/Speak-That-Windows.git
   cd Speak-That-Windows
   ```

2. **Launch with `run.bat`:**
   ```powershell
   .\run.bat
   ```
   *The launcher will automatically create a `.venv`, install all dependencies from `requirements.txt`, verify local model integrity, and start the app.*

3. **Silent Background Mode:**
   ```powershell
   run_background.vbs
   ```

---

## 🔨 Building the Standalone Executable & Installer

To compile `SpeakThat.exe` and `SpeakThat-Setup.exe` from source:

```powershell
# 1. Activate your virtual environment
.\.venv\Scripts\activate

# 2. Run the release builder script
python build_release.py
```

The script will automatically:
1. Bundle all dependencies, assets, Misaki phonemizer dicts, Spacy models, and Paradee ONNX weights.
2. Compile `dist\SpeakThat\SpeakThat.exe` using PyInstaller.
3. Generate `dist\SpeakThat\Install.bat` for one-click setup.
4. Package `dist\SpeakThat-v1.2-Windows-x64.zip` (portable distribution).
5. Compile the self-extracting GUI installer `dist\SpeakThat-Setup.exe`.

---

## 🛠️ Project Structure

```
E:\Speak-That-Windows\
├── assets\
│   ├── icon.ico            # Windows application icon (16px - 256px)
│   └── icon.png            # Fluent brand icon
├── speak_that\
│   ├── __init__.py         # Package init
│   ├── app.py              # Application lifecycle coordinator
│   ├── config.py           # Settings manager & JSON persistence
│   ├── engine.py           # Paradee TTS engine with sentence streaming
│   ├── hotkeys.py          # Global hotkey manager (pynput)
│   ├── hud.py              # WinUI 3 Fluent Glassmorphism floating HUD
│   ├── model\              # Bundled local offline ONNX model
│   │   ├── config.json     # Architecture configuration
│   │   └── paradee_int8.onnx # 8.4 MB quantized ONNX weights
│   ├── selection.py        # Windows selected text grabber & clipboard manager
│   ├── tray.py             # System tray icon & context menu (pystray)
│   └── ui.py               # WinUI 3 Fluent dashboard window
├── build_release.py        # Release compiler & packager
├── installer_src.py        # Graphical installer source
├── main.py                 # Application entry point
├── run.bat                 # One-click Windows batch launcher
├── run_background.vbs      # Silent background launcher
├── requirements.txt        # Dependencies
└── README.md               # Documentation
```

---

## ⚙️ Configuration (`config.json`)

Settings are automatically persisted to `config.json`:
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
- **Microsoft UI XAML**: [https://github.com/microsoft/microsoft-ui-xaml](https://github.com/microsoft/microsoft-ui-xaml)
- **Paradee TTS**: [https://github.com/sahilmahendrakar/paradee](https://github.com/sahilmahendrakar/paradee)
- **Model**: [https://huggingface.co/sahilmahendrakar/Paradee-8M-v1.2](https://huggingface.co/sahilmahendrakar/Paradee-8M-v1.2)
- **Base Architecture**: Kokoro-82M / Misaki G2P
