# Unified Windows Accessibility & Reading Suite: SpeakThat + Bionic Reader

*   **Author:** Abdullah Mohammad Zakaria (@amzmihon)
*   **Status:** In Review (Draft Complete)
*   **Date:** 2026-11-20
*   **Predecessor Concept Brief:** [concepts_brief.md](../../concepts_brief.md)

--------------------------------------------------------------------------------

## Overview

This project unites high-performance offline speech processing with real-time typographic reading assistance into a single, native Windows accessibility client written in Rust. It consolidates two previously disconnected tools:
1. **SpeakThat**: An offline desktop text-to-speech engine using a distilled Kokoro neural model (Paradee 8M ONNX).
2. **ADHD Bionic Reader**: A typographic saccade guide that bolds the opening characters of words to increase reading speed and reduce cognitive fatigue for neurodivergent individuals.

In addition to text-to-speech (TTS) and visual bionic reading, the suite introduces offline speech-to-text (STT) dictation via **NVIDIA Parakeet-TDT 0.6B**. The STT model is distributed as an optional, on-demand in-app download to keep the base installer under 25 MB while giving users private, on-device voice dictation triggered by universal keyboard chords or side mouse buttons (`XButton1` / `XButton2`). The companion Chrome extension is decoupled from all internal audio synthesis, functioning strictly as a lightweight DOM fixation engine and bridge.

--------------------------------------------------------------------------------

## The Problem

Neurodivergent computer users—particularly those with ADHD, dyslexia, or executive function challenges—encounter measurable friction when reading and typing:
1. **Sensory Fragmentation**: Reading tools in web browsers cannot interact with external Windows desktop applications (PDF viewers, IDEs, Slack, Word). Desktop speech readers lack visual fixation guidance (bionic bolding) and tactile voice-input dictation.
2. **Input Chord Fatigue**: Triggering assistive tools with complex three-key or four-key keyboard shortcuts (`Ctrl+Alt+Shift+R`) requires high working memory and frequently misfires or clashes with existing application hotkeys.
3. **Large Downloads vs. Privacy Trade-Offs**: Conventional speech-to-text tools either mandate downloading multi-gigabyte models upfront or transmit private microphone audio to remote cloud APIs.
4. **Browser Tab Audio Throttling**: Web extensions attempting local audio synthesis suffer from browser background throttling, thread contention on heavy web pages, and synthetic voices lacking neural pitch inflection.

--------------------------------------------------------------------------------

## Goals

*   **Sub-100ms Desktop TTS Latency**: Synthesize and begin playing speech from any highlighted Windows text within 100 milliseconds of hotkey activation using the bundled Paradee-8M ONNX model on a reference baseline CPU (Intel Core i5-8250U / AMD Ryzen 5 3500U or higher with AVX2 enabled).
*   **Modular Base Installer Under 25 MB**: Package the complete core Rust client, GUI, input hooks, and Paradee-8M TTS model in an installer smaller than 25 MB.
*   **On-Demand Chunked STT Delivery**: Provide an in-app download manager for NVIDIA Parakeet-TDT 0.6B (~600 MB on-disk INT8 file) featuring HTTP Range requests, resumable downloads, SHA-256 integrity verification, and explicit disk management.
*   **Universal Input Remapping (1–4 Keys & Side Mouse)**: Allow users to map any reading or dictation action to single keys (`F8`), multi-key chords (`Ctrl+Space`, `Ctrl+Shift+R`), or hardware side mouse buttons (`Mouse 4` / `Mouse 5` / `XButton1` / `XButton2`).
*   **Non-Blocking OS Hook Watchdog Safety**: Execute Windows low-level keyboard and mouse hooks (`WH_KEYBOARD_LL`, `WH_MOUSE_LL`) with asynchronous lock-free queueing to yield within 0.1 milliseconds, preventing Windows hook timeout evictions.
*   **Non-Destructive Clipboard & Unicode Typing**: Preserve all system clipboard formats during selection grabbing, and inject transcribed speech directly into active fields via `SendInput(KEYEVENTF_UNICODE)` without overwriting the clipboard.
*   **Decoupled Web Extension Architecture**: Remove audio synthesis bloat from the Chrome extension; run pure client-side Bionic reading without any background IPC coupling.
*   **Zero Cloud Telemetry**: Guarantee 100% on-device local execution for all text reading, audio inference, and voice dictation.

