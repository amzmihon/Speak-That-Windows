# EGM Goldfish Review Report: Initial Zoom Out Review (Stage 5)

**Target:** `E:\Speak-That-Windows\docs\designs\unified_accessibility_suite.md` (`Lines 1-318`)

## Reviewer Status

| Reviewer | Status |
| --- | --- |
| `egm-zoom-out` | completed |
| `egm-inventive-catalyst` | completed |

---

## Executive Summary & Strategic Synthesis

The unified design document successfully establishes a compelling product hypothesis: uniting ultra-fast offline TTS (Paradee-8M ONNX) with typographic bionic fixation and on-demand local STT (NVIDIA Parakeet-TDT 0.6B) in a native Rust architecture. The document reflects thoughtful TRIZ resolutions in installer modularization (Principle 1: Segmentation) and low-level hook extraction (Principle 2: Extraction).

However, rigorous zooming out and inventive contradiction audits reveal two critical architectural blockers and five major systems/ergonomic risks:
1. **Low-Level Hook Suppression Contradiction (Blocker)**: The hook callback cannot asynchronously yield with `CallNextHookEx` while simultaneously delegating synchronous message suppression (`return 1` for mouse side buttons) to a downstream consumer channel. Event suppression in Win32 must be decided synchronously before the hook procedure returns.
2. **Keystroke Injection Modifier State Corruption (Blocker)**: Emitting `SendInput(KEYEVENTF_UNICODE)` for dictation while physical or virtual modifier keys (`Ctrl`, `Alt`, `Shift`) remain active results in catastrophic shortcut collisions (e.g., `Ctrl+A`, `Ctrl+W`) in the foreground target window.
3. **Dead Pause in Batch Dictation & Missing Visual Feedback (Major)**: Deferring all Parakeet-TDT inference until push-to-talk key release creates a 5–15s dead pause on CPU fallback, breaking ADHD working memory flow, while providing no active recording HUD indicator.
4. **Clipboard History (`Win+V`) Pollution (Major)**: Simulating `Ctrl+C` repeatedly pollutes Windows 10/11 Clipboard History with phantom snippets and trips security alarms in protected environments; UI Automation (`IUIAutomationTextPattern`) must be prioritized.
5. **Decoupled Extension Identity & Web Pacing Gap (Major)**: Running an unpacked extension triggers persistent Chrome warnings, while true synchronized visual-audio bionic pacing is omitted from web pages, existing only in the desktop scratchpad.

---

## Prioritized Findings (Blockers -> Major -> Nits)

### 1. Incompatible Hook Architecture: Asynchronous Consumer Cannot Retroactively Suppress Mouse/Keyboard Events - Severity: Blocker
* **Reviewer Lens:** `egm-inventive-catalyst` & `egm-zoom-out`
* **Affected Scope:** Lines 130-135 (`Subsystem 1: Low-Level Input & Hook Dispatcher`)
* **Discrepancy Description**: Direct architectural contradiction between Line 132 and Line 134. Line 132 mandates that hook callbacks perform zero processing, zero allocations, and zero mutex acquisitions, immediately enqueue raw messages into a `crossbeam::channel::bounded(512)` queue, and immediately return `CallNextHookEx`. However, Line 134 states: *"When an XBUTTONDOWN event matches a mapped hotkey, the consumer can optionally suppress the event (return 1 in hook) to prevent browser Back/Forward navigation..."*. In the Win32 low-level hook model (`WH_MOUSE_LL`), event suppression is strictly synchronous: once `CallNextHookEx` is returned by the callback procedure, the event has already been delivered to the OS and active application. An asynchronous consumer thread processing events from a channel cannot retroactively suppress an event that has already been dispatched.
* **Rationale & Recommendation**: Apply **TRIZ Principle 2 (Extraction)** and **Principle 10 (Prior Action)**. Do not defer the suppression decision to the consumer thread. Instead, provide the hook callback procedure with direct, zero-overhead access to an atomic trigger mask or lock-free cache (e.g. `AtomicU32` or `arc_swap`). In the hook callback, perform an atomic bitwise check (<10ns); if a mapped side mouse button is pressed and suppression is active, return `1` immediately from the callback procedure to swallow the message, while still pushing the notification into the worker channel.

