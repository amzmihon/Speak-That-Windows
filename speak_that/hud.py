"""WinUI 3 Fluent Glassmorphism Floating Capsule HUD for SpeakThat.

Supports 4 Distinct User-Selected Display Styles:
1. 'default' - Full glassmorphism pill (440×74) with sinusoidal wave animation, status & text snippet preview.
2. 'small'   - Compact sleek capsule (310×54) with wave animation & concise status text.
3. 'tiny'    - Minimalist micro-pill (154×46) with mini wave bars and pause/stop controls (zero screen obstruction).
4. 'none'    - Pop-up completely disabled for pure keyboard shortcut reading (Ctrl+Shift+R / Ctrl+Shift+X).
"""

import ctypes
import math
import tkinter as tk
import customtkinter as ctk

# Color key used by Windows DWM compositor to make rectangular window boundaries 100% invisible
TRANS_KEY_COLOR = "#000001"

HUD_STYLES = {
    "default": {
        "width": 440,
        "height": 74,
        "corner_radius": 26,
        "badge_size": 42,
        "badge_radius": 14,
        "canvas_size": (32, 26),
        "wave_center_y": 13,
        "wave_bar_xs": [7, 15, 23],
        "wave_max_h": (10, 14, 10),
        "btn_size": 32,
        "btn_radius": 12,
        "font_size_btn": 12,
        "show_sentence": True,
        "show_status": True,
        "status_font_size": 10,
        "snippet_font_size": 9,
        "snippet_max_chars": 46,
        "content_padding": (14, 10),
        "text_pad_left": 2,
    },
    "small": {
        "width": 310,
        "height": 54,
        "corner_radius": 20,
        "badge_size": 34,
        "badge_radius": 11,
        "canvas_size": (26, 20),
        "wave_center_y": 10,
        "wave_bar_xs": [5, 12, 19],
        "wave_max_h": (7, 10, 7),
        "btn_size": 28,
        "btn_radius": 10,
        "font_size_btn": 10,
        "show_sentence": True,
        "show_status": True,
        "status_font_size": 9,
        "snippet_font_size": 8,
        "snippet_max_chars": 28,
        "content_padding": (10, 7),
        "text_pad_left": 2,
    },
    "tiny": {
        "width": 154,
        "height": 46,
        "corner_radius": 18,
        "badge_size": 30,
        "badge_radius": 10,
        "canvas_size": (22, 18),
        "wave_center_y": 9,
        "wave_bar_xs": [4, 10, 16],
        "wave_max_h": (5, 8, 5),
        "btn_size": 26,
        "btn_radius": 9,
        "font_size_btn": 9,
        "show_sentence": False,
        "show_status": False,
        "status_font_size": 8,
        "snippet_font_size": 7,
        "snippet_max_chars": 0,
        "content_padding": (8, 6),
        "text_pad_left": 0,
    },
    "none": {
        "width": 0,
        "height": 0,
        "corner_radius": 0,
    }
}


