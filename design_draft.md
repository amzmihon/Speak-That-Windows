# Unified Windows Accessibility & Reading Suite: SpeakThat + Bionic Reader

*   **Author:** Abdullah Mohammad Zakaria (@amzmihon)
*   **Status:** Draft (Step 3: Technical Plan Added)
*   **Date:** 2026-11-20

--------------------------------------------------------------------------------

## Overview

This project unites high-performance offline speech processing with real-time typographic reading assistance into a single, native Windows accessibility client written in Rust. It consolidates two previously disconnected tools:
1. **SpeakThat**: An offline desktop text-to-speech engine using a distilled Kokoro neural model (Paradee 8M ONNX).
2. **ADHD Bionic Reader**: A typographic saccade guide that bolds the opening characters of words to increase reading speed and reduce cognitive fatigue for neurodivergent individuals.

In addition to text-to-speech (TTS) and visual bionic reading, the suite introduces offline speech-to-text (STT) dictation via **NVIDIA Parakeet-TDT 0.6B**. The STT model is distributed as an optional, on-demand in-app download to keep the base installer under 25 MB while giving users private, on-device voice dictation triggered by universal keyboard chords or side mouse buttons (`XButton1` / `XButton2`). The companion Chrome extension is decoupled from all internal audio synthesis, functioning strictly as a lightweight DOM fixation engine and bridge.

--------------------------------------------------------------------------------

## The Problem

Neurodivergent computer users—particularly those with ADHD, dyslexia, or executive function challenges—frequently encounter high cognitive friction when reading and typing:
1. **Sensory Fragmentation**: Reading aids in web browsers cannot interact with external Windows desktop applications (PDF viewers, IDEs, Slack, Word). Desktop speech readers lack visual fixation guidance (bionic bolding) and tactile voice-input dictation.
2. **Input Chord Fatigue**: Triggering assistive tools with complex three-key or four-key keyboard shortcuts (`Ctrl+Alt+Shift+R`) requires significant working memory and frequently misfires or clashes with existing application hotkeys.
3. **Bloated Bundles vs. Privacy Risks**: Modern AI dictation and voice apps either force users to download multi-gigabyte models upfront (causing installation abandonment) or stream private microphone audio to third-party cloud APIs (violating offline privacy invariants).
4. **Browser Tab Audio Throttling**: Web extensions attempting local audio synthesis suffer from browser background throttling, thread contention on heavy web pages, and robotic Web Speech API voices.

--------------------------------------------------------------------------------

## Goals

*   **Sub-100ms Desktop TTS Latency**: Synthesize and begin playing speech from any highlighted Windows text within 100 milliseconds of hotkey activation using the bundled Paradee-8M ONNX model on CPU.
*   **Modular Base Installer Under 25 MB**: Package the complete core Rust client, GUI, input hooks, and Paradee-8M TTS model in an installer smaller than 25 MB.
*   **On-Demand Chunked STT Delivery**: Provide an in-app download manager for NVIDIA Parakeet-TDT 0.6B (~600 MB INT8 / 1.2 GB FP16) featuring HTTP Range requests, resumable downloads, SHA-256 integrity verification, and explicit disk management.
*   **Universal Input Remapping (1–4 Keys & Side Mouse)**: Allow users to map any reading or dictation action to single keys (`F8`), multi-key chords (`Ctrl+Space`, `Ctrl+Shift+R`), or hardware side mouse buttons (`Mouse 4` / `Mouse 5` / `XButton1` / `XButton2`).
*   **Non-Blocking OS Hook Watchdog Safety**: Execute Windows low-level keyboard and mouse hooks (`WH_KEYBOARD_LL`, `WH_MOUSE_LL`) with asynchronous lock-free queueing to yield within 0.1 milliseconds, preventing Windows hook timeout evictions.
*   **Non-Destructive Clipboard & Unicode Typing**: Preserve all system clipboard formats during selection grabbing, and inject transcribed speech directly into active fields via `SendInput(KEYEVENTF_UNICODE)` without overwriting the clipboard.
*   **Decoupled Web Extension Architecture**: Remove audio synthesis bloat from the Chrome extension; communicate bidirectionally with the native desktop engine via Chrome Native Messaging.
*   **Zero Cloud Telemetry**: Guarantee 100% on-device local execution for all text reading, audio inference, and voice dictation.

