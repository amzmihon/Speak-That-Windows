# SpeakThat + ADHD Bionic Reader Suite — Project Knowledge & Conversation Log

**Workspace:** `E:\Speak-That-Windows`  
**Release:** `v0.2.0` (100% Pure Rust + Native ONNX Runtime, zero Python dependency)  
**Last Updated:** 2026-11-28  

---

## 1. Project Overview

**SpeakThat + ADHD Bionic Reader Suite (v0.2.0)** is a unified, 100% offline-capable Windows accessibility and reading assistant built in pure **Rust** (`speakthat.exe`) alongside **cross-browser extensions** (Chromium & Firefox).

### Core Pillars
1. **Pure-Rust Offline Neural Text-to-Speech (Paradee 8M):**
   - Uses the bundled 8.5 MB quantized ONNX model (`models/paradee_int8.onnx` or `speak_that/model/paradee_int8.onnx`) directly via `ort` (`load-dynamic` + `onnxruntime.dll`) and `rodio` 24 kHz WASAPI audio output (`src/audio/tts.rs`), with embedded compressed US + GB Misaki English G2P lexicons (`assets/misaki_us.tsv.gz`, `assets/misaki_gb.tsv.gz`, `src/audio/g2p.rs`). Zero Python / `.venv` runtime dependencies.
   - Reads highlighted text from any Windows application via global hotkeys (`Ctrl + Space` or `Mouse 4 (Back)`) and stops immediately via `Ctrl + Shift + X`.
2. **On-Demand Offline Speech-to-Text (NVIDIA Parakeet-TDT 0.6B v3):**
   - Optional ~670 MB model downloaded on demand from Hugging Face CDN with live progress tracking (`src/downloader/mod.rs` & `src/ui/dashboard.rs`).
   - Designed for Push-to-Talk dictation (`MouseSide1(Back)` hold or keyboard chord).
3. **Native Windows Bionic Reading & Distraction-Free Reader View:**
   - In-place Unicode bionic text transformation (`Alt + B`) via `src/bionic/engine.rs` and `src/input/injector.rs`.
   - Native `egui` Reader View window (`Alt + R`, `src/ui/reader_view.rs`) supporting Dark, OLED Black, Sepia, and Light themes, font scaling, bionic toggling, and TTS playback.
4. **Cross-Browser Extension (`ADHD_Bionic-Reader/`):**
   - Unpacked Chromium extension (`ADHD_Bionic-Reader/ADHD_Bionic-Reader Extantion Unpacked Loader/`) and Firefox extension (`ADHD_Bionic-Reader/extension_firefox/`).
   - Non-blocking `TreeWalker` + `scheduler.yield()` DOM transformation, shielded `<span data-bionic="1">` wrappers, `DarkReader` visual modes, focus dimming, peripheral breathing border, and multi-theme Reader Mode.
5. **System Integration (`eframe` / `egui` + Win32):**
   - Settings Dashboard (`src/ui/dashboard.rs`) with interactive shortcut/mouse-button chord editor, collision protection (`src/input/catalog.rs`), voice/speed controls, STT model downloader, and browser extension path detector (`src/ui/browser_detect.rs`).
   - Win32 system tray icon (`src/ui/tray.rs`) and global `WH_KEYBOARD_LL` / `WH_MOUSE_LL` hooks (`src/input/hook.rs`).

---

## 2. Chronological Conversation & Development History