--------------------------------------------------------------------------------

## Non-Goals

*   **Cloud Audio Fallbacks**: No network-based speech synthesis or cloud transcription APIs will be implemented or queried.
*   **Mandatory Model Downloads**: Users who only require TTS or visual reading will never be prompted or forced to download the STT model weights.
*   **Cross-Platform Parity in v1**: The initial release targets Windows 10 (1809+) and Windows 11 (x64 / ARM64). macOS and Linux ports are deferred.
*   **Arbitrary In-Process Code Injection**: The native application will not inject DLLs into third-party browsers or applications; browser DOM interaction occurs strictly through the official Chrome extension manifest.

--------------------------------------------------------------------------------

## Resolved Architectural Commitments

*   **Resolution 1 (CPU Baseline with Opt-In DirectML)**: CPU inference with multi-threading and AVX2 vectorization is the default verified baseline across all Windows x64/ARM64 systems, guaranteeing functionality on enterprise systems and older integrated graphics (Intel UHD). DirectML GPU acceleration is exposed as an opt-in setting in `SttSettings.execution_provider`.
*   **Resolution 2 (Side Mouse Button Hold Threshold & Process Blacklist)**: To prevent breaking browser and Explorer Back/Forward navigation, side mouse button actions use a 200ms hold threshold: a rapid click (<200ms) generates a synthetic click replay to preserve navigation, whereas holding (>200ms) enters push-to-talk dictation. Additionally, `AppConfig.process_blacklist` suppresses mouse hooking entirely when full-screen games, CAD software, or virtual machines are active.

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

### CUJ 4: On-Demand Model Download, Network Interruption & Resumption
*   **Given**: The user clicks "Download Speech-to-Text Model" in the desktop settings pane.
*   **When**: Network connectivity drops midway through downloading the ~600 MB INT8 file, or the user clicks "Pause".
*   **Then**: The download manager preserves partial byte ranges in `%LOCALAPPDATA%\SpeakThat\models\parakeet-tdt.part`. The UI transitions to a "Paused / Network Error" state with an actionable "Resume" button. Upon reconnecting, the worker sends an HTTP Range request (`bytes=bytes_downloaded-`), completes the download, verifies the SHA-256 hash against the hard-coded checksum, and activates the dictation feature without corrupting storage.

### CUJ 5: Audio Input Device Error & Windows Privacy Restriction Handling
*   **Given**: The user triggers push-to-talk dictation, but no microphone is connected, the device is exclusively claimed by another app, or Windows Microphone Privacy Access is disabled.
*   **When**: The user presses and holds their dictation hotkey.
*   **Then**: The app avoids freezing the hook or UI thread. The Floating Pill HUD immediately displays an amber warning icon with an explanatory badge: *"Microphone unavailable: Check Windows Privacy Settings or audio device"*. No synthetic typing is emitted, and the active foreground window remains unmodified.

### CUJ 6: Unresponsive Target Application & Clipboard Contention Recovery
*   **Given**: The user highlights text in a legacy or busy application that blocks clipboard operations or UI Automation queries.
*   **When**: The user presses the reading hotkey.
*   **Then**: UI Automation queries time out after 50ms, triggering clipboard fallback. If `GetClipboardSequenceNumber` does not advance within the 200ms polling window (5ms, 15ms, 45ms, 100ms intervals), the worker terminates the capture cleanly, restores the previous clipboard state, and pulses a brief "Selection unavailable" notification in the Floating Pill HUD without speaking stale clipboard data.

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
      - SendInput(Ctrl+C) + Backoff                            - Push-to-Talk Gate & Silence Trim
      - Read Selection CF_UNICODETEXT                          - Streaming Acoustic Mel-Filter
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
*   **Watchdog Safety & Synchronous Event Suppression**:
    - Windows enforces `LowLevelHooksTimeout` (typically 200ms; down to 25ms in security-hardened environments). Hook callback functions do zero heap allocations and zero mutex acquisitions.
    - Event suppression in Win32 is strictly synchronous. The hook callback procedure evaluates an `AtomicU32` trigger bitmask directly in the callback within <10ns. If a mapped hotkey or side mouse button (`XButton1` / `XButton2`) matches an active suppression rule, the callback returns `1` immediately to swallow the message at the OS level (preventing unwanted browser Back/Forward navigation).
    - Event notifications are pushed to the worker channel using non-blocking `sender.try_send()` into a `crossbeam::channel::bounded(512)` queue before returning `CallNextHookEx` (or `1`). If the queue is saturated, an atomic overflow counter increments with zero thread blocking.