--------------------------------------------------------------------------------

## Non-Goals

*   **Cloud Audio Fallbacks**: No network-based speech synthesis or cloud transcription APIs will be implemented or queried.
*   **Mandatory Model Downloads**: Users who only require TTS or visual reading will never be prompted or forced to download the STT model weights.
*   **Cross-Platform Parity in v1**: The initial release targets Windows 10 (1809+) and Windows 11 (x64 / ARM64). macOS and Linux ports are deferred.
*   **Arbitrary In-Process Code Injection**: The native application will not inject DLLs into third-party browsers or applications; browser DOM interaction occurs strictly through the official Chrome extension manifest.

--------------------------------------------------------------------------------

## Open Questions

*   **Question 1 (DirectML vs CPU for Parakeet-TDT)**: Does the INT8 quantized Parakeet-TDT ONNX graph run reliably across older integrated GPUs (Intel UHD / Iris Xe) via DirectML, or should CPU inference with multi-threading be the guaranteed baseline with DirectML as opt-in?
*   **Question 2 (Side Mouse Button Exclusions)**: Since `XButton1` and `XButton2` default to browser Back/Forward navigation, should the mouse hook provide a pre-populated process blacklist (e.g., active games, CAD software) where side mouse triggers are automatically suppressed?

--------------------------------------------------------------------------------

## Critical User Journeys (CUJs)

### CUJ 1: Instant Highlight & Read Across Desktop Apps
*   **Given**: The user has the desktop suite running in the system tray and is reading a PDF document in Acrobat or a code file in VS Code.
*   **When**: The user highlights a paragraph of text and presses their configured chord (or side mouse button `Mouse 4`).
*   **Then**: The app snapshots the clipboard, simulates a selection grab, restores the previous clipboard state, and begins sentence-streamed Paradee 8M voice playback within 100ms. A minimal acrylic floating HUD appears showing playback progress and controls.

### CUJ 2: On-Demand Dictation Activation & In-Place Typing
*   **Given**: The user wants voice dictation and has downloaded the optional Parakeet-TDT model via the in-app settings card.
*   **When**: The user places their cursor in any text input field (Notepad, browser form, chat) and holds down their push-to-talk hotkey (e.g., `Mouse 5` or `Ctrl+Space`).
*   **Then**: The app captures microphone audio via WASAPI (`cpal`), feeds it into the Parakeet-TDT transducer upon key release, and synthesizes the transcription directly into the active field as Unicode key events (`SendInput`) without modifying clipboard contents.

### CUJ 3: Distraction-Free Desktop Bionic Reading
*   **Given**: The user has long-form text copied or imported into the application.
*   **When**: The user opens the native desktop scratchpad or presses the hotkey to view current text in Reader Mode.
*   **Then**: The window renders the text with hardware-accelerated bionic fixation bolding (customizable 10%–100% ratio and weight), free of web distractions or ads, with optional synchronized word highlighting pacing alongside TTS audio.

--------------------------------------------------------------------------------

## Technical Plan (Architecture)

### 1. High-Level System Architecture

