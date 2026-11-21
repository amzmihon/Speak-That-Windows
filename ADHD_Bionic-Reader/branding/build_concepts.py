"""
Refined SVG concepts for ADHD Bionic Reader:
Concept A: The Bionic B (Monogram / Fixation Anchor)
Concept B: The Guided Saccade (Eye & Forward Vector)
Concept C: The Focus Lock (Bionic Reticle & Fixation Target)
"""
import os

concepts_dir = r"E:\ADHD_Bionic-Reader\branding\concepts"

# -------------------------------------------------------------
# Concept A: The Bionic B (Fixation Anchor + Kinetic Bowls)
# -------------------------------------------------------------
svg_a_symbol = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256" role="img" aria-labelledby="title-a">
  <title id="title-a">The Bionic B - Fixation Anchor</title>
  <!-- Left Stem: Solid Fixation Anchor -->
  <path fill="#000000" d="M 56,36 L 92,36 L 92,220 L 56,220 C 47.16,220 40,212.84 40,204 L 40,52 C 40,43.16 47.16,36 56,36 Z"/>
  <!-- Top Kinetic Bowl -->
  <path fill="#000000" fill-rule="evenodd" d="
    M 108,36
    L 160,36
    A 42,42 0 0 1 202,78
    A 42,42 0 0 1 160,120
    L 108,120
    Z
    M 108,62
    L 156,62
    A 16,16 0 0 1 172,78
    A 16,16 0 0 1 156,94
    L 108,94
    Z
  "/>
  <!-- Bottom Kinetic Bowl (Optical Overshoot) -->
  <path fill="#000000" fill-rule="evenodd" d="
    M 108,128
    L 166,128
    A 46,46 0 0 1 212,174
    A 46,46 0 0 1 166,220
    L 108,220
    Z
    M 108,154
    L 162,154
    A 20,20 0 0 1 182,174
    A 20,20 0 0 1 162,194
    L 108,194
    Z
  "/>
</svg>'''

# -------------------------------------------------------------
# Concept B: The Guided Saccade (The Bionic Eye & Forward Vector)
# -------------------------------------------------------------
svg_b_symbol = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256" role="img" aria-labelledby="title-b">
  <title id="title-b">The Guided Saccade - Bionic Eye</title>
  <!-- Outer Eyelid Frame (Generous, balanced arcs) -->
  <path fill="#000000" fill-rule="evenodd" d="
    M 24,128
    C 52,36 204,36 232,128
    C 204,220 52,220 24,128 Z
    M 54,128
    C 76,68 180,68 202,128
    C 180,188 76,188 54,128 Z
  "/>
  <!-- Floating Focal Iris with Negative-Space Forward Arrow -->
  <path fill="#000000" fill-rule="evenodd" d="
    M 128,86
    A 42,42 0 1 1 127.9,86 Z
    M 116,104
    L 144,128
    L 116,152
    L 128,152
    L 156,128
    L 128,104 Z
  "/>
</svg>'''

# -------------------------------------------------------------
# Concept C: The Focus Lock (Bionic Reticle & Fixation Point)
# Brackets lock onto the initial bold fixation dot and forward saccade indicator
# -------------------------------------------------------------
svg_c_symbol = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256" role="img" aria-labelledby="title-c">
  <title id="title-c">The Focus Lock - Bionic Reticle</title>
  <!-- Top-Left Focus Bracket -->
  <path fill="#000000" d="M 40,92 L 40,56 C 40,47.16 47.16,40 56,40 L 92,40 L 92,62 L 62,62 L 62,92 Z"/>
  <!-- Top-Right Focus Bracket -->
  <path fill="#000000" d="M 164,40 L 200,40 C 208.84,40 216,47.16 216,56 L 216,92 L 194,92 L 194,62 L 164,62 Z"/>
  <!-- Bottom-Left Focus Bracket -->
  <path fill="#000000" d="M 40,164 L 40,200 C 40,208.84 47.16,216 56,216 L 92,216 L 92,194 L 62,194 L 62,164 Z"/>
  <!-- Bottom-Right Focus Bracket -->
  <path fill="#000000" d="M 164,216 L 200,216 C 208.84,216 216,208.84 216,200 L 216,164 L 194,164 L 194,194 L 164,194 Z"/>
  <!-- Center: Bold Fixation Core (The Fixation Point) -->
  <circle cx="106" cy="128" r="32" fill="#000000"/>
  <!-- Forward Saccade Indicator: Clean Kinetic Arrow -->
  <polygon points="146,104 176,128 146,152 158,128" fill="#000000"/>
</svg>'''

with open(os.path.join(concepts_dir, "concept-a-symbol.svg"), "w", encoding="utf-8") as f:
    f.write(svg_a_symbol.strip())

with open(os.path.join(concepts_dir, "concept-b-symbol.svg"), "w", encoding="utf-8") as f:
    f.write(svg_b_symbol.strip())

with open(os.path.join(concepts_dir, "concept-c-symbol.svg"), "w", encoding="utf-8") as f:
    f.write(svg_c_symbol.strip())

print("Built refined concepts A, B, C.")