| Date (UTC+6) | User Request / Milestone | Outcome |
| :--- | :--- | :--- |
| **2026-11-20** | Installed/checked Antigravity plugins & skills (`modern-web-guidance`, `elephant-goldfish-model`, `logo-design-skill`). | Verified/installed plugins into `~/.gemini/config/plugins/`. |
| **2026-11-20** | *"make brand kit for the plagin i wirking on"* | Created brand brief and visual assets for ADHD Bionic Reader. |
| **2026-11-20** | *"follow The Modern Web Guidance and fix my chrome extantion..."* | Replaced blocking DOM loops with cooperative `scheduler.yield()` chunking, debounced `MutationObserver`, and `TreeWalker`. |
| **2026-11-20** | *"hmmm, the main perpous the bionic reading is not working"* | Replaced non-bolding CSS `::highlight()` approach with direct `<b data-bionic-bold="1">` + `<span data-bionic-rest="1">` DOM wrapping. |
| **2026-11-20** | Proposed merging ADHD Bionic Reader with SpeakThat, adding one-click browser extension setup, and adding `nvidia/parakeet-tdt-0.6b-v3` STT in Rust. | Evaluated `anomalyco/rune`, switched focus to `E:\Speak-That-Windows`, drafted `concepts_brief.md` and `docs/designs/unified_accessibility_suite.md`. |
| **2026-11-20** | Requested optional/on-demand STT download, Rust toolchain setup, and EGM design reviews. | Installed `rustup` (`rustc 1.100.0`, GNU toolchain), ran EGM review stages, and added shortcut collision rules + multi-browser detection to the design. |
| **2026-11-21** | *"whare is the extension file i mean whitch file to load?"* | Clarified loading the folder containing `manifest.json` in `chrome://extensions`. |
| **2026-11-21** | *"it making bold the hole thing... and why you tuch the E:\ADHD_Bionic-Reader\ ... only commit no push"* | Fixed recursive bolding & parent bold inheritance (`font-weight: 400 !important` on rest spans, commit `b907517`); enforced strict `E:\Speak-That-Windows` workspace boundary and local-only commits. |
| **2026-11-21** | *"reader mode only comes in light mode. fix that"* | Added Auto dark-mode detection + Dark, Black, Sepia, and Light themes with floating toolbar (`2cc859a`). |
| **2026-11-21** | *"status to make everything in rust? ... resolve the issue and start the devoloping process."* | Resolved EGM review items and bootstrapped Rust codebase (`e18c1c3`, `9c86f45`). |
| **2026-11-21** | *"status check on tts.rs and stt.rs... wire up real Paradee 8M TTS audio playback... egui system tray, settings dashboard, and floating pill HUD."* | Wired `tts_worker.py` to `speak_that/engine.py` (Paradee 8M) and built `dashboard.rs`, `hud.rs`, `tray.rs` (`82c4493`). |
| **2026-11-21** | *"update the git ignore and do a new commit"* | Updated `.gitignore` for `target/`, `.pdb`, model parts, and packaged extensions (`807f517`). |
| **2026-11-21** | *"check what is messing and what need to be done. make a to-do list and start working on them."* | Built interactive chord/mouse recorder, live STT downloader progress UI, native `ReaderViewWindow`, and Win32 tray menu (`a7495ba`). |
| **2026-11-22** | *"none of the hotkeys work at all... Add INFO-level debug logs... Make the egui Dashboard window open automatically... fix the browser extension path bug"* | Fixed `WH_KEYBOARD_LL` modifier normalization & chord dispatch, moved `eframe::run_native` to main OS thread, added `🔥 [HOTKEY MATCHED]` INFO logs, fixed `find_project_root()` for browser & TTS paths, fixed `tts_worker.py` stdout/stderr IPC isolation, resolved MinGW `libshlwapi.a` linking, and verified visible window (`HWND: 1379582`) + live keystrokes (`b62ef93`). |
| **2026-11-27** | *"make a knoladge.md fale that log all the convertation..."* | Generated this `knowledge.md` reference file in `E:\Speak-That-Windows`. |

---

## 3. High-Level Engineering Reasoning & Key Architectural Decisions

1. **Extension Bionic Bolding (`::highlight()` → Shielded DOM Spans):**  
   CSS `::highlight()` cannot alter `font-weight` in Chromium, and naive `<b>` + sibling text-node splitting caused dynamic pages (like Google Search AI Overview) to inherit bold weights or re-trigger `MutationObserver` loops. Wrapping each transformed node in `<span data-bionic="1">` with explicit `font-weight: 400 !important` on `<span data-bionic-rest="1">` and `MutationObserver` exclusion guards solved both issues.
2. **Main-Thread `eframe` / `winit` Event Loop:**  
   On Windows, `winit` requires its window event loop to be created on the main OS thread. Running `eframe::run_native` inside `std::thread::spawn` prevented reliable startup. Moving `tokio::runtime` into a background multi-thread runtime (`rt.enter()`) while running `eframe::run_native` on `main()` guarantees the Settings Dashboard opens visibly on startup while Win32 hooks and async tasks run concurrently.
3. **Global Hotkey Normalization & Matching:**  
   `WH_KEYBOARD_LL` receives specific left/right virtual key codes (`VK_LCONTROL`, `VK_RCONTROL`, etc.). Filtering out standalone modifier presses (`is_modifier_vk`) and querying `GetAsyncKeyState` across generic and left/right VKs normalizes them into `ModifierKey::{Control, Shift, Alt, Win}`. Order-independent `InputChord::matches` ensures consistent hotkey triggering.
