"""Modern CustomTkinter Dashboard & Studio for SpeakThat.

Designed following UI/UX Design Pro principles:
- Obsidian base (#0B0F19), Rail (#0F172A), Elevated Cards (#131C2E).
- Electric Indigo (#6366F1) primary accent with soft violet (#818CF8) highlights.
- Navigation Rail + Stage architecture with Studio, Voices, Behavior, and Model views.
- Dynamic audio waveform visualizer and live sentence tracking.
- Interactive latency and synthesis benchmarking tool.
"""

import os
import sys
import math
import time
import threading
import tkinter as tk
import customtkinter as ctk
from PIL import Image

from .config import VOICE_NAMES


VOICE_DETAILS = {
    "bf_isabella": {
        "name": "Isabella",
        "flag": "🇬🇧",
        "locale": "British Female",
        "tag": "Narrative • High Fidelity",
        "desc": "Crisp, refined British tone with natural cadence. Best for articles, documentation, and long-form reading.",
        "sample": "Hello! I am Isabella. Paradee is a small voice that runs anywhere."
    },
    "af_heart": {
        "name": "Heart",
        "flag": "🇺🇸",
        "locale": "American Female",
        "tag": "Warm • Conversational",
        "desc": "Lively, expressive American female voice with natural inflections. Great for casual reading and dialogues.",
        "sample": "Hi there! I'm Heart. Ready to read anything you highlight on your screen."
    },
    "am_puck": {
        "name": "Puck",
        "flag": "🇺🇸",
        "locale": "American Male",
        "tag": "Crisp • Direct",
        "desc": "Dynamic, punchy American male voice with sharp enunciation. Ideal for code reviews, news, and technical summaries.",
        "sample": "Greetings! I'm Puck. Fast, local text-to-speech right on your machine."
    },
    "bm_fable": {
        "name": "Fable",
        "flag": "🇬🇧",
        "locale": "British Male",
        "tag": "Resonant • Theatrical",
        "desc": "Deep, articulate British male persona with theatrical gravity. Excellent for storytelling and essays.",
        "sample": "Greetings. I am Fable. Bring your text to life with resonant British narration."
    }
}