```text
                                  [ USER INPUT MODES ]
                 ┌───────────────────────────┴───────────────────────────┐
                 │                                                       │
        [ Universal Key Chords ]                                 [ Mouse 4/5 (Side) ]
       (1 to 4 keys: F8, Ctrl+Shift+R)                         (XButton1 / XButton2)
                 │                                                       │
                 └───────────────────────────┬───────────────────────────┘
                                             │
                                   [ Windows OS Kernel ]
                     SetWindowsHookExW (WH_KEYBOARD_LL / WH_MOUSE_LL)
                                             │  Non-blocking immediate yield (<0.1ms)
                                             ▼
                        [ Lock-Free Atomic Ring Buffer ]
                            (crossbeam::channel::bounded)
                                             │
                 ┌───────────────────────────┴───────────────────────────┐
                 │                                                       │
                 ▼                                                       ▼
      [ Selection Capture Worker ]                             [ STT Dictation Worker ]
      - Snapshot Clipboard Formats                             - Stream WASAPI Audio (cpal)
      - SendInput(Ctrl+C) + Backoff                            - Push-to-Talk Gate
      - Read Selection CF_UNICODETEXT                          - Ring buffer VAD
      - Restore Clipboard Formats                              - ort DirectML / CPU Inference
                 │                                                       │
                 ▼                                                       ▼
      [ Paradee-8M TTS Engine ]                                [ Parakeet-TDT 0.6B Engine ]
      - Sentence-level chunking                                - Fast-Conformer TDT Graph
      - ONNX Runtime CPU (AVX2/AVX-512)                        - Greedy / Beam Search Decode
      - Rodio / WASAPI audio playback                          - SendInput(KEYEVENTF_UNICODE)
      - First token audio latency <80ms                        - In-place typing into active window
                 │                                                       │
                 └───────────────────────────┬───────────────────────────┘
                                             │
                                   [ Desktop Application ]
                                   (egui / WinUI 3 Fluent)
                                             │
                 ┌───────────────────────────┴───────────────────────────┐
                 │                                                       │
                 ▼                                                       ▼
        [ Floating Pill HUD ]                                  [ Native Bionic Reader ]
        - Animated soundwave                                   - Immediate-mode text view
        - Pause / Resume / Stop                                - GPU Bionic fixation
        - Acrylic DWM Backdrop                                 - Synchronized word pulse
```

### 2. Subsystem Breakdown

#### 2.1 Subsystem 1: Low-Level Input & Hook Dispatcher
*   **Windows API**: `SetWindowsHookExW` registering both `WH_KEYBOARD_LL` and `WH_MOUSE_LL` hooks within a dedicated Win32 message loop thread (`GetMessageW`).
*   **Watchdog Safety Guarantee**: Windows enforces `LowLevelHooksTimeout` (typically 200ms; down to 25ms in enterprise-hardened configurations). Hook callback functions do zero processing, zero heap allocations, and zero mutex acquisitions. Each callback packages raw message data into an 8-byte value and writes to a `crossbeam::channel::bounded(512)` queue before immediately returning `CallNextHookEx`.
*   **Chord Matching Engine**: A separate consumer thread tracks key state bitmasks (supporting single keys `F1–F12`, 2–4 key chords `Ctrl+Shift+Alt+Key`, and mouse side buttons `XButton1`/`XButton2`). Upon matching a configured trigger, the consumer dispatches a task message to the appropriate worker.
*   **Side Mouse Pass-Through**: When an `XBUTTONDOWN` event matches a mapped hotkey, the consumer can optionally suppress the event (`return 1` in hook) to prevent browser Back/Forward navigation, while bypassing suppression for blacklisted applications (games, CAD).

#### 2.2 Subsystem 2: Text Selection & Clipboard Snapshot
*   **Multi-Format Snapshot**: Before querying highlighted text, the worker opens the clipboard via `OpenClipboard(hwnd)`. It enumerates all registered formats via `EnumClipboardFormats`, copying raw data pointers into a vector of `(u32 format_id, Vec<u8> payload)` tuples.
*   **Selection Grab**: The worker simulates `Ctrl+C` via `SendInput`. To avoid race conditions with slower native applications (Excel, Adobe Reader), it applies an exponential backoff retry loop (5ms, 15ms, 45ms up to 200ms) waiting for clipboard sequence number changes (`GetClipboardSequenceNumber`).
*   **Format Restoration**: Once `CF_UNICODETEXT` is extracted for speech synthesis, the worker clears the clipboard (`EmptyClipboard`) and restores all original format buffers, ensuring images, files, and rich text remain in the user's clipboard intact.