---

### 2. Keystroke Injection Modifier State Collision and In-Place Overwrite Risk - Severity: Blocker
* **Reviewer Lens:** `egm-inventive-catalyst`
* **Affected Scope:** Lines 66-70 (`CUJ 2`), Lines 150-152 (`Subsystem 4`), Lines 270-272 (`src/input/injector.rs`)
* **Discrepancy Description**: Dictation push-to-talk allows multi-key chords (e.g. `Ctrl+Space`) or side mouse buttons. When dictation completes, `src/input/injector.rs` uses Win32 `SendInput` with `KEYEVENTF_UNICODE` to type characters into the active foreground window. If the user is still physically holding the `Ctrl` key or if the OS modifier state remains set when injection commences, Windows translates incoming Unicode characters as control chords in the target window (e.g., typing character 'a' with `Ctrl` active triggers `Ctrl+A` [Select All], followed by overwriting the entire document; typing 'w' triggers `Ctrl+W` [Close Tab/Window]). Additionally, there is no verification that the foreground window has not changed during the transcription latency period.
* **Rationale & Recommendation**: Apply **TRIZ Principle 11 (Beforehand Cushioning)**. The keystroke injector must snapshot the current physical modifier state (`GetAsyncKeyState` for `VK_CONTROL`, `VK_SHIFT`, `VK_MENU`, `VK_LWIN`, `VK_RWIN`), emit explicit synthetic `KEYEVENTF_KEYUP` events for any active modifiers before character streaming begins, verify that `GetForegroundWindow()` matches the target window that held focus when push-to-talk was released, and restore modifier states once injection finishes.

---

### 3. Post-Release Batch Latency Stall vs Cognitive Flow: Missing Streaming Inference and Recording HUD - Severity: Major
* **Reviewer Lens:** `egm-zoom-out` & `egm-inventive-catalyst`
* **Affected Scope:** Lines 66-70 (`CUJ 2`), Lines 146-152 (`Subsystem 4`)
* **Discrepancy Description**: CUJ 2 specifies that audio is passively accumulated in a ring buffer while the hotkey is held, and only upon key release is the entire buffer sent to the Parakeet-TDT ONNX graph for Mel-spectrogram extraction, inference, decoding, and typing. For a 15–30 second dictation utterance, a 600M parameter model running on CPU fallback (RTF ~0.5x–1.2x) will incur a 7 to 20 second dead stall after the user releases the button before any text appears. This dead pause breaks ADHD working memory and induces accidental focus switching. Furthermore, unlike TTS which displays an Acrylic Floating HUD (Line 64), the STT journey provides zero visual feedback during push-to-talk recording, leaving the user blind as to whether their microphone is capturing audio.
* **Rationale & Recommendation**: Apply **TRIZ Principle 10 (Prior Action)** and **Principle 23 (Feedback)**:
  1. Implement chunked acoustic feature extraction and partial Fast-Conformer streaming passes during the hold-down duration so that inference is 80–90% complete at the moment of key release, slashing post-release latency to <200ms.
  2. Expand the Floating Pill HUD (`Subsystem 5`) to display an active microphone recording state / live audio wave whenever push-to-talk is active.

---

