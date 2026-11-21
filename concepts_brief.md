# Unified Windows Accessibility & Reading Suite: SpeakThat + Bionic Reader
## Architectural Concept Brief & Goldfish Swarm Synthesis (Rust / Parakeet-TDT / Rune)

* **Lead Architect:** Abdullah Mohammad Zakaria (@amzmihon)
* **Date:** 2026-11-20
* **Status:** Iteration 3 — Complete Swarm Synthesis & TRIZ Resolution
* **Target Platforms:** Windows 10 (1809+) & Windows 11 (64-bit x64 / ARM64)

---

## 1. Executive Summary & Core Hypothesis

Modern neurodivergent readers (ADHD, dyslexia, executive dysfunction) face severe sensory fragmentation: browser reading tools lack system-wide voice speed, while desktop text-to-speech tools lack visual saccade guidance (Bionic fixation) and tactile voice-input dictation.

**The Unified Suite Hypothesis:**  
Consolidating high-speed offline speech synthesis, local push-to-talk speech-to-text dictation, and real-time visual Bionic reading into a single **native Rust client** delivers an order-of-magnitude reduction in cognitive friction:
1. **Ultra-Low Latency Offline TTS (<100ms CPU):** Bundled distilled Paradee-8M ONNX model delivers immediate sentence-streaming speech directly from any highlighted text.
2. **On-Demand Local STT Dictation:** Dictation powered by **NVIDIA Parakeet-TDT 0.6B** (~600MB int8 / 1.2GB fp16) is decoupled into an optional in-app download, preserving a featherweight ~20MB base installer while providing human-parity local transcription.
3. **Decoupled Standalone Chrome Extension:** The web extension sheds audio synthesis bloat, focusing strictly on high-performance DOM fixation (`TreeWalker`) entirely client-side. System-wide voice synthesis is handled globally by the native desktop app via Windows OS hotkeys and mouse buttons without requiring any browser IPC.
4. **Universal 1-to-4 Key & Hardware Mouse Hooks:** Full global hotkey remapping supporting single keys (`F8`), multi-key chords (`Ctrl+Shift+R`), and hardware side mouse buttons (`Mouse 4` / `Mouse 5` / `XButton1` / `XButton2`) for effortless push-to-talk dictation and reading.
5. **Native Desktop Scratchpad & Reader:** Hardware-accelerated native text reader providing distraction-free reading with live Bionic fixation bolding.

---

## 2. In-Scope Goals vs. Out-of-Scope Non-Goals

### In-Scope Goals
* **Featherweight Core Distribution:** Installer package remains under 25 MB, pre-bundling Paradee 8M TTS. No external runtimes (no Python, no heavy PyInstaller wrappers, no Electron).
* **Chunked Resumable Model Downloader:** In-app download manager for the optional NVIDIA Parakeet-TDT 0.6B model with HTTP Range support, pause/resume, SHA-256 integrity verification, and storage management.
* **Non-Blocking Low-Level OS Hooks:** Asynchronous message queue architecture for `WH_KEYBOARD_LL` and `WH_MOUSE_LL` hooks to guarantee <0.5ms callback times, preventing Windows hook timeout unhooking.
* **Non-Destructive Clipboard & Unicode Typing:** Non-destructive clipboard snapshotting for text selection grab, plus zero-clipboard synthetic typing via `SendInput(KEYEVENTF_UNICODE)` for dictation.
* **Dual-Sensory Visual-Audio Alignment:** Real-time synchronization between speech synthesis word streaming and visual Bionic reading highlights in the desktop reader.
* **Zero-IPC Standalone Extension & In-App Installer Helper:** The Chrome extension operates 100% client-side with zero IPC dependencies; the desktop app provides a 1-click helper to install and open the extension in Chrome.

### Out-of-Scope Non-Goals
* **Cloud Dependence & Telemetry:** All inference (TTS and STT) operates strictly on local CPU/GPU hardware; zero telemetry or cloud audio streaming.
* **Mandatory STT Storage Footprint:** Users wanting only TTS or Bionic reading never incur the 600MB+ storage penalty of the STT weights.
* **Full-Page DOM Mutation Injection:** The native app does not inject arbitrary code into external browser processes; web interactions occur exclusively through the vetted extension manifest.

---

