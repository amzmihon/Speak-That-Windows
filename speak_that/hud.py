"""Dynamic Island-style floating mini-player HUD for on-screen speech feedback."""

import tkinter as tk
import customtkinter as ctk


class FloatingHUD:
    """A modern, borderless, draggable floating pill widget inspired by Dynamic Island."""

    def __init__(self, master, on_pause_toggle=None, on_stop=None):
        self.master = master
        self.on_pause_toggle = on_pause_toggle
        self.on_stop = on_stop

        self.window = ctk.CTkToplevel(master)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.attributes("-alpha", 0.95)

        # Dimensions & default placement
        self.width = 440
        self.height = 56
        self._set_default_position()

        # Dragging state
        self._offset_x = 0
        self._offset_y = 0

        # Animation state
        self._is_animating = False
        self._anim_phase = 0.0

        self._build_ui()

    def _set_default_position(self):
        screen_w = self.master.winfo_screenwidth()
        screen_h = self.master.winfo_screenheight()
        x = max(20, screen_w - self.width - 30)
        y = max(20, screen_h - self.height - 80)
        self.window.geometry(f"{self.width}x{self.height}+{x}+{y}")

    def _build_ui(self):
        self.window.configure(fg_color="#090D16")

        # Main Capsule Frame
        self.capsule = ctk.CTkFrame(
            self.window,
            corner_radius=22,
            fg_color="#0F172A",
            border_width=1,
            border_color="#334155"
        )
        self.capsule.pack(fill="both", expand=True, padx=2, pady=2)

        # Drag bindings
        self.capsule.bind("<Button-1>", self._start_drag)
        self.capsule.bind("<B1-Motion>", self._on_drag)

        # --- Left: Mini Waveform Canvas ---
        self.wave_canvas = tk.Canvas(
            self.capsule,
            width=36,
            height=28,
            bg="#0F172A",
            highlightthickness=0
        )
        self.wave_canvas.pack(side="left", padx=(14, 8), pady=12)
        self.wave_canvas.bind("<Button-1>", self._start_drag)
        self.wave_canvas.bind("<B1-Motion>", self._on_drag)

        # Draw resting bars
        self.wave_bars = []
        for i in range(5):
            x = 4 + i * 7
            line_id = self.wave_canvas.create_line(x, 10, x, 18, width=3, capstyle=tk.ROUND, fill="#6366F1")
            self.wave_bars.append(line_id)

        # --- Middle: Spoken Text & Status Snippet ---
        self.text_container = ctk.CTkFrame(self.capsule, fg_color="transparent")
        self.text_container.pack(side="left", fill="both", expand=True, padx=2, pady=6)
        self.text_container.bind("<Button-1>", self._start_drag)
        self.text_container.bind("<B1-Motion>", self._on_drag)

        self.meta_label = ctk.CTkLabel(
            self.text_container,
            text="SPEAKTHAT • READING",
            font=("Segoe UI", 9, "bold"),
            text_color="#818CF8",
            anchor="w"
        )
        self.meta_label.pack(fill="x", pady=(2, 0))
        self.meta_label.bind("<Button-1>", self._start_drag)
        self.meta_label.bind("<B1-Motion>", self._on_drag)

        self.sentence_label = ctk.CTkLabel(
            self.text_container,
            text="Listening...",
            font=("Segoe UI", 11),
            text_color="#F8FAFC",
            anchor="w"
        )
        self.sentence_label.pack(fill="x", pady=(0, 2))
        self.sentence_label.bind("<Button-1>", self._start_drag)
        self.sentence_label.bind("<B1-Motion>", self._on_drag)

        # --- Right: Micro Action Controls ---
        self.btn_frame = ctk.CTkFrame(self.capsule, fg_color="transparent")
        self.btn_frame.pack(side="right", padx=(4, 12))

        self.pause_btn = ctk.CTkButton(
            self.btn_frame,
            text="⏸",
            width=28,
            height=28,
            corner_radius=14,
            fg_color="#1E293B",
            hover_color="#334155",
            text_color="#F8FAFC",
            font=("Segoe UI Emoji", 11),
            command=self._handle_pause_click
        )
        self.pause_btn.pack(side="left", padx=3)

        self.stop_btn = ctk.CTkButton(
            self.btn_frame,
            text="⏹",
            width=28,
            height=28,
            corner_radius=14,
            fg_color="#7F1D1D",
            hover_color="#991B1B",
            text_color="#FECACA",
            font=("Segoe UI Emoji", 11),
            command=self._handle_stop_click
        )
        self.stop_btn.pack(side="left", padx=3)

    def _start_drag(self, event):
        self._offset_x = event.x_root - self.window.winfo_x()
        self._offset_y = event.y_root - self.window.winfo_y()

    def _on_drag(self, event):
        x = event.x_root - self._offset_x
        y = event.y_root - self._offset_y
        self.window.geometry(f"+{x}+{y}")

    def show(self, sentence="Reading text..."):
        self.update_sentence(sentence)
        self.pause_btn.configure(text="⏸")
        self.meta_label.configure(text="SPEAKTHAT • READING", text_color="#818CF8")
        self.capsule.configure(border_color="#6366F1")
        self.window.deiconify()
        self.window.lift()
        self.start_wave_animation()

    def hide(self):
        self.stop_wave_animation()
        self.window.withdraw()

    def update_sentence(self, text):
        clean = text.strip().replace("\n", " ")
        if len(clean) > 46:
            clean = clean[:44] + "…"
        self.sentence_label.configure(text=clean)

    def set_paused_state(self, is_paused):
        if is_paused:
            self.pause_btn.configure(text="▶")
            self.meta_label.configure(text="SPEAKTHAT • PAUSED", text_color="#F59E0B")
            self.capsule.configure(border_color="#F59E0B")
            self.stop_wave_animation()
        else:
            self.pause_btn.configure(text="⏸")
            self.meta_label.configure(text="SPEAKTHAT • READING", text_color="#818CF8")
            self.capsule.configure(border_color="#6366F1")
            self.start_wave_animation()

    def start_wave_animation(self):
        if not self._is_animating:
            self._is_animating = True
            self._animate_wave()

    def stop_wave_animation(self):
        self._is_animating = False
        # Reset to resting heights
        for i, line_id in enumerate(self.wave_bars):
            x = 4 + i * 7
            self.wave_canvas.coords(line_id, x, 11, x, 17)
            self.wave_canvas.itemconfig(line_id, fill="#475569")

    def _animate_wave(self):
        if not self._is_animating:
            return

        import math
        self._anim_phase += 0.35
        for i, line_id in enumerate(self.wave_bars):
            x = 4 + i * 7
            h = 4 + int(8 * (1 + math.sin(self._anim_phase + i * 0.9)))
            y1 = max(2, 14 - h // 2)
            y2 = min(26, 14 + h // 2)
            self.wave_canvas.coords(line_id, x, y1, x, y2)
            self.wave_canvas.itemconfig(line_id, fill="#818CF8")

        self.window.after(60, self._animate_wave)

    def _handle_pause_click(self):
        if self.on_pause_toggle:
            self.on_pause_toggle()

    def _handle_stop_click(self):
        if self.on_stop:
            self.on_stop()
        self.hide()