*   **Chord Matching Engine**: A separate consumer thread tracks key state bitmasks (supporting single keys `F1–F12`, 2–4 key chords `Ctrl+Shift+Alt+Key`, and mouse side buttons `XButton1`/`XButton2`). Upon matching a configured trigger, the consumer dispatches a task message to the appropriate worker.
*   **Shortcut Collision Protection System**:
    - **Hard-Blocked Windows System Shortcuts**: To protect OS stability and user security, critical Windows shortcuts are strictly prevented from being bound in the chord recorder. Attempting to bind these generates an immediate red rejection notice: `Win+L` (Lock), `Ctrl+Alt+Del` (Security), `Win+D` (Desktop), `Win+E` (Explorer), `Alt+F4` (Close), `Ctrl+Shift+Esc` (Task Manager), `Alt+Tab` (Task Switch), `Win+Tab` (Task View), `Win+V` (Clipboard History), `Win+R` (Run), `Win+X` (Power Menu), `Ctrl+C` (Copy), `Ctrl+V` (Paste), `Ctrl+X` (Cut), `Ctrl+Z` (Undo), `Ctrl+A` (Select All).
    - **Soft-Warned Application Shortcuts (MS Office, Browsers, Adobe)**: Common productivity shortcuts may be bound at user discretion, but the UI triggers an amber advisory warning: *"⚠️ Warning: This chord overrides standard shortcuts in Chrome, MS Word, Excel, Acrobat, or Photoshop"*. Catalog includes: `Ctrl+S` (Save), `Ctrl+P` (Print), `Ctrl+F` (Find), `Ctrl+T` (New Tab), `Ctrl+W` (Close Tab), `Ctrl+N` (New Window), `Ctrl+O` (Open), `Ctrl+B` (Bold), `Ctrl+I` (Italic), `Ctrl+U` (Underline), `Alt+Left` / `Alt+Right` (Navigate), `F5` / `Ctrl+R` (Reload).

#### 2.2 Subsystem 2: Text Selection & Clipboard Snapshot (with UI Automation Priority)
*   **Primary Path (Windows UI Automation)**: The worker first queries the foreground window using UI Automation (`IUIAutomation::GetFocusedElement` and `IUIAutomationTextPattern`). If supported by the active application (Word, Edge, Chrome, Notepad, Acrobat, VS Code), selected text is retrieved directly from the element's text pattern in memory without touching the clipboard.
*   **Fallback Path (Clipboard Snapshot with Exclusion Flags)**: When UI Automation is unsupported (legacy GDI or custom canvas controls), the worker falls back to clipboard capture:
    - Opens clipboard via `OpenClipboard(hwnd)` and snapshots all formats (`EnumClipboardFormats`) into `(u32 format_id, Vec<u8> payload)` vectors.
    - Simulates `Ctrl+C` via `SendInput` with exponential backoff (5ms, 15ms, 45ms up to 200ms) watching `GetClipboardSequenceNumber`.
    - **Empty Selection Handling**: If `GetClipboardSequenceNumber` does not advance within the 200ms timeout window (indicating no selectable text was highlighted), the operation aborts immediately. The clipboard formats are restored, no audio is synthesized, and a subtle "No text selected" notice pulses briefly in the Floating Pill HUD to prevent reading stale clipboard content.
    - **Clipboard History Exclusion**: Registers Windows exclusion formats `CanIncludeInClipboardHistory = 0` and `CanUploadToCloudClipboard = 0` to ensure simulated grabs never inject phantom entries into the user's `Win+V` history or cloud clipboard.
    - Extracts `CF_UNICODETEXT` for speech synthesis, then empties and restores all original format buffers.