### 4. Clipboard History (`Win+V`) and Protected App Corruption via Simulated `Ctrl+C` - Severity: Major
* **Reviewer Lens:** `egm-zoom-out`
* **Affected Scope:** Lines 101-105 (`Architecture Diagram`), Lines 136-140 (`Subsystem 2: Text Selection & Clipboard Snapshot`)
* **Discrepancy Description**: The design relies exclusively on simulating `Ctrl+C`, reading `CF_UNICODETEXT`, and restoring prior formats. In Windows 10/11, the native Clipboard History service (`Win+V`) and cloud clipboard listeners intercept all clipboard mutations. Executing `Ctrl+C` followed by `EmptyClipboard` and format restoration injects multiple phantom entries into the user's persistent clipboard history on every single read action. Additionally, in terminal emulators, code editors, or enterprise DLP-restricted applications, sending `Ctrl+C` triggers SIGINT signal interruptions, selection clearing, or enterprise compliance security alerts.
* **Rationale & Recommendation**: Apply **TRIZ Principle 28 (Mechanics Substitution)**. Prioritize Windows UI Automation (`IUIAutomationTextPattern` / `GetFocusedElement`) to retrieve selected text directly from the focused UI element's text pattern without touching the clipboard. Only fall back to `SendInput(Ctrl+C)` when UI Automation is unsupported. When the clipboard fallback is used, register and attach the Windows exclusion formats `CanIncludeInClipboardHistory = 0` and `CanUploadToCloudClipboard = 0` to prevent polluting the user's `Win+V` history.

---

### 5. Extension "Unified Suite" Disconnect, Unpacked Developer Warnings, and Synchronization Gaps - Severity: Major
* **Reviewer Lens:** `egm-zoom-out`
* **Affected Scope:** Lines 159-163 (`Subsystem 6`), Lines 216-220 (`Alternative D`), Lines 309-315 (`Chrome Extension Files`)
* **Discrepancy Description**: Strategic and product abstraction boundary gap. The design document decouples the Chrome extension completely (zero IPC, zero communication), stripping all audio logic and leaving it as a standalone unpacked extension. The only integration is an in-app button that opens `chrome://extensions` and Windows File Explorer. Consequently:
  1. Running an unpacked extension in Chrome triggers an obtrusive, persistent "Disable developer mode extensions" warning banner on every browser startup, creating high cognitive annoyance for neurodivergent users.
  2. The core feature of the suite—"Dual-Sensory Visual-Audio Alignment" (bionic text pacing synchronized with speech)—is completely missing on the web, available only if users copy-paste web text into the native desktop scratchpad.
* **Rationale & Recommendation**: Re-evaluate the product abstraction boundary. Either clearly scope the Chrome extension in the documentation as an independent companion utility with a clear roadmap for Chrome Web Store publishing (to eliminate the developer mode warning), or provide a lightweight, non-invasive protocol/URI bridge (or native messaging manifest) that allows web users to trigger synchronized reader mode directly from the browser without manual copy-paste friction.

---

### 6. Memory Footprint Contradiction & Undefined STT Model Residency Lifecycle - Severity: Major
* **Reviewer Lens:** `egm-inventive-catalyst` & `egm-zoom-out`
* **Affected Scope:** Lines 189-195 (`SttSettings`), Lines 237-238 (`Resource Footprint`), Lines 281-284 (`src/audio/stt.rs`)
* **Discrepancy Description**: The NFR states: *"Idle memory consumption remains under 20 MB... peak memory during TTS playback remains under 60 MB. When Parakeet-TDT STT is active, memory remains under 1.2 GB."* However, the design nowhere defines the memory residency lifecycle of the 600M parameter Parakeet-TDT model. If loaded at startup, idle memory immediately inflates to ~1.2 GB, violating the <20 MB idle NFR. If loaded synchronously on the first push-to-talk press, the user experiences a 2–4 second initialization stall before recording can begin.
* **Rationale & Recommendation**: Apply **TRIZ Principle 15 (Dynamism)**. Explicitly specify an on-demand dynamic lifecycle: lazy-load the DirectML/CPU session in the background when the user first focuses a text input field or toggles dictation, and automatically unload the model weights after an idle period (e.g. 5–10 minutes without dictation activity) to return the process to its <20 MB baseline footprint.

---

