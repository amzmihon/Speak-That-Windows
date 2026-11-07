"""Generate precision-crafted concept marks and lockups for SpeakThat."""

import os
import math

CONCEPTS_DIR = os.path.join(r"E:\Speak-That-Windows\brand\concepts")
os.makedirs(CONCEPTS_DIR, exist_ok=True)

# --------------------------------------------------------------------
# Helper to create geometric letterforms for "SpeakThat"
# Height: 80px (y: 88 to 168), cap height: 80px, x-height: 58px.
# --------------------------------------------------------------------
# We will use clean geometric strokes/fills for "SpeakThat"
wordmark_paths = '''
  <!-- S -->
  <path d="M 284 106 C 280 94 268 88 252 88 C 234 88 222 98 222 112 C 222 130 240 136 260 142 C 282 148 296 156 296 178 C 296 202 276 216 250 216 C 226 216 210 204 206 188" fill="none" stroke="currentColor" stroke-width="18" stroke-linecap="round" />
  <!-- p -->
  <path d="M 320 114 L 320 250" fill="none" stroke="currentColor" stroke-width="18" stroke-linecap="round" />
  <circle cx="348" cy="148" r="32" fill="none" stroke="currentColor" stroke-width="18" />
  <!-- e -->
  <path d="M 396 154 L 448 154 C 448 132 436 114 418 114 C 398 114 388 132 388 154 C 388 178 400 196 422 196 C 438 196 446 188 450 180" fill="none" stroke="currentColor" stroke-width="18" stroke-linecap="round" />
  <!-- a -->
  <circle cx="488" cy="154" r="28" fill="none" stroke="currentColor" stroke-width="18" />
  <path d="M 516 126 L 516 196" fill="none" stroke="currentColor" stroke-width="18" stroke-linecap="round" />
  <!-- k -->
  <path d="M 548 76 L 548 196" fill="none" stroke="currentColor" stroke-width="18" stroke-linecap="round" />
  <path d="M 584 126 L 552 156 L 586 196" fill="none" stroke="currentColor" stroke-width="18" stroke-linecap="round" stroke-linejoin="round" />
  <!-- T -->
  <path d="M 618 84 L 668 84" fill="none" stroke="#6366F1" stroke-width="18" stroke-linecap="round" />
  <path d="M 643 84 L 643 196" fill="none" stroke="#6366F1" stroke-width="18" stroke-linecap="round" />
  <!-- h -->
  <path d="M 686 76 L 686 196" fill="none" stroke="#6366F1" stroke-width="18" stroke-linecap="round" />
  <path d="M 686 142 C 696 126 712 118 726 118 C 742 118 750 128 750 148 L 750 196" fill="none" stroke="#6366F1" stroke-width="18" stroke-linecap="round" stroke-linejoin="round" />
  <!-- a -->
  <circle cx="788" cy="154" r="26" fill="none" stroke="#6366F1" stroke-width="18" />
  <path d="M 814 128 L 814 196" fill="none" stroke="#6366F1" stroke-width="18" stroke-linecap="round" />
  <!-- t -->
  <path d="M 844 98 L 844 196 C 844 204 848 208 856 208" fill="none" stroke="#6366F1" stroke-width="18" stroke-linecap="round" />
  <path d="M 834 124 L 858 124" fill="none" stroke="#6366F1" stroke-width="18" stroke-linecap="round" />
'''

# -------------------------------------------------------------
# CONCEPT A: The Soundwave Cursor (Refined exact 45° angles + balanced margins)
# dx=60, dy=60 -> exact 45° angle.
# Left margin: 38, Right margin: 38. Bounded 38 to 218.
# -------------------------------------------------------------
concept_a_symbol = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256">
  <title>SpeakThat — The Soundwave Cursor</title>
  <g fill="none" stroke="#000000" stroke-linecap="round" stroke-linejoin="round">
    <!-- Selection Cursor Caret: exact 45° (dx=60, dy=60) -->
    <path d="M 48 68 L 108 128 L 48 188" stroke-width="26" />
    <!-- Inner Sound Arc (r=42) -->
    <path d="M 134 94 A 42 42 0 0 1 134 162" stroke-width="22" />
    <!-- Middle Sound Arc (r=74) -->
    <path d="M 162 68 A 74 74 0 0 1 162 188" stroke-width="22" />
    <!-- Outer Sound Arc (r=106) -->
    <path d="M 190 44 A 106 106 0 0 1 190 212" stroke-width="22" />
  </g>