#### 2.3 Subsystem 3: Paradee-8M ONNX TTS Engine
*   **Model**: Distilled Kokoro architecture (8M parameters, ~8.4 MB INT8 ONNX file).
*   **G2P & Tokenization Pipeline**: Raw Unicode text is first normalized and processed through an embedded Grapheme-to-Phoneme (G2P) phonemizer (`misaki-rs` / embedded English phoneme dictionary) to convert words into Kokoro IPA phoneme tokens, which are mapped to vocabulary IDs for tensor generation.
*   **Inference Execution**: Bound through `ort` (ONNX Runtime Rust bindings) configured with the native CPU Execution Provider, multi-threaded intra-op parallelism, and AVX2/AVX-512 vector acceleration.
*   **Sentence-Streaming Pipeline**: Text is parsed into sentences using punctuation boundaries (`.`, `!`, `?`, `\n`). Sentence 0 phonemes are fed into inference immediately, producing first audio in <80ms. Sentence 1+ is synthesized concurrently in the background while sentence 0 plays through a WASAPI ring buffer (`cpal` / `rodio`).

#### 2.4 Subsystem 4: On-Demand Parakeet-TDT 0.6B STT Engine
*   **Model Architecture**: NVIDIA Fast-Conformer with Token-and-Duration Transducer (TDT) decoding heads, standardized on the single universal **INT8 ONNX graph (~600 MB)** compatible with both DirectML and CPU.
*   **Chunked Resumable Downloader & Remote Endpoints**:
    - Downloaded via `reqwest` with HTTP Range headers (`bytes=start-end`), temporary `.part` file preservation, and SHA-256 verification.
    - **Primary Host**: Hugging Face Hub (`https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3/resolve/main/parakeet-tdt-0.6b-v3-int8.onnx`).
    - **Secondary Mirror**: GitHub Releases release asset CDN mirror (`https://github.com/amzmihon/Speak-That-Windows/releases/download/...`).
    - Stored strictly in `%LOCALAPPDATA%\SpeakThat\models\` to prevent multi-hundred-megabyte network synchronization issues in enterprise roaming profiles (`%APPDATA%`).
*   **Dynamic Model Residency Lifecycle**:
    - To satisfy the <20 MB idle memory NFR, the 600M parameter model is lazy-loaded in the background on the first push-to-talk press or text field focus.
    - If no dictation activity occurs for 5 consecutive minutes, model weights are automatically unloaded from memory, returning process memory to the lightweight baseline.
*   **Audio Capture, Duplex Ducking & Streaming Pre-Inference**:
    - When push-to-talk is depressed, `cpal` opens a 16 kHz mono WASAPI capture stream.
    - **Audio Duplex Arbiter State Machine**:
      1. *Push-to-Talk Depressed*: The capture trigger immediately pauses active TTS playback and preserves the current sentence playback timestamp.
      2. *Push-to-Talk Released*: Dictation completes and characters are injected; after a 300ms post-typing cushion, TTS playback automatically resumes seamlessly from the saved timestamp.
    - Mel-spectrogram features are continuously extracted in chunked streaming passes while the user speaks, ensuring inference is 85–90% complete at key release, cutting post-release latency to <200ms.
*   **Keystroke Typing with Modifier State Cushioning**:
    - Before character streaming begins, `src/input/injector.rs` queries `GetAsyncKeyState` for active modifiers (`VK_CONTROL`, `VK_SHIFT`, `VK_MENU`, `VK_LWIN`, `VK_RWIN`) and emits synthetic `KEYEVENTF_KEYUP` events to prevent dangerous chord collisions (e.g., `Ctrl+A` or `Ctrl+W` in the target window).
    - Verifies `GetForegroundWindow()` matches the target window that held focus at the start of dictation.
    - Injects Unicode characters directly via Win32 `SendInput(KEYEVENTF_UNICODE)` with 1–2ms micro-yields without touching the clipboard.
    - Restores the original modifier key states once text injection completes.

#### 2.5 Subsystem 5: Native GUI & Desktop Bionic Reader
*   **UI Framework & Accessibility**:
    - Native hardware-accelerated immediate-mode GUI (`egui` with `eframe` WGPU/DirectX backend), styled with WinUI 3 Fluent design language (Acrylic blur, rounded geometry, Segoe Fluent typography).
    - Fully integrates `accesskit` and `egui-accesskit` to expose the accessibility tree to Windows Narrator, NVDA, and assistive keyboard navigation.
*   **Floating Pill HUD**:
    - Acrylic/DWM blurred HUD window positioned non-intrusively near the active text selection or screen edge without stealing focus (`WS_EX_NOACTIVATE`).
    - **Dual Mode Visuals**: Displays animated audio playback waveforms during TTS reading; automatically transitions to a live microphone recording state and red recording indicator during push-to-talk dictation.
*   **Bionic Reader Scratchpad**: Distraction-free native reading pane with immediate-mode bionic bolding. Configurable fixation ratio (10%–100%) and stroke weight, with synchronous active-word rhythmic pulsing aligned to TTS speech playback.
*   **Settings & Shortcut Collision Protection**:
    - Visual chord recorder with real-time detection of mouse buttons (`Mouse 4`/`Mouse 5`) and 1–4 key chords.
    - Hard rejection of critical Windows system shortcuts (`Win+L`, `Ctrl+C`, etc.) and amber warnings for common browser/Office/Adobe productivity hotkeys.
    - On-demand STT model download card with progress bar, pause/resume, and SHA-256 verification.
    - 1-click Chrome Extension helper button.

#### 2.6 Subsystem 6: Universal Cross-Browser Extension Suite & Desktop Multi-Browser Manager
*   **Zero IPC / Standalone Architecture**: The browser extension operates entirely client-side with zero audio dependencies and zero background IPC connections to the desktop daemon. It is dedicated strictly to high-performance DOM TreeWalker bionic text bolding, focus dimming, and reader mode.
*   **Unified OS-Level Audio Reading**: When browsing any website across any browser, users do not need in-browser audio buttons. Highlighting text and triggering the global desktop hotkey or side mouse button (`Mouse 4` / `Ctrl+Shift+R`) works identically across Chrome, Edge, Brave, Firefox, Opera, and Vivaldi.
*   **Dual Multi-Browser Packages**:
    - **Chromium Package (`extension/chromium/`)**: Targets Google Chrome, Microsoft Edge, Brave, Opera, Opera GX, Vivaldi, and Arc using standard Manifest V3 with service workers.
    - **Firefox Package (`extension/firefox/`)**: Targets Mozilla Firefox, Floorp, and LibreWolf using Gecko WebExtensions Manifest V3 with `browser_specific_settings.gecko` and background scripts.
*   **Desktop In-App Multi-Browser Detection & 1-Click Installation Manager**:
    - The desktop client automatically scans the system via Windows Registry (`HKLM\SOFTWARE\Clients\StartMenuInternet`) and default filesystem paths to detect installed browsers.
    - The Settings UI provides an interactive **Browser Extensions Card** with tailored 1-click install buttons for each detected browser:
      - **Google Chrome**: 1-click opens `chrome://extensions/` + copies Chromium extension folder path.
      - **Microsoft Edge**: 1-click opens `edge://extensions/` + copies Chromium extension folder path.
      - **Brave Browser**: 1-click opens `brave://extensions/` + copies Chromium extension folder path.
      - **Mozilla Firefox**: 1-click opens `about:debugging#/runtime/this-firefox` + copies Firefox extension folder path (`Load Temporary Add-on`).
      - **Opera / Opera GX**: 1-click opens `opera://extensions/` + copies Chromium extension folder path.
      - **Vivaldi**: 1-click opens `vivaldi://extensions/` + copies Chromium extension folder path.
    - Each button presents a clean 2-step visual prompt: (1) Toggle Developer Mode on; (2) Click "Load unpacked" (or "Load Temporary Add-on") and paste the copied path.

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