4. **Path Resolution Independent of Working Directory:**  
   Relying on `current_dir()` failed when running `target\debug\speakthat.exe` from `target\debug`. Walking parent directories from `current_exe()` (with `current_dir()` fallback) in `BrowserDetector::find_project_root()` ensures both browser extension folders and `.venv` / `tts_worker.py` resolve reliably.
5. **IPC Stream Isolation in `tts_worker.py`:**  
   `speak_that/engine.py` prints diagnostic logs via `print(..., flush=True)`, which previously collided with `tts_worker.py`'s JSON-over-stdout protocol. Redirecting `sys.stdout` to `sys.stderr` while keeping a dedicated `ipc_stdout` handle protects the JSON stream from corruption and Windows pipe `OSError`s.

---

## 4. Tools & Capabilities Used

During this project, the assistant utilized the following workspace tools and environment capabilities:
- **File & Code Inspection / Editing:** Reading, creating, and patching Rust, Python, JavaScript, HTML, and Markdown files (`read_file`, `write_file`, `edit_file`).
- **Workflow & Subprocess Execution (`run_workflow`):** Running Python automation scripts, `cargo check` / `cargo build`, live Windows executable tests, and `ctypes` Win32 window verification (`FindWindowW` / `IsWindowVisible`).
- **Rust & Windows Toolchain:** `rustc 1.100.0` (`stable-x86_64-pc-windows-gnu`), `cargo`, and MinGW GNU linker (`x86_64-w64-mingw32-gcc` with `libshlwapi.a` resolved).
- **Version Control (`git`):** Local staging, diff inspection, and commits (`git status`, `git diff`, `git log`, `git add`, `git commit`) strictly without pushing.
- **Subagents & Skills:** Coordinated Elephant-Goldfish Model (`egm-*`) review subagents, `modern-web-guidance`, `logo-design`, and `antigravity-guide` / `plugin` skills.

---

## 5. Repository Structure (`E:\Speak-That-Windows`)

```text
E:\Speak-That-Windows\
├── Cargo.toml                  # Rust dependencies (windows 0.58, tokio, reqwest, serde, eframe 0.27, tracing)
├── .gitignore                  # Ignores target/, *.pdb, *.onnx.part, packaged zips/extensions
├── main.py                     # Legacy/reference Python entry point
├── speak_that/                 # Python Paradee 8M engine & bundled ONNX model (paradee_int8.onnx)
├── ADHD_Bionic-Reader/         # Browser extensions
│   ├── ADHD_Bionic-Reader Extantion Unpacked Loader/   # Chromium (Chrome/Edge/Brave/Opera)
│   └── extension_firefox/                              # Firefox
├── docs/designs/               # Unified suite architecture & EGM review reports
└── src/                        # Native Rust client
    ├── main.rs                 # Entry point, Tokio runtime, hotkey event loop, eframe dashboard launch
    ├── config.rs               # AppConfig persistence (AppData\Local\SpeakThat\config.json)
    ├── audio/
    │   ├── mod.rs
    │   ├── tts.rs              # Paradee 8M IPC manager
    │   ├── tts_worker.py       # Python IPC worker wrapping speak_that.engine.TTSEngine
    │   ├── stt.rs              # STT engine state/controller
    │   └── mic.rs              # Push-to-Talk & audio ducking manager
    ├── bionic/
    │   ├── mod.rs
    │   └── engine.rs           # Native Unicode bionic text transformer
    ├── clipboard/
    │   ├── mod.rs
    │   └── selection.rs        # Win32 clipboard & synthetic Ctrl+C selection capture
    ├── downloader/
    │   └── mod.rs              # Resumable Hugging Face CDN downloader for Parakeet-TDT 0.6B v3
    ├── input/
    │   ├── mod.rs
    │   ├── hook.rs             # Win32 WH_KEYBOARD_LL & WH_MOUSE_LL hooks
    │   ├── chord.rs            # InputChord model & order-independent matches()
    │   ├── catalog.rs          # Shortcut collision protection (Allowed / Warning / HardBlocked)
    │   └── injector.rs         # Win32 text injection for bionic replacement
    └── ui/
        ├── mod.rs
        ├── dashboard.rs        # egui Settings Dashboard (Shortcuts, Voice, Bionic, Dictation, Browsers)
        ├── reader_view.rs      # Native egui Distraction-Free Reader window (Alt+R)
        ├── hud.rs              # FloatingPillHud struct (available for HUD integration)
        ├── tray.rs             # Win32 Shell_NotifyIconW system tray & context menu
        └── browser_detect.rs   # Installed browser & extension path detector
```