## 3. End-to-End System Architecture

```
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
                            (crossbeam / tokio::sync::mpsc)
                                             │
                 ┌───────────────────────────┴───────────────────────────┐
                 │                                                       │
                 ▼                                                       ▼
      [ Selection Capture Worker ]                             [ STT Dictation Worker ]
      - Snapshot Clipboard Data                                - Stream WASAPI Audio (cpal)
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
                              (egui / WinUI 3 Fluent / Rune)
                                             │
                 ┌───────────────────────────┴───────────────────────────┐
                 │                                                       │
                 ▼                                                       ▼
        [ Floating Pill HUD ]                                  [ Native Bionic Reader ]
        - Animated soundwave                                   - TreeWalker-like text view
        - Pause / Resume / Stop                                - GPU Bionic fixation
        - Acrylic DWM Backdrop                                 - Synchronized word pulse
```

---

## 4. Comprehensive 7-Lens Swarm Evaluation

### 4.1 Lens 1: UX & Interaction Ergonomics (`egm-design`)
* **Side Mouse Button Tactile Feedback:** Using Mouse 4 / Mouse 5 (`XButton1` / `XButton2`) for push-to-talk dictation provides an immediate, zero-friction interaction. However, mouse side buttons are universally bound to "Back" and "Forward" in web browsers and File Explorer. The hook handler must cleanly consume the message (`return 1`) when mapped, while offering an application blacklist/whitelist (e.g. bypass when specific full-screen games are focused).
* **Floating Pill HUD Distraction Budget:** For ADHD users, visual interruptions trigger context switching. The floating HUD must default to a minimal pill style with an automatic fade-out timer, or an optional "stealth/audio-only" mode where playback occurs without taking window focus.
* **Model Download Transparency:** The 600MB+ STT model download must present a dedicated, friendly onboarding card explaining disk space, download speeds, and hardware utilization (DirectML GPU vs CPU), complete with pause/resume and integrity verification.

### 4.2 Lens 2: Systems, Windows OS & Rust Mechanics (`egm-codebase-details`)
* **Hook Timeout Watchdog:** Windows enforces `LowLevelHooksTimeout` (typically 200–300ms, down to 25ms in security-hardened environments). If a hook callback blocks on mutexes or audio initializations, Windows drops the hook silently. The hook callback must strictly push raw `(nCode, wParam, lParam)` structs into a lock-free queue and return `CallNextHookEx` immediately.
* **Clipboard Snapshot Rigor:** Grabbing highlighted text via simulated `Ctrl+C` requires backing up all clipboard formats (DIB, HTML, custom shell formats), not merely `CF_UNICODETEXT`. If an application (e.g. Microsoft Excel) temporarily locks the clipboard, a geometric backoff retry loop (e.g. 5ms, 15ms, 45ms up to 200ms) prevents clipboard access collisions.
* **Direct Unicode Keystroke Injection:** For STT dictation, text output must avoid pasting through the clipboard (`Ctrl+V`), which corrupts the user's copied data. The engine must emit `SendInput` events using `KEYEVENTF_UNICODE`, chunked into natural word boundaries with small micro-delays (1–2ms) to prevent dropped characters in legacy Win32 text fields.

### 4.3 Lens 3: Strategic Horizon & Ecosystem Alignment (`egm-zoom-out`)
* **Local-First Privacy Moat:** Dictation tools (Wispr Flow, Otter, Whisper Cloud) stream sensitive audio to third-party endpoints. SpeakThat’s zero-network, local-only architecture establishes a profound privacy guarantee suitable for legal, healthcare, and enterprise software engineers.
* **Tiered Modular Payload:** Distributing a base ~20MB installer with Paradee 8M TTS gives 95% of users an instant, frictionless download. The optional ~600MB Parakeet-TDT STT package converts high-intent power users without penalizing basic reading users.
* **Extension Synergies:** The ADHD Bionic Reader extension benefits from delegating audio processing to SpeakThat: it bypasses browser audio background throttling, eliminates Web Speech API robotic voices, and unlocks global system-wide hotkeys.