pub type InputChord = InputTrigger;

pub enum InputTrigger {
    Key(u16),                          // Virtual-Key code
    Chord(Vec<u16>),                   // 2 to 4 virtual keys
    MouseButton(u32),                  // 4 = XButton1, 5 = XButton2
}

pub struct SttSettings {
    pub model_installed: bool,
    pub model_path: PathBuf,
    pub remote_url: String,            // Primary CDN endpoint (Hugging Face / GitHub release mirror)
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
*   **Rationale**: Defines the root crate, compiler optimizations (`opt-level = 3`, `lto = "thin"`, `codegen-units = 1`), and dependencies (`windows`, `cpal`, `rodio`, `ort`, `egui`, `eframe`, `accesskit`, `egui-accesskit`, `crossbeam`, `reqwest`, `serde`, `serde_json`, `tokio`, `sha2`).

#### 2. `src/main.rs` (Create)
*   **Type / Scope**: Application Entry Point.
*   **Rationale**: Enforces single-instance execution via Win32 `CreateMutexW`, parses CLI flags, initializes file-based tracing (`tracing-appender`), loads configuration, and launches background worker channels and the GUI message loop.

#### 3. `src/config.rs` (Create)
*   **Type / Scope**: Settings Model & Persistence Engine.
*   **Rationale**: Defines strongly typed structures (`AppConfig`, `HotkeyMap`, `SttSettings`, `TtsSettings`) and provides thread-safe, atomic disk persistence to `%LOCALAPPDATA%\SpeakThat\config.json`.

#### 4. `src/input/hook.rs` (Create)
*   **Type / Scope**: Win32 Low-Level Input Hook Service.
*   **Rationale**: Spawns an isolated Win32 thread running `GetMessageW` and registers `WH_KEYBOARD_LL` and `WH_MOUSE_LL` hooks via `SetWindowsHookExW`. Performs synchronous message suppression via atomic bitmask lookup (<10ns) and dispatches raw events using non-blocking `try_send()` into a `crossbeam::channel::bounded` queue.

#### 5. `src/input/catalog.rs` (Create)
*   **Type / Scope**: Reserved Shortcut & Conflict Protection Catalog.
*   **Rationale**: Enforces hard-blocking for Windows critical system hotkeys (`Win+L`, `Ctrl+Alt+Del`, `Win+D`, `Alt+F4`, `Ctrl+C`, etc.) and provides soft-warning heuristics for common browser, Office, and Adobe productivity shortcuts (`Ctrl+S`, `Ctrl+P`, `Ctrl+F`, etc.).

#### 6. `src/input/chord.rs` (Create)
*   **Type / Scope**: Key Chord & Mouse Button Pattern Matcher.
*   **Rationale**: Maintains virtual key bitmasks to match single keys (`F1–F12`), 2-to-4 key combinations (`Ctrl+Shift+Alt+Key`), and side mouse buttons (`XButton1` / `XButton2`), managing push-to-talk press and release transitions against the catalog.

#### 7. `src/input/injector.rs` (Create)
*   **Type / Scope**: Synthetic Keystroke Injector with Modifier Cushioning.
*   **Rationale**: Queries `GetAsyncKeyState` to release active modifiers before typing, verifies foreground window focus, and injects transcribed text directly via Win32 `SendInput(KEYEVENTF_UNICODE)` with 1–2ms micro-yields.

#### 8. `src/clipboard/selection.rs` (Create)
*   **Type / Scope**: Text Selection Capture with UI Automation Priority.
*   **Rationale**: Prioritizes `IUIAutomationTextPattern` to fetch selected text directly from memory without clipboard mutation; falls back to multi-format clipboard snapshotting with `CanIncludeInClipboardHistory = 0` to preserve `Win+V` history.

#### 9. `src/audio/g2p.rs` (Create)
*   **Type / Scope**: Embedded Grapheme-to-Phoneme Phonemizer & Tokenizer.
*   **Rationale**: Normalizes raw Unicode text and maps words into Kokoro/IPA phoneme token sequences using an embedded phoneme dictionary (`misaki-rs`), generating tensor token ID sequences for the Paradee-8M ONNX graph.

#### 10. `src/audio/tts.rs` (Create)
*   **Type / Scope**: Neural Text-to-Speech Engine.
*   **Rationale**: Executes the bundled Paradee-8M ONNX model using `ort` on CPU with AVX2 vectorization, streaming sentence chunks through `rodio` / WASAPI ring buffers for sub-100ms first-audio latency.

#### 11. `src/audio/stt.rs` (Create)
*   **Type / Scope**: Neural Speech-to-Text Dictation Engine.
*   **Rationale**: Manages the NVIDIA Parakeet-TDT 0.6B Fast-Conformer INT8 ONNX graph using `ort` with DirectML GPU acceleration and graceful CPU fallback, decoding Mel-filterbank spectrograms into text.

#### 12. `src/audio/mic.rs` (Create)
*   **Type / Scope**: Audio Input Capture Service.
*   **Rationale**: Configures a 16 kHz 16-bit mono WASAPI microphone stream via `cpal`, accumulating PCM samples into a ring buffer gated by push-to-talk key states with silence trimming.

#### 13. `src/downloader/mod.rs` (Create)
*   **Type / Scope**: Resumable Chunked Download Manager.
*   **Rationale**: Downloads the optional ~600 MB Parakeet-TDT model from Hugging Face / GitHub release asset CDN via `reqwest` with HTTP Range headers (`bytes=start-end`), temporary `.part` file preservation, real-time progress callbacks, and SHA-256 integrity validation.

#### 14. `src/ui/app.rs` (Create)
*   **Type / Scope**: Desktop Main Window & Settings Interface.
*   **Rationale**: Implemented via `egui`/`eframe`, providing an interactive chord recorder, mouse button binder, STT model download card, Bionic scratchpad, and Chrome Extension helper.

#### 15. `src/ui/hud.rs` (Create)
*   **Type / Scope**: Floating Acrylic Pill HUD.
*   **Rationale**: Renders a non-activating (`WS_EX_NOACTIVATE`) floating window with DWM acrylic backdrop, showing live animated audio waveforms, recording indicator, and playback controls without stealing keyboard focus.

#### 16. `src/ui/bionic_renderer.rs` (Create)
*   **Type / Scope**: Hardware-Accelerated Bionic Text View.
*   **Rationale**: Renders imported or pasted text with customizable bionic fixation bolding (10%–100%) and stroke weight, supporting synchronized word highlighting that advances alongside TTS playback.

#### 17. `build.rs` (Create)
*   **Type / Scope**: Windows Build Script.
*   **Rationale**: Embeds application icon resources, DPI awareness manifests, and version metadata into the Windows executable.

#### 18. `src/ui/browser_detect.rs` (Create)
*   **Type / Scope**: Win32 Installed Browser Scanner & Extension Manager.
*   **Rationale**: Scans the Windows Registry (`HKLM\SOFTWARE\Clients\StartMenuInternet`) to detect installed browsers (Chrome, Edge, Brave, Firefox, Opera, Vivaldi), dynamically rendering customized 1-click install cards with appropriate deep links and target paths.

#### 19. Universal Extension Packages (`extension/chromium/` & `extension/firefox/`) (Modified)
*   **Chromium Package (`extension/chromium/`)**: Targets Google Chrome, Microsoft Edge, Brave, Opera, Opera GX, Vivaldi, and Arc with Manifest V3 service worker architecture.
*   **Firefox Package (`extension/firefox/`)**: Targets Mozilla Firefox, Floorp, and LibreWolf with Gecko WebExtensions Manifest V3 and `browser_specific_settings.gecko`.
*   **Shared Codebase**: Removed all internal TTS audio logic; shared clean DOM TreeWalker bionic fixation, focus dimming, and reader mode across all browsers.

#### 20. `README.md` (Modify)
*   **Type / Scope**: Documentation.
*   **Rationale**: Documents the unified native Rust architecture, offline TTS capabilities, on-demand Parakeet-TDT STT installation, universal chord mapping, and multi-browser extension installation across Chrome, Edge, Brave, Firefox, Opera, and Vivaldi.