#### 2.3 Subsystem 3: Paradee-8M ONNX TTS Engine
*   **Model**: Distilled Kokoro architecture (8M parameters, ~8.4 MB INT8 ONNX file).
*   **Inference Execution**: Bound through `ort` (ONNX Runtime Rust bindings) configured with the native CPU Execution Provider, multi-threaded intra-op parallelism, and AVX2/AVX-512 vector acceleration.
*   **Sentence-Streaming Pipeline**: Text is parsed into sentences using punctuation boundaries (`.`, `!`, `?`, `\n`). Sentence 0 is fed into inference immediately, producing first audio in <80ms. Sentence 1+ is synthesized concurrently in the background while sentence 0 plays through a WASAPI ring buffer (`cpal` / `rodio`).

#### 2.4 Subsystem 4: On-Demand Parakeet-TDT 0.6B STT Engine
*   **Model Architecture**: NVIDIA Fast-Conformer with Token-and-Duration Transducer (TDT) decoding heads (~600 MB INT8 ONNX).
*   **Chunked Resumable Downloader**: Built using `reqwest` with HTTP Range headers (`bytes=start-end`), writing to a temporary `.part` file. Features include download pause/resume, download speed calculation, ETA, and final SHA-256 checksum verification against a signed manifest.
*   **Audio Capture & Push-to-Talk**: When the configured dictation key/mouse button is depressed, `cpal` opens a 16 kHz mono WASAPI capture stream. Audio PCM samples accumulate in a ring buffer with optional Voice Activity Detection (VAD).
*   **Inference & Fallback**: Audio Mel-filterbank features pass into the ONNX graph. The execution provider defaults to DirectML (GPU acceleration across NVIDIA, AMD, and Intel Arc/Iris Xe), with automatic graceful fallback to CPU if DirectML device initialization encounters driver errors.
*   **Keystroke Typing**: The recognized text string is typed directly into the active foreground window using `SendInput` with `KEYEVENTF_UNICODE` flags. Characters are emitted with 1–2ms micro-yields to guarantee compatibility across legacy Win32, Qt, and Electron input fields without clipboard paste contamination.

#### 2.5 Subsystem 5: Native GUI & Desktop Bionic Reader
*   **UI Framework**: Native hardware-accelerated immediate-mode GUI (`egui` with `eframe` WGPU/DirectX backend), compiled to sub-5 MB binary overhead.
*   **Floating Pill HUD**: Acrylic/DWM blurred HUD window positioned non-intrusively near the active text selection or screen edge. Displays animated audio waveform, play/pause toggle, voice speed slider, and stop button without stealing keyboard focus (`WS_EX_NOACTIVATE`).
*   **Bionic Reader Scratchpad**: Distraction-free native reading pane with immediate-mode bionic bolding. Configurable fixation ratio (10%–100%) and stroke weight, with synchronous active-word rhythmic pulsing aligned to TTS speech playback.
*   **Settings & Extension Installer Card**: Graphical settings pane providing visual chord recording (press key combination to bind), mouse button detection, model download manager, and a 1-click Chrome Extension registration button.

#### 2.6 Subsystem 6: Decoupled Chrome Extension & In-App Installer Helper
*   **Zero IPC / Standalone Architecture**: The Chrome extension has zero audio dependencies and zero IPC connections to the desktop daemon. It runs entirely client-side in the browser, focusing purely on high-performance DOM TreeWalker bionic text bolding, distraction dimming, and reader mode.
*   **Unified OS-Level Reading**: When reading a webpage in Chrome, the user does not need an in-browser audio button. Highlighting text and triggering the global desktop chord (e.g. `Mouse 4` or `Ctrl+Shift+R`) works across Chrome just as it does in Word, Acrobat, or Slack.
*   **In-App 1-Click Installer Helper**: The desktop settings pane provides an "Install Chrome Extension" button that copies the extension directory path, automatically opens `chrome://extensions/` in Chrome, and reveals the extension folder in Windows File Explorer for effortless setup.

