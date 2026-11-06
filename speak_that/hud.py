"""Floating mini-player HUD bar for on-screen speech feedback and quick controls."""

import customtkinter as ctk


class FloatingHUD:
    """A sleek, borderless, draggable floating pill widget displaying current speech status."""

    def __init__(self, master, on_pause_toggle=None, on_stop=None):
        self.master = master
        self.on_pause_toggle = on_pause_toggle
        self.on_stop = on_stop

        self.window = ctk.CTkToplevel(master)
        self.window.withdraw()  # hidden initially
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.attributes("-alpha", 0.94)

        # Size and default position
        self.width = 380
        self.height = 64
        self._set_default_position()

        # Dragging state
        self._offset_x = 0
        self._offset_y = 0

        self._build_ui()

    def _set_default_position(self):
        screen_w = self.master.winfo_screenwidth()
        screen_h = self.master.winfo_screenheight()
        x = max(10, screen_w - self.width - 25)
        y = max(10, screen_h - self.height - 75)
        self.window.geometry(f"{self.width}x{self.height}+{x}+{y}")

    def _build_ui(self):
        self.window.configure(fg_color="#181824")

        # Container card with rounded corner border
        self.card = ctk.CTkFrame(
            self.window,
            corner_radius=16,
            fg_color="#1e1e2f",
            border_width=1,
            border_color="#3b3b54"
        )
        self.card.pack(fill="both", expand=True, padx=2, pady=2)

        # Make card draggable
        self.card.bind("<Button-1>", self._start_drag)
        self.card.bind("<B1-Motion>", self._on_drag)

        # Layout
        # Left: Icon & Speaking indicator
        self.icon_label = ctk.CTkLabel(
            self.card,
            text="🔊",
            font=("Segoe UI Emoji", 18),
            text_color="#6366f1"
        )
        self.icon_label.pack(side="left", padx=(12, 6))

        # Middle: Text snippet
        self.text_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        self.text_frame.pack(side="left", fill="both", expand=True, padx=4)
        self.text_frame.bind("<Button-1>", self._start_drag)
        self.text_frame.bind("<B1-Motion>", self._on_drag)

        self.status_title = ctk.CTkLabel(
            self.text_frame,
            text="Reading selected text...",
            font=("Segoe UI", 11, "bold"),
            text_color="#a5b4fc",
            anchor="w"
        )
        self.status_title.pack(fill="x", pady=(4, 0))
        self.status_title.bind("<Button-1>", self._start_drag)
        self.status_title.bind("<B1-Motion>", self._on_drag)

        self.sentence_label = ctk.CTkLabel(
            self.text_frame,
            text="Initializing...",
            font=("Segoe UI", 10),
            text_color="#e2e8f0",
            anchor="w"
        )
        self.sentence_label.pack(fill="x", pady=(0, 4))
        self.sentence_label.bind("<Button-1>", self._start_drag)
        self.sentence_label.bind("<B1-Motion>", self._on_drag)

        # Right: Buttons (Pause/Resume, Stop, Close)
        self.btn_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        self.btn_frame.pack(side="right", padx=(4, 10))

        self.pause_btn = ctk.CTkButton(
            self.btn_frame,
            text="⏸",
            width=28,
            height=28,
            corner_radius=14,
            fg_color="#312e81",
            hover_color="#4338ca",
            font=("Segoe UI Emoji", 12),
            command=self._handle_pause_click
        )
        self.pause_btn.pack(side="left", padx=3)

        self.stop_btn = ctk.CTkButton(
            self.btn_frame,
            text="⏹",
            width=28,
            height=28,
            corner_radius=14,
            fg_color="#dc2626",
            hover_color="#b91c1c",
            font=("Segoe UI Emoji", 12),
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
        self.status_title.configure(text="Reading selected text...")
        self.window.deiconify()
        self.window.lift()

    def hide(self):
        self.window.withdraw()

    def update_sentence(self, text):
        clean = text.strip().replace("\n", " ")
        if len(clean) > 42:
            clean = clean[:40] + "…"
        self.sentence_label.configure(text=clean)

    def set_paused_state(self, is_paused):
        if is_paused:
            self.pause_btn.configure(text="▶")
            self.status_title.configure(text="Paused")
        else:
            self.pause_btn.configure(text="⏸")
            self.status_title.configure(text="Reading selected text...")

    def _handle_pause_click(self):
        if self.on_pause_toggle:
            self.on_pause_toggle()

    def _handle_stop_click(self):
        if self.on_stop:
            self.on_stop()
        self.hide()

