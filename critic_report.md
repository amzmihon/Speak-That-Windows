# EGM Goldfish Review Report: Feature Specification Critic Review (Stage 7)

**Target:** `E:\Speak-That-Windows\docs\designs\unified_accessibility_suite.md` (`Lines 1..292`)  
**Goldfish Context:** `E:\Speak-That-Windows\concepts_brief.md`  
**Applied Standard:** `resources/document_standards/feature-spec-standard.md` (CUJ completeness, boundary integrity, structural hierarchy, anti-fluff style)

## Reviewer Status

| Reviewer | Status |
| --- | --- |
| `egm-design` | completed |
| `egm-structural` | completed |
| `egm-style` | completed |

---

## Executive Summary & Strategic Synthesis

The Critic Review evaluates the feature specification scope against system boundaries, user journeys, interaction ergonomics, and structural rigor. While the design articulates an ambitious local-first architecture, 12 actionable findings were identified across the three lenses:
*   🔴 **3 Blockers**: STT lazy-loading cold start race, side mouse button hi-jacking without click vs hold distinction, and UI Automation COM apartment threading / coordinate loss.
*   🟡 **5 Majors**: Missing error/recovery CUJs, startling automatic audio resumption after dictation, unresolved Open Questions, UTF-16 surrogate pair omission in `KEYEVENTF_UNICODE`, and under-specified download manager state synchronization.
*   🟢 **4 Nits**: Hyperbolic style phrasing, benchmark hardware reference, RAM vs VRAM residency ambiguity, and exact clipboard retry sequence.

---

## Prioritized Findings (Blockers -> Major -> Nits)

### 1. STT Model Residency Lazy-Loading Race & First-Dictation Latency Spike - Severity: Blocker
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** Lines 163-166 (Section 2.4: Dynamic Model Residency Lifecycle)
* **Discrepancy Description**: Initializing an ONNX session with DirectML/CPU providers, compiling graph execution nodes, and allocating tensor memory takes 500ms to 3,000ms on consumer hardware. Loading on the "first push-to-talk press" directly violates the <200ms latency budget and causes initial speech stutter or dropped phonemes while the user is actively speaking. Furthermore, triggering lazy-loading on "text field focus" requires a global Win32 accessibility hook (`SetWinEventHook` listening for `EVENT_OBJECT_FOCUS`), which is completely omitted from Subsystem 1.
* **Rationale & Recommendation**: 
  1. Specify the focus-detection mechanism using `SetWinEventHook` in Subsystem 1 or introduce a background warm-up daemon on app launch that pre-allocates the ONNX session into low-priority memory.
  2. If loaded on demand, buffer incoming PCM audio in a ring buffer with an explicit visual "Model warming up..." spinner in the HUD during cold-start dictation, preventing dropped audio or hung UI threads.
  3. Formally specify the eviction and warm-up state transitions in the architecture.

---

### 2. Global Side Mouse Button Hi-jacking & Inability to Represent Composite Chords - Severity: Blocker
* **Reviewer Lens:** `egm-design`, `egm-structural`
* **Affected Scope:** Lines 134-135, 221-235 (Section 2.1 & Section 3: Data Structures)
* **Discrepancy Description**:
  1. The hook procedure unconditionally swallows side mouse clicks (`return 1` for `XButton1`/`XButton2` matching an active rule) without distinguishing between a rapid click (navigation intent) and a sustained press/hold (dictation intent), and without implementing the application blacklist/whitelist raised in Open Question 2. This globally breaks standard browser and File Explorer Back/Forward navigation across the entire operating system whenever side mouse buttons are mapped.
  2. In Section 3, `InputTrigger` is defined as an enum separating `Chord(Vec<u16>)` from `MouseButton(u32)`. This data structure makes it impossible to define composite chords that combine modifiers and mouse buttons (e.g., `Ctrl + Mouse 4` or `Shift + Mouse 5`), directly contradicting Section 2.1 and Section 2.5.