---

## 6. Recent Git History & Strict Constraints

### Recent Local Commits
- `b62ef93` — `fix(input): wire WH_KEYBOARD_LL modifier normalization, launch egui dashboard on startup, add hotkey logs, and fix extension path`
- `a7495ba` — `feat: add interactive chord recorder, live stt downloader, native reader view, and system tray manager`
- `807f517` — `chore: update .gitignore for rust target artifacts, models, and extensions; update Cargo.lock`
- `82c4493` — `feat(tts): wire real Paradee 8M inference with egui settings dashboard, floating hud, and system tray`
- `9c86f45` — `feat(rust): integrate selection capture, bionic engine, audio pipeline, and hook handlers`
- `b907517` — `fix(bionic): enforce 400 normal weight on unbolded rest-spans to prevent parent bold inheritance on Google search`
- `e18c1c3` — `feat(rust): bootstrap native windows client with chord recorder, collision guards, multi-browser detector, and on-demand model downloader`

### Active Constraints
- **No `git push`:** Only local commits are permitted unless explicitly requested.
- **Workspace Boundary:** All work must remain strictly inside `E:\Speak-That-Windows`.

---

## 7. Known Gaps & Next Milestones
- **`stt.rs` & `mic.rs` Inference/Audio Capture:** `stt.rs` currently manages status and model path alongside `ModelDownloader`, while actual live microphone capture (`mic.rs`) and ONNX Runtime (`ort`) inference for `parakeet-tdt-0.6b-v3.onnx` remain to be wired.
- **`FloatingPillHud` Integration:** `src/ui/hud.rs` is implemented and ready to be wired into live `TtsEngine` playback state updates as an active overlay/viewport.
- **Tray Re-open / Multi-Viewport Behavior:** Right-click tray `IDM_OPEN_DASHBOARD` and `Alt+R` (`ReaderViewWindow`) can be unified under `eframe`'s viewport system (`ctx.show_viewport_immediate`) so multiple windows never conflict with `winit`'s single-event-loop-per-process rule on Windows.

---

## 8. Complete Turn-by-Turn Instructions & Actions Log

Every user instruction from this conversation and the exact actions performed in response:

### Turn 1 (`2026-11-20T11:21:06Z`)
* **User Instruction:**
  > `agy plugin install https://github.com/GoogleChrome/modern-web-guidance`
* **What Was Done:**
  - Verified plugin installation status; confirmed **Modern Web Guidance** was already installed and enabled under `~/.gemini/config/plugins/modern-web-guidance-plugin/`.

### Turn 2 (`2026-11-20T11:24:48Z`)
* **User Instruction:**
  > `agy plugin install https://github.com/google/elephant-goldfish-model`
* **What Was Done:**
  - Located **Elephant-Goldfish Model (`egm`)** in the Agent Marketplace, surfaced the plugin card, and confirmed its installation and activation (`customization://egm`).

### Turn 3 (`2026-11-20T11:33:09Z`)
* **User Instruction:**
  > `https://github.com/kaankiziltug/logo-design-skill.git`  
  > `install this skill on my antigravity`
* **What Was Done:**
  - Cloned and installed the **Logo Design** skill into `~/.gemini/config/plugins/logo-design/`, including the 1,400+ SVG reference library and Python design/audit scripts (`svg_audit.py`, `concept_sheet.py`, `preview_sheet.py`, `presentation_board.py`, `export_variants.py`, `search_library.py`).

### Turn 4 (`2026-11-20T11:42:17Z`)
* **User Instruction:**
  > `make brand kit for the plagin i wirking on. i hope you see the project`
* **What Was Done:**
  - Audited the **ADHD Bionic Reader Extension** project and produced a brand brief targeting crisp 16×16 px, 48×48 px, and 128×128 px legibility.
  - Generated three logo concepts (**Concept A: The Bionic B**, **Concept B: The Guided Saccade**, **Concept C: The Focus Lock**), audited them at 100/100 production readiness, and exported the concept sheet (`concepts.svg` / `concepts.png`).

### Turn 5 (`2026-11-20T12:04:01Z`)
* **User Instruction:**
  > `follow The Modern Web Guidance and fix my chrome extantion that it work properly and make it effecient and that it lage the hole browser and undestand my idiya and consept and make it more batter.`