### 3. Data Structures & State Management

```rust
// Configuration Schema (persisted to config.json)
pub struct AppConfig {
    pub tts: TtsSettings,
    pub stt: SttSettings,
    pub bionic: BionicSettings,
    pub hotkeys: HotkeyMap,
    pub ui: UiSettings,
}

pub struct HotkeyMap {
    pub read_selection: InputChord,    // e.g. Chord([Ctrl, Shift, R]) or MouseButton(4)
    pub dictation_ptt: InputChord,     // e.g. Chord([Ctrl, Space]) or MouseButton(5)
    pub toggle_reader: InputChord,     // e.g. Chord([Alt, R])
    pub stop_audio: InputChord,        // e.g. Chord([Escape])
}

pub enum InputTrigger {
    Key(u16),                          // Virtual-Key code
    Chord(Vec<u16>),                   // 2 to 4 virtual keys
    MouseButton(u32),                  // 4 = XButton1, 5 = XButton2
}

pub struct SttSettings {
    pub model_installed: bool,
    pub model_path: PathBuf,
    pub auto_punctuation: bool,
    pub execution_provider: ExecutionProviderChoice, // Auto / DirectML / CPU
}
```

--------------------------------------------------------------------------------

## Alternatives Considered

### Alternative A: Monolithic Model Bundling (Pre-packaging Parakeet-TDT 0.6B)
*   **Pros**: Out-of-the-box dictation is immediately functional upon installation without requiring an in-app download step.
*   **Cons**: Expands the installer footprint from ~20 MB to >650 MB (or >1.2 GB uncompressed), leading to slow downloads and high installation abandonment for users who only want TTS reading.
*   **Reason for Rejection**: Rejected by author: Violates the core lightweight constraint (<25 MB base installer). Users who do not need speech-to-text should not be forced to download or store over 600 MB of model weights.

### Alternative B: Web Speech API & In-Browser TTS in Chrome Extension
*   **Pros**: Functions entirely within the browser without needing a desktop application running.
*   **Cons**: Relies on robotic, inconsistent system synthetic voices; background tabs suffer from aggressive Chromium audio throttling; completely unusable in non-browser desktop applications (Word, PDF readers, IDEs).
*   **Reason for Rejection**: Rejected by author: High maintenance overhead with inferior voice quality. A native desktop client reading highlighted text at the OS level delivers superior neural audio (Paradee 8M) across all desktop software.

### Alternative C: Standard Win32 `RegisterHotKey` API
*   **Pros**: Standard Win32 registration mechanism that does not require global message hooking threads.
*   **Cons**: Cannot detect hardware mouse buttons (`XButton1` / `XButton2`); strictly enforces traditional modifier key pairings; fails when competing applications hold identical chords; cannot reliably capture key-up transitions for push-to-talk dictation.
*   **Reason for Rejection**: Rejected by author: Incompatible with the core requirement for side mouse button triggers (`Mouse 4` / `Mouse 5`) and push-to-talk release detection. `SetWindowsHookExW` with lock-free bounded buffering provides the required flexibility while eliminating watchdog timeout risks.

### Alternative D: Chrome Native Messaging IPC Bridge
*   **Pros**: Allows a floating button rendered inside Chrome pages to command the desktop app.
*   **Cons**: Requires Windows Registry modifications (`HKCU\Software\Google\Chrome\NativeMessagingHosts`), stdio JSON length-prefixed protocol plumbing, and fragile background process synchronization.
*   **Reason for Rejection**: Rejected by author: Redundant and needlessly complex. The desktop app already captures and reads text highlighted in Chrome globally via Windows-level input hooks, making browser-to-desktop IPC unnecessary.

### Alternative E: Python / PyInstaller / Electron Desktop Shell
*   **Pros**: Rapid UI prototyping; reuses the existing Python codebase from SpeakThat.
*   **Cons**: High memory consumption (150–350 MB idle), sluggish cold startup times (>1.5s), large installer packages (>100 MB), and complex C/C++ low-level hook interop.
*   **Reason for Rejection**: Rejected by author: Native Rust (`egui` + `windows-rs` + `ort`) achieves instant startup (<50ms), sub-15 MB memory footprint, sub-25 MB installer size, and direct Win32 API execution with zero runtime overhead.