### 4.4 Lens 4: ADHD Cognitive Ergonomics & Comprehension (`egm-comprehension`)
* **Cognitive Chord Friction:** 3-key or 4-key chords (e.g., `Ctrl+Alt+Shift+R`) overload working memory and trigger misfires. The suite must prioritize single-action triggers: holding a side mouse button or a single function key (`F8`).
* **Visual-Auditory Sensory Entrainment:** Playing audio while reading static bionic text can create sensory desynchronization if the speech pace diverges from eye saccades. In the native desktop reader, active word bolding pulses synchronously with Paradee phoneme generation.

### 4.5 Lens 5: Implementation Feasibility & Tech Stack (`egm-implementation-readiness`)
* **Rust GUI Framework:** `egui` with `eframe` or `iced` with Direct3D/WGPU backend. `egui` provides immediate-mode simplicity, sub-5MB binary overhead, and instant 60 FPS rendering of bionic text and audio waveforms.
* **Inference Runtime (`ort`):**
  - Paradee 8M: `ort` CPU Execution Provider with multi-threading and AVX2/AVX-512 vectorization.
  - Parakeet-TDT 0.6B: `ort` with DirectML Execution Provider, enabling hardware acceleration across NVIDIA, AMD, and Intel Iris/Arc GPUs without bulky CUDA dependencies.
* **Audio Capture & Synthesis:** `cpal` for high-fidelity WASAPI loopback and microphone input; `rodio` / `symphonia` for audio streaming and real-time sentence-by-sentence playback.

### 4.6 Lens 6: Structural Architecture & Subsystem Boundaries (`egm-structural`)
* **Process Separation & Fault Isolation:** If the STT inference engine encounters an out-of-memory condition or DirectML device removal, it must fail within an isolated worker thread or sub-process, ensuring the TTS hotkey daemon and desktop UI continue functioning uninterrupted.
* **Standalone Decoupled Boundaries:** The extension and desktop app operate with zero IPC coupling. The extension runs entirely client-side in the browser; the desktop app reads any selected text anywhere in Windows via global OS hooks (`Ctrl+Shift+R` or side mouse button).


### 4.7 Lens 7: Inventive TRIZ Contradictions & Pattern Resolutions (`egm-inventive-catalyst`)

| TRIZ Contradiction | Conflicting Parameters | TRIZ Inventive Principle Applied | Technical Resolution in Suite |
| :--- | :--- | :--- | :--- |
| **Contradiction 1** | STT Accuracy & Model Capability vs Binary Size & Download Speed | **Principle 1: Segmentation** & **Principle 10: Prior Action** | Decouple base installer (~20MB with Paradee 8M) from the large Parakeet-TDT model (~600MB). Provide chunked, resumable on-demand downloading with integrity hash validation. |
| **Contradiction 2** | Deep Universal Input Hooking vs OS Thread Stability & Hook Timeouts | **Principle 2: Taking Out / Extraction** & **Principle 19: Periodic Action** | Separate hook event interception from logic processing. Windows hook procedure executes zero allocations, instantly enqueues raw events to a lock-free ring buffer, and returns immediately. |
| **Contradiction 3** | Dual-Sensory Immersion vs Cognitive Overload & Eye Fatigue | **Principle 5: Merging** & **Principle 28: Mechanics Substitution** | Synchronous Word Pacing: Replace static bionic bolding with rhythmic dynamic fixation highlighting that advances at the exact cadence of TTS audio synthesis. |
| **Contradiction 4** | Web Sandbox Security vs Universal Desktop Hotkeys & Synthesis | **Principle 2: Taking Out / Extraction** | Extract audio completely from the browser sandbox. The native desktop app handles speech synthesis globally at the OS level across all applications; the extension stays 100% lightweight and client-side without any IPC bridges. |

---

## 5. Deduplicated & Prioritized Risk Matrix

### 🔴 Blockers (Must Resolve Before Architecture Finalization)
1. **LowLevelHooksTimeout Window Dropping:**  
   * *Risk:* If any system hook blocks for >25–200ms, Windows permanently evicts the hook without warning.
   * *Resolution:* The hook callback must only perform an atomic write to a lock-free queue (`crossbeam::channel::bounded` or atomic ring buffer) and immediately call `CallNextHookEx`.
2. **Side Mouse Button Interception Collisions (`XButton1` / `XButton2`):**  
   * *Risk:* Consuming side mouse clicks globally breaks default browser Back/Forward navigation.
   * *Resolution:* Make mouse button binding explicitly opt-in with contextual pass-through, customizable whitelist/blacklist for gaming/browser executables, and double-click / hold-to-talk distinction.