</svg>
'''

# -------------------------------------------------------------
# CONCEPT B: The Acoustic S Ribbon (Fluid Voice Monogram)
# Centered, balanced, optical overshoot
# -------------------------------------------------------------
concept_b_symbol = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256">
  <title>SpeakThat — Acoustic S Ribbon</title>
  <g fill="none" stroke="#000000" stroke-linecap="round" stroke-linejoin="round">
    <!-- Outer Speech/Sound Echo Arc -->
    <path d="M 186 52 A 88 88 0 0 0 68 128 C 68 186 188 154 188 198 C 188 222 164 236 136 236 C 104 236 78 220 68 194" stroke-width="26" />
    <path d="M 120 20 C 158 20 188 38 188 74 C 188 116 68 86 68 132 C 68 174 122 178 172 160" stroke-width="26" />
    <circle cx="128" cy="128" r="14" fill="#000000" stroke="none" />
  </g>
</svg>
'''

# -------------------------------------------------------------
# CONCEPT C: The Voice Pulse Spectrum (Reader Frequency Wave)
# -------------------------------------------------------------
concept_c_symbol = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256">
  <title>SpeakThat — Voice Pulse Spectrum</title>
  <g fill="#000000">
    <!-- Bar 1 (Left Caret Anchor) -->
    <rect x="40" y="98" width="24" height="60" rx="12" />
    <!-- Bar 2 (Rising Voice) -->
    <rect x="79" y="66" width="24" height="124" rx="12" />
    <!-- Bar 3 (Peak Amplitude - Text Focus) -->
    <rect x="118" y="38" width="24" height="180" rx="12" />
    <!-- Bar 4 (Resonance) -->
    <rect x="157" y="66" width="24" height="124" rx="12" />
    <!-- Bar 5 (Tail Accent) -->
    <rect x="196" y="98" width="24" height="60" rx="12" />
  </g>
</svg>
'''

with open(os.path.join(CONCEPTS_DIR, "concept-a-symbol.svg"), "w", encoding="utf-8") as f:
    f.write(concept_a_symbol.strip())

with open(os.path.join(CONCEPTS_DIR, "concept-b-symbol.svg"), "w", encoding="utf-8") as f:
    f.write(concept_b_symbol.strip())

with open(os.path.join(CONCEPTS_DIR, "concept-c-symbol.svg"), "w", encoding="utf-8") as f:
    f.write(concept_c_symbol.strip())

def get_inner_g(svg_text):
    start = svg_text.find("<g")
    end = svg_text.rfind("</g>") + 4
    return svg_text[start:end]

with open(os.path.join(CONCEPTS_DIR, "concept-a-lockup.svg"), "w", encoding="utf-8") as f:
    f.write(f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 880 256" width="880" height="256">
  <title>SpeakThat Lockup A</title>
  <g transform="translate(16, 0)">
    {get_inner_g(concept_a_symbol)}
  </g>
  <g transform="translate(24, 0)">
    {wordmark_paths}
  </g>
</svg>'''.strip())

with open(os.path.join(CONCEPTS_DIR, "concept-b-lockup.svg"), "w", encoding="utf-8") as f:
    f.write(f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 880 256" width="880" height="256">
  <title>SpeakThat Lockup B</title>
  <g transform="translate(16, 0)">
    {get_inner_g(concept_b_symbol)}
  </g>
  <g transform="translate(24, 0)">
    {wordmark_paths}
  </g>
</svg>'''.strip())

with open(os.path.join(CONCEPTS_DIR, "concept-c-lockup.svg"), "w", encoding="utf-8") as f:
    f.write(f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 880 256" width="880" height="256">
  <title>SpeakThat Lockup C</title>
  <g transform="translate(16, 0)">
    {get_inner_g(concept_c_symbol)}
  </g>
  <g transform="translate(24, 0)">
    {wordmark_paths}
  </g>
</svg>'''.strip())

print("Precision concept files generated.")
