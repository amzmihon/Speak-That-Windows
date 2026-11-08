"""WinUI 3 Fluent Glassmorphism Floating Capsule HUD for SpeakThat.

Key Improvements:
- 100% transparent window canvas (-transparentcolor) completely eliminates rectangular box artifacts.
- Fully rounded 26px pebble capsule with zero sharp or pointy edges.
- Semi-transparent frosted glass aesthetic with -alpha 0.90.
- Official Microsoft Fluent Icons (Segoe Fluent Icons / Segoe MDL2 Assets) for Pause, Play, and Stop.
- AI Neural Pulse icon badge with 3 smooth, rounded sinusoidal wave bars.
- Amber status indicator dot and warm champagne/wheat typography.
- Smooth Windows 11 DWM rounded corner clipping.
"""

import ctypes
import math
import tkinter as tk
import customtkinter as ctk

# Color key used by Windows DWM compositor to make rectangular window boundaries 100% invisible
TRANS_KEY_COLOR = "#000001"


class FloatingHUD:
    """A soft, borderless, draggable floating pill widget with WinUI 3 Acrylic styling."""

    def __init__(self, master, on_pause_toggle=None, on_stop=None):
        self.master = master
        self.on_pause_toggle = on_pause_toggle
        self.on_stop = on_stop

        self.window = ctk.CTkToplevel(master)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)

        # Detect optimal icon font and glyph symbols after window handle exists
        self.icon_font, self.icons = self._detect_icon_font_and_glyphs()

        # Semi-transparency & Transparent Color Keying (completely removes outer square corners)
        try:
            self.window.configure(fg_color=TRANS_KEY_COLOR)
            self.window.wm_attributes("-transparentcolor", TRANS_KEY_COLOR)
            self.window.attributes("-alpha", 0.90)
        except Exception:
            pass

        # Apply Windows 11 DWM attributes (strictly disables rectangular drop shadow)
        self._apply_dwm_attributes()

        # Dimensions & default placement
        self.width = 440
        self.height = 74
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
        screen_w = self.master.winfo_screenwidth()
        screen_h = self.master.winfo_screenheight()
        x = max(20, screen_w - self.width - 35)
        y = max(20, screen_h - self.height - 85)
        self.window.geometry(f"{self.width}x{self.height}+{x}+{y}")

    def _build_ui(self):
        # Outer padding frame colored with TRANS_KEY_COLOR with zero padding (no extra shadow margin)
        outer_container = tk.Frame(self.window, bg=TRANS_KEY_COLOR)
        outer_container.pack(fill="both", expand=True, padx=0, pady=0)
        outer_container.bind("<Button-1>", self._start_drag)
        outer_container.bind("<B1-Motion>", self._on_drag)

        # Main Capsule Frame: Fully rounded pebble (corner_radius=26)
        self.capsule = ctk.CTkFrame(
            outer_container,
            corner_radius=26,
            fg_color="#1A1816",
            border_width=1,
            border_color="#4F4336"
        )
        self.capsule.pack(fill="both", expand=True)

        self.capsule.bind("<Button-1>", self._start_drag)
        self.capsule.bind("<B1-Motion>", self._on_drag)

        # Main Content Row
        content_row = ctk.CTkFrame(self.capsule, fg_color="transparent")
        content_row.pack(fill="both", expand=True, padx=14, pady=10)
        content_row.bind("<Button-1>", self._start_drag)
        content_row.bind("<B1-Motion>", self._on_drag)

        # 1. AI Neural Pulse / Waveform Icon Badge
        self.badge = ctk.CTkFrame(
            content_row,
            width=42,
            height=42,
            corner_radius=14,
            fg_color="#2A231C",
            border_width=1,
            border_color="#544636"
        )
        self.badge.pack(side="left", padx=(0, 10))
        self.badge.pack_propagate(False)
        self.badge.bind("<Button-1>", self._start_drag)
        self.badge.bind("<B1-Motion>", self._on_drag)

        # 3 Sound wave animation bars inside the badge
        self.wave_canvas = tk.Canvas(
            self.badge,
            width=32,
            height=26,
            bg="#2A231C",
            highlightthickness=0
        )
        self.wave_canvas.pack(expand=True)
        self.wave_canvas.bind("<Button-1>", self._start_drag)
        self.wave_canvas.bind("<B1-Motion>", self._on_drag)

        self.wave_bars = [
            self.wave_canvas.create_line(7, 11, 7, 15, width=3, capstyle=tk.ROUND, fill="#FAEDCD"),
            self.wave_canvas.create_line(15, 9, 15, 17, width=3, capstyle=tk.ROUND, fill="#FDE68A"),
            self.wave_canvas.create_line(23, 11, 23, 15, width=3, capstyle=tk.ROUND, fill="#FAEDCD"),
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
            bg="#1A1816",
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

        # 3. Minimalist Interactive Control Buttons (WinUI 3 Segoe Fluent Icons)
        self.btn_frame = ctk.CTkFrame(content_row, fg_color="transparent")
        self.btn_frame.pack(side="right", padx=(6, 0))

        # Pause / Resume Button (Warm Champagne)
        self.pause_btn = ctk.CTkButton(
            self.btn_frame,
            text=self.icons["pause"],
            width=32,
            height=32,
            corner_radius=12,
            fg_color="#2A231C",
            hover_color="#3D342B",
            border_width=1,
            border_color="#544636",
            text_color="#FAEDCD",
            font=(self.icon_font, 12 if "Segoe" in self.icon_font else 10),
            command=self._handle_pause_click
        )
        self.pause_btn.pack(side="left", padx=3)

        # Stop Button (Rose 500 Tint)
        self.stop_btn = ctk.CTkButton(
            self.btn_frame,
            text=self.icons["stop"],
            width=32,
            height=32,
            corner_radius=12,
            fg_color="#3C1820",
            hover_color="#52212D",
            border_width=1,
            border_color="#7F2736",
            text_color="#FECDD3",
            font=(self.icon_font, 12 if "Segoe" in self.icon_font else 10),
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

    def show(self, sentence="Reading selected text..."):
        self._is_paused = False
        self.update_sentence(sentence)
        self.pause_btn.configure(text=self.icons["pause"])
        self.status_label.configure(text="Reading selected text...", text_color="#FAEDCD")
        self.dot_canvas.itemconfig(self.dot_id, fill="#FCD34D")
        self.capsule.configure(border_color="#5E4F3D")
        self.window.deiconify()
        self.window.lift()
        self.start_wave_animation()

    def show_warming_up(self, sentence="Loading AI model..."):
        self._is_paused = False
        self.update_sentence(sentence)
        self.pause_btn.configure(text=self.icons["pause"])
        self.status_label.configure(text="AI Voice Engine Warming Up...", text_color="#FCD34D")
        self.dot_canvas.itemconfig(self.dot_id, fill="#F59E0B")
        self.capsule.configure(border_color="#785936")
        self.window.deiconify()
        self.window.lift()
        self.start_wave_animation()

    def update_status(self, status):
        if not getattr(self, "_is_alive", True):
            return
        try:
            if status == "Speaking":
                self.status_label.configure(text="Reading selected text...", text_color="#FAEDCD")
                self.dot_canvas.itemconfig(self.dot_id, fill="#FCD34D")
            elif status == "Synthesizing...":
                self.status_label.configure(text="Synthesizing audio...", text_color="#FDE68A")
                self.dot_canvas.itemconfig(self.dot_id, fill="#FDE68A")
            elif "Warming" in status or "Loading" in status:
                self.status_label.configure(text="AI Engine Warming Up...", text_color="#F59E0B")
                self.dot_canvas.itemconfig(self.dot_id, fill="#F59E0B")
            elif status == "Paused":
                self.status_label.configure(text="Paused (Click to resume)", text_color="#F59E0B")
                self.dot_canvas.itemconfig(self.dot_id, fill="#F59E0B")
        except Exception:
            pass

    def hide(self):
        self.stop_wave_animation()
        self.window.withdraw()

    def update_sentence(self, text):
        clean = text.strip().replace("\n", " ")
        if len(clean) > 46:
            clean = clean[:43] + "…"
        self.sentence_label.configure(text=f'"{clean}"')

    def set_paused_state(self, is_paused):
        self._is_paused = is_paused
        if is_paused:
            self.pause_btn.configure(text=self.icons["play"])
            self.status_label.configure(text="Paused (Click to resume)", text_color="#F59E0B")
            self.dot_canvas.itemconfig(self.dot_id, fill="#F59E0B")
            self.capsule.configure(border_color="#8C775D")
            self.stop_wave_animation()
        else:
            self.pause_btn.configure(text=self.icons["pause"])
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
        try:
            self.wave_canvas.coords(self.wave_bars[0], 7, 11, 7, 15)
            self.wave_canvas.coords(self.wave_bars[1], 15, 10, 15, 16)
            self.wave_canvas.coords(self.wave_bars[2], 23, 11, 23, 15)
            for b in self.wave_bars:
                self.wave_canvas.itemconfig(b, fill="#786B5E")
        except Exception:
            pass

    def _animate_wave(self):
        if not getattr(self, "_is_alive", True) or not self._is_animating or self._is_paused:
            return

        try:
            self._anim_phase += 0.22

            # 3 frequencies matching the HTML animation: 1.1s, 0.8s, 1.3s
            h1 = 4 + int(10 * abs(math.sin(self._anim_phase * 1.1)))
            h2 = 4 + int(14 * abs(math.sin(self._anim_phase * 1.5 + 0.3)))
            h3 = 4 + int(10 * abs(math.sin(self._anim_phase * 0.9 + 0.7)))

            # Update coords centered around y=13
            self.wave_canvas.coords(self.wave_bars[0], 7, max(3, 13 - h1 // 2), 7, min(23, 13 + h1 // 2))
            self.wave_canvas.coords(self.wave_bars[1], 15, max(2, 13 - h2 // 2), 15, min(24, 13 + h2 // 2))
            self.wave_canvas.coords(self.wave_bars[2], 23, max(3, 13 - h3 // 2), 23, min(23, 13 + h3 // 2))

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
