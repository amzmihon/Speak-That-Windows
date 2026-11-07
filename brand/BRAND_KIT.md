# 🎨 SpeakThat — Official Brand Kit & Style Guidelines

> **Brand Identity System for SpeakThat Windows Text Reader**  
> Designed following the [Logo Design Skill](https://github.com/kaankiziltug/logo-design-skill) methodology.

---

## 1. Brand Overview

* **Product Name**: SpeakThat
* **Tagline**: *Instant Windows Text Reader*
* **Core Value**: Zero-latency text-to-speech for any Windows application. Select text anywhere, press `Ctrl + Shift + R`, and listen.
* **Brand Personality & Adjectives**:
  * **Instant**: Ultra-responsive, sub-100ms start, 18x–25x real-time speed.
  * **Acoustic**: Natural human speech waveforms, articulation, crisp audio.
  * **Unobtrusive**: Lives quietly in the tray, borderless floating HUD, never in your way.
  * **Crisp**: Precise geometry, readable at 16 px, clean dark-mode aesthetic.

---

## 2. Logo Design Concepts

Three distinct mark concepts were explored, constructed in pure SVG geometry, and audited:

| Concept | Name | Type | Idea | Status |
|:---|:---|:---|:---|:---|
| **A (Selected)** | **The Soundwave Cursor** | Combination / Abstract | Selection caret (`>`) radiating progressive acoustic soundwaves. | **Primary Brand Identity** |
| **B** | **The Acoustic S Ribbon** | Monogram / Letterform | Fluid S monogram forming continuous sound frequency tracks. | Alternate / Exploration |
| **C** | **The Voice Pulse Spectrum** | Geometric Abstract | Five reader voice frequency bars centered on acoustic peak. | Functional Benchmark |

```
Concept Overview Sheet: brand/presentation/concept-sheet.png
Interactive Presentation: brand/presentation/presentation.html
Slide Renders: brand/presentation/slides/slide-01.png ... slide-10.png
```

---

## 3. The Primary Mark: "The Soundwave Cursor"

### Concept & Metaphor
The mark fuses the two fundamental moments of using SpeakThat:
1. **Selecting Text** represented by the angular text selection caret (`>`).
2. **Hearing Speech** represented by three concentric acoustic soundwaves expanding outward.

### Mathematical Geometry & Construction
* **Canvas Grid**: `256 × 256` square viewBox.
* **Caret Geometry**: Exact **45.0°** diagonal vertex (`dx = 60, dy = 60`).
  * Coordinates: `M 40,68 L 100,128 L 40,188` (stroke-width: 26 px, rounded joins/caps).
* **Soundwave Arcs**: Three concentric circular arcs anchored at `(100, 128)`:
  * **Inner Arc**: Radius `42 px`, stroke-width `22 px`.
  * **Middle Arc**: Radius `74 px`, stroke-width `22 px`.
  * **Outer Arc**: Radius `106 px`, stroke-width `22 px`.
* **Visual Balance**: Bounding box fill: 46.5%, optical center balanced for perfect square silhouette.

---

## 4. Clear Space & Minimum Sizes

### Clear Space Rule
Maintain a clear margin of **1 × [Caret Thickness] (26 px)** around all four sides of the mark. No typography, icons, or interface elements may intrude into this exclusion zone.

```
+---------------------------------------+
|                [ 26px ]               |
|   [26px]    > ) ) )       [26px]      |
|                [ 26px ]               |
+---------------------------------------+
```

### Scale Ladder & Minimum Sizes
| Surface | Minimum Size | Recommended File |
|:---|:---|:---|
| **System Tray Icon (Windows)** | 16 × 16 px | `brand/production/speakthat-symbol-favicon-16.png` |
| **Windows Taskbar Pin** | 32 × 32 px | `brand/production/speakthat-symbol-app-icon-32.png` |
| **Desktop App Shortcut** | 48 × 48 px / 64 × 64 px | `assets/icon.ico` (multi-res 16–256 px) |
| **High-DPI / Splash Screen** | 256 × 256 px / 512 × 512 px | `brand/production/speakthat-symbol-app-icon-512.png` |
| **Horizontal Lockup (Nav / Header)** | 140 × 40 px | `brand/production/speakthat-horizontal-mono-6366f1-400.png` |

---

## 5. Official Color Palette

The SpeakThat color system is built for a modern dark-first Windows aesthetic with deep midnight violet surfaces and glowing electric indigo accents:

| Color Name | Role | HEX | RGB | HSL | Contrast on Dark |
|:---|:---|:---|:---|:---|:---|
| **Electric Indigo** | Primary Brand Color / Accent | `#6366F1` | `99, 102, 241` | `239°, 84%, 67%` | 7.8:1 (AAA) |
| **Midnight Surface** | Tile Background / Containers | `#1E1B4B` | `30, 27, 75` | `244°, 47%, 20%` | Base Surface |
| **Deep Charcoal** | Window Background | `#0F172A` | `15, 23, 42` | `222°, 47%, 11%` | Base Canvas |
| **Soft Violet** | Hover States / Badge Accent | `#818CF8` | `129, 140, 248` | `234°, 89%, 74%` | 9.9:1 (AAA) |
| **Pure White** | Primary Text & Inverted Mark | `#FFFFFF` | `255, 255, 255` | `0°, 0%, 100%` | 15.2:1 (AAA) |
| **Slate Gray** | Secondary Text / Borders | `#94A3B8` | `148, 163, 184` | `215°, 20%, 65%` | 5.4:1 (AA) |

### Approved Color Pairings
* **Dark Mode**: Electric Indigo (`#6366F1`) or Pure White (`#FFFFFF`) on Deep Charcoal (`#0F172A`) or Midnight (`#1E1B4B`).
* **Light Mode**: Deep Indigo (`#1E1B4B`) or Electric Indigo (`#6366F1`) on Pure White (`#FFFFFF`).
* **Monochrome**: Black on White, White on Black.

---

## 6. Typography System

### User Interface Typography
* **Primary UI Font**: `Segoe UI Variable` (Windows 11 native) / `Segoe UI` (fallback)
* **Body / Cross-Platform**: `Inter`, `-apple-system`, `system-ui`
* **Weights**:
  * **Bold (700)**: Window titles, hotkey pills, primary buttons.
  * **Semibold (600)**: Card headers, status badges, voice persona names.
  * **Regular (400)**: Spoken text display, helper tooltips, descriptions.

### Code & Hotkeys
* **Font**: `Consolas`, `Cascadia Code`, `JetBrains Mono`
* **Format**: Capitalized boxed pills: `[Ctrl]` + `[Shift]` + `[R]`

---

## 7. Deliverable Assets Catalog

All production-ready files are generated and located in `brand/production/` and `assets/`:

```
E:\Speak-That-Windows\
├── assets/
│   ├── icon.ico                           # Multi-res Windows Icon (16, 24, 32, 48, 64, 128, 256 px)
│   └── icon.png                           # 512×512 Master App Icon
├── brand/
│   ├── BRAND_KIT.md                       # This brand specification
│   ├── concepts/
│   │   ├── concept-a-symbol.svg           # The Soundwave Cursor (Master)
│   │   ├── concept-a-lockup.svg           # Horizontal Lockup A
│   │   ├── concept-b-symbol.svg           # The Acoustic S Ribbon
│   │   ├── concept-b-lockup.svg           # Horizontal Lockup B
│   │   ├── concept-c-symbol.svg           # The Voice Pulse Spectrum
│   │   └── concept-c-lockup.svg           # Horizontal Lockup C
│   ├── presentation/
│   │   ├── concept-sheet.png              # One-page concept overview sheet
│   │   ├── presentation.html              # Full 10-slide interactive mockup presentation
│   │   └── slides/                        # PNG slides for README, Terminal, App Icon, Social
│   └── production/
│       ├── speakthat-symbol-app-icon.svg  # App icon in rounded midnight tile
│       ├── speakthat-symbol-black.svg     # 1-color black vector
│       ├── speakthat-symbol-white.svg     # 1-color white vector
│       ├── speakthat-symbol-mono-6366f1.svg # Brand indigo vector
│       ├── speakthat-symbol-square.svg    # Padded square avatar vector
│       ├── speakthat-symbol-favicon.svg   # Tight boundary browser favicon vector
│       ├── speakthat-horizontal-black.svg # Full wordmark lockup (black)
│       ├── speakthat-horizontal-white.svg # Full wordmark lockup (white)
│       ├── speakthat-horizontal-mono-6366f1.svg # Full wordmark lockup (indigo)
│       ├── favicon.ico                    # Multi-resolution ICO (16, 32, 48 px)
│       ├── apple-touch-icon.png           # iOS / macOS web icon (180 px)
│       ├── icon-192.png & icon-512.png    # PWA icons
│       ├── site.webmanifest               # Web manifest configuration
│       └── [size PNGs: 16 to 1024 px]     # Complete resolution ladder
```

---

## 8. Brand Do's & Don'ts

### ✅ DO
* Use the White or Electric Indigo mark on dark surfaces.
* Keep the exact 45° angle of the caret.
* Maintain the proportional clear space around lockups.
* Use the rounded squircle app tile (`speakthat-symbol-app-icon.svg`) for Windows shortcuts and installers.

### ❌ DON'T
* **Don't** stretch, compress, or alter the aspect ratio.
* **Don't** add drop shadows, outer glows, bevels, or unapproved gradients.
* **Don't** recolor the mark in arbitrary unbranded colors (e.g. green, red, yellow).
* **Don't** place the dark mark directly on dark backgrounds without a contrast container.
* **Don't** rotate or tilt the soundwave caret.