### 7. Audio Concurrency & Acoustic Feedback: Missing Duplex Ducking Between TTS and STT - Severity: Major
* **Reviewer Lens:** `egm-inventive-catalyst`
* **Affected Scope:** Lines 141-152 (`Subsystems 3 & 4`), Lines 277-288 (`src/audio/tts.rs` & `src/audio/mic.rs`)
* **Discrepancy Description**: The design treats TTS playback and STT microphone capture as completely isolated parallel workers. If a user triggers push-to-talk dictation while TTS audio is playing through the system speakers, the microphone capture stream (`cpal`) captures the speaker output. Parakeet-TDT will transcribe the suite's own synthetic speech alongside the user's voice, resulting in severe transcription corruption and acoustic feedback.
* **Rationale & Recommendation**: Apply **TRIZ Principle 5 (Merging - Coordination of Actions)**. Introduce an audio arbiter channel between the TTS engine and the STT capture service. Activating push-to-talk must immediately duck (attenuate by -24dB) or pause the active WASAPI playback stream, resuming or restoring playback volume cleanly upon key release.

---

### 8. Missing Screen Reader Accessibility (UI Automation / AccessKit) in `egui` - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out`
* **Affected Scope:** Line 117, Lines 154-158 (`Subsystem 5`), Lines 293-296 (`src/ui/app.rs`)
* **Discrepancy Description**: The design specifies `egui` for the GUI. `egui` is an immediate-mode GPU renderer that does not expose native Windows UI Automation (UIA) or MSAA accessibility trees by default. An accessibility tool whose settings and HUD cannot be navigated by Windows Narrator or assistive keyboard navigation is a noticeable ergonomic oversight.
* **Rationale & Recommendation**: Explicitly include `accesskit` and `egui-accesskit` in `Cargo.toml` and `src/ui/app.rs` to expose the UI tree to Windows accessibility clients.

---

### 9. Roaming `%APPDATA%` vs Local `%LOCALAPPDATA%` for Large Models - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out`
* **Affected Scope:** Line 260 (`src/config.rs`), Lines 289-292 (`src/downloader/mod.rs`)
* **Discrepancy Description**: Line 260 specifies `%APPDATA%\SpeakThat\config.json`. The design does not specify the download destination directory for the 600MB–1.2GB Parakeet-TDT model. In enterprise Windows domain environments, `%APPDATA%` (Roaming) is synchronized across domain controllers during login/logout, which causes network timeouts and IT policy violations when storing multi-hundred-megabyte binary models.
* **Rationale & Recommendation**: Models must strictly be downloaded to `%LOCALAPPDATA%\SpeakThat\models\`, while user configuration json may remain in `%LOCALAPPDATA%\SpeakThat\` or `%APPDATA%\SpeakThat\`.

---

### 10. Bounded Queue Blocking Hazard in Low-Level Hook Callback - Severity: Nit
* **Reviewer Lens:** `egm-inventive-catalyst`
* **Affected Scope:** Line 96, Line 132 (`Subsystem 1`)
* **Discrepancy Description**: The hook callback sends events to `crossbeam::channel::bounded(512)`. If the consumer thread stalls and the channel fills, standard `sender.send()` would block the hook callback thread, immediately tripping Windows `LowLevelHooksTimeout` and causing hook unhooking.
* **Rationale & Recommendation**: The hook callback must strictly use `sender.try_send()`. If the queue is full, increment an atomic overflow counter and immediately return `CallNextHookEx`, ensuring zero possibility of thread blocking.

---

### 11. Ambiguous Framework Naming: `egui / WinUI 3 Fluent` - Severity: Nit
* **Reviewer Lens:** `egm-zoom-out`
* **Affected Scope:** Line 117 (`Architecture Diagram`), Line 154
* **Discrepancy Description**: Line 117 labels the GUI layer `(egui / WinUI 3 Fluent)`. `WinUI 3` is Microsoft's heavyweight XAML framework requiring the Windows App SDK, whereas `egui` is a lightweight Rust immediate-mode renderer. Combining them in a slash notation creates architectural ambiguity.
* **Rationale & Recommendation**: Standardize the wording to: *"Immediate-mode GUI (`egui`) styled with WinUI 3 Fluent design language (Acrylic, rounded geometry, Segoe Fluent typography)"*.