* **What Was Done:**
  - Diagnosed browser-wide lag: synchronous whole-page string concatenation (`virtualText`), 20k–50k synchronous `Range` allocations, `IntersectionObserver` + `MutationObserver` infinite feedback loops, per-scroll `getBoundingClientRect()` layout thrashing, and `document_start` injection of DarkReader/Readability across all frames.
  - Rewrote `content.js` & `manifest.json` using native C++ `TreeWalker`, 6 ms cooperative task chunking via `scheduler.yield()`, `position: fixed` floating TTS, lazy DarkReader loading (`run_at: "document_idle"`, `all_frames: false`), `Alt+B` / `Alt+R` shortcuts, domain blacklist button, and integrated crisp 16/48/128 px brand icons.

### Turn 6 (`2026-11-20T12:25:44Z`)
* **User Instruction:**
  > `hmmm, the main perpous the bionic reading is not working`
* **What Was Done:**
  - Identified that Chromium's CSS Custom Highlight API (`::highlight()`) strictly forbids/ignores `font-weight: bold` and that an initial-load `needsRehighlight` check skipped transformation on first load.
  - Replaced `::highlight()` with direct atomic TextNode transformation wrapping fixation anchors in `<b>`, paired with `undoBionic()` + `.normalize()` reversibility and guaranteed initial-load/SPA execution.

### Turn 7 (`2026-11-20T13:04:04Z`)
* **User Instruction:**
  > `i think we can marge that with the speak that app and had an option to install the chrome extantion on ther pcs just clicking a button inside the app. and i think you might be able to utilize this for that task "rune = { git = "https://github.com/anomalyco/rune", rev = "<dev rev>" }"`
* **What Was Done:**
  - Explained that `anomalyco/rune` is a `wgpu`/SDF Rust UI framework rather than an installer, and outlined Windows Chrome extension installation paths (External Extensions Registry, 1-click interactive loader, and pre-bundled installer) plus merging SpeakThat + Bionic Reader into a Dual-Coding ADHD Suite.

### Turn 8 (`2026-11-20T13:14:15Z`)
* **User Instruction:**
  > `can you notice taht we have switch the work space?`
* **What Was Done:**
  - Confirmed recognition of the transition to `E:\Speak-That-Windows` (with `ADHD_Bionic-Reader` integrated inside `E:\Speak-That-Windows\ADHD_Bionic-Reader`) and scanned the integrated extension files.

### Turn 9 (`2026-11-20T13:18:47Z`)
* **User Instruction:**
  > `do you undestand the curent project?`
* **What Was Done:**
  - Summarized SpeakThat's offline Paradee 8M ONNX TTS architecture (`engine.py`, `selection.py`, `hotkeys.py`, `hud.py`, `ui.py`, `tray.py`), the integrated Chromium extension, and the unified Dual-Sensory ADHD Suite vision.

### Turn 10 (`2026-11-20T13:30:36Z` & `2026-11-20T13:35:55Z`)
* **User Instruction:**
  > `so speking is common in both project so we can knock this form the extentation app can do that easyli. and we want another thisg that is use https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3 and have audio to text. like this app https://tenerife.mykhaylo.dev/`  
  > `and make the entire thing in rust. with the https://github.com/google/rune`  
  > `and use thouse` *(listed `/egm-bootstrap`, `/egm-brainstorm`, `/egm-draft`, `/egm-drift-report`, `/egm-resolve`, `/egm-review`, `/egm-review-loop`, and EGM reviewer personas)*
* **What Was Done:**
  - Drafted `concepts_brief.md` and `docs/designs/unified_accessibility_suite.md`.
  - Identified hardware/footprint trade-offs for `parakeet-tdt-0.6b-v3`, dictation UX (Tenerife pattern), extension audio decoupling, and missing Rust toolchain.

### Turn 11 (`2026-11-20T14:53:34Z`)
* **User Instruction:**
  > `give option to use that they want to speech-to-text or not and if they want there should be option to download if thaey want and when they want to the speech-to-text they click and download form cdn or github or the huggingface.`  
  > `and the second thing about the hot key is user should have option to chouse there hot key for all the fungtionalaty also one key option for the open the app home page. user can chouse any key combanition ranging to 2 to 4 key. like ctrl + space or ctrl + shift + alt + p. any thing and also have use mouse key if they have multiple fungtion button on there mouse. if mouse conected it should work. if not the keyboard shortcut will always there.`  
  > `the extantion no need to have the audio option. just do the other do the other fungtion. and i am thinking if that can be bring all that fungtion on the native windows as well if possable.`  
  > `setup rust on my pc`
