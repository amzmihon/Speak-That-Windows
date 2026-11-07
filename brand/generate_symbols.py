"""Build geometric SVG concepts for SpeakThat brand kit."""

import os
import math

CONCEPTS_DIR = os.path.join(r"E:\Speak-That-Windows\brand\concepts")
os.makedirs(CONCEPTS_DIR, exist_ok=True)

# -------------------------------------------------------------
# CONCEPT A: The Soundwave Cursor (Selection Caret + Voice Ripples)
# -------------------------------------------------------------
concept_a_symbol = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256">
  <g fill="none" stroke="#000000" stroke-linecap="round" stroke-linejoin="round">
    <!-- Selection Cursor Caret -->
    <path d="M 52 68 L 108 128 L 52 188" stroke-width="26" />
    <!-- Inner Sound Arc -->
    <path d="M 132 94 A 42 42 0 0 1 132 162" stroke-width="22" />
    <!-- Middle Sound Arc -->
    <path d="M 158 68 A 74 74 0 0 1 158 188" stroke-width="22" />
    <!-- Outer Sound Arc -->
    <path d="M 186 44 A 108 108 0 0 1 186 212" stroke-width="22" />
  </g>
</svg>
'''

# -------------------------------------------------------------
# CONCEPT B: The Acoustic 'S' Monogram (Continuous fluid sound ribbon)
# -------------------------------------------------------------
concept_b_symbol = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256">
  <g fill="none" stroke="#000000" stroke-linecap="round" stroke-linejoin="round">
    <!-- Upper Sound Loop of S -->
    <path d="M 192 76 C 180 50 152 40 128 40 C 92 40 68 62 68 94 C 68 136 188 124 188 168 C 188 202 160 216 128 216 C 96 216 72 202 60 178" stroke-width="28" />
    <!-- Speech Voice Accent Point -->
    <circle cx="196" cy="128" r="14" fill="#000000" stroke="none" />
    <path d="M 218 108 A 28 28 0 0 1 218 148" stroke-width="16" />
  </g>
</svg>
'''

# -------------------------------------------------------------
# CONCEPT C: The Voice Pulse / Spectrum (Reader Frequency Bars)
# -------------------------------------------------------------
concept_c_symbol = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256">
  <g fill="#000000">
    <!-- Bar 1 (Left Caret Anchor) -->
    <rect x="42" y="98" width="24" height="60" rx="12" />
    <!-- Bar 2 (Rising Voice) -->
    <rect x="80" y="66" width="24" height="124" rx="12" />
    <!-- Bar 3 (Peak Amplitude - Text Focus) -->
    <rect x="118" y="38" width="24" height="180" rx="12" />
    <!-- Bar 4 (Resonance) -->
    <rect x="156" y="74" width="24" height="108" rx="12" />
    <!-- Bar 5 (Tail Accent) -->
    <rect x="194" y="104" width="24" height="48" rx="12" />
  </g>
</svg>
'''

with open(os.path.join(CONCEPTS_DIR, "concept-a-symbol.svg"), "w", encoding="utf-8") as f:
    f.write(concept_a_symbol.strip())

with open(os.path.join(CONCEPTS_DIR, "concept-b-symbol.svg"), "w", encoding="utf-8") as f:
    f.write(concept_b_symbol.strip())

with open(os.path.join(CONCEPTS_DIR, "concept-c-symbol.svg"), "w", encoding="utf-8") as f:
    f.write(concept_c_symbol.strip())

print("Base concept symbols generated successfully!")