* **Rationale & Recommendation**:
  1. Redesign `InputChord` to support composite modifiers and trigger modes:
     ```rust
     pub struct InputChord {
         pub modifiers: Vec<ModifierKey>,
         pub trigger: TriggerSource,      // Key(u16) or MouseButton(u32)
         pub trigger_mode: TriggerMode,   // Press, Hold(Duration), Click
     }
     ```
  2. Implement a timer-based threshold (e.g., >200ms hold enters push-to-talk, whereas a <200ms click releases and replays synthetic `XButton` click to preserve Back/Forward navigation), or enforce a foreground process whitelist/blacklist map in `AppConfig`.

---

### 3. UI Automation COM Apartment Threading Hazards & HUD Coordinate Loss - Severity: Blocker
* **Reviewer Lens:** `egm-structural`, `egm-design`
* **Affected Scope:** Lines 141-149, 182-185 (Section 2.2 & Section 2.5)
* **Discrepancy Description**:
  1. Subsystem 2 specifies querying Windows UI Automation (`IUIAutomation::GetFocusedElement` and `IUIAutomationTextPattern`) on the selection capture worker thread. Windows UI Automation requires explicit COM apartment initialization via `CoInitializeEx`. Using UI Automation on MTA worker threads without proper message pumping or apartment marshaling causes hangs or `RPC_E_WRONG_THREAD` errors with legacy GDI / Win32 apps.
  2. Subsystem 5 specifies that the Floating Pill HUD is "positioned non-intrusively near the active text selection or screen edge". When UI Automation fails and the worker falls back to clipboard capture (`SendInput(Ctrl+C)`), the application receives only plain text (`CF_UNICODETEXT`) and has zero bounding box coordinates for where the text was highlighted on screen. The spec provides no fallback positioning algorithm or multi-monitor bounding box resolution logic for this primary fallback path.
* **Rationale & Recommendation**:
  1. Mandate dedicated STA/MTA worker initialization for the UI Automation worker and specify a strict timeout (e.g., 50ms) before falling back to clipboard capture.
  2. Provide an explicit coordinate fallback hierarchy for the Floating Pill HUD: (a) UI Automation bounding rect if available; (b) Win32 `GetCaretPos` / `GetGUIThreadInfo`; (c) current mouse cursor position via `GetCursorPos`; (d) primary/active monitor bottom-right anchor.

---

### 4. Missing Negative & Recovery CUJs (Model Downloader Failure & Mic Errors) - Severity: Major
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** Lines 59-75 (Section: Critical User Journeys)
* **Discrepancy Description**: The specification defines only 3 happy-path CUJs. It completely lacks CUJs for critical error states, user onboarding, and recovery workflows:
  1. *Downloader Failure CUJ*: Downloading a ~600 MB model from Hugging Face or GitHub CDN over unstable networks can fail, timeout, or fail SHA-256 validation. There is no journey describing how download errors are communicated to the user, how partial downloads (`.part`) are resumed, or how corrupted files are pruned.
  2. *Audio Hardware Failure CUJ*: When push-to-talk is pressed, if the default microphone is disconnected, in exclusive use by another application, or denied by Windows Privacy Settings, the spec does not describe the visual/audio error state in the Floating HUD.
  3. *Empty Selection & Timeout CUJ*: While Section 2.2 mentions a brief HUD pulse on empty selection, no formal CUJ specifies user perception, HUD feedback duration, or recovery when an application blocks `Ctrl+C`.
* **Rationale & Recommendation**: Expand the CUJ section to include:
  - `CUJ 4: On-Demand Model Download, Network Interruption & Resumption`
  - `CUJ 5: Audio Input Device Error & Windows Privacy Restriction Handling`
  - `CUJ 6: Unresponsive Target Application & Clipboard Contention Recovery`

---