--------------------------------------------------------------------------------

## Non-Functional Requirements

### Security & Privacy
*   **Strict Offline Invariant**: Zero telemetry, zero external API calls for audio inference or transcription. All microphone audio and highlighted text remains strictly within local process memory.
*   **Integrity Verification**: Downloaded model weights (Parakeet-TDT) are strictly validated against a hard-coded SHA-256 hash before loading into the inference runtime.

### Performance & Latency
*   **TTS Latency**: First-audio sentence playback commences within 100 milliseconds of chord activation on standard x64 CPU architectures.
*   **Hook Watchdog Budget**: Low-level hook callbacks return within 0.1 milliseconds (well below the Windows 25–200ms `LowLevelHooksTimeout` limit).
*   **Resource Footprint**: Idle memory consumption remains under 20 MB; peak memory during TTS playback remains under 60 MB. When Parakeet-TDT STT is active, memory remains under 1.2 GB (INT8 DirectML).

### Rollout & Compatibility
*   **OS Support**: Compatible with Windows 10 (version 1809+) and Windows 11 on x64 and ARM64.
*   **Hardware Fallback**: DirectML GPU acceleration automatically falls back to multi-threaded CPU execution if DirectX device creation fails.

--------------------------------------------------------------------------------

## Detailed Implementation Plan

### Target Files to Create / Modify

#### 1. `Cargo.toml` (Create)
*   **Type / Scope**: Rust Workspace Configuration & Manifest.
*   **Rationale**: Defines the root crate, compiler optimizations (`opt-level = 3`, `lto = "thin"`, `codegen-units = 1`), and dependencies (`windows`, `cpal`, `rodio`, `ort`, `egui`, `eframe`, `crossbeam`, `reqwest`, `serde`, `serde_json`, `tokio`, `sha2`).

#### 2. `src/main.rs` (Create)
*   **Type / Scope**: Application Entry Point.
*   **Rationale**: Enforces single-instance execution via Win32 `CreateMutexW`, parses CLI flags, initializes file-based tracing (`tracing-appender`), loads configuration, and launches background worker channels and the GUI message loop.

#### 3. `src/config.rs` (Create)
*   **Type / Scope**: Settings Model & Persistence Engine.
*   **Rationale**: Defines strongly typed structures (`AppConfig`, `HotkeyMap`, `SttSettings`, `TtsSettings`) and provides thread-safe, atomic disk persistence to `%APPDATA%\SpeakThat\config.json`.

#### 4. `src/input/hook.rs` (Create)
*   **Type / Scope**: Win32 Low-Level Input Hook Service.
*   **Rationale**: Spawns an isolated Win32 thread running `GetMessageW` and registers `WH_KEYBOARD_LL` and `WH_MOUSE_LL` hooks via `SetWindowsHookExW`. Guarantees sub-0.1ms non-blocking return by immediately dispatching raw events to a `crossbeam::channel::bounded` queue.

#### 5. `src/input/chord.rs` (Create)
*   **Type / Scope**: Key Chord & Mouse Button Pattern Matcher.
*   **Rationale**: Maintains virtual key bitmasks to match single keys (`F1–F12`), 2-to-4 key combinations (`Ctrl+Shift+Alt+Key`), and side mouse buttons (`XButton1` / `XButton2`), managing push-to-talk press and release transitions.

#### 6. `src/input/injector.rs` (Create)
*   **Type / Scope**: Synthetic Keystroke Injector.
*   **Rationale**: Types transcribed text directly into the active foreground window using Win32 `SendInput` with `KEYEVENTF_UNICODE`, chunking words with 1–2ms micro-yields without touching the system clipboard.