class FloatingHUD:
    """A soft, borderless, draggable floating pill widget with WinUI 3 Acrylic styling and multiple size styles."""

    def __init__(self, master, on_pause_toggle=None, on_stop=None, style="default", enabled=True):
        self.master = master
        self.on_pause_toggle = on_pause_toggle
        self.on_stop = on_stop

        self.current_style = style if style in HUD_STYLES else "default"
        self.enabled = (self.current_style != "none") and bool(enabled)

        self.window = ctk.CTkToplevel(master)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)

        # Detect optimal icon font and glyph symbols
        self.icon_font, self.icons = self._detect_icon_font_and_glyphs()

        # Semi-transparency & Transparent Color Keying (completely removes outer square corners)
        try:
            self.window.configure(fg_color=TRANS_KEY_COLOR)
            self.window.wm_attributes("-transparentcolor", TRANS_KEY_COLOR)
            self.window.attributes("-alpha", 0.90)
        except Exception:
            pass

        # Dimensions & default placement
        cfg = HUD_STYLES.get(self.current_style, HUD_STYLES["default"])
        self.width = cfg.get("width", 440)
        self.height = cfg.get("height", 74)
        self._set_default_position()

        # Dragging state
        self._offset_x = 0
        self._offset_y = 0

        # Animation state
        self._is_animating = False
        self._is_paused = False
        self._is_alive = True
        self._anim_phase = 0.0

        # Widget references
        self.capsule = None
        self.badge = None
        self.wave_canvas = None
        self.wave_bars = []
        self.text_container = None
        self.dot_canvas = None
        self.dot_id = None
        self.status_label = None
        self.sentence_label = None
        self.btn_frame = None
        self.pause_btn = None
        self.stop_btn = None

        self._build_ui()
        self._apply_dwm_attributes()

    def _detect_icon_font_and_glyphs(self):
        """Detect the best installed Fluent / Segoe icon font and return font name and glyph mapping."""
        try:
            import tkinter.font as tkfont
            families = tkfont.families(self.window)
            if "Segoe Fluent Icons" in families:
                return "Segoe Fluent Icons", {"pause": "\uE769", "play": "\uE768", "stop": "\uE71A"}
            if "Segoe MDL2 Assets" in families:
                return "Segoe MDL2 Assets", {"pause": "\uE769", "play": "\uE768", "stop": "\uE71A"}
            if "Segoe UI Symbol" in families:
                return "Segoe UI Symbol", {"pause": "\u23F8", "play": "\u25B6", "stop": "\u25FC"}
        except Exception:
            pass
        return "Segoe UI", {"pause": "❚❚", "play": "▶", "stop": "■"}

    def _apply_dwm_attributes(self):
        """Disables DWM non-client rendering and rectangular drop shadows completely."""
        try:
            self.window.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.window.winfo_id())
            if not hwnd:
                hwnd = self.window.winfo_id()
            dwm = ctypes.windll.dwmapi
            # DWMWA_NCRENDERING_POLICY = 2, DWMNCRP_DISABLED = 1 (removes DWM drop shadow)
            dwm.DwmSetWindowAttribute(hwnd, 2, ctypes.byref(ctypes.c_int(1)), 4)
            # DWMWA_WINDOW_CORNER_PREFERENCE = 33, DWMWCP_DONOTROUND = 1 (prevents DWM shadow generator)
            dwm.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(ctypes.c_int(1)), 4)
            # DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(ctypes.c_int(1)), 4)
            # Remove Win32 window class drop shadow if present
            try:
                style = ctypes.windll.user32.GetClassLongW(hwnd, -26)
                ctypes.windll.user32.SetClassLongW(hwnd, -26, style & ~0x00020000)
            except Exception:
                pass
        except Exception:
            pass

    def _set_default_position(self):
        try:
            screen_w = self.master.winfo_screenwidth()
            screen_h = self.master.winfo_screenheight()
            x = max(20, screen_w - self.width - 35)
            y = max(20, screen_h - self.height - 85)
            self.window.geometry(f"{self.width}x{self.height}+{x}+{y}")
        except Exception:
            pass

    def _build_ui(self):
        # Clear any existing child widgets
        for widget in self.window.winfo_children():
            try:
                widget.destroy()
            except Exception:
                pass

        if self.current_style == "none" or not self.enabled:
            return

        cfg = HUD_STYLES.get(self.current_style, HUD_STYLES["default"])
        self.width = cfg["width"]
        self.height = cfg["height"]

        # Outer padding frame colored with TRANS_KEY_COLOR with zero padding (no extra shadow margin)
        outer_container = tk.Frame(self.window, bg=TRANS_KEY_COLOR)
        outer_container.pack(fill="both", expand=True, padx=0, pady=0)
        outer_container.bind("<Button-1>", self._start_drag)
        outer_container.bind("<B1-Motion>", self._on_drag)

        # Main Capsule Frame: Fully rounded pebble
        self.capsule = ctk.CTkFrame(
            outer_container,
            corner_radius=cfg["corner_radius"],
            fg_color="#1A1816",
            border_width=1,
            border_color="#4F4336"
        )
        self.capsule.pack(fill="both", expand=True)
        self.capsule.bind("<Button-1>", self._start_drag)
        self.capsule.bind("<B1-Motion>", self._on_drag)

        pad_x, pad_y = cfg["content_padding"]
        content_row = ctk.CTkFrame(self.capsule, fg_color="transparent")
        content_row.pack(fill="both", expand=True, padx=pad_x, pady=pad_y)
        content_row.bind("<Button-1>", self._start_drag)
        content_row.bind("<B1-Motion>", self._on_drag)

        # 1. AI Neural Pulse / Waveform Icon Badge
        bs = cfg["badge_size"]
        self.badge = ctk.CTkFrame(
            content_row,
            width=bs,
            height=bs,
            corner_radius=cfg["badge_radius"],
            fg_color="#2A231C",
            border_width=1,
            border_color="#544636"
        )
        self.badge.pack(side="left", padx=(0, 6 if self.current_style == "tiny" else 10))
        self.badge.pack_propagate(False)
        self.badge.bind("<Button-1>", self._start_drag)
        self.badge.bind("<B1-Motion>", self._on_drag)

        cw, ch = cfg["canvas_size"]
        self.wave_canvas = tk.Canvas(
            self.badge,
            width=cw,
            height=ch,
            bg="#2A231C",
            highlightthickness=0
        )
        self.wave_canvas.pack(expand=True)
        self.wave_canvas.bind("<Button-1>", self._start_drag)
        self.wave_canvas.bind("<B1-Motion>", self._on_drag)

        xs = cfg["wave_bar_xs"]
        cy = cfg["wave_center_y"]
        bar_w = 3 if bs >= 34 else 2
        self.wave_bars = [
            self.wave_canvas.create_line(xs[0], cy - 2, xs[0], cy + 2, width=bar_w, capstyle=tk.ROUND, fill="#FAEDCD"),
            self.wave_canvas.create_line(xs[1], cy - 3, xs[1], cy + 3, width=bar_w, capstyle=tk.ROUND, fill="#FDE68A"),
            self.wave_canvas.create_line(xs[2], cy - 2, xs[2], cy + 2, width=bar_w, capstyle=tk.ROUND, fill="#FAEDCD"),
        ]

        # 2. Content Area: Status & Snippet (for default and small styles)
        if cfg["show_status"]:
            self.text_container = ctk.CTkFrame(content_row, fg_color="transparent")
            self.text_container.pack(side="left", fill="both", expand=True, padx=cfg["text_pad_left"])
            self.text_container.bind("<Button-1>", self._start_drag)
            self.text_container.bind("<B1-Motion>", self._on_drag)

            status_row = ctk.CTkFrame(self.text_container, fg_color="transparent")
            status_row.pack(fill="x", pady=(1 if self.current_style == "small" else 2, 0))
            status_row.bind("<Button-1>", self._start_drag)
            status_row.bind("<B1-Motion>", self._on_drag)

            dot_size = 8 if self.current_style == "small" else 10
            self.dot_canvas = tk.Canvas(
                status_row,
                width=dot_size,
                height=dot_size,
                bg="#1A1816",
                highlightthickness=0
            )
            self.dot_canvas.pack(side="left", padx=(0, 4))
            self.dot_canvas.bind("<Button-1>", self._start_drag)
            self.dot_canvas.bind("<B1-Motion>", self._on_drag)
            self.dot_id = self.dot_canvas.create_oval(1, 1, dot_size - 1, dot_size - 1, fill="#FCD34D", outline="")

            self.status_label = ctk.CTkLabel(
                status_row,
                text="Reading selected text...",
                font=("Segoe UI", cfg["status_font_size"], "bold"),
                text_color="#FAEDCD",
                anchor="w"
            )
            self.status_label.pack(side="left", fill="x", expand=True)
            self.status_label.bind("<Button-1>", self._start_drag)
            self.status_label.bind("<B1-Motion>", self._on_drag)

            if cfg["show_sentence"]:
                self.sentence_label = ctk.CTkLabel(
                    self.text_container,
                    text="Highlight any text and press Ctrl+Shift+R...",
                    font=("Segoe UI", cfg["snippet_font_size"]),
                    text_color="#E6D5BC",
                    anchor="w"
                )
                self.sentence_label.pack(fill="x", pady=(0 if self.current_style == "small" else 1, 0))
                self.sentence_label.bind("<Button-1>", self._start_drag)
                self.sentence_label.bind("<B1-Motion>", self._on_drag)
            else:
                self.sentence_label = None
        else:
            self.text_container = None
            self.dot_canvas = None
            self.dot_id = None
            self.status_label = None
            self.sentence_label = None

        # In 'tiny' style, add a subtle glowing status dot between badge and controls
        if self.current_style == "tiny":
            self.dot_canvas = tk.Canvas(
                content_row,
                width=8,
                height=8,
                bg="#1A1816",
                highlightthickness=0
            )
            self.dot_canvas.pack(side="left", padx=(0, 6))
            self.dot_canvas.bind("<Button-1>", self._start_drag)
            self.dot_canvas.bind("<B1-Motion>", self._on_drag)
            self.dot_id = self.dot_canvas.create_oval(1, 1, 7, 7, fill="#FCD34D", outline="")

        # 3. Minimalist Interactive Control Buttons (WinUI 3 Segoe Fluent Icons)
        btn_s = cfg["btn_size"]
        btn_r = cfg["btn_radius"]
        f_size = cfg["font_size_btn"]
        btn_font = (self.icon_font, f_size if "Segoe" in self.icon_font else max(8, f_size - 1))

        self.btn_frame = ctk.CTkFrame(content_row, fg_color="transparent")
        self.btn_frame.pack(side="right", padx=(2 if self.current_style == "tiny" else 6, 0))

        # Pause / Resume Button (Warm Champagne)
        self.pause_btn = ctk.CTkButton(
            self.btn_frame,
            text=self.icons["pause"],
            width=btn_s,
            height=btn_s,
            corner_radius=btn_r,
            fg_color="#2A231C",
            hover_color="#3D342B",
            border_width=1,
            border_color="#544636",
            text_color="#FAEDCD",
            font=btn_font,
            command=self._handle_pause_click
        )
        self.pause_btn.pack(side="left", padx=2 if self.current_style == "tiny" else 3)

        # Stop Button (Rose 500 Tint)
        self.stop_btn = ctk.CTkButton(
            self.btn_frame,
            text=self.icons["stop"],
            width=btn_s,
            height=btn_s,
            corner_radius=btn_r,
            fg_color="#3C1820",
            hover_color="#52212D",
            border_width=1,
            border_color="#7F2736",
            text_color="#FECDD3",
            font=btn_font,
            command=self._handle_stop_click
        )
        self.stop_btn.pack(side="left", padx=2 if self.current_style == "tiny" else 3)

    def set_style(self, style, enabled=True):
        """Dynamically update HUD style ('default', 'small', 'tiny', 'none') and rebuild widgets."""
        if style not in HUD_STYLES:
            style = "default"
        self.current_style = style
        self.enabled = (style != "none") and bool(enabled)

        was_visible = False
        try:
            was_visible = bool(self.window.winfo_viewable())
        except Exception:
            pass

        self.stop_wave_animation()

        if not self.enabled or self.current_style == "none":
            self.window.withdraw()
            return

        self._build_ui()
        self._apply_dwm_attributes()
        self._set_default_position()

        if was_visible:
            self.show()

    def preview(self, style=None):
        """Previews the pop-up on screen for 4 seconds so user can see their style choice."""
        if style:
            self.set_style(style, enabled=(style != "none"))
        if not self.enabled or self.current_style == "none":
            return
        self.show("Previewing SpeakThat Floating Pop-up Widget...")
        self.window.after(4000, self.hide)

    def _start_drag(self, event):
        self._offset_x = event.x_root - self.window.winfo_x()
        self._offset_y = event.y_root - self.window.winfo_y()

    def _on_drag(self, event):
        x = event.x_root - self._offset_x
        y = event.y_root - self._offset_y
        self.window.geometry(f"+{x}+{y}")

    def show(self, sentence="Reading selected text..."):
        if not self.enabled or self.current_style == "none":
            return
        self._is_paused = False
        self.update_sentence(sentence)
        if getattr(self, "pause_btn", None):
            self.pause_btn.configure(text=self.icons["pause"])
        if getattr(self, "status_label", None):
            self.status_label.configure(text="Reading selected text...", text_color="#FAEDCD")
        if getattr(self, "dot_canvas", None) and getattr(self, "dot_id", None):
            self.dot_canvas.itemconfig(self.dot_id, fill="#FCD34D")
        if getattr(self, "capsule", None):
            self.capsule.configure(border_color="#5E4F3D")
        self.window.deiconify()
        self.window.lift()
        self.start_wave_animation()

    def show_warming_up(self, sentence="Loading AI model..."):
        if not self.enabled or self.current_style == "none":
            return
        self._is_paused = False
        self.update_sentence(sentence)
        if getattr(self, "pause_btn", None):
            self.pause_btn.configure(text=self.icons["pause"])
        if getattr(self, "status_label", None):
            self.status_label.configure(text="AI Voice Engine Warming Up...", text_color="#FCD34D")
        if getattr(self, "dot_canvas", None) and getattr(self, "dot_id", None):
            self.dot_canvas.itemconfig(self.dot_id, fill="#F59E0B")
        if getattr(self, "capsule", None):
            self.capsule.configure(border_color="#785936")
        self.window.deiconify()
        self.window.lift()
        self.start_wave_animation()

    def update_status(self, status):
        if not getattr(self, "_is_alive", True) or not self.enabled or self.current_style == "none":
            return
        try:
            color = "#FCD34D"
            text = "Reading selected text..."
            if status == "Speaking":
                text = "Reading selected text..."
                color = "#FCD34D"
            elif status == "Synthesizing...":
                text = "Synthesizing audio..."
                color = "#FDE68A"
            elif "Warming" in status or "Loading" in status:
                text = "AI Engine Warming Up..."
                color = "#F59E0B"
            elif status == "Paused":
                text = "Paused (Click to resume)"
                color = "#F59E0B"

            if getattr(self, "status_label", None):
                self.status_label.configure(text=text, text_color=color)
            if getattr(self, "dot_canvas", None) and getattr(self, "dot_id", None):
                self.dot_canvas.itemconfig(self.dot_id, fill=color)
        except Exception:
            pass

    def hide(self):
        self.stop_wave_animation()
        try:
            self.window.withdraw()
        except Exception:
            pass

    def update_sentence(self, text):
        if not getattr(self, "sentence_label", None):
            return
        cfg = HUD_STYLES.get(self.current_style, HUD_STYLES["default"])
        max_c = cfg.get("snippet_max_chars", 46)
        clean = text.strip().replace("\n", " ")
        if len(clean) > max_c:
            clean = clean[:max(10, max_c - 3)] + "…"
        try:
            self.sentence_label.configure(text=f'"{clean}"')
        except Exception:
            pass

    def set_paused_state(self, is_paused):
        if not getattr(self, "_is_alive", True) or not self.enabled or self.current_style == "none":
            return
        self._is_paused = is_paused
        if is_paused:
            if getattr(self, "pause_btn", None):
                self.pause_btn.configure(text=self.icons["play"])
            if getattr(self, "status_label", None):
                self.status_label.configure(text="Paused (Click to resume)", text_color="#F59E0B")
            if getattr(self, "dot_canvas", None) and getattr(self, "dot_id", None):
                self.dot_canvas.itemconfig(self.dot_id, fill="#F59E0B")
            if getattr(self, "capsule", None):
                self.capsule.configure(border_color="#8C775D")
            self.stop_wave_animation()
        else:
            if getattr(self, "pause_btn", None):
                self.pause_btn.configure(text=self.icons["pause"])
            if getattr(self, "status_label", None):
                self.status_label.configure(text="Reading selected text...", text_color="#FAEDCD")
            if getattr(self, "dot_canvas", None) and getattr(self, "dot_id", None):
                self.dot_canvas.itemconfig(self.dot_id, fill="#FCD34D")
            if getattr(self, "capsule", None):
                self.capsule.configure(border_color="#5E4F3D")
            self.start_wave_animation()

    def start_wave_animation(self):
        if not self._is_animating and self.enabled and self.current_style != "none":
            self._is_animating = True
            self._animate_wave()

    def stop_wave_animation(self):
        self._is_animating = False
        try:
            cfg = HUD_STYLES.get(self.current_style, HUD_STYLES["default"])
            xs = cfg.get("wave_bar_xs", [7, 15, 23])
            cy = cfg.get("wave_center_y", 13)
            if self.wave_canvas and self.wave_bars and len(self.wave_bars) >= 3:
                self.wave_canvas.coords(self.wave_bars[0], xs[0], cy - 2, xs[0], cy + 2)
                self.wave_canvas.coords(self.wave_bars[1], xs[1], cy - 3, xs[1], cy + 3)
                self.wave_canvas.coords(self.wave_bars[2], xs[2], cy - 2, xs[2], cy + 2)
                for b in self.wave_bars:
                    self.wave_canvas.itemconfig(b, fill="#786B5E")
        except Exception:
            pass

    def _animate_wave(self):
        if not getattr(self, "_is_alive", True) or not self._is_animating or self._is_paused or not self.enabled:
            return

        try:
            cfg = HUD_STYLES.get(self.current_style, HUD_STYLES["default"])
            if not self.wave_canvas or not self.wave_bars or len(self.wave_bars) < 3:
                return

            self._anim_phase += 0.22
            cy = cfg.get("wave_center_y", 13)
            xs = cfg.get("wave_bar_xs", [7, 15, 23])
            m1, m2, m3 = cfg.get("wave_max_h", (10, 14, 10))

            h1 = 3 + int(m1 * abs(math.sin(self._anim_phase * 1.1)))
            h2 = 3 + int(m2 * abs(math.sin(self._anim_phase * 1.5 + 0.3)))
            h3 = 3 + int(m3 * abs(math.sin(self._anim_phase * 0.9 + 0.7)))

            self.wave_canvas.coords(self.wave_bars[0], xs[0], cy - h1 // 2, xs[0], cy + h1 // 2)
            self.wave_canvas.coords(self.wave_bars[1], xs[1], cy - h2 // 2, xs[1], cy + h2 // 2)
            self.wave_canvas.coords(self.wave_bars[2], xs[2], cy - h3 // 2, xs[2], cy + h3 // 2)

            self.wave_canvas.itemconfig(self.wave_bars[0], fill="#FAEDCD")
            self.wave_canvas.itemconfig(self.wave_bars[1], fill="#FDE68A")
            self.wave_canvas.itemconfig(self.wave_bars[2], fill="#FAEDCD")

            if getattr(self, "_is_alive", True):
                self.window.after(50, self._animate_wave)
        except Exception:
            pass

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
