# Stage 6: Comprehension Test Report

**Target Document:** `E:\Speak-That-Windows\docs\designs\unified_accessibility_suite.md`  
**Active Scopes:** FeatureRange: Lines 1..271 | DetailedRange: Lines 272..349  
**Persona:** egm-comprehension (Naive Reader, zero assumed tribal knowledge)

---

### Paraphrase

#### What this proposes
This document proposes building a unified native Windows desktop accessibility application written in Rust (`egui`/WinUI 3 styling) that combines local neural text-to-speech reading with hardware-accelerated typographic bionic bolding and an optional on-demand speech-to-text dictation engine. The desktop client uses low-level Windows keyboard and mouse hooks to capture global user hotkeys or side mouse buttons (`XButton1`/`XButton2`), extracts text across any desktop application via Windows UI Automation or a non-destructive clipboard snapshot fallback, and injects transcribed dictation in-place using synthetic Unicode keystrokes. It bundles a compact 8M-parameter Paradee ONNX model for instant offline reading, provides an in-app chunked downloader for an optional 600M-parameter NVIDIA Parakeet-TDT STT model, and strips all audio synthesis dependencies out of the companion Chrome extension so the extension operates purely as a lightweight, client-side DOM bionic reader.

#### How the existing system works, per this document
According to the document, the existing setup consists of two separate, uncoordinated tools: a Python-based desktop text-to-speech application called SpeakThat (using a distilled Kokoro neural model) and a Chrome extension called ADHD Bionic Reader that applies typographic bolding to web pages. Currently, the Chrome extension handles text-to-speech synthesis internally via the Web Speech API and background scripts, resulting in robotic voices, thread contention, and audio throttling when browser tabs run in the background. Meanwhile, the desktop TTS utility lacks visual fixation bolding, has no speech-to-text dictation capabilities, and cannot coordinate input or reading experiences across arbitrary non-browser desktop software like Word, IDEs, or PDF viewers.

---

### Audit Findings