* **What Was Done:**
  - Downloaded `rustup-init.exe`, installed Rust (`rustc 1.100.0`, `cargo 1.100.0`) with the `x86_64-pc-windows-gnu` toolchain.
  - Executed EGM review stages (Stage 5 Zoom Out, Stage 6 Comprehension, Stage 7 Critic) on `docs/designs/unified_accessibility_suite.md`.
  - Added Shortcut Collision Protection (hard-blocked OS shortcuts + soft-warned app shortcuts), synchronous `WH_MOUSE_LL` suppression, modifier-cushioned keystroke injection, UI Automation + clipboard isolation, streaming STT pre-inference, `-24dB` audio ducking, cross-browser extension architecture (Chromium + Firefox), and fixed Google Search dynamic DOM streaming in `content.js`.

### Turn 12 (`2026-11-21T00:08:58Z`)
* **User Instruction:**
  > `whare is the extension file i mean whitch file to load?`
* **What Was Done:**
  - Explained that Chrome/Chromium loads the entire folder containing `manifest.json` via Developer Mode → **Load unpacked** (and Firefox loads `extension_firefox/manifest.json` via `about:debugging`).

### Turn 13 (`2026-11-21T00:17:29Z`) & Turn 14 (`2026-11-21T00:22:47Z`)
* **User Instruction:**
  > `it making bold the hole thing. 1st it bold the what it need to then it make bold the hole thing. fix that and also fix the fix the git and why you tuch the E:\ADHD_Bionic-Reader\ your curent workplace is E:\Speak-That-Windows\ how do i will trust you taht you working on out of your working dir? you done it this E:\Speak-That-Windows\ADHD_Bionic-Reader dir but why also E:\ADHD_Bionic-Reader\ this? now at this point i am bit scare to work with you.`  
  > `only commit no push`
* **What Was Done:**
  - Diagnosed recursive bolding (naked trailing text node re-processed by `MutationObserver` every 150 ms) and parent bold inheritance on Google AI Overview (`font-weight: 500–600`).
  - Encapsulated words in `<span data-bionic="1"><b data-bionic-bold="1">...</b><span data-bionic-rest="1">...</span></span>` with `font-weight: 400 !important` on rest spans and strict observer exclusions.
  - Locked all operations strictly inside `E:\Speak-That-Windows` and committed locally (`710c0a6`, `b907517`) with zero pushes.

### Turn 15 (`2026-11-21T00:29:21Z`)
* **User Instruction:**
  > `looks good. but reader mode only comes in light mode. fix that some people would prafer dark mode so fix that`
* **What Was Done:**
  - Added `Auto` dark-mode detection (`prefers-color-scheme: dark` + extension settings), 4 Reader Mode themes (Dark Slate, OLED Black, Warm Sepia, Light Paper), a floating in-article toolbar (theme switcher, `A-`/`A+` font size 14–32 px, Exit), and Reader Theme radio controls in `popup.html`; committed locally (`2cc859a`).

### Turn 16 (`2026-11-21T00:31:29Z`)
* **User Instruction:**
  > `so what is the status to make everything in rust? and all the things and feature we have discous earlier?`
* **What Was Done:**
  - Reported status of the Rust toolchain, completed Chromium/Firefox extensions, finalized `docs/designs/unified_accessibility_suite.md`, and the 12-feature Rust implementation plan ready for `Cargo.toml` scaffolding.

### Turn 17 (`2026-11-21T00:32:52Z`)
* **User Instruction:**
  > `so resolve the issue and start the devoloping process.`
* **What Was Done:**
  - Resolved EGM review items, initialized `Cargo.toml` and `src/` modules (`config.rs`, `input/`, `bionic/engine.rs`, `clipboard/selection.rs`, `audio/`, `downloader/mod.rs`, `ui/browser_detect.rs`), configured MinGW toolchain/linking, and committed locally (`e18c1c3`, `9c86f45`).

### Turn 18 (`2026-11-21T17:37:21Z`)
* **User Instruction:**
  > `The Chrome extension bolding looks good now. Next, give me a quick status check on tts.rs and stt.rs—are they currently wired to real ONNX inference (Paradee 8M + G2P) or still placeholders? Then, let's build the next phase: wire up real Paradee 8M TTS audio playback so I can highlight text in Notepad, press a hotkey, and actually hear it speak, followed by the egui system tray, settings dashboard, and floating pill HUD.`
