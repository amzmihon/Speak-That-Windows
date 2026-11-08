"""Modern CustomTkinter Dashboard & Studio for SpeakThat.

Key UI/UX Enhancements:
- Softened, less-edged design with rounded corners (16-18px), gentle contrast, and warm accents.
- Dynamic window sizing with step configuration (width in steps of 200, height in steps of 100, up to 1400x900 max based on screen space).
- Zero scrollbars at default size (all views budget vertical space to fit cleanly within available stage).
- Navigation Rail + Stage architecture across Studio Reader, Voice Personas, Shortcuts & Behavior, and Model Benchmark.
- High-performance animated waveform monitor and live sentence marquee.
"""

import os
import sys
import math
import time
import ctypes
import threading
import tkinter as tk
import customtkinter as ctk
from PIL import Image

from .config import VOICE_NAMES
from .hotkeys import format_hotkey_for_display, validate_hotkey, normalize_hotkey


VOICE_DETAILS = {
    "bf_isabella": {
        "name": "Isabella",
        "flag": "🇬🇧",
        "locale": "British Female",
        "tag": "Narrative",
        "desc": "Crisp British cadence for docs & articles.",
        "sample": "Hello! I am Isabella. Paradee is a small voice that runs anywhere."
    },
    "af_heart": {
        "name": "Heart",
        "flag": "🇺🇸",
        "locale": "American Female",
        "tag": "Warm",
        "desc": "Expressive American female voice for dialogues.",
        "sample": "Hi there! I'm Heart. Ready to read anything on your screen."
    },
    "am_puck": {
        "name": "Puck",
        "flag": "🇺🇸",
        "locale": "American Male",
        "tag": "Crisp",
        "desc": "Sharp enunciation for code & quick summaries.",
        "sample": "Greetings! I'm Puck. Fast, local text-to-speech right on your machine."
    },
    "bm_fable": {
        "name": "Fable",
        "flag": "🇬🇧",
        "locale": "British Male",
        "tag": "Resonant",
        "desc": "Deep, articulate tone for storytelling & essays.",
        "sample": "Greetings. I am Fable. Bring your text to life with resonant British narration."
    }
}