### 🟡 Majors (Critical Engineering Considerations)
1. **DirectML Fast-Conformer ONNX Compatibility:**  
   * *Risk:* NVIDIA Parakeet-TDT uses Fast-Conformer architecture with duration predictor heads and blank symbol decoding loops that can exhibit DirectML graph compilation errors.
   * *Resolution:* Validate int8 quantized Parakeet-TDT ONNX graph with DirectML runtime in a standalone spike; implement automatic CPU execution provider fallback if DirectML device initialization fails.
2. **Rich Clipboard Restoration Integrity:**  
   * *Risk:* Restoring only plain text wipes user-copied images, files, or rich text formatting.
   * *Resolution:* Snapshot all clipboard format IDs (`EnumClipboardFormats`) and raw byte payloads, restoring the full multi-format bundle upon reading capture completion.
3. **Resumable Download & Model Storage Management:**  
   * *Risk:* High failure rate on 600MB+ downloads over slow or unstable connections.
   * *Resolution:* Implement chunked range requests (`bytes=start-end`), temporary `.part` file preservation, SHA-256 hash checks, and clear disk space pre-allocation checks.

### 🟢 Nits (Polish & Edge Case Refinements)
1. **Multiple Monitor & DPI Scaling in Floating HUD:**  
   * *Resolution:* Query Windows DWM monitor DPI attributes (`GetDpiForWindow`) to position floating pill smoothly near the active cursor or selection bounding box.
2. **Audio Device Switching During Playback:**  
   * *Resolution:* Listen for Windows `IMMNotificationClient` device change events and seamlessly re-route active audio streams to new default audio endpoints.

---

## 6. Implementation Roadmap & Phased Delivery

```
Phase 1: Rust Core & Low-Level Hooks (Weeks 1-2)
├── SetWindowsHookExW (Keyboard & Mouse 4/5) with lock-free ring buffer
├── Selection grabber with clipboard snapshot & restoration
└── Paradee-8M ONNX CPU inference (<100ms latency validation)

Phase 2: UI Engine & Floating HUD (Weeks 3-4)
├── egui / WinUI 3 Fluent floating pill widget with Acrylic backdrop
├── Native Bionic Reader scratchpad with GPU-accelerated text rendering
└── Keyboard & mouse button shortcut configuration interface

Phase 3: Parakeet-TDT STT & Dictation Engine (Weeks 5-6)
├── Resumable chunked model downloader with SHA-256 verification
├── Audio capture pipeline via cpal (Push-to-talk WASAPI)
├── ort DirectML / CPU inference integration for Parakeet-TDT 0.6B
└── Unicode keystroke injection (SendInput)

Phase 4: Extension Decoupling & Suite Integration (Weeks 7-8)
├── Register Chrome Native Messaging Host in Windows Registry
├── Strip extension audio logic; connect DOM TreeWalker to native host
└── End-to-end stress testing, memory profiling, and release packaging
```

---

## 7. Reviewer Sign-Off Matrix

| Reviewer | Lens | Decision | Sign-off Notes |
| :--- | :--- | :---: | :--- |
| `egm-design` | UX & Ergonomics | **APPROVED** | Tactile push-to-talk ergonomics & HUD distraction mitigations validated. |
| `egm-codebase-details` | Skeptical Rust/OS Engineer | **APPROVED** | Lock-free hook buffering & Unicode SendInput address all Windows API failure points. |
| `egm-zoom-out` | Strategic Architect | **APPROVED** | Tiered download architecture provides optimal adoption and competitive moat. |
| `egm-comprehension` | Cognitive Clarity | **APPROVED** | Simplified single-action triggers eliminate ADHD chord friction. |
| `egm-implementation-readiness` | Implementation Readiness | **APPROVED** | `egui` + `ort` DirectML + `cpal` stack is robust and production-ready. |
| `egm-structural` | Structural Consistency | **APPROVED** | IPC schema and fault isolation boundaries protect application stability. |
| `egm-inventive-catalyst` | Inventive TRIZ Catalyst | **APPROVED** | 4 core contradictions resolved cleanly using TRIZ principles. |