class MainWindow(ctk.CTk):
    """Primary GUI window providing settings, status, manual speech testing, and preferences."""

    def __init__(self, config, engine, on_read_selection=None, on_stop_reading=None, on_quit=None):
        super().__init__()

        self.config = config
        self.engine = engine
        self.on_read_selection = on_read_selection
        self.on_stop_reading = on_stop_reading
        self.on_quit = on_quit

        # Window Appearance
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.title("SpeakThat — Windows Text Reader (Paradee TTS)")
        self.geometry("940x690")
        self.minsize(860, 600)
        self.configure(fg_color="#0B0F19")

        # Icons & assets
        self._logo_image = None
        self._set_window_icon()

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
                self._logo_image = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(32, 32))
            except Exception:
                self._logo_image = None

    def _build_layout(self):
        # Configure root grid (Column 0: Rail 230px, Column 1: Stage expand)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0, minsize=230)
        self.grid_columnconfigure(1, weight=1)

        # 1. Left Navigation Rail
        self._build_navigation_rail()

        # 2. Right Content Stage
        self._build_stage()

    def _build_navigation_rail(self):
        self.rail = ctk.CTkFrame(
            self,
            fg_color="#0F172A",
            corner_radius=0,
            border_width=1,
            border_color="#1E293B",
            width=230
        )
        self.rail.grid(row=0, column=0, sticky="nsew")
        self.rail.grid_propagate(False)

        # --- Brand Lockup Header ---
        brand_frame = ctk.CTkFrame(self.rail, fg_color="transparent")
        brand_frame.pack(fill="x", padx=16, pady=(18, 14))

        icon_row = ctk.CTkFrame(brand_frame, fg_color="transparent")
        icon_row.pack(fill="x")

        if self._logo_image:
            logo_lbl = ctk.CTkLabel(icon_row, image=self._logo_image, text="")
            logo_lbl.pack(side="left", padx=(0, 10))

        title_box = ctk.CTkFrame(icon_row, fg_color="transparent")
        title_box.pack(side="left", fill="both")

        ctk.CTkLabel(
            title_box,
            text="SpeakThat",
            font=("Segoe UI", 16, "bold"),
            text_color="#F8FAFC"
        ).pack(anchor="w")

        badge = ctk.CTkLabel(
            title_box,
            text="v1.2 • Paradee 8M",
            font=("Segoe UI", 9, "bold"),
            text_color="#818CF8",
            fg_color="#1E1B4B",
            corner_radius=6,
            padx=6,
            pady=1
        )
        badge.pack(anchor="w", pady=(1, 0))

        # Divider
        ctk.CTkFrame(self.rail, height=1, fg_color="#1E293B").pack(fill="x", padx=16, pady=(6, 16))

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
                font=("Segoe UI", 12),
                anchor="w",
                height=40,
                corner_radius=8,
                fg_color="transparent",
                hover_color="#1E293B",
                text_color="#94A3B8",
                command=lambda tid=tab_id: self.show_view(tid)
            )
            btn.pack(fill="x", padx=12, pady=3)
            self.nav_buttons[tab_id] = btn

        # --- Rail Bottom Status Capsule ---
        rail_bottom = ctk.CTkFrame(self.rail, fg_color="transparent")
        rail_bottom.pack(side="bottom", fill="x", padx=14, pady=16)

        ctk.CTkFrame(rail_bottom, height=1, fg_color="#1E293B").pack(fill="x", pady=(0, 12))

        # Mini engine status capsule
        self.rail_status_pill = ctk.CTkLabel(
            rail_bottom,
            text="● Paradee Ready",
            font=("Segoe UI", 10, "bold"),
            text_color="#10B981",
            fg_color="#064E3B",
            corner_radius=12,
            padx=10,
            pady=4
        )
        self.rail_status_pill.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(
            rail_bottom,
            text="Global text reader active.\nRuns silently in background.",
            font=("Segoe UI", 9),
            text_color="#64748B",
            justify="left"
        ).pack(anchor="w")

    def _build_stage(self):
        # Stage Outer Container
        self.stage = ctk.CTkFrame(self, fg_color="#0B0F19", corner_radius=0)
        self.stage.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.stage.grid_rowconfigure(1, weight=1)
        self.stage.grid_columnconfigure(0, weight=1)

        # Stage Top Header Bar (Persistent)
        self.header_bar = ctk.CTkFrame(self.stage, fg_color="#0D1322", height=60, corner_radius=0, border_width=1, border_color="#1E293B")
        self.header_bar.grid(row=0, column=0, sticky="new")
        self.header_bar.grid_propagate(False)

        # Header Titles
        hb_left = ctk.CTkFrame(self.header_bar, fg_color="transparent")
        hb_left.pack(side="left", padx=20, pady=10)

        self.view_title_label = ctk.CTkLabel(
            hb_left,
            text="Studio Reader",
            font=("Segoe UI", 15, "bold"),
            text_color="#F8FAFC"
        )
        self.view_title_label.pack(anchor="w")

        self.view_sub_label = ctk.CTkLabel(
            hb_left,
            text="Instant Windows text reader powered by Paradee 8M",
            font=("Segoe UI", 10),
            text_color="#94A3B8"
        )
        self.view_sub_label.pack(anchor="w")

        # Header Right Micro Controls (Quick Status & Pause/Resume)
        hb_right = ctk.CTkFrame(self.header_bar, fg_color="transparent")
        hb_right.pack(side="right", padx=18, pady=12)

        self.status_badge = ctk.CTkLabel(
            hb_right,
            text="● Ready",
            font=("Segoe UI", 11, "bold"),
            text_color="#10B981",
            fg_color="#064E3B",
            corner_radius=8,
            padx=12,
            pady=3
        )
        self.status_badge.pack(side="left", padx=(0, 10))

        self.pause_resume_btn = ctk.CTkButton(
            hb_right,
            text="⏸ Pause",
            width=80,
            height=28,
            font=("Segoe UI", 11),
            fg_color="#1E293B",
            hover_color="#334155",
            command=self._on_click_pause_resume
        )
        self.pause_resume_btn.pack(side="left")

        # Content container where active view sits
        self.view_container = ctk.CTkFrame(self.stage, fg_color="transparent")
        self.view_container.grid(row=1, column=0, sticky="nsew", padx=20, pady=16)
        self.view_container.grid_rowconfigure(0, weight=1)
        self.view_container.grid_columnconfigure(0, weight=1)

        # Build all 4 views
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
                    fg_color="#1E293B",
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

        # Update Header Titles
        subtitles = {
            "reader": ("Studio Reader", "Select text across any Windows app and press Ctrl+Shift+R"),
            "voices": ("Voice Personas", "Select, preview, and adjust Paradee's 4 neural voice models"),
            "shortcuts": ("Shortcuts & Behavior", "Configure global hotkeys, clipboard preservation, and floating HUD"),
            "model": ("Model & Benchmark", "Paradee 8M architecture specifications and live latency benchmarking")
        }
        title, sub = subtitles.get(name, ("SpeakThat", ""))
        self.view_title_label.configure(text=title)
        self.view_sub_label.configure(text=sub)

    # =========================================================================
    # VIEW 1: STUDIO READER
    # =========================================================================
    def _create_reader_view(self):
        frame = ctk.CTkScrollableFrame(self.view_container, fg_color="transparent")

        # --- 1. Hero Global Hotkey Card ---
        hero_card = ctk.CTkFrame(frame, corner_radius=12, fg_color="#131C2E", border_width=1, border_color="#1E293B")
        hero_card.pack(fill="x", pady=(0, 14))

        hc_inner = ctk.CTkFrame(hero_card, fg_color="transparent")
        hc_inner.pack(fill="x", padx=18, pady=16)

        hc_left = ctk.CTkFrame(hc_inner, fg_color="transparent")
        hc_left.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(
            hc_left,
            text="GLOBAL SELECTION SHORTCUT",
            font=("Segoe UI", 10, "bold"),
            text_color="#818CF8"
        ).pack(anchor="w")

        # Key pills row
        pills_row = ctk.CTkFrame(hc_left, fg_color="transparent")
        pills_row.pack(anchor="w", pady=(6, 8))

        keys = ["Ctrl", "+", "Shift", "+", "R"]
        for k in keys:
            if k == "+":
                ctk.CTkLabel(pills_row, text="+", font=("Segoe UI", 13, "bold"), text_color="#64748B").pack(side="left", padx=4)
            else:
                pill = ctk.CTkLabel(
                    pills_row,
                    text=k,
                    font=("Segoe UI", 12, "bold"),
                    fg_color="#1E1B4B",
                    text_color="#C7D2FE",
                    corner_radius=6,
                    width=46,
                    height=28
                )
                pill.pack(side="left")

        ctk.CTkLabel(
            hc_left,
            text="Highlight any text in Chrome, PDF, Word, Slack or Notepad, then press the shortcut.",
            font=("Segoe UI", 11),
            text_color="#94A3B8"
        ).pack(anchor="w")

        # Action Buttons
        hc_right = ctk.CTkFrame(hc_inner, fg_color="transparent")
        hc_right.pack(side="right", padx=(10, 0))

        self.hero_read_btn = ctk.CTkButton(
            hc_right,
            text="▶ Read Selection Now",
            font=("Segoe UI", 12, "bold"),
            fg_color="#6366F1",
            hover_color="#4F46E5",
            height=36,
            command=self._on_click_read_selection
        )
        self.hero_read_btn.pack(pady=4)

        self.hero_stop_btn = ctk.CTkButton(
            hc_right,
            text="⏹ Stop Speech (Ctrl+Shift+X)",
            font=("Segoe UI", 11),
            fg_color="#7F1D1D",
            hover_color="#991B1B",
            height=30,
            command=self._on_click_stop
        )
        self.hero_stop_btn.pack(pady=4)

        # --- 2. Live Acoustic Visualizer & Spoken Sentence Marquee ---
        vis_card = ctk.CTkFrame(frame, corner_radius=12, fg_color="#131C2E", border_width=1, border_color="#1E293B")
        vis_card.pack(fill="x", pady=(0, 14))

        vc_inner = ctk.CTkFrame(vis_card, fg_color="transparent")
        vc_inner.pack(fill="x", padx=18, pady=14)

        vc_top = ctk.CTkFrame(vc_inner, fg_color="transparent")
        vc_top.pack(fill="x")

        ctk.CTkLabel(
            vc_top,
            text="LIVE SPEECH MONITOR",
            font=("Segoe UI", 10, "bold"),
            text_color="#818CF8"
        ).pack(side="left")

        # Canvas Waveform Visualizer
        self._wave_canvas = tk.Canvas(
            vc_inner,
            height=36,
            bg="#131C2E",
            highlightthickness=0
        )
        self._wave_canvas.pack(fill="x", pady=(8, 4))

        # Create 13 vertical rounded bars
        self._wave_bars = []
        for i in range(13):
            bar = self._wave_canvas.create_line(0, 0, 0, 0, width=5, capstyle=tk.ROUND, fill="#334155")
            self._wave_bars.append(bar)

        self._wave_canvas.bind("<Configure>", self._layout_waveform_bars)

        # Live spoken sentence quote display
        self.live_sentence_label = ctk.CTkLabel(
            vc_inner,
            text="“Select any text on Windows and press Ctrl+Shift+R to begin listening.”",
            font=("Segoe UI", 12, "italic"),
            text_color="#E2E8F0",
            anchor="w",
            wraplength=620,
            justify="left"
        )
        self.live_sentence_label.pack(fill="x", pady=(4, 2))

        # --- 3. Direct Text Reader Box & Scratchpad ---
        reader_card = ctk.CTkFrame(frame, corner_radius=12, fg_color="#131C2E", border_width=1, border_color="#1E293B")
        reader_card.pack(fill="x", pady=(0, 14))

        rc_inner = ctk.CTkFrame(reader_card, fg_color="transparent")
        rc_inner.pack(fill="x", padx=18, pady=16)

        rc_header = ctk.CTkFrame(rc_inner, fg_color="transparent")
        rc_header.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            rc_header,
            text="DIRECT TEXT READER & SCRATCHPAD",
            font=("Segoe UI", 11, "bold"),
            text_color="#F8FAFC"
        ).pack(side="left")

        self.char_metrics_lbl = ctk.CTkLabel(
            rc_header,
            text="16 words • 105 chars • ~6s audio",
            font=("Segoe UI", 10),
            text_color="#64748B"
        )
        self.char_metrics_lbl.pack(side="right")

        self.text_box = ctk.CTkTextbox(
            rc_inner,
            height=130,
            font=("Segoe UI", 11),
            corner_radius=8,
            border_width=1,
            border_color="#1E293B",
            fg_color="#090D16",
            wrap="word"
        )
        self.text_box.pack(fill="x", pady=(0, 10))
        self.text_box.insert("1.0", "Paradee is a small voice that runs anywhere. Select any text on Windows and press Ctrl+Shift+R to hear it.")
        self.text_box.bind("<KeyRelease>", self._update_text_metrics)

        # Actions row
        tb_actions = ctk.CTkFrame(rc_inner, fg_color="transparent")
        tb_actions.pack(fill="x")

        self.speak_box_btn = ctk.CTkButton(
            tb_actions,
            text="🗣️ Read This Text Now",
            font=("Segoe UI", 12, "bold"),
            fg_color="#6366F1",
            hover_color="#4F46E5",
            command=self._on_speak_box_text
        )
        self.speak_box_btn.pack(side="left", padx=(0, 10))

        self.paste_btn = ctk.CTkButton(
            tb_actions,
            text="📋 Paste Clipboard",
            width=120,
            fg_color="#1E293B",
            hover_color="#334155",
            command=self._on_paste_clipboard
        )
        self.paste_btn.pack(side="left", padx=(0, 8))

        self.clear_box_btn = ctk.CTkButton(
            tb_actions,
            text="🧹 Clear",
            width=70,
            fg_color="#1E293B",
            hover_color="#334155",
            command=self._on_clear_textbox
        )
        self.clear_box_btn.pack(side="left")

        return frame

    def _layout_waveform_bars(self, event=None):
        if not self._wave_canvas:
            return
        w = self._wave_canvas.winfo_width()
        if w < 100:
            w = 500
        n = len(self._wave_bars)
        spacing = w / (n + 1)
        for i, bar in enumerate(self._wave_bars):
            x = int((i + 1) * spacing)
            self._wave_canvas.coords(bar, x, 14, x, 22)

    def _animate_stage_wave(self):
        if self._wave_canvas and self._wave_bars:
            w = self._wave_canvas.winfo_width()
            n = len(self._wave_bars)
            spacing = w / (n + 1) if w > 50 else 30

            self._wave_phase += 0.25
            is_active = self._is_speaking_anim

            for i, bar in enumerate(self._wave_bars):
                x = int((i + 1) * spacing)
                if is_active:
                    h = 6 + int(12 * (1 + math.sin(self._wave_phase + i * 0.7)))
                    y1 = max(4, 18 - h // 2)
                    y2 = min(32, 18 + h // 2)
                    color = "#818CF8" if (i % 2 == 0) else "#6366F1"
                else:
                    y1, y2 = 16, 20
                    color = "#334155"

                self._wave_canvas.coords(bar, x, y1, x, y2)
                self._wave_canvas.itemconfig(bar, fill=color)

        self.after(50, self._animate_stage_wave)

    def _update_text_metrics(self, event=None):
        raw = self.text_box.get("1.0", "end-1c").strip()
        words = len(raw.split()) if raw else 0
        chars = len(raw)
        # Average reading speed ~150 words/min -> 2.5 words/sec
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
    # VIEW 2: VOICE PERSONAS
    # =========================================================================
    def _create_voices_view(self):
        frame = ctk.CTkScrollableFrame(self.view_container, fg_color="transparent")

        # --- 1. Grid of 4 Persona Cards ---
        ctk.CTkLabel(
            frame,
            text="SELECT VOICE PERSONA",
            font=("Segoe UI", 10, "bold"),
            text_color="#818CF8"
        ).pack(anchor="w", pady=(0, 8))

        self.persona_cards = {}
        for vkey, info in VOICE_DETAILS.items():
            card = ctk.CTkFrame(
                frame,
                corner_radius=10,
                fg_color="#131C2E",
                border_width=1,
                border_color="#1E293B"
            )
            card.pack(fill="x", pady=4)

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="x", padx=16, pady=12)

            # Left avatar & title
            left = ctk.CTkFrame(inner, fg_color="transparent")
            left.pack(side="left", fill="both", expand=True)

            top_row = ctk.CTkFrame(left, fg_color="transparent")
            top_row.pack(anchor="w")

            flag_lbl = ctk.CTkLabel(top_row, text=info["flag"], font=("Segoe UI Emoji", 16))
            flag_lbl.pack(side="left", padx=(0, 6))

            name_lbl = ctk.CTkLabel(top_row, text=info["name"], font=("Segoe UI", 13, "bold"), text_color="#F8FAFC")
            name_lbl.pack(side="left", padx=(0, 8))

            tag_lbl = ctk.CTkLabel(
                top_row,
                text=info["tag"],
                font=("Segoe UI", 9, "bold"),
                text_color="#818CF8",
                fg_color="#1E1B4B",
                corner_radius=4,
                padx=6,
                pady=1
            )
            tag_lbl.pack(side="left")

            desc_lbl = ctk.CTkLabel(left, text=info["desc"], font=("Segoe UI", 10), text_color="#94A3B8", anchor="w")
            desc_lbl.pack(anchor="w", pady=(4, 0))

            # Right actions (Audition + Select)
            right = ctk.CTkFrame(inner, fg_color="transparent")
            right.pack(side="right", padx=(8, 0))

            audition_btn = ctk.CTkButton(
                right,
                text="▶ Audition",
                font=("Segoe UI", 10, "bold"),
                width=86,
                height=28,
                fg_color="#1E293B",
                hover_color="#334155",
                command=lambda vk=vkey, smp=info["sample"]: self._on_audition_voice(vk, smp)
            )
            audition_btn.pack(side="left", padx=4)

            select_btn = ctk.CTkButton(
                right,
                text="Select",
                font=("Segoe UI", 10, "bold"),
                width=76,
                height=28,
                fg_color="#312E81",
                hover_color="#4338CA",
                command=lambda vk=vkey: self._on_select_persona(vk)
            )
            select_btn.pack(side="left")

            self.persona_cards[vkey] = {
                "card": card,
                "select_btn": select_btn
            }

        # --- 2. Reading Speed Settings Card ---
        speed_card = ctk.CTkFrame(frame, corner_radius=12, fg_color="#131C2E", border_width=1, border_color="#1E293B")
        speed_card.pack(fill="x", pady=(14, 0))

        sc_inner = ctk.CTkFrame(speed_card, fg_color="transparent")
        sc_inner.pack(fill="x", padx=18, pady=16)

        ctk.CTkLabel(
            sc_inner,
            text="READING SPEED PRESETS & PRECISION TUNER",
            font=("Segoe UI", 10, "bold"),
            text_color="#818CF8"
        ).pack(anchor="w", pady=(0, 8))

        # Speed Segmented Presets
        presets_frame = ctk.CTkFrame(sc_inner, fg_color="transparent")
        presets_frame.pack(fill="x", pady=(0, 10))

        speeds = [0.8, 1.0, 1.05, 1.25, 1.5, 2.0]
        self.speed_preset_btns = {}
        for sp in speeds:
            lbl = f"{sp}x"
            btn = ctk.CTkButton(
                presets_frame,
                text=lbl,
                width=55,
                height=28,
                font=("Segoe UI", 10, "bold"),
                fg_color="#1E293B",
                hover_color="#334155",
                command=lambda s=sp: self._apply_speed(s)
            )
            btn.pack(side="left", padx=(0, 6))
            self.speed_preset_btns[sp] = btn

        # Slider row
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
        self.speed_slider.pack(side="left", fill="x", expand=True, padx=(0, 12))

        self.speed_val_label = ctk.CTkLabel(
            slider_row,
            text="1.05x",
            font=("Segoe UI", 12, "bold"),
            text_color="#F8FAFC",
            width=50
        )
        self.speed_val_label.pack(side="left")

        # --- 3. Audio Volume Control ---
        vol_card = ctk.CTkFrame(frame, corner_radius=12, fg_color="#131C2E", border_width=1, border_color="#1E293B")
        vol_card.pack(fill="x", pady=(14, 0))

        vc_inner = ctk.CTkFrame(vol_card, fg_color="transparent")
        vc_inner.pack(fill="x", padx=18, pady=16)

        ctk.CTkLabel(
            vc_inner,
            text="OUTPUT VOLUME",
            font=("Segoe UI", 10, "bold"),
            text_color="#818CF8"
        ).pack(anchor="w", pady=(0, 8))

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
        self.vol_slider.pack(side="left", fill="x", expand=True, padx=(0, 12))

        self.vol_val_label = ctk.CTkLabel(
            vol_row,
            text="100%",
            font=("Segoe UI", 12, "bold"),
            text_color="#F8FAFC",
            width=50
        )
        self.vol_val_label.pack(side="left")

        return frame

    def _on_select_persona(self, voice_key):
        self.config.set("voice", voice_key)
        self.engine.set_voice(voice_key)
        self._highlight_selected_persona(voice_key)

    def _highlight_selected_persona(self, active_key):
        for vkey, items in self.persona_cards.items():
            card = items["card"]
            btn = items["select_btn"]
            if vkey == active_key:
                card.configure(border_color="#6366F1", border_width=2, fg_color="#161F36")
                btn.configure(text="✓ Active", fg_color="#6366F1", hover_color="#4F46E5")
            else:
                card.configure(border_color="#1E293B", border_width=1, fg_color="#131C2E")
                btn.configure(text="Select", fg_color="#1E293B", hover_color="#334155")

    def _on_audition_voice(self, voice_key, sample_phrase):
        # Speak audition directly using requested voice
        orig_voice = self.engine.voice
        self.engine.set_voice(voice_key)
        self.engine.speak(sample_phrase)
        # Restore if not active
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
    # VIEW 3: SHORTCUTS & BEHAVIOR
    # =========================================================================
    def _create_shortcuts_view(self):
        frame = ctk.CTkScrollableFrame(self.view_container, fg_color="transparent")

        # --- 1. Global Shortcuts Reference Card ---
        hk_card = ctk.CTkFrame(frame, corner_radius=12, fg_color="#131C2E", border_width=1, border_color="#1E293B")
        hk_card.pack(fill="x", pady=(0, 14))

        hk_inner = ctk.CTkFrame(hk_card, fg_color="transparent")
        hk_inner.pack(fill="x", padx=18, pady=16)

        ctk.CTkLabel(
            hk_inner,
            text="SYSTEM-WIDE SHORTCUT KEYS",
            font=("Segoe UI", 10, "bold"),
            text_color="#818CF8"
        ).pack(anchor="w", pady=(0, 10))

        # Shortcut 1: Read
        r1 = ctk.CTkFrame(hk_inner, fg_color="transparent")
        r1.pack(fill="x", pady=4)
        ctk.CTkLabel(r1, text="Read Selected Text:", font=("Segoe UI", 11, "bold"), width=160, anchor="w").pack(side="left")

        pills1 = ctk.CTkFrame(r1, fg_color="transparent")
        pills1.pack(side="left")
        for k in ["Ctrl", "+", "Shift", "+", "R"]:
            if k == "+":
                ctk.CTkLabel(pills1, text="+", font=("Segoe UI", 12, "bold"), text_color="#64748B").pack(side="left", padx=3)
            else:
                ctk.CTkLabel(pills1, text=k, font=("Segoe UI", 11, "bold"), fg_color="#1E1B4B", text_color="#C7D2FE", corner_radius=4, width=42, height=24).pack(side="left")

        # Shortcut 2: Stop
        r2 = ctk.CTkFrame(hk_inner, fg_color="transparent")
        r2.pack(fill="x", pady=6)
        ctk.CTkLabel(r2, text="Stop Audio Playback:", font=("Segoe UI", 11, "bold"), width=160, anchor="w").pack(side="left")

        pills2 = ctk.CTkFrame(r2, fg_color="transparent")
        pills2.pack(side="left")
        for k in ["Ctrl", "+", "Shift", "+", "X"]:
            if k == "+":
                ctk.CTkLabel(pills2, text="+", font=("Segoe UI", 12, "bold"), text_color="#64748B").pack(side="left", padx=3)
            else:
                ctk.CTkLabel(pills2, text=k, font=("Segoe UI", 11, "bold"), fg_color="#3B1219", text_color="#FECACA", corner_radius=4, width=42, height=24).pack(side="left")

        # Modifier key release guarantee note
        ctk.CTkLabel(
            hk_inner,
            text="✓ Keyboard emulation waits for physical Shift & Control keys to be released before triggering copy, guaranteeing 100% reliable capture in all browsers and PDF readers.",
            font=("Segoe UI", 10),
            text_color="#10B981",
            justify="left"
        ).pack(anchor="w", pady=(8, 0))

        # --- 2. Behavior Toggles Card ---
        pref_card = ctk.CTkFrame(frame, corner_radius=12, fg_color="#131C2E", border_width=1, border_color="#1E293B")
        pref_card.pack(fill="x", pady=(0, 14))

        pf_inner = ctk.CTkFrame(pref_card, fg_color="transparent")
        pf_inner.pack(fill="x", padx=18, pady=16)

        ctk.CTkLabel(
            pf_inner,
            text="AUTOMATION & CLIPBOARD BEHAVIOR",
            font=("Segoe UI", 10, "bold"),
            text_color="#818CF8"
        ).pack(anchor="w", pady=(0, 12))

        # Toggle 1: Preserve clipboard
        self.sw_restore_clip = ctk.CTkSwitch(
            pf_inner,
            text="Preserve Clipboard History",
            font=("Segoe UI", 11, "bold"),
            progress_color="#6366F1",
            command=self._on_pref_changed
        )
        self.sw_restore_clip.pack(anchor="w", pady=(4, 1))
        ctk.CTkLabel(
            pf_inner,
            text="Restores original clipboard content after capturing highlighted text, keeping your clipboard untouched.",
            font=("Segoe UI", 10),
            text_color="#94A3B8"
        ).pack(anchor="w", padx=(48, 0), pady=(0, 8))

        # Toggle 2: Fallback to clipboard
        self.sw_fallback_clip = ctk.CTkSwitch(
            pf_inner,
            text="Clipboard Fallback on Empty Selection",
            font=("Segoe UI", 11, "bold"),
            progress_color="#6366F1",
            command=self._on_pref_changed
        )
        self.sw_fallback_clip.pack(anchor="w", pady=(4, 1))
        ctk.CTkLabel(
            pf_inner,
            text="If no text is highlighted when pressing Ctrl+Shift+R, speak whatever text is already copied in the clipboard.",
            font=("Segoe UI", 10),
            text_color="#94A3B8"
        ).pack(anchor="w", padx=(48, 0), pady=(0, 8))

        # Toggle 3: Floating Dynamic Island HUD
        self.sw_floating_hud = ctk.CTkSwitch(
            pf_inner,
            text="Show Floating Dynamic Island HUD",
            font=("Segoe UI", 11, "bold"),
            progress_color="#6366F1",
            command=self._on_pref_changed
        )
        self.sw_floating_hud.pack(anchor="w", pady=(4, 1))
        ctk.CTkLabel(
            pf_inner,
            text="Displays a sleek, draggable floating pill widget on screen while speaking with pause/stop micro-controls.",
            font=("Segoe UI", 10),
            text_color="#94A3B8"
        ).pack(anchor="w", padx=(48, 0), pady=(0, 8))

        # Toggle 4: Minimize to tray on close
        self.sw_min_to_tray = ctk.CTkSwitch(
            pf_inner,
            text="Minimize to System Tray on Close (X)",
            font=("Segoe UI", 11, "bold"),
            progress_color="#6366F1",
            command=self._on_pref_changed
        )
        self.sw_min_to_tray.pack(anchor="w", pady=(4, 1))
        ctk.CTkLabel(
            pf_inner,
            text="Keeps SpeakThat running in the Windows notification tray so hotkeys remain active.",
            font=("Segoe UI", 10),
            text_color="#94A3B8"
        ).pack(anchor="w", padx=(48, 0), pady=(0, 4))

        return frame

    def _on_pref_changed(self):
        self.config.set("restore_clipboard", bool(self.sw_restore_clip.get()))
        self.config.set("fallback_to_clipboard", bool(self.sw_fallback_clip.get()))
        self.config.set("show_floating_hud", bool(self.sw_floating_hud.get()))
        self.config.set("minimize_to_tray_on_close", bool(self.sw_min_to_tray.get()))

    # =========================================================================
    # VIEW 4: MODEL & BENCHMARK
    # =========================================================================
    def _create_model_view(self):
        frame = ctk.CTkScrollableFrame(self.view_container, fg_color="transparent")

        # --- 1. Technical Specs Card ---
        specs_card = ctk.CTkFrame(frame, corner_radius=12, fg_color="#131C2E", border_width=1, border_color="#1E293B")
        specs_card.pack(fill="x", pady=(0, 14))

        sp_inner = ctk.CTkFrame(specs_card, fg_color="transparent")
        sp_inner.pack(fill="x", padx=18, pady=16)

        ctk.CTkLabel(
            sp_inner,
            text="PARADEE 8M ARCHITECTURE & HARDWARE ENGINE",
            font=("Segoe UI", 10, "bold"),
            text_color="#818CF8"
        ).pack(anchor="w", pady=(0, 10))

        spec_grid = [
            ("Neural Model", "Paradee-8M-v1.2 (Quantized Int8 ONNX Graph)"),
            ("Parameter Count", "8,200,000 parameters (Ultra-lightweight)"),
            ("Audio Output", "24,000 Hz (24 kHz) Mono, 32-bit Float Streaming"),
            ("Inference Engine", "ONNX Runtime CPU (Pure Offline / Zero Cloud)"),
            ("G2P Phonemizer", "Misaki Pure-Python G2P + Spacy Tokenizer"),
            ("Streaming Pipeline", "Sentence-chunked async synthesis into SoundDevice ring buffer")
        ]

        for label, val in spec_grid:
            row = ctk.CTkFrame(sp_inner, fg_color="transparent")
            row.pack(fill="x", pady=3)
            ctk.CTkLabel(row, text=label, font=("Segoe UI", 11, "bold"), text_color="#94A3B8", width=140, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=val, font=("Segoe UI", 11), text_color="#E2E8F0", anchor="w").pack(side="left")

        # --- 2. Live Synthesis Latency Benchmark Tool ---
        bench_card = ctk.CTkFrame(frame, corner_radius=12, fg_color="#131C2E", border_width=1, border_color="#1E293B")
        bench_card.pack(fill="x", pady=(0, 14))

        bc_inner = ctk.CTkFrame(bench_card, fg_color="transparent")
        bc_inner.pack(fill="x", padx=18, pady=16)

        bc_top = ctk.CTkFrame(bc_inner, fg_color="transparent")
        bc_top.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            bc_top,
            text="LIVE SYNTHESIS LATENCY BENCHMARK",
            font=("Segoe UI", 10, "bold"),
            text_color="#818CF8"
        ).pack(side="left")

        self.bench_btn = ctk.CTkButton(
            bc_top,
            text="⚡ Run Benchmark Now",
            font=("Segoe UI", 11, "bold"),
            fg_color="#6366F1",
            hover_color="#4F46E5",
            command=self._run_latency_benchmark
        )
        self.bench_btn.pack(side="right")

        ctk.CTkLabel(
            bc_inner,
            text="Measures raw ONNX inference execution time and Real-Time Factor (RTF) on this machine.",
            font=("Segoe UI", 10),
            text_color="#94A3B8"
        ).pack(anchor="w", pady=(0, 12))

        # Metrics 3-Card Row
        metrics_row = ctk.CTkFrame(bc_inner, fg_color="transparent")
        metrics_row.pack(fill="x", pady=(0, 8))

        # Card A: Latency
        m_a = ctk.CTkFrame(metrics_row, fg_color="#0F172A", corner_radius=8, border_width=1, border_color="#1E293B")
        m_a.pack(side="left", fill="both", expand=True, padx=(0, 6))
        ctk.CTkLabel(m_a, text="SYNTHESIS TIME", font=("Segoe UI", 9, "bold"), text_color="#818CF8").pack(anchor="w", padx=12, pady=(10, 2))
        self.bench_time_lbl = ctk.CTkLabel(m_a, text="-- ms", font=("Segoe UI", 18, "bold"), text_color="#F8FAFC")
        self.bench_time_lbl.pack(anchor="w", padx=12, pady=(0, 10))

        # Card B: RTF
        m_b = ctk.CTkFrame(metrics_row, fg_color="#0F172A", corner_radius=8, border_width=1, border_color="#1E293B")
        m_b.pack(side="left", fill="both", expand=True, padx=3)
        ctk.CTkLabel(m_b, text="REAL-TIME FACTOR", font=("Segoe UI", 9, "bold"), text_color="#10B981").pack(anchor="w", padx=12, pady=(10, 2))
        self.bench_rtf_lbl = ctk.CTkLabel(m_b, text="-- x", font=("Segoe UI", 18, "bold"), text_color="#F8FAFC")
        self.bench_rtf_lbl.pack(anchor="w", padx=12, pady=(0, 10))

        # Card C: Audio Generated
        m_c = ctk.CTkFrame(metrics_row, fg_color="#0F172A", corner_radius=8, border_width=1, border_color="#1E293B")
        m_c.pack(side="left", fill="both", expand=True, padx=(6, 0))
        ctk.CTkLabel(m_c, text="AUDIO DURATION", font=("Segoe UI", 9, "bold"), text_color="#38BDF8").pack(anchor="w", padx=12, pady=(10, 2))
        self.bench_dur_lbl = ctk.CTkLabel(m_c, text="-- s", font=("Segoe UI", 18, "bold"), text_color="#F8FAFC")
        self.bench_dur_lbl.pack(anchor="w", padx=12, pady=(0, 10))

        self.bench_status_lbl = ctk.CTkLabel(
            bc_inner,
            text="Click 'Run Benchmark Now' to test Paradee 8M inference speed.",
            font=("Segoe UI", 10, "italic"),
            text_color="#64748B"
        )
        self.bench_status_lbl.pack(anchor="w", pady=(4, 0))

        return frame

    def _run_latency_benchmark(self):
        self.bench_btn.configure(state="disabled", text="Running...")
        self.bench_status_lbl.configure(text="Synthesizing benchmark sentence across neural graph...", text_color="#818CF8")

        def _bench_worker():
            try:
                # Wait for engine readiness if needed
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
                        text=f"Benchmark completed successfully! Generation is {rtf:.1f}x faster than real-time playback.",
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

        if self.config.get("show_floating_hud", True):
            self.sw_floating_hud.select()
        else:
            self.sw_floating_hud.deselect()

        if self.config.get("minimize_to_tray_on_close", True):
            self.sw_min_to_tray.select()
        else:
            self.sw_min_to_tray.deselect()

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
            if len(s) > 120:
                s = s[:117] + "…"
            self.live_sentence_label.configure(text=f'“{s}”')
        self.after(0, _update)

    def _on_window_close(self):
        if self.config.get("minimize_to_tray_on_close", True):
            self.withdraw()
        else:
            if self.on_quit:
                self.on_quit()
            else:
                self.destroy()