### 5. Startling Automatic Audio Resumption Post-Dictation - Severity: Major
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** Lines 168-171 (Section 2.4: Audio Duplex Arbiter State Machine)
* **Discrepancy Description**: The Audio Duplex Arbiter specifies: "Push-to-Talk Released: Dictation completes and characters are injected; after a 300ms post-typing cushion, TTS playback automatically resumes seamlessly from the saved timestamp." For neurodivergent users (particularly those with ADHD or auditory processing sensitivities), having voice speech suddenly resume playing 300ms after dictating a thought creates auditory disorientation and cognitive overload. The user likely spoke a response to someone or shifted task context, meaning resuming background reading is jarring and unwanted in most dictation scenarios.
* **Rationale & Recommendation**: Change the default duplex behavior to keep TTS playback paused upon dictation completion, with an audible subtle chime and a visible "Resume [Chord]" prompt in the Floating HUD. Provide an explicit user toggle in `TtsSettings`: `auto_resume_after_dictation: bool` (defaulting to `false`).

---

### 6. Unresolved Open Questions in Architectural Specification - Severity: Major
* **Reviewer Lens:** `egm-structural`, `egm-style`
* **Affected Scope:** Lines 52-56 (Section: Open Questions)
* **Discrepancy Description**: Open Question 1 (DirectML vs CPU for Parakeet-TDT) and Open Question 2 (Side Mouse Button Exclusions & Process Blacklist) remain unresolved in the body of a document marked "Status: In Review (Draft Complete)". Downstream implementation cannot deterministically build the configuration schema or hook callback logic while these architectural questions remain uncommitted.
* **Rationale & Recommendation**: Resolve both questions directly into the specification:
  1. *Question 1 Resolution*: Standardize on CPU inference as the default verified baseline across all Windows x64/ARM64 systems, with DirectML as an opt-in GPU acceleration setting in `SttSettings`.
  2. *Question 2 Resolution*: Add `process_blacklist: Vec<String>` to `HotkeyMap` / `AppConfig` initialized with standard high-priority targets (games, CAD software, virtual machines), and implement foreground window check (`GetWindowThreadProcessId` + `QueryFullProcessImageNameW`).

---

### 7. Win32 `KEYEVENTF_UNICODE` Astral Plane & Surrogate Pair Handling Omission - Severity: Major
* **Reviewer Lens:** `egm-style`, `egm-structural`
* **Affected Scope:** Lines 172-176 (Section 2.4: Keystroke Typing with Modifier State Cushioning)
* **Discrepancy Description**: The specification mandates injecting Unicode characters via Win32 `SendInput(KEYEVENTF_UNICODE)`. However, Win32 `KEYEVENTF_UNICODE` takes a `u16` (`wScan`), representing UTF-16 code units. If Parakeet-TDT transcribes characters outside the Basic Multilingual Plane (BMP, code points > U+FFFF, such as emojis, specialized symbols, or extended character sets), passing a raw 32-bit `char` will truncate the data, injecting invalid or garbled glyphs. The spec fails to specify UTF-16 surrogate pair splitting (high and low surrogate `KEYEVENTF_UNICODE` pairs) and corresponding key-up releases.
* **Rationale & Recommendation**: Specify in Section 2.4 that `src/input/injector.rs` encodes Unicode scalar values into UTF-16 code units via `char::encode_utf16()`. For each `u16` unit, emit a `KEYEVENTF_UNICODE` down event followed by a `KEYEVENTF_KEYUP | KEYEVENTF_UNICODE` up event.

---

