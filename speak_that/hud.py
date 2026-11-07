"""Warm Champagne Glassmorphism Floating Mini-Player Pop-up for SpeakThat.

Styled 1:1 after the modern TTS AI Floating Widget specification:
- Deep warm stone base (#1C1917) with ultra-soft glassmorphism.
- Warm champagne (#FAEDCD) and wheat accents with glowing top highlight edge.
- AI Neural Pulse / Waveform Icon Badge with 3 animated resonant wave bars.
- Amber pulsating status indicator and clean sentence snippet.
- Minimalist rounded-xl interactive controls (Champagne Pause/Resume and Rose Stop).
"""

import math
import tkinter as tk
import customtkinter as ctk


class FloatingHUD:
    """A soft, borderless, draggable floating pill widget with warm champagne glassmorphism."""

    def __init__(self, master, on_pause_toggle=None, on_stop=None):
        self.master = master
        self.on_pause_toggle = on_pause_toggle
        self.on_stop = on_stop

        self.window = ctk.CTkToplevel(master)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.attributes("-alpha", 0.96)

        # Dimensions & default placement
        self.width = 430
        self.height = 70
        self._set_default_position()

        # Dragging state
        self._offset_x = 0
        self._offset_y = 0

        # Animation state
        self._is_animating = False
        self._is_paused = False
        self._is_alive = True
        self._anim_phase = 0.0

        self._build_ui()

    def _set_default_position(self):
        screen_w = self.master.winfo_screenwidth()
        screen_h = self.master.winfo_screenheight()
        x = max(20, screen_w - self.width - 35)
        y = max(20, screen_h - self.height - 85)
        self.window.geometry(f"{self.width}x{self.height}+{x}+{y}")

    def _build_ui(self):
        self.window.configure(fg_color="#141211")

        # Main Capsule Frame (Deep warm stone with subtle champagne border)
        self.capsule = ctk.CTkFrame(
            self.window,
            corner_radius=18,
            fg_color="#1C1917",
            border_width=1,
            border_color="#4A3F35"
        )
        self.capsule.pack(fill="both", expand=True, padx=2, pady=2)

        # Bind dragging on the capsule
        self.capsule.bind("<Button-1>", self._start_drag)
        self.capsule.bind("<B1-Motion>", self._on_drag)

        # --- Ambient Glowing Top Edge Highlight (Warm Champagne) ---
        self.top_glow = tk.Canvas(
            self.capsule,
            height=2,
            bg="#1C1917",
            highlightthickness=0
        )
        self.top_glow.pack(fill="x", side="top", padx=16, pady=(1, 0))
        self.top_glow.bind("<Button-1>", self._start_drag)
        self.top_glow.bind("<B1-Motion>", self._on_drag)
        self.top_glow.bind("<Configure>", self._draw_top_glow)

        # --- Content Row ---
        content_row = ctk.CTkFrame(self.capsule, fg_color="transparent")
        content_row.pack(fill="both", expand=True, padx=12, pady=(4, 8))
        content_row.bind("<Button-1>", self._start_drag)
        content_row.bind("<B1-Motion>", self._on_drag)

        # 1. AI Neural Pulse / Waveform Icon Badge
        self.badge = ctk.CTkFrame(
            content_row,
            width=42,
            height=42,
            corner_radius=12,
            fg_color="#2A241E",
            border_width=1,
            border_color="#5E4F3D"
        )
        self.badge.pack(side="left", padx=(2, 10))
        self.badge.pack_propagate(False)
        self.badge.bind("<Button-1>", self._start_drag)
        self.badge.bind("<B1-Motion>", self._on_drag)

        # 3 Sound wave animation bars inside the badge
        self.wave_canvas = tk.Canvas(
            self.badge,
            width=32,
            height=24,
            bg="#2A241E",
            highlightthickness=0
        )
        self.wave_canvas.pack(expand=True)
        self.wave_canvas.bind("<Button-1>", self._start_drag)
        self.wave_canvas.bind("<B1-Motion>", self._on_drag)

        self.wave_bars = [
            self.wave_canvas.create_line(7, 10, 7, 14, width=2.5, capstyle=tk.ROUND, fill="#FAEDCD"),
            self.wave_canvas.create_line(15, 8, 15, 16, width=2.5, capstyle=tk.ROUND, fill="#FDE68A"),
            self.wave_canvas.create_line(23, 10, 23, 14, width=2.5, capstyle=tk.ROUND, fill="#FAEDCD"),
        ]

        # 2. Content Area: Status & Snippet
        self.text_container = ctk.CTkFrame(content_row, fg_color="transparent")
        self.text_container.pack(side="left", fill="both", expand=True, padx=2)
        self.text_container.bind("<Button-1>", self._start_drag)
        self.text_container.bind("<B1-Motion>", self._on_drag)

        # Status row with amber pulse dot
        status_row = ctk.CTkFrame(self.text_container, fg_color="transparent")
        status_row.pack(fill="x", pady=(2, 0))
        status_row.bind("<Button-1>", self._start_drag)
        status_row.bind("<B1-Motion>", self._on_drag)

        self.dot_canvas = tk.Canvas(
            status_row,
            width=10,
            height=10,
            bg="#1C1917",
            highlightthickness=0
        )
        self.dot_canvas.pack(side="left", padx=(0, 5))
        self.dot_canvas.bind("<Button-1>", self._start_drag)
        self.dot_canvas.bind("<B1-Motion>", self._on_drag)
        self.dot_id = self.dot_canvas.create_oval(2, 2, 8, 8, fill="#FCD34D", outline="")

        self.status_label = ctk.CTkLabel(
            status_row,
            text="Reading selected text...",
            font=("Segoe UI", 10, "bold"),
            text_color="#FAEDCD",
            anchor="w"
        )
        self.status_label.pack(side="left", fill="x", expand=True)
        self.status_label.bind("<Button-1>", self._start_drag)
        self.status_label.bind("<B1-Motion>", self._on_drag)

        # Snippet label
        self.sentence_label = ctk.CTkLabel(
            self.text_container,
            text="Highlight any text and press Ctrl+Shift+R...",
            font=("Segoe UI", 9),
            text_color="#E6D5BC",
            anchor="w"
        )
        self.sentence_label.pack(fill="x", pady=(1, 0))
        self.sentence_label.bind("<Button-1>", self._start_drag)
        self.sentence_label.bind("<B1-Motion>", self._on_drag)

        # 3. Minimalist Interactive Control Buttons
        self.btn_frame = ctk.CTkFrame(content_row, fg_color="transparent")
        self.btn_frame.pack(side="right", padx=(6, 2))

        # Pause / Resume Button (Warm Champagne)
        self.pause_btn = ctk.CTkButton(
            self.btn_frame,
            text="⏸",
            width=32,
            height=32,
            corner_radius=10,
            fg_color="#2A241E",
            hover_color="#3D3328",
            border_width=1,
            border_color="#5E4F3D",
            text_color="#FAEDCD",
            font=("Segoe UI", 10, "bold"),
            command=self._handle_pause_click
        )
        self.pause_btn.pack(side="left", padx=3)

        # Stop Button (Rose 500 Tint)
        self.stop_btn = ctk.CTkButton(
            self.btn_frame,
            text="■",
            width=32,
            height=32,
            corner_radius=10,
            fg_color="#3C1820",
            hover_color="#54202B",
            border_width=1,
            border_color="#7F2736",
            text_color="#FECDD3",
            font=("Segoe UI", 10, "bold"),
            command=self._handle_stop_click
        )
        self.stop_btn.pack(side="left", padx=3)

    def _draw_top_glow(self, event=None):
        w = self.top_glow.winfo_width()
        if w <= 1:
            return
        self.top_glow.delete("all")
        # Smooth warm champagne highlight centered along top edge
        left = int(w * 0.15)
        right = int(w * 0.85)
        self.top_glow.create_line(left, 1, right, 1, width=2, capstyle=tk.ROUND, fill="#FAEDCD")

    def _start_drag(self, event):
        self._offset_x = event.x_root - self.window.winfo_x()
        self._offset_y = event.y_root - self.window.winfo_y()

    def _on_drag(self, event):
        x = event.x_root - self._offset_x
        y = event.y_root - self._offset_y
        self.window.geometry(f"+{x}+{y}")

    def show(self, sentence="Reading selected text..."):
        self._is_paused = False
        self.update_sentence(sentence)
        self.pause_btn.configure(text="⏸")
        self.status_label.configure(text="Reading selected text...", text_color="#FAEDCD")
        self.dot_canvas.itemconfig(self.dot_id, fill="#FCD34D")
        self.capsule.configure(border_color="#5E4F3D")
        self.window.deiconify()
        self.window.lift()
        self.start_wave_animation()

    def hide(self):
        self.stop_wave_animation()
        self.window.withdraw()

    def update_sentence(self, text):
        clean = text.strip().replace("\n", " ")
        if len(clean) > 48:
            clean = clean[:45] + "…"
        self.sentence_label.configure(text=f'"{clean}"')

    def set_paused_state(self, is_paused):
        self._is_paused = is_paused
        if is_paused:
            self.pause_btn.configure(text="▶")
            self.status_label.configure(text="Paused (Click to resume)", text_color="#F59E0B")
            self.dot_canvas.itemconfig(self.dot_id, fill="#F59E0B")
            self.capsule.configure(border_color="#8C775D")
            self.stop_wave_animation()
        else:
            self.pause_btn.configure(text="⏸")
            self.status_label.configure(text="Reading selected text...", text_color="#FAEDCD")
            self.dot_canvas.itemconfig(self.dot_id, fill="#FCD34D")
            self.capsule.configure(border_color="#5E4F3D")
            self.start_wave_animation()

    def start_wave_animation(self):
        if not self._is_animating:
            self._is_animating = True
            self._animate_wave()

    def stop_wave_animation(self):
        self._is_animating = False
        # Set to resting heights
        self.wave_canvas.coords(self.wave_bars[0], 7, 10, 7, 14)
        self.wave_canvas.coords(self.wave_bars[1], 15, 9, 15, 15)
        self.wave_canvas.coords(self.wave_bars[2], 23, 10, 23, 14)
        for b in self.wave_bars:
            self.wave_canvas.itemconfig(b, fill="#786B5E")

    def _animate_wave(self):
        if not getattr(self, "_is_alive", True) or not self._is_animating or self._is_paused:
            return

        self._anim_phase += 0.22

        # 3 frequencies matching the HTML animation: 1.1s, 0.8s, 1.3s
        h1 = 4 + int(10 * abs(math.sin(self._anim_phase * 1.1)))
        h2 = 4 + int(13 * abs(math.sin(self._anim_phase * 1.5 + 0.3)))
        h3 = 4 + int(10 * abs(math.sin(self._anim_phase * 0.9 + 0.7)))

        # Update coords centered around y=12
        self.wave_canvas.coords(self.wave_bars[0], 7, max(3, 12 - h1 // 2), 7, min(21, 12 + h1 // 2))
        self.wave_canvas.coords(self.wave_bars[1], 15, max(2, 12 - h2 // 2), 15, min(22, 12 + h2 // 2))
        self.wave_canvas.coords(self.wave_bars[2], 23, max(3, 13 - h3 // 2), 23, min(21, 13 + h3 // 2))

        self.wave_canvas.itemconfig(self.wave_bars[0], fill="#FAEDCD")
        self.wave_canvas.itemconfig(self.wave_bars[1], fill="#FDE68A")
        self.wave_canvas.itemconfig(self.wave_bars[2], fill="#FAEDCD")

        self.window.after(50, self._animate_wave)

    def _handle_pause_click(self):
        if self.on_pause_toggle:
            self.on_pause_toggle()

    def _handle_stop_click(self):
        if self.on_stop:
            self.on_stop()
        self.hide()

    def destroy(self):
        self._is_alive = False
        self._is_animating = False
        try:
            self.window.destroy()
        except Exception:
            pass