#### Finding 1: Unspecified Parakeet-TDT Download Source and Remote Endpoint
1. **Severity**: Major
2. **Affected Scope**: Section 2.4 (Subsystem 4: On-Demand Parakeet-TDT 0.6B STT Engine, lines 154–158), Section 320–323 (`src/downloader/mod.rs`), and Goal 3 (line 34).
3. **Discrepancy Description & Rationale**: The document specifies in granular detail how the ~600 MB model is downloaded (using `reqwest`, HTTP Range headers for chunked/resumable downloads, `.part` temporary files, and SHA-256 validation) and where it is saved locally (`%LOCALAPPDATA%\SpeakThat\models\`). However, it never states *where* the model is hosted or downloaded from. There is no remote URL, endpoint specification, release asset host (e.g., Hugging Face, GitHub Releases, S3/CDN), or configuration field in `SttSettings` for the remote URL. An engineer implementing `src/downloader/mod.rs` has no way to know where HTTP Range requests must be directed.

#### Finding 2: Undefined / Mismatched Type `InputChord` vs. `InputTrigger` in Configuration Schema
1. **Severity**: Major
2. **Affected Scope**: Section 3 (Data Structures & State Management, lines 193–222).
3. **Discrepancy Description & Rationale**: The configuration schema declares `HotkeyMap` with fields typed as `InputChord`:
   ```rust
   pub struct HotkeyMap {
       pub read_selection: InputChord,
       pub dictation_ptt: InputChord,
       pub toggle_reader: InputChord,
       pub stop_audio: InputChord,
   }
   ```
   Immediately below, the document defines an enum named `InputTrigger`:
   ```rust
   pub enum InputTrigger {
       Key(u16),
       Chord(Vec<u16>),
       MouseButton(u32),
   }
   ```
   `InputChord` is neither defined nor aliased anywhere in the document. A developer reading this code cannot tell whether `InputChord` is an obsolete name for `InputTrigger` or a separate struct wrapping `InputTrigger`.

#### Finding 3: Omission of Text Grapheme-to-Phoneme (G2P) / Tokenization Pipeline for Paradee-8M
1. **Severity**: Major
2. **Affected Scope**: Section 2.3 (Subsystem 3: Paradee-8M ONNX TTS Engine, lines 149–153) and Section 308–311 (`src/audio/tts.rs`).
3. **Discrepancy Description & Rationale**: The document describes splitting text on sentence boundaries (`.`, `!`, `?`, `\n`) and immediately states: *"Sentence 0 is fed into inference immediately, producing first audio in <80ms"*. Kokoro-based neural TTS architectures do not accept raw Unicode text strings as direct tensor inputs; they require a grapheme-to-phoneme (G2P) phonemizer (such as eSpeak-ng, Misaki, or an embedded phoneme map) followed by vocabulary tokenization to generate the input sequence tensor IDs. Omitting the phonemization/tokenization layer entirely is an unstated prerequisite and an unaddressed architectural gap for building `src/audio/tts.rs`.

#### Finding 4: Architectural Discrepancy Regarding "Ring Buffer VAD" in STT Engine
1. **Severity**: Major
2. **Affected Scope**: Section 1 (High-Level System Architecture diagram, line 104) vs. Section 2.4 (Subsystem 4, lines 154–170) and Section 316–319 (`src/audio/mic.rs`).
3. **Discrepancy Description & Rationale**: In the high-level system diagram (line 104), the `STT Dictation Worker` lists:
   - Stream WASAPI Audio (cpal)
   - Push-to-Talk Gate
   - Ring buffer VAD
   - ort DirectML / CPU Inference
   
   However, throughout Subsystem 4, CUJ 2, and `src/audio/mic.rs`, dictation is described strictly as Push-to-Talk (audio capture begins when the hotkey is depressed and ends when the key is released). Voice Activity Detection (VAD) is never mentioned, defined, or explained in any narrative section or file specification. It is unclear whether an actual VAD algorithm (e.g., energy thresholding or Silero VAD) is used to trim audio, or if "Ring buffer VAD" in the diagram is an undefined remnant from an earlier draft.

#### Finding 5: Vague Duplex Arbiter Behavior and Missing Resumption State Machine
1. **Severity**: Major
2. **Affected Scope**: Section 2.4 (Subsystem 4: Audio Capture, Duplex Ducking & Streaming Pre-Inference, line 164).
3. **Discrepancy Description & Rationale**: Line 164 states: *"Audio Duplex Arbiter: The capture trigger immediately ducks active TTS playback volume by -24dB (or pauses playback), preventing the microphone from capturing synthesized speaker output..."*
   - Stating `ducks active TTS playback volume by -24dB (or pauses playback)` is ambiguous and leaves the actual implementation contract unspecified.
   - Crucially, the document omits the return transition: when the user finishes dictation and releases push-to-talk, does TTS resume from the paused timestamp, unduck to 0dB, or abort entirely?
   - The Arbiter component is absent from both the subsystem breakdown and the target files list in Section 272–339.

#### Finding 6: Unclear Chrome Extension Distribution and Unpacked Loading Workflow
1. **Severity**: Major
2. **Affected Scope**: Section 2.6 (Subsystem 6: Decoupled Chrome Extension & In-App Installer Helper, lines 186–190) and Section 340–346 (Chrome Extension Files).
3. **Discrepancy Description & Rationale**: The document explains that the desktop UI includes an "Install Chrome Extension" button that opens `chrome://extensions/` and reveals the extension directory in Windows File Explorer. However, it does not explain how the extension folder (`ADHD_Bionic-Reader Extantion Unpacked Loader`) gets onto the user's system in a production release. Is it extracted by the desktop installer into `%LOCALAPPDATA%` or `Program Files`? Furthermore, Chromium browsers do not permit loading unpacked extensions unless "Developer Mode" is toggled on by the user. Relying on an automated button without explaining the packaging location or guiding the user through Developer Mode creates an unstated workflow prerequisite.

#### Finding 7: Duplicate Item Numbering in Target Implementation Plan
1. **Severity**: Nit
2. **Affected Scope**: Section 272–339 (Detailed Implementation Plan, lines 304 and 308).
3. **Discrepancy Description & Rationale**: Item 8 appears twice in succession:
   - Line 304: `#### 8. src/clipboard/selection.rs (Create)`
   - Line 308: `#### 8. src/audio/tts.rs (Create)`
   Subsequent entries continue from 9 to 17, creating an off-by-one numbering error.

#### Finding 8: Ambiguity in Parakeet-TDT Quantization Distribution (INT8 vs. FP16)
1. **Severity**: Nit
2. **Affected Scope**: Lines 34, 155, 220, and 264.
3. **Discrepancy Description & Rationale**: The document refers to Parakeet-TDT as "~600 MB INT8 / 1.2 GB FP16" (line 34), "~600 MB INT8 ONNX" (line 155), and predicts peak memory under "1.2 GB (INT8 DirectML)" (line 264). It is ambiguous whether the remote host provides an INT8 file, an FP16 file, or both, and whether the downloader dynamically selects the quantization variant based on the chosen execution provider (`ExecutionProviderChoice`). `SttSettings` only exposes `execution_provider`, with no precision or model variant configuration.

#### Finding 9: Unspecified Behavior on Empty Text Selection or Timeout
1. **Severity**: Nit
2. **Affected Scope**: Section 2.2 (Fallback Path, lines 143–148).
3. **Discrepancy Description & Rationale**: Section 2.2 details how clipboard formats are snapshotted, `Ctrl+C` is simulated, and `CF_UNICODETEXT` is extracted. If the user invokes the shortcut when no selectable text is active, `GetClipboardSequenceNumber` will not advance within the 200ms backoff window. The document does not describe what happens on timeout: does the app fail silently, display an acrylic HUD warning, or accidentally read previously copied clipboard text?

#### Finding 10: Extension Directory Name Typo in Scope List
1. **Severity**: Nit
2. **Affected Scope**: Section 340–346 (lines 341, 342, 343, 344, 345).
3. **Discrepancy Description & Rationale**: The directory path is listed as `ADHD_Bionic-Reader Extantion Unpacked Loader/...` ("Extantion" rather than "Extension"). While this may reflect an existing workspace folder name, a naive reader unfamiliar with the repo cannot distinguish whether this is a typographical error in the design document or an intentional legacy path.
