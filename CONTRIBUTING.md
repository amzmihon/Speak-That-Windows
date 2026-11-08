# Contributing to SpeakThat Windows

Thank you for your interest in contributing to **SpeakThat**! We welcome bug fixes, documentation improvements, UI polish, and new feature contributions.

---

## 🛠️ Getting Started

### Prerequisites
- **Windows 10 or 11 (64-bit)**
- **Python 3.10 – 3.13**
- **Git**

### 1. Clone the Repository
```bash
git clone https://github.com/amzmihon/Speak-That-Windows.git
cd Speak-That-Windows
```

### 2. Quick Developer Launch
SpeakThat includes an automated bootstrap script that sets up the virtual environment and installs dependencies:
```cmd
run.bat
```

Or manually with PowerShell:
```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

---

## 📂 Project Structure

```
Speak-That-Windows/
├── main.py                  # Application entry point
├── run.bat                  # Developer launch script
├── build_release.py         # PyInstaller build & packaging automation
├── installer_src.py         # Standalone GUI installer builder
├── speak_that/
│   ├── app.py               # Main application controller & lifecycle
│   ├── config.py            # User settings & hotkey configuration
│   ├── engine.py            # Paradee 8M ONNX TTS speech synthesis engine
│   ├── hotkeys.py           # Global keyboard shortcut listener
│   ├── hud.py               # WinUI 3 styled semi-transparent floating pill HUD
│   ├── selection.py         # Windows selection & clipboard capture
│   ├── tray.py              # Windows system tray menu & notifications
│   ├── ui.py                # Fluent Settings & Voice Manager UI
│   └── model/               # Distilled Paradee 8M ONNX weights & configs
├── assets/                  # Icons, fonts, previews, and HUD templates
└── brand/                   # Brand identity guidelines and vector assets
```

---

## 🎨 Design & Code Principles

1. **100% Offline & Private**: SpeakThat never transmits clipboard text or synthesized audio over the network. All AI inference runs locally using ONNX Runtime.
2. **WinUI 3 Fluent Design**: UI components adhere to Microsoft Fluent Design standards: semi-transparent frosted Acrylic backdrops, DWM hardware rounded corners, and Segoe Fluent icons.
3. **Snappy & Non-blocking**: All TTS inference, clipboard polling, and audio playback execute asynchronously off the main thread.
4. **Lightweight Footprint**: Keep binary sizes compact and avoid unnecessary dependencies.

---

## 🧪 Testing Your Changes

Before submitting a Pull Request, verify that:
1. Syntax and compilation pass without errors:
   ```cmd
   python -m compileall speak_that main.py build_release.py
   ```
2. The global hotkey (`Ctrl+Shift+R`) successfully captures selected text across Notepad, browsers, and Office apps.
3. The HUD cleanly displays waveforms and playback controls without graphical glitches.
4. The system tray icon correctly minimizes and restores the application window.

---

## 🚀 Submitting a Pull Request

1. Fork the repository and create a new branch from `main`:
   ```bash
   git checkout -b feature/my-new-feature
   ```
2. Commit your changes with clear, descriptive commit messages.
3. Push to your fork:
   ```bash
   git push origin feature/my-new-feature
   ```
4. Open a **Pull Request** targeting the `main` branch on GitHub.
5. Provide a summary of changes, screenshots/GIFs of any UI modifications, and test results.

---

## 📄 License
By contributing to SpeakThat, you agree that your contributions will be licensed under the project's [MIT License](LICENSE).