#### 7. `src/clipboard/mod.rs` (Create)
*   **Type / Scope**: Non-Destructive Multi-Format Clipboard Controller.
*   **Rationale**: Snapshots all registered clipboard formats (`EnumClipboardFormats`) before simulating `Ctrl+C` with geometric backoff, extracts `CF_UNICODETEXT` for reading, and restores all prior formats intact.

#### 8. `src/audio/tts.rs` (Create)
*   **Type / Scope**: Neural Text-to-Speech Engine.
*   **Rationale**: Executes the bundled Paradee-8M ONNX model using `ort` on CPU with AVX2 vectorization, streaming sentence chunks through `rodio` / WASAPI ring buffers for sub-100ms first-audio latency.

#### 9. `src/audio/stt.rs` (Create)
*   **Type / Scope**: Neural Speech-to-Text Dictation Engine.
*   **Rationale**: Manages the NVIDIA Parakeet-TDT 0.6B Fast-Conformer ONNX graph using `ort` with DirectML GPU acceleration and graceful CPU fallback, decoding Mel-filterbank spectrograms into text.

#### 10. `src/audio/mic.rs` (Create)
*   **Type / Scope**: Audio Input Capture Service.
*   **Rationale**: Configures a 16 kHz 16-bit mono WASAPI microphone stream via `cpal`, accumulating PCM samples into a ring buffer gated by push-to-talk key states.

#### 11. `src/downloader/mod.rs` (Create)
*   **Type / Scope**: Resumable Chunked Download Manager.
*   **Rationale**: Downloads the optional ~600 MB Parakeet-TDT model via `reqwest` with HTTP Range headers (`bytes=start-end`), temporary `.part` file preservation, real-time progress callbacks, and SHA-256 integrity validation.

#### 12. `src/ui/app.rs` (Create)
*   **Type / Scope**: Desktop Main Window & Settings Interface.
*   **Rationale**: Implemented via `egui`/`eframe`, providing an interactive chord recorder, mouse button binder, STT model download card, Bionic scratchpad, and Chrome Extension helper.

#### 13. `src/ui/hud.rs` (Create)
*   **Type / Scope**: Floating Acrylic Pill HUD.
*   **Rationale**: Renders a non-activating (`WS_EX_NOACTIVATE`) floating window with DWM acrylic backdrop, showing live animated audio waveforms and playback controls without stealing keyboard focus.

#### 14. `src/ui/bionic_renderer.rs` (Create)
*   **Type / Scope**: Hardware-Accelerated Bionic Text View.
*   **Rationale**: Renders imported or pasted text with customizable bionic fixation bolding (10%–100%) and stroke weight, supporting synchronized word highlighting that advances alongside TTS playback.

#### 15. `build.rs` (Create)
*   **Type / Scope**: Windows Build Script.
*   **Rationale**: Embeds application icon resources, DPI awareness manifests, and version metadata into the Windows executable.

#### 16. Chrome Extension Files (Modified)
*   **`ADHD_Bionic-Reader Extantion Unpacked Loader/manifest.json`**: Removed `"tts"` permission; bumped version to 1.2.0; updated description.
*   **`ADHD_Bionic-Reader Extantion Unpacked Loader/background.js`**: Removed audio queues, `chrome.tts` invocations, and speech listeners; preserved settings broadcast and keyboard commands.
*   **`ADHD_Bionic-Reader Extantion Unpacked Loader/popup.html`**: Removed the Audio (TTS) tab, leaving clean tabs for Bionic Text, Environment, and Reader.
*   **`ADHD_Bionic-Reader Extantion Unpacked Loader/popup.js`**: Removed floating TTS button toggle and voice speed slider handlers.
*   **`ADHD_Bionic-Reader Extantion Unpacked Loader/content.js`**: Removed floating audio widget DOM elements, selection audio listeners, and shadow DOM host.

#### 17. `README.md` (Modify)
*   **Type / Scope**: Documentation.
*   **Rationale**: Documents the unified native Rust architecture, offline TTS capabilities, on-demand Parakeet-TDT STT installation, universal chord mapping, and decoupled extension installation.
