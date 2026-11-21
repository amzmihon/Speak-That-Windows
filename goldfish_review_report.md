# Goldfish Annotated Review Report

**Target:** `E:\Speak-That-Windows\docs\designs\unified_accessibility_suite.md` (`Lines 1..292`)

## Prioritized Findings & AI Suggestions

### 1. STT Model Residency Lazy-Loading Race & First-Dictation Latency Spike [`egm-structural`] - Severity: Blocker
*   **Affected Scope:** [unified_accessibility_suite.md#L163-L166](docs/designs/unified_accessibility_suite.md#L163-L166) (`Subsystem 4`)
*   **Discrepancy Description:** Initializing an ONNX session with DirectML/CPU providers, compiling graph execution nodes, and allocating tensor memory takes 500ms to 3,000ms on consumer hardware. Loading on the "first push-to-talk press" directly violates the <200ms latency budget and causes initial speech stutter or dropped phonemes while the user is actively speaking. Furthermore, triggering lazy-loading on "text field focus" requires a global Win32 accessibility hook (`SetWinEventHook` listening for `EVENT_OBJECT_FOCUS`), which is completely omitted from Subsystem 1.
*   **Rationale:** Cold-start graph compilation must never drop user speech or freeze the UI thread.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Pre-buffer incoming PCM audio in a ring buffer immediately upon keypress, display a "Model warming up..." spinner in the HUD during cold-start dictation, and run a low-priority background warm-up session on app launch.
*   ***Proposed Edit:***
    *   Location: Section 2.4 (Dynamic Model Residency Lifecycle)
    *   Change: Specify pre-buffered PCM ring buffer, HUD "Warming up..." state, and background thread pre-allocation on app launch.

---

### 2. Global Side Mouse Button Hi-jacking & Inability to Represent Composite Chords [`egm-design`, `egm-structural`] - Severity: Blocker
*   **Affected Scope:** [unified_accessibility_suite.md#L134-L135](docs/designs/unified_accessibility_suite.md#L134-L135), [unified_accessibility_suite.md#L221-L235](docs/designs/unified_accessibility_suite.md#L221-L235) (`Subsystem 1 & Section 3`)
*   **Discrepancy Description:**
    1. Unconditionally returning `1` for side mouse buttons breaks browser Back/Forward navigation on quick clicks.
    2. The `InputTrigger` enum separates chords from mouse buttons, preventing composite chords like `Ctrl + Mouse 4`.
*   **Rationale:** Side mouse buttons must preserve default browser navigation for clicks while enabling push-to-talk holds and composite modifier chords.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Implement a hold threshold (>200ms enters push-to-talk, <200ms replays synthetic click), add `process_blacklist`, and refactor `InputChord` struct to hold `modifiers: Vec<ModifierKey>`, `trigger: TriggerSource`, and `trigger_mode: TriggerMode`.
*   ***Proposed Edit:***
    *   Location: Section 2.1 & Section 3
    *   Change: Update `InputChord` data model and specify hold-vs-click threshold logic.

---

### 3. UI Automation COM Apartment Threading Hazards & HUD Coordinate Loss [`egm-structural`, `egm-design`] - Severity: Blocker
*   **Affected Scope:** [unified_accessibility_suite.md#L141-L149](docs/designs/unified_accessibility_suite.md#L141-L149), [unified_accessibility_suite.md#L182-L185](docs/designs/unified_accessibility_suite.md#L182-L185) (`Subsystems 2 & 5`)
*   **Discrepancy Description:**
    1. UI Automation requires dedicated STA COM apartment initialization with timeout.
    2. When falling back to `Ctrl+C`, plain text has zero bounding box coordinates, leaving HUD positioning undefined.
*   **Rationale:** Worker threads must not freeze on COM calls, and the HUD must have a deterministic multi-monitor positioning algorithm.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Initialize dedicated STA thread for UI Automation with a 50ms timeout, and define a clear 4-level coordinate fallback hierarchy: (a) UI Automation text bounding rect, (b) Win32 caret pos (`GetGUIThreadInfo`), (c) cursor pos (`GetCursorPos`), (d) primary monitor bottom-right anchor.
*   ***Proposed Edit:***
    *   Location: Section 2.2 & Section 2.5
    *   Change: Add STA COM thread specification and 4-tier coordinate fallback hierarchy.

---

### 4. Missing Negative & Recovery CUJs [`egm-design`] - Severity: Major
*   **Affected Scope:** [unified_accessibility_suite.md#L59-L75](docs/designs/unified_accessibility_suite.md#L59-L75) (`Critical User Journeys`)
*   **Discrepancy Description:** The specification lacks user journeys for network drops during the 600 MB download, microphone disconnected/privacy restrictions, and uncooperative applications blocking clipboard reads.
*   **Rationale:** Error recovery is critical for user trust in assistive software.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Add CUJ 4 (Download Interruption & Resumption), CUJ 5 (Microphone Disconnected / Privacy Denial), and CUJ 6 (Application Contention & Selection Recovery).
*   ***Proposed Edit:***
    *   Location: Section: Critical User Journeys
    *   Change: Append CUJs 4, 5, and 6 detailing user experience and system recovery.

---

### 5. Startling Automatic Audio Resumption Post-Dictation [`egm-design`] - Severity: Major
*   **Affected Scope:** [unified_accessibility_suite.md#L168-L171](docs/designs/unified_accessibility_suite.md#L168-L171) (`Subsystem 4`)
*   **Discrepancy Description:** Automatically resuming speech 300ms after dictation completes causes auditory disorientation and cognitive overload for neurodivergent users who just shifted tasks.
*   **Rationale:** Reading speech should remain paused after dictation unless explicitly unpaused.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Keep TTS playback paused upon dictation completion, display a "Resume [Hotkey]" pill in the HUD, and add an opt-in toggle `auto_resume_after_dictation: bool` (defaulting to `false`).
*   ***Proposed Edit:***
    *   Location: Section 2.4 (Duplex Arbiter State Machine) & Section 3 (`TtsSettings`)
    *   Change: Change default to remain paused, add HUD resume prompt, and expose `auto_resume_after_dictation` setting.

---

### 6. Unresolved Open Questions in Architectural Specification [`egm-structural`, `egm-style`] - Severity: Major
*   **Affected Scope:** [unified_accessibility_suite.md#L52-L56](docs/designs/unified_accessibility_suite.md#L52-L56) (`Open Questions`)
*   **Discrepancy Description:** Open Questions 1 and 2 remain open in a specification marked "Draft Complete".
*   **Rationale:** Engineering requirements must be deterministic before implementation.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Resolve Question 1 (CPU inference baseline with opt-in DirectML GPU acceleration) and Question 2 (`process_blacklist` for games, CAD, and virtual machines).
*   ***Proposed Edit:***
    *   Location: Section: Open Questions
    *   Change: Mark both questions resolved with committed technical decisions.

---

### 7. Win32 `KEYEVENTF_UNICODE` Astral Plane & Surrogate Pair Handling Omission [`egm-style`, `egm-structural`] - Severity: Major
*   **Affected Scope:** [unified_accessibility_suite.md#L172-L176](docs/designs/unified_accessibility_suite.md#L172-L176) (`Subsystem 4`)
*   **Discrepancy Description:** `SendInput(KEYEVENTF_UNICODE)` accepts a 16-bit scan code (`u16`). Characters outside the Basic Multilingual Plane (code points > U+FFFF) will be truncated without UTF-16 surrogate pair splitting.
*   **Rationale:** Parakeet-TDT dictation outputting emojis or extended Unicode must not inject corrupted glyphs.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Explicitly specify encoding via `char::encode_utf16()` and emitting surrogate pairs with corresponding key-up releases.
*   ***Proposed Edit:***
    *   Location: Section 2.4 (Keystroke Typing)
    *   Change: Detail `encode_utf16()` surrogate pair emission in `src/input/injector.rs`.

---

### 8. Under-specified Downloader Lifecycle & UI State Synchronization [`egm-structural`] - Severity: Major
*   **Affected Scope:** [unified_accessibility_suite.md#L158-L162](docs/designs/unified_accessibility_suite.md#L158-L162), [unified_accessibility_suite.md#L236-L243](docs/designs/unified_accessibility_suite.md#L236-L243) (`Subsystem 4 & Section 3`)
*   **Discrepancy Description:** Concurrency and state synchronization between the background download worker and the `egui` UI thread are not defined.
*   **Rationale:** The UI must display accurate progress, speed, ETA, and error states without thread contention.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Formally define `DownloadState` enum and `tokio::sync::watch` channel updates to the settings card.
*   ***Proposed Edit:***
    *   Location: Section 2.4 & Section 3
    *   Change: Add `DownloadState` enum and communication channel specification.

---

### 9. Subjective Promotional Prose Violating Anti-Fluff Standard [`egm-style`] - Severity: Nit
*   **Affected Scope:** Lines 12-16, 20-27 (Overview, The Problem)
*   **Discrepancy Description:** Subjective words ("featherweight", "order-of-magnitude") degrade technical specification rigor.
*   **Rationale:** Maintain objective, empirical plain-English descriptions.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Replace promotional adjectives with concrete numbers and objective terms.
*   ***Proposed Edit:***
    *   Location: Overview and The Problem
    *   Change: Replace with empirical phrasing.

---

### 10. Missing Hardware Reference Baseline for Sub-100ms TTS Latency [`egm-style`] - Severity: Nit
*   **Affected Scope:** Line 32, Line 283 (`Goals & NFRs`)
*   **Discrepancy Description:** Metric "Sub-100ms Desktop TTS Latency" is non-verifiable without designating reference baseline CPU hardware.
*   **Rationale:** Benchmarks require reproducible hardware specifications.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Specify baseline hardware: Intel Core i5-8250U / AMD Ryzen 5 3500U with AVX2.
*   ***Proposed Edit:***
    *   Location: Goals & Performance NFRs
    *   Change: Add reference CPU baseline.

---

### 11. Ambiguity Between On-Disk Model Size and VRAM/RAM Residency [`egm-style`, `egm-structural`] - Severity: Nit
*   **Affected Scope:** Lines 34, 157, 285 (`Goals, Subsystem 4 & NFRs`)
*   **Discrepancy Description:** On-disk file size, working RAM set, and DirectML GPU VRAM allocation are interchanged without clear distinction.
*   **Rationale:** Clear distinction is required for resource planning.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Define: On-Disk File Size (~600 MB), System RAM Working Set (<250 MB), and DirectML VRAM (<1.2 GB during active inference).
*   ***Proposed Edit:***
    *   Location: Goals & Resource Footprint NFR
    *   Change: Explicitly separate the three metrics.

---

### 12. Incomplete Specification of Clipboard Exponential Backoff Cadence [`egm-style`] - Severity: Nit
*   **Affected Scope:** Lines 145-146 (`Subsystem 2`)
*   **Discrepancy Description:** Backoff polling sequence is incomplete and lacks explicit timing primitives.
*   **Rationale:** Prevents lock-step retry loops.
*   ***AI Suggestion:*** PROPOSE FIX
*   ***Justification:*** Specify polling intervals: 5ms, 15ms, 45ms, 100ms (max 200ms) with Win32 waitable timers.
*   ***Proposed Edit:***
    *   Location: Section 2.2
    *   Change: Update backoff interval specification.
