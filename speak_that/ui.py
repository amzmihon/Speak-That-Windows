"""Modern CustomTkinter Dashboard & Settings Window for SpeakThat."""

import os
import threading
import tkinter as tk
import customtkinter as ctk

from .config import VOICE_NAMES


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
        self.geometry("740x780")
        self.minsize(680, 640)

        # Set Window Icon
        self._set_window_icon()

        # Handle window close protocol (minimize to tray if configured)
        self.protocol("WM_DELETE_WINDOW", self._on_window_close)

        # Build UI layout
        self._build_ui()

        # Sync UI with config values
        self._load_config_to_ui()

    def _set_window_icon(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ico_path = os.path.join(base_dir, "assets", "icon.ico")
        if os.path.exists(ico_path):
            try:
                self.iconbitmap(ico_path)
            except Exception:
                pass

    def _build_ui(self):
        # Main scrollable canvas container
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=15)

        # --- 1. Header Banner ---
        self.header_frame = ctk.CTkFrame(self.scroll_frame, corner_radius=12, fg_color="#1e1b4b", border_width=1, border_color="#3730a3")
        self.header_frame.pack(fill="x", pady=(0, 15), padx=2)

        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text="🗣️ SpeakThat",
            font=("Segoe UI", 24, "bold"),
            text_color="#c7d2fe"
        )
        self.title_label.pack(anchor="w", padx=20, pady=(14, 2))

        self.subtitle_label = ctk.CTkLabel(
            self.header_frame,
            text="Lightning-fast Windows Text Reader powered by Paradee 8M ONNX TTS",
            font=("Segoe UI", 12),
            text_color="#a5b4fc"
        )
        self.subtitle_label.pack(anchor="w", padx=20, pady=(0, 14))

        # --- 2. Hotkey Quick-Action Card ---
        self.hotkey_card = ctk.CTkFrame(self.scroll_frame, corner_radius=12, fg_color="#181825", border_width=1, border_color="#2d2d42")
        self.hotkey_card.pack(fill="x", pady=(0, 15), padx=2)

        hk_inner = ctk.CTkFrame(self.hotkey_card, fg_color="transparent")
        hk_inner.pack(fill="x", padx=16, pady=14)

        hk_left = ctk.CTkFrame(hk_inner, fg_color="transparent")
        hk_left.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(
            hk_left,
            text="GLOBAL SHORTCUT",
            font=("Segoe UI", 10, "bold"),
            text_color="#818cf8"
        ).pack(anchor="w")

        # Key pills
        pills_frame = ctk.CTkFrame(hk_left, fg_color="transparent")
        pills_frame.pack(anchor="w", pady=(4, 6))

        for k in ["Ctrl", "Shift", "R"]:
            pill = ctk.CTkLabel(
                pills_frame,
                text=k,
                font=("Segoe UI", 12, "bold"),
                fg_color="#312e81",
                text_color="#e0e7ff",
                corner_radius=6,
                width=48,
                height=28
            )
            pill.pack(side="left", padx=(0, 6))

        ctk.CTkLabel(
            hk_left,
            text="Select text in any app (browser, PDF, Word, etc.) and press shortcut to read aloud.",
            font=("Segoe UI", 11),
            text_color="#94a3b8"
        ).pack(anchor="w")

        # Right action buttons
        hk_right = ctk.CTkFrame(hk_inner, fg_color="transparent")
        hk_right.pack(side="right", padx=10)

        self.read_sel_btn = ctk.CTkButton(
            hk_right,
            text="▶ Read Selection Now",
            font=("Segoe UI", 12, "bold"),
            fg_color="#4f46e5",
            hover_color="#4338ca",
            height=36,
            command=self._on_click_read_selection
        )
        self.read_sel_btn.pack(pady=4)

        self.stop_btn = ctk.CTkButton(
            hk_right,
            text="⏹ Stop Speech (Ctrl+Shift+X)",
            font=("Segoe UI", 11),
            fg_color="#dc2626",
            hover_color="#b91c1c",
            height=32,
            command=self._on_click_stop
        )
        self.stop_btn.pack(pady=4)

        # --- 3. Live Status & Player Banner ---
        self.status_card = ctk.CTkFrame(self.scroll_frame, corner_radius=12, fg_color="#181825", border_width=1, border_color="#2d2d42")
        self.status_card.pack(fill="x", pady=(0, 15), padx=2)

        st_inner = ctk.CTkFrame(self.status_card, fg_color="transparent")
        st_inner.pack(fill="x", padx=16, pady=12)

        st_top = ctk.CTkFrame(st_inner, fg_color="transparent")
        st_top.pack(fill="x")

        ctk.CTkLabel(
            st_top,
            text="STATUS",
            font=("Segoe UI", 10, "bold"),
            text_color="#94a3b8"
        ).pack(side="left")

        self.status_badge = ctk.CTkLabel(
            st_top,
            text="● Ready",
            font=("Segoe UI", 11, "bold"),
            text_color="#10b981",
            fg_color="#064e3b",
            corner_radius=6,
            padx=10,
            pady=2
        )
        self.status_badge.pack(side="left", padx=10)

        self.pause_resume_btn = ctk.CTkButton(
            st_top,
            text="⏸ Pause",
            width=80,
            height=26,
            font=("Segoe UI", 11),
            fg_color="#334155",
            hover_color="#475569",
            command=self._on_click_pause_resume
        )
        self.pause_resume_btn.pack(side="right")

        self.live_sentence_label = ctk.CTkLabel(
            st_inner,
            text="Press Ctrl+Shift+R on highlighted text to begin listening.",
            font=("Segoe UI", 11, "italic"),
            text_color="#cbd5e1",
            anchor="w"
        )
        self.live_sentence_label.pack(fill="x", pady=(8, 0))

        # --- 4. Voice & Speech Settings ---
        self.voice_card = ctk.CTkFrame(self.scroll_frame, corner_radius=12, fg_color="#181825", border_width=1, border_color="#2d2d42")
        self.voice_card.pack(fill="x", pady=(0, 15), padx=2)

        vc_inner = ctk.CTkFrame(self.voice_card, fg_color="transparent")
        vc_inner.pack(fill="x", padx=16, pady=14)

        ctk.CTkLabel(
            vc_inner,
            text="VOICE & AUDIO SETTINGS",
            font=("Segoe UI", 12, "bold"),
            text_color="#c7d2fe"
        ).pack(anchor="w", pady=(0, 10))

        # Voice Selector Row
        row_voice = ctk.CTkFrame(vc_inner, fg_color="transparent")
        row_voice.pack(fill="x", pady=6)

        ctk.CTkLabel(row_voice, text="Voice Persona:", font=("Segoe UI", 11, "bold"), width=110, anchor="w").pack(side="left")

        voice_options = [f"{k} — {v}" for k, v in VOICE_NAMES.items()]
        self.voice_dropdown = ctk.CTkOptionMenu(
            row_voice,
            values=voice_options,
            command=self._on_voice_selected,
            width=320,
            fg_color="#312e81",
            button_color="#4338ca",
            button_hover_color="#4f46e5"
        )
        self.voice_dropdown.pack(side="left", padx=10)

        self.test_voice_btn = ctk.CTkButton(
            row_voice,
            text="🔊 Test Voice",
            width=110,
            command=self._on_test_voice,
            fg_color="#2563eb",
            hover_color="#1d4ed8"
        )
        self.test_voice_btn.pack(side="left", padx=6)

        # Speed Slider Row
        row_speed = ctk.CTkFrame(vc_inner, fg_color="transparent")
        row_speed.pack(fill="x", pady=8)

        ctk.CTkLabel(row_speed, text="Reading Speed:", font=("Segoe UI", 11, "bold"), width=110, anchor="w").pack(side="left")

        self.speed_slider = ctk.CTkSlider(
            row_speed,
            from_=0.7,
            to=2.0,
            number_of_steps=26,
            command=self._on_speed_changed,
            width=320,
            progress_color="#6366f1"
        )
        self.speed_slider.pack(side="left", padx=10)

        self.speed_val_label = ctk.CTkLabel(row_speed, text="1.05x", font=("Segoe UI", 11, "bold"), width=60)
        self.speed_val_label.pack(side="left")

        # Volume Slider Row
        row_vol = ctk.CTkFrame(vc_inner, fg_color="transparent")
        row_vol.pack(fill="x", pady=8)

        ctk.CTkLabel(row_vol, text="Audio Volume:", font=("Segoe UI", 11, "bold"), width=110, anchor="w").pack(side="left")

        self.vol_slider = ctk.CTkSlider(
            row_vol,
            from_=0.1,
            to=1.0,
            number_of_steps=18,
            command=self._on_volume_changed,
            width=320,
            progress_color="#6366f1"
        )
        self.vol_slider.pack(side="left", padx=10)

        self.vol_val_label = ctk.CTkLabel(row_vol, text="100%", font=("Segoe UI", 11, "bold"), width=60)
        self.vol_val_label.pack(side="left")

        # --- 5. Direct Text Reader Box ---
        self.reader_card = ctk.CTkFrame(self.scroll_frame, corner_radius=12, fg_color="#181825", border_width=1, border_color="#2d2d42")
        self.reader_card.pack(fill="x", pady=(0, 15), padx=2)

        rc_inner = ctk.CTkFrame(self.reader_card, fg_color="transparent")
        rc_inner.pack(fill="x", padx=16, pady=14)

        ctk.CTkLabel(
            rc_inner,
            text="DIRECT TEXT READER (TYPE OR PASTE)",
            font=("Segoe UI", 12, "bold"),
            text_color="#c7d2fe"
        ).pack(anchor="w", pady=(0, 6))

        self.text_box = ctk.CTkTextbox(
            rc_inner,
            height=120,
            font=("Segoe UI", 11),
            corner_radius=8,
            border_width=1,
            border_color="#334155",
            fg_color="#0f172a"
        )
        self.text_box.pack(fill="x", pady=(0, 8))
        self.text_box.insert("1.0", "Paradee is a small voice that runs anywhere. Select any text on Windows and press Ctrl+Shift+R to hear it.")

        tb_actions = ctk.CTkFrame(rc_inner, fg_color="transparent")
        tb_actions.pack(fill="x")

        self.speak_box_btn = ctk.CTkButton(
            tb_actions,
            text="🗣️ Read This Text",
            font=("Segoe UI", 12, "bold"),
            fg_color="#4f46e5",
            hover_color="#4338ca",
            command=self._on_speak_box_text
        )
        self.speak_box_btn.pack(side="left", padx=(0, 10))

        self.clear_box_btn = ctk.CTkButton(
            tb_actions,
            text="Clear",
            width=70,
            fg_color="#334155",
            hover_color="#475569",
            command=lambda: self.text_box.delete("1.0", "end")
        )
        self.clear_box_btn.pack(side="left")

        # --- 6. Preferences & Behaviors ---
        self.pref_card = ctk.CTkFrame(self.scroll_frame, corner_radius=12, fg_color="#181825", border_width=1, border_color="#2d2d42")
        self.pref_card.pack(fill="x", pady=(0, 15), padx=2)

        pf_inner = ctk.CTkFrame(self.pref_card, fg_color="transparent")
        pf_inner.pack(fill="x", padx=16, pady=14)

        ctk.CTkLabel(
            pf_inner,
            text="BEHAVIOR & PREFERENCES",
            font=("Segoe UI", 12, "bold"),
            text_color="#c7d2fe"
        ).pack(anchor="w", pady=(0, 10))

        self.cb_restore_clip = ctk.CTkCheckBox(
            pf_inner,
            text="Preserve clipboard history (restores original clipboard content after reading selection)",
            font=("Segoe UI", 11),
            command=self._on_pref_changed
        )
        self.cb_restore_clip.pack(anchor="w", pady=4)

        self.cb_fallback_clip = ctk.CTkCheckBox(
            pf_inner,
            text="Read existing clipboard text if no active text is highlighted",
            font=("Segoe UI", 11),
            command=self._on_pref_changed
        )
        self.cb_fallback_clip.pack(anchor="w", pady=4)

        self.cb_floating_hud = ctk.CTkCheckBox(
            pf_inner,
            text="Show floating mini-player HUD on screen while speaking",
            font=("Segoe UI", 11),
            command=self._on_pref_changed
        )
        self.cb_floating_hud.pack(anchor="w", pady=4)

        self.cb_min_to_tray = ctk.CTkCheckBox(
            pf_inner,
            text="Minimize to system tray when clicking close (X)",
            font=("Segoe UI", 11),
            command=self._on_pref_changed
        )
        self.cb_min_to_tray.pack(anchor="w", pady=4)

    def _load_config_to_ui(self):
        # Voice
        cur_voice = self.config.get("voice", "bf_isabella")
        for opt in self.voice_dropdown._values:
            if opt.startswith(cur_voice):
                self.voice_dropdown.set(opt)
                break

        # Speed
        spd = float(self.config.get("speed", 1.05))
        self.speed_slider.set(spd)
        self.speed_val_label.configure(text=f"{spd:.2f}x")

        # Volume
        vol = float(self.config.get("volume", 1.0))
        self.vol_slider.set(vol)
        self.vol_val_label.configure(text=f"{int(vol * 100)}%")

        # Checkboxes
        if self.config.get("restore_clipboard", True):
            self.cb_restore_clip.select()
        else:
            self.cb_restore_clip.deselect()

        if self.config.get("fallback_to_clipboard", True):
            self.cb_fallback_clip.select()
        else:
            self.cb_fallback_clip.deselect()

        if self.config.get("show_floating_hud", True):
            self.cb_floating_hud.select()
        else:
            self.cb_floating_hud.deselect()

        if self.config.get("minimize_to_tray_on_close", True):
            self.cb_min_to_tray.select()
        else:
            self.cb_min_to_tray.deselect()

    def _on_voice_selected(self, choice):
        voice_key = choice.split(" ")[0].strip()
        self.config.set("voice", voice_key)
        self.engine.set_voice(voice_key)

    def _on_speed_changed(self, value):
        spd = round(value, 2)
        self.speed_val_label.configure(text=f"{spd:.2f}x")
        self.config.set("speed", spd)
        self.engine.set_speed(spd)

    def _on_volume_changed(self, value):
        vol = round(value, 2)
        self.vol_val_label.configure(text=f"{int(vol * 100)}%")
        self.config.set("volume", vol)
        self.engine.set_volume(vol)

    def _on_pref_changed(self):
        self.config.set("restore_clipboard", bool(self.cb_restore_clip.get()))
        self.config.set("fallback_to_clipboard", bool(self.cb_fallback_clip.get()))
        self.config.set("show_floating_hud", bool(self.cb_floating_hud.get()))
        self.config.set("minimize_to_tray_on_close", bool(self.cb_min_to_tray.get()))

    def _on_test_voice(self):
        cur_voice = self.config.get("voice", "bf_isabella")
        name = VOICE_NAMES.get(cur_voice, cur_voice)
        phrase = f"Hello! This is {name} speaking. Paradee is a small voice that runs anywhere."
        self.engine.speak(phrase)

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
        """Thread-safe status update."""
        def _update():
            if status.lower() == "ready":
                self.status_badge.configure(text="● Ready", text_color="#10b981", fg_color="#064e3b")
                self.pause_resume_btn.configure(text="⏸ Pause", state="disabled")
            elif status.lower() == "speaking":
                self.status_badge.configure(text="● Speaking", text_color="#60a5fa", fg_color="#1e3a8a")
                self.pause_resume_btn.configure(text="⏸ Pause", state="normal")
            elif status.lower() == "paused":
                self.status_badge.configure(text="● Paused", text_color="#f59e0b", fg_color="#78350f")
                self.pause_resume_btn.configure(text="▶ Resume", state="normal")
            elif status.lower() == "synthesizing...":
                self.status_badge.configure(text="● Synthesizing", text_color="#c084fc", fg_color="#581c87")
                self.pause_resume_btn.configure(text="⏸ Pause", state="normal")
            else:
                self.status_badge.configure(text=f"● {status}", text_color="#94a3b8", fg_color="#334155")

        self.after(0, _update)

    def update_sentence(self, sentence):
        """Thread-safe sentence update."""
        def _update():
            s = sentence.strip().replace("\n", " ")
            if len(s) > 75:
                s = s[:72] + "…"
            self.live_sentence_label.configure(text=f'"{s}"')
        self.after(0, _update)

    def _on_window_close(self):
        if self.config.get("minimize_to_tray_on_close", True):
            self.withdraw()
        else:
            if self.on_quit:
                self.on_quit()
            else:
                self.destroy()