### 8. Under-specified Downloader Lifecycle & UI State Synchronization - Severity: Major
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** Lines 158-162, 236-243 (Section 2.4 & Section 3: Data Structures)
* **Discrepancy Description**: Subsystem 4 specifies chunked HTTP range requests and SHA-256 checks, but fails to define the concurrency and state management architecture between the downloader thread and the `egui` UI thread. There is no data structure or channel protocol defined for download state updates (bytes received, total bytes, download speed, SHA-256 verification status, pause/resume commands, cancellation). Furthermore, `SttSettings` only stores `model_installed: bool` and static paths, lacking runtime persistence for partially downloaded byte ranges.
* **Rationale & Recommendation**:
  1. Define a concrete download state enum:
     ```rust
     pub enum DownloadState {
         NotInstalled,
         Downloading { progress: f32, bytes_downloaded: u64, total_bytes: u64, speed_bps: u64 },
         Paused { bytes_downloaded: u64, total_bytes: u64 },
         VerifyingHash,
         Installed,
         Error(DownloadError),
     }
     ```
  2. Specify the communication channel (`crossbeam::channel` or `tokio::sync::watch`) between `src/downloader/mod.rs` and the `egui` settings card.

---

### 9. Subjective Promotional Prose Violating Anti-Fluff Standard - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 12-16, 20-27, 257-258, 272 (Overview, The Problem, Alternatives Considered)
* **Discrepancy Description**: The specification contains promotional and hyperbolic phrasing that degrades document rigor: e.g., "order-of-magnitude reduction in cognitive friction", "featherweight base installer", "blazing startup", "robotic, inconsistent system synthetic voices".
* **Rationale & Recommendation**: Replace subjective phrasing with objective, empirical descriptions (e.g., replace "featherweight" with "<25 MB binary installer"; replace "robotic voices" with "synthesizers lacking neural pitch inflection").

---

### 10. Missing Hardware Reference Baseline for Sub-100ms TTS Latency - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 32, 283-284 (Goals & Non-Functional Requirements)
* **Discrepancy Description**: The performance goal mandates "Sub-100ms Desktop TTS Latency" on "standard x64 CPU architectures". This metric is non-verifiable without designating a minimum hardware specification (e.g., number of logical cores, base clock frequency, and AVX2 instruction availability).
* **Rationale & Recommendation**: Clarify the target benchmark baseline: e.g., "Synthesize first sentence audio in <100ms on a reference baseline Intel Core i5-8250U / AMD Ryzen 5 3500U or higher with AVX2 support enabled."

---

### 11. Ambiguity Between On-Disk Model Size and VRAM/RAM Residency - Severity: Nit
* **Reviewer Lens:** `egm-style`, `egm-structural`
* **Affected Scope:** Lines 34, 157, 285 (Goals, Subsystem 4 & NFRs)
* **Discrepancy Description**: Section 2.4 states the INT8 ONNX graph is "~600 MB", whereas the NFR section states memory remains "under 1.2 GB (INT8 DirectML)". The document frequently interchanges on-disk file size, working RAM set, and DirectML GPU VRAM allocation without distinguishing between model weights and intermediate activation buffers.
* **Rationale & Recommendation**: Specify distinct resource constraints: (1) On-Disk File Size (~600 MB); (2) Working Set System RAM (<250 MB); (3) GPU Dedicated/Shared VRAM (<1.2 GB during active inference).

---

### 12. Incomplete Specification of Clipboard Exponential Backoff Cadence - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 145-146 (Section 2.2: Subsystem 2)
* **Discrepancy Description**: The clipboard polling mechanism specifies "exponential backoff (5ms, 15ms, 45ms up to 200ms) watching `GetClipboardSequenceNumber`". The sequence 5, 15, 45, 135 exceeds 200ms in 4 iterations. It does not state whether thread sleep or asynchronous event timers are used, nor does it specify random jitter to prevent lock-step retry contention with other clipboard utilities.
* **Rationale & Recommendation**: Formulate the retry policy explicitly: "Poll `GetClipboardSequenceNumber` with intervals of 5ms, 15ms, 45ms, and 100ms (maximum cumulative deadline: 200ms) using `tokio::time::sleep` or high-resolution Win32 waitable timers, aborting immediately upon sequence advance."
