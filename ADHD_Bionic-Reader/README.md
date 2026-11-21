# ADHD Bionic Reader Extension

A high-performance Chrome extension designed for ADHD and neurodivergent readers. It guides eye saccades through text faster using the Bionic Reading method, paired with dual-sensory Text-to-Speech (TTS), distraction reduction, and reader view.

---

## What's New in v1.1 (Performance & Modern Web Overhaul)

- **High-Performance Non-Blocking Architecture**: Conforms to **The Modern Web Guidance** (`break-up-long-tasks`). Uses `scheduler.yield()` to chunk heavy DOM processing into sub-6ms slices, keeping Interaction to Next Paint (INP) under 16ms and eliminating browser freezes on large pages (Wikipedia, Reddit, Substack).
- **Native C++ TreeWalker Processing**: Replaced slow recursive JavaScript DOM traversals with native `document.createTreeWalker(NodeFilter.SHOW_TEXT)` running in linear $O(N)$ time.
- **Zero Layout-Thrashing Floating TTS**: Redesigned the floating audio widget with `position: fixed` and viewport transforms, removing continuous layout queries on scroll.
- **Surgical Memory Management**: Highlight ranges are tracked via `WeakMap<TextNode, Range[]>`, preventing memory leaks and avoiding deep DOM queries on node removal.
- **Native Brand Kit Icons**: Replaced blurry placeholder assets with high-contrast, scalable vector-derived icons (`16px`, `48px`, `128px`) engineered for instant recognition in the Chrome toolbar.
- **Keyboard Shortcuts**:
  - `Alt + B`: Toggle Bionic Reading mode on/off instantly.
  - `Alt + R`: Toggle Distraction-Free Reader View.

---

## Features

- **Bionic Reading Mode**: Automatically emboldens the start of words for quicker reading and reduced cognitive fatigue.
- **Fixation & Boldness Sliders**: Fine-tune the fixation percentage (10%–100%) and stroke weight (0.1x–5.0x) to match your personal focus comfort.
- **Text-to-Speech (TTS)**: Floating audio controls for selected text with auto language detection.
- **Distraction Reduction (Focus Mode)**: Softly dims non-essential media (videos, banners, ads) to keep attention locked onto the text.
- **ADHD Peripheral Breathing Border**: Gentle pulsing visual anchor on viewport edges for calming focus.
- **Distraction-Free Reader View**: Strips away sidebars, ads, and clutter into clean typography using Readability.
- **Domain Blacklist**: One-click disabling on interactive web apps or sites where bionic text is unneeded.

---

## Installation (Developer Mode)

1. Open Chrome (or any Chromium-based browser) and navigate to `chrome://extensions/`.
2. Enable **Developer mode** using the toggle in the top-right corner.
3. Click on **Load unpacked**.
4. Select the `ADHD_Bionic-Reader Extantion Unpacked Loader` directory from this repository.
5. If already installed, simply click the **Refresh (↻)** button on the extension card to load the optimized build.

---

## Permissions Used

- `storage`: For saving user preferences and domain blacklists.
- `activeTab`: To interact with the current page.
- `tts`: Chrome Text-to-Speech engine.
- `contextMenus`: Right-click "Read Bionic Text" option.

---

## Built With

- Modern Web APIs: CSS Custom Highlight API (`::highlight`), `scheduler.yield()`, `TreeWalker`, Shadow DOM
- Manifest V3 Service Workers & Isolated Content Scripts
- Vanilla HTML / Modern CSS