class ShortcutRecorderDialog(ctk.CTkToplevel):
    """WinUI 3 Modal Dialog for capturing or typing customized keyboard shortcuts."""

    def __init__(self, master, action_name, current_hotkey, on_save):
        super().__init__(master)
        self.action_name = action_name
        self.on_save = on_save
        self.captured_hotkey = current_hotkey

        self.title(f"Customize Shortcut — {action_name}")
        self.geometry("460x280")
        self.resizable(False, False)
        self.configure(fg_color="#121622")
        self.transient(master)
        self.attributes("-topmost", True)

        try:
            self.update_idletasks()
            mx = master.winfo_x()
            my = master.winfo_y()
            mw = master.winfo_width()
            mh = master.winfo_height()
            x = mx + max(20, (mw - 460) // 2)
            y = my + max(20, (mh - 280) // 2)
            self.geometry(f"+{x}+{y}")
        except Exception:
            pass

        self._build_ui(current_hotkey)

        self.bind("<KeyPress>", self._on_key_press)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.after(100, self.focus_force)

    def _build_ui(self, current_hotkey):
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=22, pady=18)

        # Title
        t_row = ctk.CTkFrame(container, fg_color="transparent")
        t_row.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(
            t_row,
            text=f"CUSTOMIZE SHORTCUT: {self.action_name.upper()}",
            font=("Segoe UI", 11, "bold"),
            text_color="#818CF8"
        ).pack(side="left")

        # Instruction
        ctk.CTkLabel(
            container,
            text="Press any key combination on your keyboard, select a preset, or type below:",
            font=("Segoe UI", 9),
            text_color="#94A3B8"
        ).pack(anchor="w", pady=(0, 10))

        # Active shortcut display card
        disp_card = ctk.CTkFrame(container, corner_radius=12, fg_color="#1A2234", border_width=1, border_color="#334155")
        disp_card.pack(fill="x", pady=(0, 8))

        self.display_label = ctk.CTkLabel(
            disp_card,
            text=format_hotkey_for_display(current_hotkey) or "Press keys...",
            font=("Segoe UI", 15, "bold"),
            text_color="#F8FAFC",
            height=46
        )
        self.display_label.pack(fill="x", padx=14)

        # Status note
        self.status_label = ctk.CTkLabel(
            container,
            text="Listening for key combinations... (e.g. Ctrl+Alt+S, Alt+R, F9, Ctrl+Space)",
            font=("Segoe UI", 8),
            text_color="#64748B"
        )
        self.status_label.pack(anchor="w", pady=(0, 10))

        # Quick Presets row
        pres_row = ctk.CTkFrame(container, fg_color="transparent")
        pres_row.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(pres_row, text="Presets:", font=("Segoe UI", 9, "bold"), text_color="#64748B").pack(side="left", padx=(0, 6))

        presets = ["Ctrl+Shift+R", "Ctrl+Alt+S", "Alt+S", "Ctrl+Space"] if "Read" in self.action_name else ["Ctrl+Shift+X", "Ctrl+Alt+X", "Alt+X", "Esc"]
        for p in presets:
            ctk.CTkButton(
                pres_row,
                text=p,
                width=72,
                height=24,
                corner_radius=8,
                font=("Segoe UI", 8, "bold"),
                fg_color="#151C2C",
                hover_color="#2D3A54",
                text_color="#CBD5E1",
                border_width=1,
                border_color="#334155",
                command=lambda pk=p: self._set_preset(pk)
            ).pack(side="left", padx=3)

        # Action Buttons (Cancel & Save)
        btn_row = ctk.CTkFrame(container, fg_color="transparent")
        btn_row.pack(fill="x")

        ctk.CTkButton(
            btn_row,
            text="Cancel",
            width=80,
            height=30,
            corner_radius=10,
            fg_color="#1E293B",
            hover_color="#334155",
            text_color="#94A3B8",
            font=("Segoe UI", 9, "bold"),
            command=self.destroy
        ).pack(side="right", padx=(8, 0))

        self.save_btn = ctk.CTkButton(
            btn_row,
            text="Save Shortcut",
            width=115,
            height=30,
            corner_radius=10,
            fg_color="#6366F1",
            hover_color="#4F46E5",
            text_color="#FFFFFF",
            font=("Segoe UI", 9, "bold"),
            command=self._do_save
        )
        self.save_btn.pack(side="right")

    def _set_preset(self, preset_str):
        valid, norm = validate_hotkey(preset_str)
        if valid:
            self.captured_hotkey = norm
            self.display_label.configure(text=format_hotkey_for_display(norm), text_color="#10B981")
            self.status_label.configure(text="Preset selected. Click 'Save Shortcut' to apply.", text_color="#10B981")

    def _on_key_press(self, event):
        keysym = event.keysym
        if keysym == "Escape" and not (event.state & 0x0004 or event.state & 0x20000 or event.state & 0x0001):
            if "Stop" in self.action_name:
                self.captured_hotkey = "<esc>"
                self.display_label.configure(text="Esc", text_color="#10B981")
                self.status_label.configure(text="Esc selected! Click 'Save Shortcut' to apply.", text_color="#10B981")
                return
            else:
                self.destroy()
                return

        # Determine modifiers
        mods = []
        if (event.state & 0x0004) or keysym.startswith("Control"):
            mods.append("<ctrl>")
        if (event.state & 0x20000) or (event.state & 0x0008) or keysym.startswith("Alt"):
            mods.append("<alt>")
        if (event.state & 0x0001) or keysym.startswith("Shift"):
            mods.append("<shift>")
        if keysym.startswith("Win") or keysym.startswith("Super"):
            mods.append("<cmd>")

        is_modifier = any(keysym.startswith(m) for m in ("Control", "Shift", "Alt", "Win", "Super"))
        if is_modifier:
            disp_mods = [m.replace("<", "").replace(">", "").capitalize() for m in mods]
            self.display_label.configure(text=" + ".join(disp_mods) + " + ...", text_color="#FDE68A")
            return

        # Non-modifier key
        k_lower = keysym.lower()
        if k_lower == "space":
            k = "<space>"
        elif k_lower.startswith("f") and k_lower[1:].isdigit():
            k = f"<{k_lower}>"
        elif len(k_lower) == 1:
            k = k_lower
        elif event.char and event.char.isprintable() and event.char not in " \r\n\t":
            k = event.char.lower()
        else:
            k = f"<{k_lower}>"

        combo_parts = list(mods)
        if k not in combo_parts:
            combo_parts.append(k)

        combo_str = "+".join(combo_parts)
        valid, res = validate_hotkey(combo_str)
        if valid:
            self.captured_hotkey = res
            disp = format_hotkey_for_display(res)
            self.display_label.configure(text=disp, text_color="#10B981")
            self.status_label.configure(text=f"✓ Detected: {disp}! Click 'Save Shortcut' to apply.", text_color="#10B981")
        else:
            self.status_label.configure(text="Combination needs at least one key (e.g., Ctrl + Alt + S).", text_color="#F87171")

    def _do_save(self):
        if self.captured_hotkey and self.on_save:
            self.on_save(self.captured_hotkey)
        self.destroy()


class MainWindow(ctk.CTk):
    """Primary GUI window providing settings, status, manual speech testing, and preferences."""

    def __init__(self, config, engine, on_read_selection=None, on_stop_reading=None, on_quit=None):
        super().__init__()

        self.config = config
        self.engine = engine
        self.on_read_selection = on_read_selection
        self.on_stop_reading = on_stop_reading
        self.on_quit = on_quit
        self.on_hotkey_change = None
        self.hud = None
        self.on_hud_style_change = None
        self.pref_read_badges_frame = None
        self.pref_stop_badges_frame = None
        self.hero_pills_row = None

        # Window Appearance
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.title("SpeakThat — Windows Text Reader (Paradee TTS)")
        self.configure(fg_color="#0D111A")

        # Icons & assets
        self._logo_image = None
        self._set_window_icon()
        self._is_alive = True

        # Screen dimensions & Maximum Step Sizing Calculation
        self._calc_screen_bounds()

        # Load saved or default window size
        saved_w = int(self.config.get("window_width", 1000))
        saved_h = int(self.config.get("window_height", 620))
        init_w = min(self.max_w, max(800, saved_w))
        init_h = min(self.max_h, max(580, saved_h))
        self.geometry(f"{init_w}x{init_h}")

        # Configure minimum and maximum window boundaries
        self.minsize(800, 580)
        self.maxsize(self.max_w, self.max_h)

        # Apply Windows 11 DWM native hardware rounded corners, dark mode & acrylic
        self._apply_dwm_attributes()

        # Animation state for live waveform
        self._is_speaking_anim = False
        self._wave_phase = 0.0
        self._wave_canvas = None
        self._wave_bars = []

        # Current view tracking
        self.current_view_name = "reader"
        self.nav_buttons = {}
        self.views = {}

        # Handle window close protocol
        self.protocol("WM_DELETE_WINDOW", self._on_window_close)

        # Build UI layout
        self._build_layout()

        # Sync UI with config values
        self._load_config_to_ui()

        # Start background waveform loop
        self._animate_stage_wave()

    def _calc_screen_bounds(self):
        """Calculate max window step bounds (width steps of 200, height steps of 100, max 1400x900)."""
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()

        # Cap at 1400x900 default maximum, scaled down by step if screen is smaller
        avail_w = max(800, sw - 40)
        avail_h = max(580, sh - 60)

        # Snap to steps of 200 and 100
        step_w = (avail_w // 200) * 200
        step_h = (avail_h // 100) * 100

        self.max_w = min(1400, max(800, step_w))
        self.max_h = min(900, max(580, step_h))
        self.screen_res = (sw, sh)

    def _apply_dwm_attributes(self):
        """Applies Windows 11 DWM native hardware rounded corners, dark mode, and acrylic backdrop."""
        try:
            self.attributes("-alpha", 0.95)
            self.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            if not hwnd:
                hwnd = self.winfo_id()
            dwm = ctypes.windll.dwmapi
            # DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(ctypes.c_int(1)), 4)
            # DWMWA_WINDOW_CORNER_PREFERENCE = 33, DWMWCP_ROUND = 2 (WinUI 3 standard)
            dwm.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(ctypes.c_int(2)), 4)
            # DWMWA_SYSTEMBACKDROP_TYPE = 38, Acrylic = 3
            dwm.DwmSetWindowAttribute(hwnd, 38, ctypes.byref(ctypes.c_int(3)), 4)
        except Exception:
            pass

    def _set_window_icon(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ico_path = os.path.join(base_dir, "assets", "icon.ico")
        if os.path.exists(ico_path):
            try:
                self.iconbitmap(ico_path)
            except Exception:
                pass

        png_path = os.path.join(base_dir, "assets", "icon.png")
        if os.path.exists(png_path):
            try:
                pil_img = Image.open(png_path)
                self._logo_image = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(30, 30))
            except Exception:
                self._logo_image = None

    def _build_layout(self):
        # Configure root grid: Column 0 = Rail (210px), Column 1 = Stage (expand)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0, minsize=210)
        self.grid_columnconfigure(1, weight=1)

        # 1. Left Navigation Rail
        self._build_navigation_rail()

        # 2. Right Content Stage
        self._build_stage()

    def _build_navigation_rail(self):
        self.rail = ctk.CTkFrame(
            self,
            fg_color="#121722",
            corner_radius=0,
            border_width=1,
            border_color="#1F283B",
            width=210
        )
        self.rail.grid(row=0, column=0, sticky="nsew")
        self.rail.grid_propagate(False)

        # --- Brand Lockup Header ---
        brand_frame = ctk.CTkFrame(self.rail, fg_color="transparent")
        brand_frame.pack(fill="x", padx=14, pady=(16, 12))

        icon_row = ctk.CTkFrame(brand_frame, fg_color="transparent")
        icon_row.pack(fill="x")

        if self._logo_image:
            logo_lbl = ctk.CTkLabel(icon_row, image=self._logo_image, text="")
            logo_lbl.pack(side="left", padx=(0, 8))

        title_box = ctk.CTkFrame(icon_row, fg_color="transparent")
        title_box.pack(side="left", fill="both")

        ctk.CTkLabel(
            title_box,
            text="SpeakThat",
            font=("Segoe UI", 15, "bold"),
            text_color="#F8FAFC"
        ).pack(anchor="w")

        badge = ctk.CTkLabel(
            title_box,
            text="v1.2 • Paradee 8M",
            font=("Segoe UI", 8, "bold"),
            text_color="#818CF8",
            fg_color="#1E1B4B",
            corner_radius=6,
            padx=6,
            pady=1
        )
        badge.pack(anchor="w", pady=(1, 0))

        # Divider
        ctk.CTkFrame(self.rail, height=1, fg_color="#1F283B").pack(fill="x", padx=14, pady=(4, 12))

        # --- Navigation Items ---
        nav_items = [
            ("reader", "🎧", "Studio Reader"),
            ("voices", "🎙️", "Voice Personas"),
            ("shortcuts", "⚡", "Shortcuts & Behavior"),
            ("model", "ℹ️", "Model & Benchmark"),
        ]

        for tab_id, icon, label in nav_items:
            btn = ctk.CTkButton(
                self.rail,
                text=f"  {icon}  {label}",
                font=("Segoe UI", 11),
                anchor="w",
                height=38,
                corner_radius=12,
                fg_color="transparent",
                hover_color="#1A2234",
                text_color="#94A3B8",
                command=lambda tid=tab_id: self.show_view(tid)
            )
            btn.pack(fill="x", padx=10, pady=2)
            self.nav_buttons[tab_id] = btn

        # --- Rail Bottom Status Capsule ---
        rail_bottom = ctk.CTkFrame(self.rail, fg_color="transparent")
        rail_bottom.pack(side="bottom", fill="x", padx=12, pady=14)

        ctk.CTkFrame(rail_bottom, height=1, fg_color="#1F283B").pack(fill="x", pady=(0, 10))

        self.rail_status_pill = ctk.CTkLabel(
            rail_bottom,
            text="● Paradee Ready",
            font=("Segoe UI", 10, "bold"),
            text_color="#10B981",
            fg_color="#064E3B",
            corner_radius=12,
            padx=10,
            pady=3
        )
        self.rail_status_pill.pack(fill="x", pady=(0, 4))

        ctk.CTkLabel(
            rail_bottom,
            text="Global text reader active.\nRuns silently in background.",
            font=("Segoe UI", 8),
            text_color="#64748B",
            justify="left"
        ).pack(anchor="w")

    def _build_stage(self):
        # Stage Outer Container
        self.stage = ctk.CTkFrame(self, fg_color="#0D111A", corner_radius=0)
        self.stage.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.stage.grid_rowconfigure(1, weight=1)
        self.stage.grid_columnconfigure(0, weight=1)

        # Stage Top Header Bar (Persistent)
        self.header_bar = ctk.CTkFrame(
            self.stage,
            fg_color="#111622",
            height=52,
            corner_radius=0,
            border_width=1,
            border_color="#1F283B"
        )
        self.header_bar.grid(row=0, column=0, sticky="new")
        self.header_bar.grid_propagate(False)

        # Header Titles
        hb_left = ctk.CTkFrame(self.header_bar, fg_color="transparent")
        hb_left.pack(side="left", padx=18, pady=8)

        self.view_title_label = ctk.CTkLabel(
            hb_left,
            text="Studio Reader",
            font=("Segoe UI", 14, "bold"),
            text_color="#F8FAFC"
        )
        self.view_title_label.pack(anchor="w")

        self.view_sub_label = ctk.CTkLabel(
            hb_left,
            text="Select text across any Windows app and press Ctrl+Shift+R",
            font=("Segoe UI", 9),
            text_color="#94A3B8"
        )
        self.view_sub_label.pack(anchor="w")

        # Header Right Controls (Status Badge & Pause/Resume)
        hb_right = ctk.CTkFrame(self.header_bar, fg_color="transparent")
        hb_right.pack(side="right", padx=16, pady=10)

        self.status_badge = ctk.CTkLabel(
            hb_right,
            text="● Ready",
            font=("Segoe UI", 10, "bold"),
            text_color="#10B981",
            fg_color="#064E3B",
            corner_radius=10,
            padx=10,
            pady=2
        )
        self.status_badge.pack(side="left", padx=(0, 8))

        self.pause_resume_btn = ctk.CTkButton(
            hb_right,
            text="⏸ Pause",
            width=76,
            height=26,
            corner_radius=10,
            font=("Segoe UI", 10),
            fg_color="#1A2234",
            hover_color="#2D3A54",
            command=self._on_click_pause_resume
        )
        self.pause_resume_btn.pack(side="left")

        # Content container where active view sits (Regular Frame: NO SCROLLBAR AT DEFAULT SIZE)
        self.view_container = ctk.CTkFrame(self.stage, fg_color="transparent")
        self.view_container.grid(row=1, column=0, sticky="nsew", padx=16, pady=12)
        self.view_container.grid_rowconfigure(0, weight=1)
        self.view_container.grid_columnconfigure(0, weight=1)

        # Build all 4 views (using non-scrollable CTkFrame containers sized cleanly)
        self.views["reader"] = self._create_reader_view()
        self.views["voices"] = self._create_voices_view()
        self.views["shortcuts"] = self._create_shortcuts_view()
        self.views["model"] = self._create_model_view()

        # Display default view
        self.show_view("reader")

    def show_view(self, name):
        self.current_view_name = name

        # Update Rail button states
        for tid, btn in self.nav_buttons.items():
            if tid == name:
                btn.configure(
                    fg_color="#1A2234",
                    text_color="#F8FAFC",
                    border_width=1,
                    border_color="#6366F1"
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color="#94A3B8",
                    border_width=0
                )

        # Hide all views and show selected
        for vname, vframe in self.views.items():
            if vname == name:
                vframe.grid(row=0, column=0, sticky="nsew")
            else:
                vframe.grid_forget()

        self.current_view_name = name

        # Update Header Titles
        hk_read_disp = format_hotkey_for_display(self.config.get("hotkey_read", "<ctrl>+<shift>+r"))
        subtitles = {
            "reader": ("Studio Reader", f"Select text across any Windows app and press {hk_read_disp}"),
            "voices": ("Voice Personas", "Select, preview, and adjust Paradee's 4 neural voice models"),
            "shortcuts": ("Shortcuts & Behavior", "Configure global hotkeys, window step sizing, and behavior"),
            "model": ("Model & Benchmark", "Paradee 8M architecture specifications and live latency benchmarking")
        }
        title, sub = subtitles.get(name, ("SpeakThat", ""))
        self.view_title_label.configure(text=title)
        self.view_sub_label.configure(text=sub)

    # =========================================================================
    # VIEW 1: STUDIO READER (Budget: ~390px, fits comfortably with 0 scrollbars)
    # =========================================================================
    def _create_reader_view(self):
        container = ctk.CTkFrame(self.view_container, fg_color="transparent")

        # --- 1. Hero Global Hotkey Card ---
        hero_card = ctk.CTkFrame(container, corner_radius=16, fg_color="#151C2C", border_width=1, border_color="#222D42")
        hero_card.pack(fill="x", pady=(0, 10))

        hc_inner = ctk.CTkFrame(hero_card, fg_color="transparent")
        hc_inner.pack(fill="x", padx=16, pady=12)

        hc_left = ctk.CTkFrame(hc_inner, fg_color="transparent")
        hc_left.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(
            hc_left,
            text="GLOBAL SELECTION SHORTCUT",
            font=("Segoe UI", 9, "bold"),
            text_color="#818CF8"
        ).pack(anchor="w")

        self.hero_pills_row = ctk.CTkFrame(hc_left, fg_color="transparent")
        self.hero_pills_row.pack(anchor="w", pady=(4, 4))

        ctk.CTkLabel(
            hc_left,
            text="Highlight any text in Chrome, PDF, Word, Slack or Notepad, then press shortcut.",
            font=("Segoe UI", 10),
            text_color="#94A3B8"
        ).pack(anchor="w")

        # Action Buttons
        hc_right = ctk.CTkFrame(hc_inner, fg_color="transparent")
        hc_right.pack(side="right", padx=(8, 0))

        self.hero_read_btn = ctk.CTkButton(
            hc_right,
            text="▶ Read Selection Now",
            font=("Segoe UI", 11, "bold"),
            fg_color="#6366F1",
            hover_color="#4F46E5",
            corner_radius=12,
            height=32,
            command=self._on_click_read_selection
        )
        self.hero_read_btn.pack(pady=3)

        self.hero_stop_btn = ctk.CTkButton(
            hc_right,
            text="⏹ Stop (Ctrl+Shift+X)",
            font=("Segoe UI", 10),
            fg_color="#7F1D1D",
            hover_color="#991B1B",
            corner_radius=12,
            height=26,
            command=self._on_click_stop
        )
        self.hero_stop_btn.pack(pady=3)

        # --- 2. Live Acoustic Visualizer & Spoken Sentence Marquee ---
        vis_card = ctk.CTkFrame(container, corner_radius=16, fg_color="#151C2C", border_width=1, border_color="#222D42")
        vis_card.pack(fill="x", pady=(0, 10))

        vc_inner = ctk.CTkFrame(vis_card, fg_color="transparent")
        vc_inner.pack(fill="x", padx=16, pady=10)

        vc_top = ctk.CTkFrame(vc_inner, fg_color="transparent")
        vc_top.pack(fill="x")

        ctk.CTkLabel(
            vc_top,
            text="LIVE SPEECH MONITOR",
            font=("Segoe UI", 9, "bold"),
            text_color="#818CF8"
        ).pack(side="left")

        self._wave_canvas = tk.Canvas(
            vc_inner,
            height=28,
            bg="#151C2C",
            highlightthickness=0
        )
        self._wave_canvas.pack(fill="x", pady=(4, 2))

        self._wave_bars = []
        for i in range(13):
            bar = self._wave_canvas.create_line(0, 0, 0, 0, width=4, capstyle=tk.ROUND, fill="#2D3A54")
            self._wave_bars.append(bar)

        self._wave_canvas.bind("<Configure>", self._layout_waveform_bars)

        self.live_sentence_label = ctk.CTkLabel(
            vc_inner,
            text="“Select any text on Windows and press Ctrl+Shift+R to begin listening.”",
            font=("Segoe UI", 11, "italic"),
            text_color="#E2E8F0",
            anchor="w",
            wraplength=620,
            justify="left"
        )
        self.live_sentence_label.pack(fill="x", pady=(2, 0))

        # --- 3. Direct Text Reader Box & Scratchpad ---
        reader_card = ctk.CTkFrame(container, corner_radius=16, fg_color="#151C2C", border_width=1, border_color="#222D42")
        reader_card.pack(fill="x", pady=(0, 0))

        rc_inner = ctk.CTkFrame(reader_card, fg_color="transparent")
        rc_inner.pack(fill="x", padx=16, pady=12)

        rc_header = ctk.CTkFrame(rc_inner, fg_color="transparent")
        rc_header.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(
            rc_header,
            text="DIRECT TEXT READER & SCRATCHPAD",
            font=("Segoe UI", 10, "bold"),
            text_color="#F8FAFC"
        ).pack(side="left")

        self.char_metrics_lbl = ctk.CTkLabel(
            rc_header,
            text="16 words • 105 chars • ~6s audio",
            font=("Segoe UI", 9),
            text_color="#64748B"
        )
        self.char_metrics_lbl.pack(side="right")

        self.text_box = ctk.CTkTextbox(
            rc_inner,
            height=100,
            font=("Segoe UI", 11),
            corner_radius=12,
            border_width=1,
            border_color="#222D42",
            fg_color="#0A0E17",
            wrap="word"
        )
        self.text_box.pack(fill="x", pady=(0, 8))
        self.text_box.insert("1.0", "Paradee is a small voice that runs anywhere. Select any text on Windows and press Ctrl+Shift+R to hear it.")
        self.text_box.bind("<KeyRelease>", self._update_text_metrics)

        # Actions row
        tb_actions = ctk.CTkFrame(rc_inner, fg_color="transparent")
        tb_actions.pack(fill="x")

        self.speak_box_btn = ctk.CTkButton(
            tb_actions,
            text="🗣️ Read This Text Now",
            font=("Segoe UI", 11, "bold"),
            fg_color="#6366F1",
            hover_color="#4F46E5",
            corner_radius=12,
            height=30,
            command=self._on_speak_box_text
        )
        self.speak_box_btn.pack(side="left", padx=(0, 8))

        self.paste_btn = ctk.CTkButton(
            tb_actions,
            text="📋 Paste",
            width=80,
            height=30,
            corner_radius=12,
            fg_color="#1A2234",
            hover_color="#2D3A54",
            command=self._on_paste_clipboard
        )
        self.paste_btn.pack(side="left", padx=(0, 6))

        self.clear_box_btn = ctk.CTkButton(
            tb_actions,
            text="🧹 Clear",
            width=65,
            height=30,
            corner_radius=12,
            fg_color="#1A2234",
            hover_color="#2D3A54",
            command=self._on_clear_textbox
        )
        self.clear_box_btn.pack(side="left")

        return container

    def _layout_waveform_bars(self, event=None):
        if not getattr(self, "_is_alive", True):
            return
        if not self._wave_canvas:
            return
        try:
            w = self._wave_canvas.winfo_width()
            if w < 100:
                w = 500
            n = len(self._wave_bars)
            spacing = w / (n + 1)
            for i, bar in enumerate(self._wave_bars):
                x = int((i + 1) * spacing)
                self._wave_canvas.coords(bar, x, 11, x, 17)
        except Exception:
            pass

    def _animate_stage_wave(self):
        if not getattr(self, "_is_alive", True):
            return
        try:
            if self._wave_canvas and self._wave_bars:
                w = self._wave_canvas.winfo_width()
                n = len(self._wave_bars)
                spacing = w / (n + 1) if w > 50 else 30

                self._wave_phase += 0.22
                is_active = self._is_speaking_anim

                for i, bar in enumerate(self._wave_bars):
                    x = int((i + 1) * spacing)
                    if is_active:
                        h = 5 + int(10 * (1 + math.sin(self._wave_phase + i * 0.7)))
                        y1 = max(2, 14 - h // 2)
                        y2 = min(26, 14 + h // 2)
                        color = "#818CF8" if (i % 2 == 0) else "#6366F1"
                    else:
                        y1, y2 = 12, 16
                        color = "#222D42"

                    self._wave_canvas.coords(bar, x, y1, x, y2)
                    self._wave_canvas.itemconfig(bar, fill=color)

            if getattr(self, "_is_alive", True):
                self._wave_after_id = self.after(50, self._animate_stage_wave)
        except Exception:
            pass

    def _update_text_metrics(self, event=None):
        raw = self.text_box.get("1.0", "end-1c").strip()
        words = len(raw.split()) if raw else 0
        chars = len(raw)
        est_sec = max(1, round(words / 2.5)) if words > 0 else 0
        self.char_metrics_lbl.configure(text=f"{words} words • {chars} chars • ~{est_sec}s audio")

    def _on_paste_clipboard(self):
        try:
            content = self.clipboard_get()
            if content:
                self.text_box.delete("1.0", "end")
                self.text_box.insert("1.0", content)
                self._update_text_metrics()
        except Exception:
            pass

    def _on_clear_textbox(self):
        self.text_box.delete("1.0", "end")
        self._update_text_metrics()

    # =========================================================================
    # VIEW 2: VOICE PERSONAS (2x2 Grid, Budget: ~340px, fits with 0 scrollbars)
    # =========================================================================
    def _create_voices_view(self):
        container = ctk.CTkFrame(self.view_container, fg_color="transparent")

        # --- 1. 2x2 Grid of 4 Persona Cards ---
        ctk.CTkLabel(
            container,
            text="SELECT VOICE PERSONA",
            font=("Segoe UI", 9, "bold"),
            text_color="#818CF8"
        ).pack(anchor="w", pady=(0, 6))

        grid_frame = ctk.CTkFrame(container, fg_color="transparent")
        grid_frame.pack(fill="x", pady=(0, 8))
        grid_frame.grid_columnconfigure(0, weight=1)
        grid_frame.grid_columnconfigure(1, weight=1)

        self.persona_cards = {}
        positions = [
            ("bf_isabella", 0, 0),
            ("af_heart", 0, 1),
            ("am_puck", 1, 0),
            ("bm_fable", 1, 1)
        ]

        for vkey, row_idx, col_idx in positions:
            info = VOICE_DETAILS[vkey]
            card = ctk.CTkFrame(
                grid_frame,
                corner_radius=14,
                fg_color="#151C2C",
                border_width=1,
                border_color="#222D42"
            )
            padx_val = (0, 4) if col_idx == 0 else (4, 0)
            card.grid(row=row_idx, column=col_idx, sticky="nsew", padx=padx_val, pady=4)

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="both", expand=True, padx=12, pady=10)

            top_row = ctk.CTkFrame(inner, fg_color="transparent")
            top_row.pack(fill="x")

            ctk.CTkLabel(top_row, text=info["flag"], font=("Segoe UI Emoji", 14)).pack(side="left", padx=(0, 4))
            ctk.CTkLabel(top_row, text=info["name"], font=("Segoe UI", 12, "bold"), text_color="#F8FAFC").pack(side="left", padx=(0, 6))
            ctk.CTkLabel(
                top_row,
                text=info["tag"],
                font=("Segoe UI", 8, "bold"),
                text_color="#818CF8",
                fg_color="#1E1B4B",
                corner_radius=4,
                padx=5,
                pady=1
            ).pack(side="left")

            ctk.CTkLabel(inner, text=info["desc"], font=("Segoe UI", 9), text_color="#94A3B8", anchor="w").pack(anchor="w", pady=(2, 6))

            # Action Row
            act_row = ctk.CTkFrame(inner, fg_color="transparent")
            act_row.pack(fill="x")

            audition_btn = ctk.CTkButton(
                act_row,
                text="▶ Audition",
                font=("Segoe UI", 9, "bold"),
                width=76,
                height=24,
                corner_radius=10,
                fg_color="#1A2234",
                hover_color="#2D3A54",
                command=lambda vk=vkey, smp=info["sample"]: self._on_audition_voice(vk, smp)
            )
            audition_btn.pack(side="left", padx=(0, 4))

            select_btn = ctk.CTkButton(
                act_row,
                text="Select",
                font=("Segoe UI", 9, "bold"),
                width=68,
                height=24,
                corner_radius=10,
                fg_color="#1E1B4B",
                hover_color="#4338CA",
                command=lambda vk=vkey: self._on_select_persona(vk)
            )
            select_btn.pack(side="left")

            self.persona_cards[vkey] = {
                "card": card,
                "select_btn": select_btn
            }

        # --- 2. Reading Speed Settings Card ---
        speed_card = ctk.CTkFrame(container, corner_radius=16, fg_color="#151C2C", border_width=1, border_color="#222D42")
        speed_card.pack(fill="x", pady=(0, 8))

        sc_inner = ctk.CTkFrame(speed_card, fg_color="transparent")
        sc_inner.pack(fill="x", padx=16, pady=10)

        ctk.CTkLabel(
            sc_inner,
            text="READING SPEED PRESETS & PRECISION TUNER",
            font=("Segoe UI", 9, "bold"),
            text_color="#818CF8"
        ).pack(anchor="w", pady=(0, 6))

        presets_frame = ctk.CTkFrame(sc_inner, fg_color="transparent")
        presets_frame.pack(fill="x", pady=(0, 6))

        speeds = [0.8, 1.0, 1.05, 1.25, 1.5, 2.0]
        self.speed_preset_btns = {}
        for sp in speeds:
            lbl = f"{sp}x"
            btn = ctk.CTkButton(
                presets_frame,
                text=lbl,
                width=50,
                height=24,
                corner_radius=10,
                font=("Segoe UI", 9, "bold"),
                fg_color="#1A2234",
                hover_color="#2D3A54",
                command=lambda s=sp: self._apply_speed(s)
            )
            btn.pack(side="left", padx=(0, 5))
            self.speed_preset_btns[sp] = btn

        slider_row = ctk.CTkFrame(sc_inner, fg_color="transparent")
        slider_row.pack(fill="x")

        self.speed_slider = ctk.CTkSlider(
            slider_row,
            from_=0.7,
            to=2.2,
            number_of_steps=30,
            command=self._on_speed_slider_moved,
            progress_color="#6366F1"
        )
        self.speed_slider.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.speed_val_label = ctk.CTkLabel(
            slider_row,
            text="1.05x",
            font=("Segoe UI", 11, "bold"),
            text_color="#F8FAFC",
            width=46
        )
        self.speed_val_label.pack(side="left")

        # --- 3. Audio Volume Control ---
        vol_card = ctk.CTkFrame(container, corner_radius=16, fg_color="#151C2C", border_width=1, border_color="#222D42")
        vol_card.pack(fill="x", pady=(0, 0))

        vc_inner = ctk.CTkFrame(vol_card, fg_color="transparent")
        vc_inner.pack(fill="x", padx=16, pady=10)

        ctk.CTkLabel(
            vc_inner,
            text="OUTPUT VOLUME",
            font=("Segoe UI", 9, "bold"),
            text_color="#818CF8"
        ).pack(anchor="w", pady=(0, 4))

        vol_row = ctk.CTkFrame(vc_inner, fg_color="transparent")
        vol_row.pack(fill="x")

        self.vol_slider = ctk.CTkSlider(
            vol_row,
            from_=0.1,
            to=1.0,
            number_of_steps=18,
            command=self._on_volume_changed,
            progress_color="#6366F1"
        )
        self.vol_slider.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.vol_val_label = ctk.CTkLabel(
            vol_row,
            text="100%",
            font=("Segoe UI", 11, "bold"),
            text_color="#F8FAFC",
            width=46
        )
        self.vol_val_label.pack(side="left")

        return container

    def _on_select_persona(self, voice_key):
        self.config.set("voice", voice_key)
        self.engine.set_voice(voice_key)
        self._highlight_selected_persona(voice_key)

    def _highlight_selected_persona(self, active_key):
        for vkey, items in self.persona_cards.items():
            card = items["card"]
            btn = items["select_btn"]
            if vkey == active_key:
                card.configure(border_color="#6366F1", border_width=2, fg_color="#182033")
                btn.configure(text="✓ Active", fg_color="#6366F1", hover_color="#4F46E5")
            else:
                card.configure(border_color="#222D42", border_width=1, fg_color="#151C2C")
                btn.configure(text="Select", fg_color="#1A2234", hover_color="#2D3A54")

    def _on_audition_voice(self, voice_key, sample_phrase):
        orig_voice = self.engine.voice
        self.engine.set_voice(voice_key)
        self.engine.speak(sample_phrase)
        cur_conf = self.config.get("voice", "bf_isabella")
        if cur_conf != voice_key:
            threading.Thread(target=lambda: (time.sleep(0.5), self.engine.set_voice(cur_conf)), daemon=True).start()

    def _apply_speed(self, speed_val):
        spd = round(speed_val, 2)
        self.speed_slider.set(spd)
        self.speed_val_label.configure(text=f"{spd:.2f}x")
        self.config.set("speed", spd)
        self.engine.set_speed(spd)

    def _on_speed_slider_moved(self, value):
        self._apply_speed(value)

    def _on_volume_changed(self, value):
        vol = round(value, 2)
        self.vol_val_label.configure(text=f"{int(vol * 100)}%")
        self.config.set("volume", vol)
        self.engine.set_volume(vol)

    # =========================================================================
    # VIEW 3: SHORTCUTS & BEHAVIOR (Window Sizing + Toggles, Budget: ~360px)
    # =========================================================================
    def _create_shortcuts_view(self):
        container = ctk.CTkFrame(self.view_container, fg_color="transparent")

        # --- 1. Window Sizing & Step Configuration Card ---
        size_card = ctk.CTkFrame(container, corner_radius=16, fg_color="#151C2C", border_width=1, border_color="#222D42")
        size_card.pack(fill="x", pady=(0, 8))

        sz_inner = ctk.CTkFrame(size_card, fg_color="transparent")
        sz_inner.pack(fill="x", padx=16, pady=10)

        sz_top = ctk.CTkFrame(sz_inner, fg_color="transparent")
        sz_top.pack(fill="x")

        ctk.CTkLabel(
            sz_top,
            text="WINDOW DIMENSIONS & STEP SIZING",
            font=("Segoe UI", 9, "bold"),
            text_color="#818CF8"
        ).pack(side="left")

        sw, sh = self.screen_res
        self.screen_info_lbl = ctk.CTkLabel(
            sz_top,
            text=f"Screen: {sw}×{sh} • Max Step: {self.max_w}×{self.max_h}",
            font=("Segoe UI", 8),
            text_color="#64748B"
        )
        self.screen_info_lbl.pack(side="right")

        ctk.CTkLabel(
            sz_inner,
            text="Snaps in steps of 200px width and 100px height up to 1400×900 max based on available screen space.",
            font=("Segoe UI", 9),
            text_color="#94A3B8"
        ).pack(anchor="w", pady=(1, 6))

        # Size Presets Row
        presets_row = ctk.CTkFrame(sz_inner, fg_color="transparent")
        presets_row.pack(fill="x")

        self.size_presets = [
            (800, 580, "800×580 Compact"),
            (1000, 620, "1000×620 Default"),
            (1200, 700, "1200×700 Expanded"),
            (1400, 900, "1400×900 Max")
        ]

        self.size_btn_widgets = {}
        for w, h, lbl in self.size_presets:
            btn = ctk.CTkButton(
                presets_row,
                text=lbl,
                height=26,
                corner_radius=10,
                font=("Segoe UI", 9, "bold"),
                fg_color="#1A2234",
                hover_color="#2D3A54",
                command=lambda tw=w, th=h: self._apply_window_size(tw, th)
            )
            # Disable if larger than max screen step allowance
            if w > self.max_w or h > self.max_h:
                btn.configure(state="disabled", fg_color="#101520", text_color="#475569")
            btn.pack(side="left", padx=(0, 6))
            self.size_btn_widgets[(w, h)] = btn

        # --- 2. System-Wide Hotkeys Card ---
        hk_card = ctk.CTkFrame(container, corner_radius=16, fg_color="#151C2C", border_width=1, border_color="#222D42")
        hk_card.pack(fill="x", pady=(0, 8))

        hk_inner = ctk.CTkFrame(hk_card, fg_color="transparent")
        hk_inner.pack(fill="x", padx=16, pady=10)

        # Header row with title & Reset button
        hk_header_row = ctk.CTkFrame(hk_inner, fg_color="transparent")
        hk_header_row.pack(fill="x", pady=(0, 4))

        ctk.CTkLabel(
            hk_header_row,
            text="CUSTOMIZABLE SYSTEM-WIDE SHORTCUT KEYS",
            font=("Segoe UI", 9, "bold"),
            text_color="#818CF8"
        ).pack(side="left")

        ctk.CTkButton(
            hk_header_row,
            text="↺ Reset to Defaults",
            width=115,
            height=24,
            corner_radius=8,
            font=("Segoe UI", 8, "bold"),
            fg_color="#1E293B",
            hover_color="#334155",
            text_color="#94A3B8",
            border_width=1,
            border_color="#334155",
            command=self._on_reset_hotkeys
        ).pack(side="right")

        ctk.CTkLabel(
            hk_inner,
            text="Press 'Change' to record any custom keyboard shortcut, or click a quick preset.",
            font=("Segoe UI", 9),
            text_color="#94A3B8"
        ).pack(anchor="w", pady=(0, 8))

        # --- Row 1: Read Selection ---
        r1_frame = ctk.CTkFrame(hk_inner, fg_color="#0F1420", corner_radius=10, border_width=1, border_color="#1F283B")
        r1_frame.pack(fill="x", pady=(0, 6), padx=0)

        r1_inner = ctk.CTkFrame(r1_frame, fg_color="transparent")
        r1_inner.pack(fill="x", padx=10, pady=8)

        # Left: label + badge container
        r1_left = ctk.CTkFrame(r1_inner, fg_color="transparent")
        r1_left.pack(side="left")

        ctk.CTkLabel(r1_left, text="Read Selection:", font=("Segoe UI", 10, "bold"), text_color="#F8FAFC").pack(side="left", padx=(0, 8))
        self.pref_read_badges_frame = ctk.CTkFrame(r1_left, fg_color="transparent")
        self.pref_read_badges_frame.pack(side="left")

        # Right: presets + Change button
        r1_right = ctk.CTkFrame(r1_inner, fg_color="transparent")
        r1_right.pack(side="right")

        ctk.CTkLabel(r1_right, text="Presets:", font=("Segoe UI", 8, "bold"), text_color="#64748B").pack(side="left", padx=(0, 4))
        for p in ["Ctrl+Shift+R", "Ctrl+Alt+S", "Alt+S", "Ctrl+Space"]:
            ctk.CTkButton(
                r1_right,
                text=p,
                width=68,
                height=22,
                corner_radius=6,
                font=("Segoe UI", 8, "bold"),
                fg_color="#1A2234",
                hover_color="#2D3A54",
                text_color="#CBD5E1",
                border_width=1,
                border_color="#334155",
                command=lambda pk=p: self._apply_hotkey_preset("Read", pk)
            ).pack(side="left", padx=2)

        ctk.CTkButton(
            r1_right,
            text="⌨ Change",
            width=76,
            height=24,
            corner_radius=8,
            font=("Segoe UI", 9, "bold"),
            fg_color="#6366F1",
            hover_color="#4F46E5",
            text_color="#FFFFFF",
            command=lambda: self._open_hotkey_recorder("Read")
        ).pack(side="left", padx=(6, 0))

        # --- Row 2: Stop Reading ---
        r2_frame = ctk.CTkFrame(hk_inner, fg_color="#0F1420", corner_radius=10, border_width=1, border_color="#1F283B")
        r2_frame.pack(fill="x", pady=(0, 0), padx=0)

        r2_inner = ctk.CTkFrame(r2_frame, fg_color="transparent")
        r2_inner.pack(fill="x", padx=10, pady=8)

        # Left: label + badge container
        r2_left = ctk.CTkFrame(r2_inner, fg_color="transparent")
        r2_left.pack(side="left")

        ctk.CTkLabel(r2_left, text="Stop Speech:", font=("Segoe UI", 10, "bold"), text_color="#F8FAFC").pack(side="left", padx=(0, 8))
        self.pref_stop_badges_frame = ctk.CTkFrame(r2_left, fg_color="transparent")
        self.pref_stop_badges_frame.pack(side="left")

        # Right: presets + Change button
        r2_right = ctk.CTkFrame(r2_inner, fg_color="transparent")
        r2_right.pack(side="right")

        ctk.CTkLabel(r2_right, text="Presets:", font=("Segoe UI", 8, "bold"), text_color="#64748B").pack(side="left", padx=(0, 4))
        for p in ["Ctrl+Shift+X", "Ctrl+Alt+X", "Alt+X", "Esc"]:
            ctk.CTkButton(
                r2_right,
                text=p,
                width=68,
                height=22,
                corner_radius=6,
                font=("Segoe UI", 8, "bold"),
                fg_color="#1A2234",
                hover_color="#2D3A54",
                text_color="#CBD5E1",
                border_width=1,
                border_color="#334155",
                command=lambda pk=p: self._apply_hotkey_preset("Stop", pk)
            ).pack(side="left", padx=2)

        ctk.CTkButton(
            r2_right,
            text="⌨ Change",
            width=76,
            height=24,
            corner_radius=8,
            font=("Segoe UI", 9, "bold"),
            fg_color="#EF4444",
            hover_color="#DC2626",
            text_color="#FFFFFF",
            command=lambda: self._open_hotkey_recorder("Stop")
        ).pack(side="left", padx=(6, 0))

        # --- 3. Floating Pop-up Widget Style Card ---
        hud_card = ctk.CTkFrame(container, corner_radius=16, fg_color="#151C2C", border_width=1, border_color="#222D42")
        hud_card.pack(fill="x", pady=(0, 8))

        hc_inner = ctk.CTkFrame(hud_card, fg_color="transparent")
        hc_inner.pack(fill="x", padx=16, pady=10)

        hc_top = ctk.CTkFrame(hc_inner, fg_color="transparent")
        hc_top.pack(fill="x")

        ctk.CTkLabel(
            hc_top,
            text="FLOATING POP-UP WIDGET STYLE & DISPLAY",
            font=("Segoe UI", 9, "bold"),
            text_color="#818CF8"
        ).pack(side="left")

        # Master enable/disable switch
        self.sw_floating_hud = ctk.CTkSwitch(
            hc_top,
            text="Enable Pop-up",
            font=("Segoe UI", 9, "bold"),
            progress_color="#6366F1",
            command=self._on_hud_switch_toggle
        )
        self.sw_floating_hud.pack(side="right")

        ctk.CTkLabel(
            hc_inner,
            text="Select visual size and layout while speaking, or choose 'No Pop-up' for pure keyboard shortcut reading.",
            font=("Segoe UI", 9),
            text_color="#94A3B8"
        ).pack(anchor="w", pady=(1, 8))

        # Styles row: 4 option buttons + preview button
        styles_row = ctk.CTkFrame(hc_inner, fg_color="transparent")
        styles_row.pack(fill="x")

        self.hud_styles_data = [
            ("default", "Default (440×74)"),
            ("small", "Small (310×54)"),
            ("tiny", "Tiny (154×46)"),
            ("none", "No Pop-up"),
        ]

        self.hud_style_buttons = {}
        for s_key, s_title in self.hud_styles_data:
            btn = ctk.CTkButton(
                styles_row,
                text=s_title,
                height=28,
                corner_radius=10,
                font=("Segoe UI", 9, "bold"),
                fg_color="#1A2234",
                hover_color="#2D3A54",
                text_color="#CBD5E1",
                command=lambda sk=s_key: self._apply_hud_style(sk)
            )
            btn.pack(side="left", padx=(0, 6))
            self.hud_style_buttons[s_key] = btn

        # Preview Button
        self.btn_preview_hud = ctk.CTkButton(
            styles_row,
            text="✨ Preview Pop-up",
            height=28,
            corner_radius=10,
            font=("Segoe UI", 9, "bold"),
            fg_color="#1E1B4B",
            hover_color="#312E81",
            text_color="#A5B4FC",
            border_width=1,
            border_color="#4338CA",
            command=self._on_preview_hud_click
        )
        self.btn_preview_hud.pack(side="right")

        # --- 4. Automation & Clipboard Behavior Card ---
        pref_card = ctk.CTkFrame(container, corner_radius=16, fg_color="#151C2C", border_width=1, border_color="#222D42")
        pref_card.pack(fill="x", pady=(0, 0))

        pf_inner = ctk.CTkFrame(pref_card, fg_color="transparent")
        pf_inner.pack(fill="x", padx=16, pady=10)

        ctk.CTkLabel(
            pf_inner,
            text="AUTOMATION & CLIPBOARD BEHAVIOR",
            font=("Segoe UI", 9, "bold"),
            text_color="#818CF8"
        ).pack(anchor="w", pady=(0, 8))

        switches_grid = ctk.CTkFrame(pf_inner, fg_color="transparent")
        switches_grid.pack(fill="x")
        switches_grid.grid_columnconfigure(0, weight=1)
        switches_grid.grid_columnconfigure(1, weight=1)

        # Switch 1: Preserve clipboard
        self.sw_restore_clip = ctk.CTkSwitch(
            switches_grid,
            text="Preserve Clipboard History",
            font=("Segoe UI", 10, "bold"),
            progress_color="#6366F1",
            command=self._on_pref_changed
        )
        self.sw_restore_clip.grid(row=0, column=0, sticky="w", pady=4, padx=(0, 10))

        # Switch 2: Fallback to clipboard
        self.sw_fallback_clip = ctk.CTkSwitch(
            switches_grid,
            text="Clipboard Fallback on Empty Selection",
            font=("Segoe UI", 10, "bold"),
            progress_color="#6366F1",
            command=self._on_pref_changed
        )
        self.sw_fallback_clip.grid(row=0, column=1, sticky="w", pady=4)

        # Switch 3: Minimize to tray on close
        self.sw_min_to_tray = ctk.CTkSwitch(
            switches_grid,
            text="Minimize to System Tray on Close (X)",
            font=("Segoe UI", 10, "bold"),
            progress_color="#6366F1",
            command=self._on_pref_changed
        )
        self.sw_min_to_tray.grid(row=1, column=0, sticky="w", pady=4, padx=(0, 10))

        return container

    def _apply_window_size(self, target_w, target_h):
        w = min(self.max_w, max(800, target_w))
        h = min(self.max_h, max(580, target_h))
        self.geometry(f"{w}x{h}")
        self.config.set("window_width", w)
        self.config.set("window_height", h)

        # Highlight active preset button
        for (pw, ph), btn in self.size_btn_widgets.items():
            if pw == w and ph == h:
                btn.configure(fg_color="#6366F1", hover_color="#4F46E5")
            elif pw <= self.max_w and ph <= self.max_h:
                btn.configure(fg_color="#1A2234", hover_color="#2D3A54")

    def _apply_hud_style(self, style_key):
        """Apply user-selected pop-up style ('default', 'small', 'tiny', 'none')."""
        is_enabled = (style_key != "none")
        self.config.set("hud_style", style_key)
        self.config.set("show_floating_hud", is_enabled)

        if is_enabled:
            self.sw_floating_hud.select()
        else:
            self.sw_floating_hud.deselect()

        for sk, btn in getattr(self, "hud_style_buttons", {}).items():
            if sk == style_key:
                btn.configure(fg_color="#6366F1", hover_color="#4F46E5", text_color="#FFFFFF")
            else:
                btn.configure(fg_color="#1A2234", hover_color="#2D3A54", text_color="#CBD5E1")

        if hasattr(self, "on_hud_style_change") and self.on_hud_style_change:
            self.on_hud_style_change(style_key, enabled=is_enabled)
        elif hasattr(self, "hud") and self.hud:
            self.hud.set_style(style_key, enabled=is_enabled)

    def _on_hud_switch_toggle(self):
        """Toggle master pop-up switch on/off."""
        enabled = bool(self.sw_floating_hud.get())
        if enabled:
            cur_s = self.config.get("hud_style", "default")
            if cur_s == "none":
                cur_s = "default"
            self._apply_hud_style(cur_s)
        else:
            self._apply_hud_style("none")

    def _on_preview_hud_click(self):
        """Preview the currently selected pop-up widget style on screen for 4 seconds."""
        cur_s = self.config.get("hud_style", "default")
        target_s = cur_s if cur_s != "none" else "default"
        if hasattr(self, "hud") and self.hud:
            self.hud.preview(target_s)

    def _on_pref_changed(self):
        self.config.set("restore_clipboard", bool(self.sw_restore_clip.get()))
        self.config.set("fallback_to_clipboard", bool(self.sw_fallback_clip.get()))
        self.config.set("minimize_to_tray_on_close", bool(self.sw_min_to_tray.get()))

    # =========================================================================
    # VIEW 4: MODEL & BENCHMARK (Budget: ~330px, fits with 0 scrollbars)
    # =========================================================================
    def _create_model_view(self):
        container = ctk.CTkFrame(self.view_container, fg_color="transparent")

        # --- 1. Technical Specs Card ---
        specs_card = ctk.CTkFrame(container, corner_radius=16, fg_color="#151C2C", border_width=1, border_color="#222D42")
        specs_card.pack(fill="x", pady=(0, 8))

        sp_inner = ctk.CTkFrame(specs_card, fg_color="transparent")
        sp_inner.pack(fill="x", padx=16, pady=10)

        ctk.CTkLabel(
            sp_inner,
            text="PARADEE 8M ARCHITECTURE & HARDWARE ENGINE",
            font=("Segoe UI", 9, "bold"),
            text_color="#818CF8"
        ).pack(anchor="w", pady=(0, 6))

        spec_grid = [
            ("Neural Model", "Paradee-8M-v1.2 (Quantized Int8 ONNX Graph)"),
            ("Parameter Count", "8,200,000 parameters (Ultra-lightweight)"),
            ("Audio Output", "24,000 Hz Mono, 32-bit Float Streaming"),
            ("Inference Engine", "ONNX Runtime CPU (Pure Offline / Zero Cloud)"),
            ("G2P Phonemizer", "Misaki Pure-Python G2P + Spacy Tokenizer"),
            ("Streaming Pipeline", "Sentence-chunked async synthesis into SoundDevice")
        ]

        for label, val in spec_grid:
            row = ctk.CTkFrame(sp_inner, fg_color="transparent")
            row.pack(fill="x", pady=1)
            ctk.CTkLabel(row, text=label, font=("Segoe UI", 10, "bold"), text_color="#94A3B8", width=130, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=val, font=("Segoe UI", 10), text_color="#E2E8F0", anchor="w").pack(side="left")

        # --- 2. Live Synthesis Latency Benchmark Tool ---
        bench_card = ctk.CTkFrame(container, corner_radius=16, fg_color="#151C2C", border_width=1, border_color="#222D42")
        bench_card.pack(fill="x", pady=(0, 0))

        bc_inner = ctk.CTkFrame(bench_card, fg_color="transparent")
        bc_inner.pack(fill="x", padx=16, pady=10)

        bc_top = ctk.CTkFrame(bc_inner, fg_color="transparent")
        bc_top.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(
            bc_top,
            text="LIVE SYNTHESIS LATENCY BENCHMARK",
            font=("Segoe UI", 9, "bold"),
            text_color="#818CF8"
        ).pack(side="left")

        self.bench_btn = ctk.CTkButton(
            bc_top,
            text="⚡ Run Benchmark Now",
            font=("Segoe UI", 10, "bold"),
            corner_radius=12,
            height=26,
            fg_color="#6366F1",
            hover_color="#4F46E5",
            command=self._run_latency_benchmark
        )
        self.bench_btn.pack(side="right")

        metrics_row = ctk.CTkFrame(bc_inner, fg_color="transparent")
        metrics_row.pack(fill="x", pady=(2, 6))

        # Latency Card
        m_a = ctk.CTkFrame(metrics_row, fg_color="#0F1420", corner_radius=10, border_width=1, border_color="#1F283B")
        m_a.pack(side="left", fill="both", expand=True, padx=(0, 4))
        ctk.CTkLabel(m_a, text="SYNTHESIS TIME", font=("Segoe UI", 8, "bold"), text_color="#818CF8").pack(anchor="w", padx=10, pady=(6, 1))
        self.bench_time_lbl = ctk.CTkLabel(m_a, text="-- ms", font=("Segoe UI", 15, "bold"), text_color="#F8FAFC")
        self.bench_time_lbl.pack(anchor="w", padx=10, pady=(0, 6))

        # RTF Card
        m_b = ctk.CTkFrame(metrics_row, fg_color="#0F1420", corner_radius=10, border_width=1, border_color="#1F283B")
        m_b.pack(side="left", fill="both", expand=True, padx=2)
        ctk.CTkLabel(m_b, text="REAL-TIME FACTOR", font=("Segoe UI", 8, "bold"), text_color="#10B981").pack(anchor="w", padx=10, pady=(6, 1))
        self.bench_rtf_lbl = ctk.CTkLabel(m_b, text="-- x", font=("Segoe UI", 15, "bold"), text_color="#F8FAFC")
        self.bench_rtf_lbl.pack(anchor="w", padx=10, pady=(0, 6))

        # Audio Duration Card
        m_c = ctk.CTkFrame(metrics_row, fg_color="#0F1420", corner_radius=10, border_width=1, border_color="#1F283B")
        m_c.pack(side="left", fill="both", expand=True, padx=(4, 0))
        ctk.CTkLabel(m_c, text="AUDIO DURATION", font=("Segoe UI", 8, "bold"), text_color="#38BDF8").pack(anchor="w", padx=10, pady=(6, 1))
        self.bench_dur_lbl = ctk.CTkLabel(m_c, text="-- s", font=("Segoe UI", 15, "bold"), text_color="#F8FAFC")
        self.bench_dur_lbl.pack(anchor="w", padx=10, pady=(0, 6))

        self.bench_status_lbl = ctk.CTkLabel(
            bc_inner,
            text="Click 'Run Benchmark Now' to test Paradee 8M inference speed on CPU.",
            font=("Segoe UI", 9, "italic"),
            text_color="#64748B"
        )
        self.bench_status_lbl.pack(anchor="w")

        return container

    def _run_latency_benchmark(self):
        self.bench_btn.configure(state="disabled", text="Running...")
        self.bench_status_lbl.configure(text="Synthesizing benchmark sentence across neural graph...", text_color="#818CF8")

        def _bench_worker():
            try:
                for _ in range(30):
                    if self.engine.is_ready():
                        break
                    time.sleep(0.1)

                phrase = "Paradee is a small voice that runs anywhere with instant local speech."
                t0 = time.perf_counter()
                audio = self.engine.model(phrase, voice=self.config.get("voice", "bf_isabella"), speed=1.0)
                elapsed = time.perf_counter() - t0

                audio_dur = len(audio) / 24000.0
                rtf = audio_dur / elapsed if elapsed > 0 else 0
                ms = elapsed * 1000

                def _ui_update():
                    self.bench_time_lbl.configure(text=f"{ms:.1f} ms")
                    self.bench_rtf_lbl.configure(text=f"{rtf:.1f}x RT")
                    self.bench_dur_lbl.configure(text=f"{audio_dur:.2f} s")
                    self.bench_status_lbl.configure(
                        text=f"Benchmark completed! Generation is {rtf:.1f}x faster than real-time playback.",
                        text_color="#10B981"
                    )
                    self.bench_btn.configure(state="normal", text="⚡ Run Benchmark Now")

                self.after(0, _ui_update)
            except Exception as e:
                def _ui_err():
                    self.bench_status_lbl.configure(text=f"Benchmark error: {e}", text_color="#EF4444")
                    self.bench_btn.configure(state="normal", text="⚡ Run Benchmark Now")
                self.after(0, _ui_err)

        threading.Thread(target=_bench_worker, daemon=True).start()

    # =========================================================================
    # CORE INTERACTION HANDLERS & LIFECYCLE
    # =========================================================================
    def _load_config_to_ui(self):
        # 1. Voice
        cur_voice = self.config.get("voice", "bf_isabella")
        self._highlight_selected_persona(cur_voice)

        # 2. Speed
        spd = float(self.config.get("speed", 1.05))
        self.speed_slider.set(spd)
        self.speed_val_label.configure(text=f"{spd:.2f}x")

        # 3. Volume
        vol = float(self.config.get("volume", 1.0))
        self.vol_slider.set(vol)
        self.vol_val_label.configure(text=f"{int(vol * 100)}%")

        # 4. Toggles
        if self.config.get("restore_clipboard", False):
            self.sw_restore_clip.select()
        else:
            self.sw_restore_clip.deselect()

        if self.config.get("fallback_to_clipboard", True):
            self.sw_fallback_clip.select()
        else:
            self.sw_fallback_clip.deselect()

        # 4. Floating Pop-up Widget State
        cur_hud_style = self.config.get("hud_style", "default")
        hud_enabled = self.config.get("show_floating_hud", True)
        if not hud_enabled:
            cur_hud_style = "none"

        if hasattr(self, "sw_floating_hud"):
            if hud_enabled and cur_hud_style != "none":
                self.sw_floating_hud.select()
            else:
                self.sw_floating_hud.deselect()

        for sk, btn in getattr(self, "hud_style_buttons", {}).items():
            if sk == cur_hud_style:
                btn.configure(fg_color="#6366F1", hover_color="#4F46E5", text_color="#FFFFFF")
            else:
                btn.configure(fg_color="#1A2234", hover_color="#2D3A54", text_color="#CBD5E1")

        if self.config.get("minimize_to_tray_on_close", True):
            self.sw_min_to_tray.select()
        else:
            self.sw_min_to_tray.deselect()

        # 5. Sizing preset button state
        cur_w = int(self.config.get("window_width", 1000))
        cur_h = int(self.config.get("window_height", 620))
        for (pw, ph), btn in self.size_btn_widgets.items():
            if pw == cur_w and ph == cur_h:
                btn.configure(fg_color="#6366F1", hover_color="#4F46E5")

        # 6. Render hotkey badges & update button labels
        self._render_hotkey_badges()

    def _render_hotkey_badges(self):
        """Re-renders hotkey keycap badges in Hero card, Preferences card, and updates button titles."""
        hk_read = self.config.get("hotkey_read", "<ctrl>+<shift>+r")
        hk_stop = self.config.get("hotkey_stop", "<ctrl>+<shift>+x")
        disp_read = format_hotkey_for_display(hk_read)
        disp_stop = format_hotkey_for_display(hk_stop)

        # 1. Update hero stop button text
        if hasattr(self, "hero_stop_btn") and self.hero_stop_btn:
            self.hero_stop_btn.configure(text=f"⏹ Stop ({disp_stop})")

        # 2. Update hero pills in Reader View
        if hasattr(self, "hero_pills_row") and self.hero_pills_row:
            for w in self.hero_pills_row.winfo_children():
                w.destroy()
            parts = disp_read.split(" + ")
            for i, p in enumerate(parts):
                if i > 0:
                    ctk.CTkLabel(self.hero_pills_row, text="+", font=("Segoe UI", 12, "bold"), text_color="#64748B").pack(side="left", padx=3)
                ctk.CTkLabel(
                    self.hero_pills_row,
                    text=p,
                    font=("Segoe UI", 11, "bold"),
                    fg_color="#1E1B4B",
                    text_color="#C7D2FE",
                    corner_radius=8,
                    height=24
                ).pack(side="left")

        # 3. Update Preferences Read Badges
        if hasattr(self, "pref_read_badges_frame") and self.pref_read_badges_frame:
            for w in self.pref_read_badges_frame.winfo_children():
                w.destroy()
            parts = disp_read.split(" + ")
            for i, p in enumerate(parts):
                if i > 0:
                    ctk.CTkLabel(self.pref_read_badges_frame, text="+", font=("Segoe UI", 9, "bold"), text_color="#64748B").pack(side="left", padx=2)
                ctk.CTkLabel(
                    self.pref_read_badges_frame,
                    text=p,
                    font=("Segoe UI", 9, "bold"),
                    fg_color="#1E1B4B",
                    text_color="#C7D2FE",
                    corner_radius=6,
                    height=20
                ).pack(side="left")

        # 4. Update Preferences Stop Badges
        if hasattr(self, "pref_stop_badges_frame") and self.pref_stop_badges_frame:
            for w in self.pref_stop_badges_frame.winfo_children():
                w.destroy()
            parts = disp_stop.split(" + ")
            for i, p in enumerate(parts):
                if i > 0:
                    ctk.CTkLabel(self.pref_stop_badges_frame, text="+", font=("Segoe UI", 9, "bold"), text_color="#64748B").pack(side="left", padx=2)
                ctk.CTkLabel(
                    self.pref_stop_badges_frame,
                    text=p,
                    font=("Segoe UI", 9, "bold"),
                    fg_color="#3B1219",
                    text_color="#FECACA",
                    corner_radius=6,
                    height=20
                ).pack(side="left")

        # 5. Update Header Subtitle if currently on reader view
        if hasattr(self, "current_view_name") and self.current_view_name == "reader":
            if hasattr(self, "view_sub_label") and self.view_sub_label:
                self.view_sub_label.configure(text=f"Select text across any Windows app and press {disp_read}")

    def _open_hotkey_recorder(self, action_type):
        """Opens live hotkey recorder modal dialog."""
        current = self.config.get("hotkey_read" if action_type == "Read" else "hotkey_stop", "")
        def _on_save(new_hotkey):
            if action_type == "Read":
                self.config.set("hotkey_read", new_hotkey)
            else:
                self.config.set("hotkey_stop", new_hotkey)
            self._render_hotkey_badges()
            if self.on_hotkey_change:
                self.on_hotkey_change(
                    self.config.get("hotkey_read", "<ctrl>+<shift>+r"),
                    self.config.get("hotkey_stop", "<ctrl>+<shift>+x")
                )
        ShortcutRecorderDialog(self, action_name=f"{action_type} Shortcut", current_hotkey=current, on_save=_on_save)

    def _apply_hotkey_preset(self, action_type, preset_str):
        """Applies a hotkey preset immediately."""
        valid, norm = validate_hotkey(preset_str)
        if valid:
            if action_type == "Read":
                self.config.set("hotkey_read", norm)
            else:
                self.config.set("hotkey_stop", norm)
            self._render_hotkey_badges()
            if self.on_hotkey_change:
                self.on_hotkey_change(
                    self.config.get("hotkey_read", "<ctrl>+<shift>+r"),
                    self.config.get("hotkey_stop", "<ctrl>+<shift>+x")
                )

    def _on_reset_hotkeys(self):
        """Resets hotkeys to standard defaults: Ctrl+Shift+R and Ctrl+Shift+X."""
        self.config.set("hotkey_read", "<ctrl>+<shift>+r")
        self.config.set("hotkey_stop", "<ctrl>+<shift>+x")
        self._render_hotkey_badges()
        if self.on_hotkey_change:
            self.on_hotkey_change("<ctrl>+<shift>+r", "<ctrl>+<shift>+x")

    def _on_speak_box_text(self):
        text = self.text_box.get("1.0", "end").strip()
        if text:
            self.engine.speak(text)

    def _on_click_read_selection(self):
        if self.on_read_selection:
            threading.Thread(target=self.on_read_selection, daemon=True).start()

    def _on_click_stop(self):
        if self.on_stop_reading:
            self.on_stop_reading()

    def _on_click_pause_resume(self):
        if self.engine.is_paused():
            self.engine.resume()
        else:
            self.engine.pause()

    def update_status(self, status):
        """Thread-safe status update for badges and waveform animation."""
        def _update():
            st = status.lower()
            if st == "ready":
                self._is_speaking_anim = False
                self.status_badge.configure(text="● Ready", text_color="#10B981", fg_color="#064E3B")
                self.rail_status_pill.configure(text="● Paradee Ready", text_color="#10B981", fg_color="#064E3B")
                self.pause_resume_btn.configure(text="⏸ Pause", state="disabled")
            elif st == "speaking":
                self._is_speaking_anim = True
                self.status_badge.configure(text="● Speaking", text_color="#38BDF8", fg_color="#1E3A8A")
                self.rail_status_pill.configure(text="● Speaking...", text_color="#38BDF8", fg_color="#1E3A8A")
                self.pause_resume_btn.configure(text="⏸ Pause", state="normal")
            elif st == "paused":
                self._is_speaking_anim = False
                self.status_badge.configure(text="● Paused", text_color="#F59E0B", fg_color="#78350F")
                self.rail_status_pill.configure(text="● Paused", text_color="#F59E0B", fg_color="#78350F")
                self.pause_resume_btn.configure(text="▶ Resume", state="normal")
            elif "synthesizing" in st or "capturing" in st:
                self._is_speaking_anim = True
                self.status_badge.configure(text="● Processing", text_color="#C084FC", fg_color="#581C87")
                self.rail_status_pill.configure(text="● Processing", text_color="#C084FC", fg_color="#581C87")
                self.pause_resume_btn.configure(text="⏸ Pause", state="normal")
            else:
                self._is_speaking_anim = False
                self.status_badge.configure(text=f"● {status}", text_color="#94A3B8", fg_color="#334155")
                self.rail_status_pill.configure(text=f"● {status}", text_color="#94A3B8", fg_color="#334155")

        self.after(0, _update)

    def update_sentence(self, sentence):
        """Thread-safe sentence update."""
        def _update():
            s = sentence.strip().replace("\n", " ")
            if len(s) > 110:
                s = s[:107] + "…"
            self.live_sentence_label.configure(text=f'“{s}”')
        self.after(0, _update)

    def destroy(self):
        self._is_alive = False
        if hasattr(self, "_wave_after_id") and self._wave_after_id:
            try:
                self.after_cancel(self._wave_after_id)
            except Exception:
                pass
        super().destroy()

    def _on_window_close(self):
        if self.config.get("minimize_to_tray_on_close", True):
            self.withdraw()
        else:
            if self.on_quit:
                self.on_quit()
            else:
                self.destroy()