* **What Was Done:**
  - Clarified `stt.rs` was a status controller wired to `ModelDownloader`, while wiring `tts.rs` + `src/audio/tts_worker.py` to real Paradee 8M ONNX + Misaki G2P audio playback.
  - Built `src/ui/dashboard.rs` (`egui` Settings Dashboard), `src/ui/hud.rs` (`FloatingPillHud`), and `src/ui/tray.rs` (Win32 `Shell_NotifyIconW` tray); committed locally (`82c4493`).

### Turn 19 (`2026-11-21T17:38:28Z`)
* **User Instruction:**
  > `update the git ignore and do a new commit`
* **What Was Done:**
  - Updated `.gitignore` to ignore `target/`, `*.pdb`, `*.ilk`, `*.obj`, `*.part`, `*.onnx.part`, `*.zip`, `*.crx`, `*.xpi`, and editor/OS files; committed locally (`807f517`).

### Turn 20 (`2026-11-21T17:41:03Z`)
* **User Instruction:**
  > `check what is messing and what need to be done. make a to-do list and start working on them.`
* **What Was Done:**
  - Audited gaps and implemented 4 items: interactive 2–4 key chord & mouse side-button recorder in `dashboard.rs`, live async STT download progress bar & SHA-256 verification in `dashboard.rs`, native distraction-free `ReaderViewWindow` (`Alt+R`) in `reader_view.rs`, and full Win32 tray menu loop in `tray.rs`; compiled cleanly and committed locally (`a7495ba`).

### Turn 21 (`2026-11-22T00:35:06Z`)
* **User Instruction:**
  > `I tested target\debug\speakthat.exe with my old app turned off, and none of the hotkeys work at all (Ctrl+Space, Ctrl+Shift+S, Alt+R all do nothing and print nothing to the terminal).`  
  > `Please debug and fix this properly:`  
  > `Inspect src/input/hook.rs, src/input/chord.rs, and src/main.rs. Check if WH_KEYBOARD_LL is normalizing VK_LCONTROL/VK_RCONTROL, VK_LSHIFT/VK_RSHIFT, and VK_LMENU/VK_RMENU to generic modifiers, and verify the Win32 GetMessageW loop is actually receiving keystrokes.`  
  > `Add INFO-level debug logs whenever a hotkey is matched so I can see it fire in the terminal.`  
  > `Make the egui Dashboard window open automatically when speakthat.exe starts (instead of hiding silently in the background), and verify that eframe actually opens a visible window on Windows.`  
  > `Also fix the browser extension path bug—it's currently looking inside target\debug\ADHD_Bionic-Reader\... instead of the real project folder.`
* **What Was Done:**
  - Fixed `WH_KEYBOARD_LL` in `src/input/hook.rs` to filter standalone modifier VKs, normalize left/right modifiers via `GetAsyncKeyState`, and emit `HookEvent::ChordTriggered`.
  - Added order-independent `InputChord::matches` in `src/input/chord.rs`.
  - Added `🔥 [HOTKEY MATCHED]` INFO logs in `src/main.rs` and moved `eframe::run_native` to the main OS thread with background Tokio `rt.enter()`.
  - Implemented `BrowserDetector::find_project_root()` in `src/ui/browser_detect.rs` (and reused it in `src/audio/tts.rs`) to resolve the real `E:\Speak-That-Windows` root.
  - Isolated `tts_worker.py` JSON stdout from `engine.py` prints (`sys.stdout = sys.stderr`) and resolved `libshlwapi.a` for the MinGW GNU linker.
  - Built and verified live on Windows (`HWND: 1379582`, `IsWindowVisible: True`, keystrokes & browser paths logged cleanly) and committed locally (`b62ef93`).

### Turn 22 (`2026-11-27T16:17:32Z` & `2026-11-27T16:18:14Z`)
* **User Instruction:**
  > `make a knoladge.md fale that log all the convertation that we head and all the tool you have and your thought process and all the chat histoory and other importent thing about the project that you know.`
* **What Was Done:**
  - Inspected `E:\Speak-That-Windows` and extracted the conversation history from `transcript.jsonl`, then created `knowledge.md`.

### Turn 23 (`2026-11-27T16:21:46Z`)
* **User Instruction:**
  > `refer that file in the readme.md file`
* **What Was Done:**
  - Added references to `knowledge.md` in `README.md` (header links, project structure tree, and Contributing section).

### Turn 24 (`2026-11-27T16:26:39Z`)
* **User Instruction:**
  > `add all the instruction that i gave you in this chat. and what you did everything in the knowledge.md file`
* **What Was Done:**
  - Appended this complete **Turn-by-Turn Instructions & Actions Log** (Turns 1–24) with verbatim user prompts and corresponding actions to `knowledge.md`.


### Turn 25 (`2026-11-27T17:10:09Z`)
* **User Instruction:**
  > `Fix the shortcut architecture and the Shortcuts UI in E:\Speak-That-Windows... Support BOTH Keyboard + Mouse Bindings Simultaneously... Fix the Shortcuts Dashboard UI... Fix False-Positive Shortcut Collision Detection... Fix Missing Font Glyphs & App Icon...`
* **What Was Done:**
  - Replaced single `InputChord` shortcut fields with dual `ActionBinding { keyboard, mouse }` in `src/config.rs` (`Speak Selection`: `Ctrl+Space` + `Mouse 4`, `Push-to-Talk`: `Ctrl+Shift+D` + `Mouse 5`).
  - Added lock-free `BOUND_MOUSE_MASK` & `WM_MBUTTONDOWN`/`WM_MBUTTONUP` support + exact `ms.time` hold tracking in `src/input/hook.rs`.
  - Switched `src/input/catalog.rs` to exact modifier-set equality (`exact_mods`) eliminating the false-positive `Ctrl+S` warning on `Ctrl+Shift+S`, and allowed 1-key bindings for Open Home Dashboard.
  - Rebuilt the `dashboard.rs` Shortcuts table with explicit column widths, wrapped Status text, visible `Change` buttons with live key-capture modal, inline Mouse Button + Hold controls, Windows Segoe UI/Symbol/Emoji fallback fonts, and embedded custom brand icon (`3766ca2`).

### Turn 26 (`2026-11-27T17:39:20Z`)
* **User Instruction:**
  > `Add a customizable "Stop Speaking (TTS)" global shortcut to E:\Speak-That-Windows so users can stop TTS playback immediately without using the system tray.`
* **What Was Done:**
  - Added `stop_speaking: ActionBinding` (`Ctrl+Shift+X` default, `#[serde(default)]` auto-migration) in `src/config.rs`, wired `tts.stop()` in `src/main.rs`, and added the 6th row `Stop Speaking (TTS)` to `src/ui/dashboard.rs`; verified live via `SendInput` (`f5e9cfb`).

### Turn 27 (`2026-11-27T18:01:07Z`)
* **User Instruction:**
  > `The live terminal logs from target\debug\speakthat.exe pinpointed the exact bugs breaking Speak Selection (both Keyboard and Mouse 4). Fix all 4 issues in E:\Speak-That-Windows...`
* **What Was Done:**
  - Released held L/R modifier keys (`VK_LWIN`..`VK_RCONTROL`) + 25 ms settle delay before sending scan-code-backed `Ctrl+C`, and polled `GetClipboardSequenceNumber()` up to 300 ms with diagnostic `INFO` logs in `src/clipboard/selection.rs`.
  - Added `speak_in_flight` debounce guard in `src/main.rs`, OS auto-repeat bitmap filtering + `LLKHF_INJECTED` exclusion + keystroke log spam removal in `src/input/hook.rs`, and hard-blocked `Win+Space` in `src/input/catalog.rs`; verified live text capture from Notepad via Mouse 4 (`ec58533`).

### Turn 28 (`2026-11-27T18:22:00Z`)
* **User Instruction:**
  > `Convert Paradee 8M TTS to 100% native Rust (eliminating ALL Python / .venv dependencies), package a standalone zero-dependency Windows release, push all updates to GitHub, and publish a new GitHub Release.`
* **What Was Done:**
  - Removed Python worker (`tts_worker.py`), exported compressed Misaki US+GB lexicons (`assets/misaki_us.tsv.gz`, `assets/misaki_gb.tsv.gz`) + `assets/paradee_config.json`, implemented `src/audio/g2p.rs` (lexicon + suffix stemming + LTS fallback + `<= 512` BOS/EOS token chunking), wired `ort` (`load-dynamic`) + `rodio` 24 kHz playback in `src/audio/tts.rs`, updated `src/ui/browser_detect.rs` for packaged `./extensions/` + `./models/`, fixed `bionic/engine.rs` unit test, built optimized release binary, verified zero-Python isolated execution in `%TEMP%`, pushed `main` & `v0.2.0`, and published the GitHub Release.
