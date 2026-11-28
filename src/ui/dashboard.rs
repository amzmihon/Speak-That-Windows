use eframe::egui;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex, RwLock};
use std::time::Duration;
use tokio::sync::watch;

use crate::audio::TtsEngine;
use crate::config::{ActionBinding, AppConfig, ShortcutConfig};
use crate::downloader::{DownloadState, ModelDownloader};
use crate::input::{
    CollisionSeverity, InputChord, InputHookManager, ModifierKey, ShortcutCatalog, TriggerSource,
};
use crate::ui::browser_detect::{BrowserDetector, InstalledBrowser};
use crate::ui::reader_view::ReaderViewWindow;

/// Loads Windows Segoe UI / Symbol / Emoji fonts into egui as fallbacks so no missing-glyph boxes appear.
pub fn configure_windows_fonts(ctx: &egui::Context) {
    let mut fonts = egui::FontDefinitions::default();
    let candidates = [
        ("segoe_ui", r"C:\Windows\Fonts\segoeui.ttf"),
        ("segoe_symbol", r"C:\Windows\Fonts\seguisym.ttf"),
        ("segoe_emoji", r"C:\Windows\Fonts\seguiemj.ttf"),
    ];

    for (name, path) in candidates {
        if let Ok(bytes) = std::fs::read(path) {
            fonts
                .font_data
                .insert(name.to_owned(), egui::FontData::from_owned(bytes));
            if let Some(fam) = fonts.families.get_mut(&egui::FontFamily::Proportional) {
                fam.push(name.to_owned());
            }
            if let Some(fam) = fonts.families.get_mut(&egui::FontFamily::Monospace) {
                fam.push(name.to_owned());
            }
        }
    }

    ctx.set_fonts(fonts);
}

#[derive(PartialEq, Eq, Clone, Copy)]
enum DashboardTab {
    Shortcuts,
    Voice,
    Bionic,
    Dictation,
    Browsers,
}

#[derive(PartialEq, Eq, Clone, Copy)]
enum EditingShortcut {
    SpeakSelection,
    StopSpeaking,
    PushToTalk,
    OpenHome,
    ToggleBionic,
    ToggleReader,
}

impl EditingShortcut {
    fn title(&self) -> &'static str {
        match self {
            Self::SpeakSelection => "Speak Selection",
            Self::StopSpeaking => "Stop Speaking (TTS)",
            Self::PushToTalk => "Push-to-Talk (STT)",
            Self::OpenHome => "Open Home Dashboard",
            Self::ToggleBionic => "Toggle Bionic Reading",
            Self::ToggleReader => "Toggle Reader View",
        }
    }

    fn allows_single_key(&self) -> bool {
        matches!(self, Self::OpenHome)
    }
}

pub struct SettingsDashboard {
    config: AppConfig,
    shared_shortcuts: Arc<RwLock<ShortcutConfig>>,
    show_dashboard_req: Arc<AtomicBool>,
    quit_requested: Arc<AtomicBool>,
    reader_request: Arc<Mutex<Option<String>>>,
    reader_window: Option<ReaderViewWindow>,
    active_tab: DashboardTab,
    tts: Arc<TtsEngine>,
    browsers: Vec<InstalledBrowser>,
    test_text: String,
    stt_rx: Option<watch::Receiver<DownloadState>>,
    status_message: Option<String>,
    app_icon: Option<Arc<egui::IconData>>,
    // Modal keyboard editor state
    editing_keyboard: Option<EditingShortcut>,
    capturing_live_key: bool,
    draft_ctrl: bool,
    draft_shift: bool,
    draft_alt: bool,
    draft_win: bool,
    draft_key_vk: u16,
}

const COMMON_KEYS: [(&str, u16); 48] = [
    ("Space", 0x20),
    ("Enter", 0x0D),
    ("Tab", 0x09),
    ("Esc", 0x1B),
    ("Home", 0x24),
    ("End", 0x23),
    ("Insert", 0x2D),
    ("Delete", 0x2E),
    ("A", 0x41), ("B", 0x42), ("C", 0x43), ("D", 0x44), ("E", 0x45),
    ("F", 0x46), ("G", 0x47), ("H", 0x48), ("I", 0x49), ("J", 0x4A),
    ("K", 0x4B), ("L", 0x4C), ("M", 0x4D), ("N", 0x4E), ("O", 0x4F),
    ("P", 0x50), ("Q", 0x51), ("R", 0x52), ("S", 0x53), ("T", 0x54),
    ("U", 0x55), ("V", 0x56), ("W", 0x57), ("X", 0x58), ("Y", 0x59),
    ("Z", 0x5A),
    ("0", 0x30), ("1", 0x31), ("2", 0x32), ("3", 0x33), ("4", 0x34),
    ("5", 0x35), ("6", 0x36), ("7", 0x37), ("8", 0x38), ("9", 0x39),
    ("F8", 0x77), ("F9", 0x78), ("F10", 0x79), ("F12", 0x7B),
];

fn vk_display_name(vk: u16) -> String {
    if let Some(&(name, _)) = COMMON_KEYS.iter().find(|(_, code)| *code == vk) {
        return name.to_string();
    }
    if (0x70..=0x7B).contains(&vk) {
        return format!("F{}", vk - 0x6F);
    }
    format!("Key(0x{:02X})", vk)
}

fn egui_key_to_vk(key: egui::Key) -> Option<u16> {
    use egui::Key;
    Some(match key {
        Key::Space => 0x20,
        Key::Enter => 0x0D,
        Key::Tab => 0x09,
        Key::Escape => 0x1B,
        Key::Backspace => 0x08,
        Key::Insert => 0x2D,
        Key::Delete => 0x2E,
        Key::Home => 0x24,
        Key::End => 0x23,
        Key::PageUp => 0x21,
        Key::PageDown => 0x22,
        Key::ArrowLeft => 0x25,
        Key::ArrowUp => 0x26,
        Key::ArrowRight => 0x27,
        Key::ArrowDown => 0x28,
        Key::A => 0x41, Key::B => 0x42, Key::C => 0x43, Key::D => 0x44, Key::E => 0x45,
        Key::F => 0x46, Key::G => 0x47, Key::H => 0x48, Key::I => 0x49, Key::J => 0x4A,
        Key::K => 0x4B, Key::L => 0x4C, Key::M => 0x4D, Key::N => 0x4E, Key::O => 0x4F,
        Key::P => 0x50, Key::Q => 0x51, Key::R => 0x52, Key::S => 0x53, Key::T => 0x54,
        Key::U => 0x55, Key::V => 0x56, Key::W => 0x57, Key::X => 0x58, Key::Y => 0x59,
        Key::Z => 0x5A,
        Key::Num0 => 0x30, Key::Num1 => 0x31, Key::Num2 => 0x32, Key::Num3 => 0x33, Key::Num4 => 0x34,
        Key::Num5 => 0x35, Key::Num6 => 0x36, Key::Num7 => 0x37, Key::Num8 => 0x38, Key::Num9 => 0x39,
        Key::F1 => 0x70, Key::F2 => 0x71, Key::F3 => 0x72, Key::F4 => 0x73,
        Key::F5 => 0x74, Key::F6 => 0x75, Key::F7 => 0x76, Key::F8 => 0x77,
        Key::F9 => 0x78, Key::F10 => 0x79, Key::F11 => 0x7A, Key::F12 => 0x7B,
        _ => return None,
    })
}

fn mouse_btn_label(btn: Option<u32>) -> &'static str {
    match btn {
        None => "None",
        Some(4) => "Mouse 4 (Back)",
        Some(5) => "Mouse 5 (Forward)",
        Some(3) => "Mouse Middle",
        Some(_) => "Other Button",
    }
}

impl SettingsDashboard {
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        cc: &eframe::CreationContext<'_>,
        config: AppConfig,
        shared_shortcuts: Arc<RwLock<ShortcutConfig>>,
        shared_ctx: Arc<RwLock<Option<egui::Context>>>,
        show_dashboard_req: Arc<AtomicBool>,
        quit_requested: Arc<AtomicBool>,
        reader_request: Arc<Mutex<Option<String>>>,
        tts: Arc<TtsEngine>,
        app_icon: Option<Arc<egui::IconData>>,
    ) -> Self {
        configure_windows_fonts(&cc.egui_ctx);
        tts.set_egui_ctx(cc.egui_ctx.clone());
        if let Ok(mut guard) = shared_ctx.write() {
            *guard = Some(cc.egui_ctx.clone());
        }
        let browsers = BrowserDetector::detect_all();
        Self {
            config,
            shared_shortcuts,
            show_dashboard_req,
            quit_requested,
            reader_request,
            reader_window: None,
            active_tab: DashboardTab::Shortcuts,
            tts,
            browsers,
            test_text: "Hello! This is offline neural speech powered by Paradee 8M.".to_string(),
            stt_rx: None,
            status_message: None,
            app_icon,
            editing_keyboard: None,
            capturing_live_key: false,
            draft_ctrl: true,
            draft_shift: false,
            draft_alt: false,
            draft_win: false,
            draft_key_vk: 0x20,
        }
    }

    fn init_keyboard_draft(&mut self, chord: &InputChord) {
        self.draft_ctrl = chord.modifiers.contains(&ModifierKey::Control);
        self.draft_shift = chord.modifiers.contains(&ModifierKey::Shift);
        self.draft_alt = chord.modifiers.contains(&ModifierKey::Alt);
        self.draft_win = chord.modifiers.contains(&ModifierKey::Win);
        self.draft_key_vk = match chord.trigger {
            TriggerSource::Key(vk) => vk,
            _ => 0x20,
        };
        self.capturing_live_key = true;
    }

    fn build_keyboard_draft(&self) -> InputChord {
        let mut mods = Vec::new();
        if self.draft_ctrl {
            mods.push(ModifierKey::Control);
        }
        if self.draft_shift {
            mods.push(ModifierKey::Shift);
        }
        if self.draft_alt {
            mods.push(ModifierKey::Alt);
        }
        if self.draft_win {
            mods.push(ModifierKey::Win);
        }
        InputChord::key_press(mods, self.draft_key_vk)
    }

    fn binding_mut(&mut self, target: EditingShortcut) -> &mut ActionBinding {
        match target {
            EditingShortcut::SpeakSelection => &mut self.config.shortcuts.speak_selection,
            EditingShortcut::StopSpeaking => &mut self.config.shortcuts.stop_speaking,
            EditingShortcut::PushToTalk => &mut self.config.shortcuts.push_to_talk,
            EditingShortcut::OpenHome => &mut self.config.shortcuts.open_home,
            EditingShortcut::ToggleBionic => &mut self.config.shortcuts.toggle_bionic,
            EditingShortcut::ToggleReader => &mut self.config.shortcuts.toggle_reader,
        }
    }

    fn apply_and_save_shortcuts(&mut self, msg: &str) {
        if let Ok(mut guard) = self.shared_shortcuts.write() {
            *guard = self.config.shortcuts.clone();
        }
        InputHookManager::update_bound_mouse_mask(self.config.shortcuts.bound_mouse_mask());
        let _ = self.config.save();
        self.status_message = Some(msg.to_string());
    }

    fn count_duplicate_bindings(&self, target: EditingShortcut) -> Option<String> {
        let rows = [
            (EditingShortcut::SpeakSelection, &self.config.shortcuts.speak_selection),
            (EditingShortcut::StopSpeaking, &self.config.shortcuts.stop_speaking),
            (EditingShortcut::PushToTalk, &self.config.shortcuts.push_to_talk),
            (EditingShortcut::OpenHome, &self.config.shortcuts.open_home),
            (EditingShortcut::ToggleBionic, &self.config.shortcuts.toggle_bionic),
            (EditingShortcut::ToggleReader, &self.config.shortcuts.toggle_reader),
        ];
        let current = match target {
            EditingShortcut::SpeakSelection => &self.config.shortcuts.speak_selection,
            EditingShortcut::StopSpeaking => &self.config.shortcuts.stop_speaking,
            EditingShortcut::PushToTalk => &self.config.shortcuts.push_to_talk,
            EditingShortcut::OpenHome => &self.config.shortcuts.open_home,
            EditingShortcut::ToggleBionic => &self.config.shortcuts.toggle_bionic,
            EditingShortcut::ToggleReader => &self.config.shortcuts.toggle_reader,
        };

        for (other_id, other) in rows {
            if other_id == target {
                continue;
            }
            if current.keyboard.matches(&other.keyboard) {
                return Some(format!("Keyboard duplicates '{}'.", other_id.title()));
            }
            if let (Some(m1), Some(m2)) = (current.mouse_button(), other.mouse_button()) {
                if m1 == m2 {
                    return Some(format!("Mouse button duplicates '{}'.", other_id.title()));
                }
            }
        }
        None
    }

    fn render_keyboard_modal(&mut self, ctx: &egui::Context) {
        let Some(target) = self.editing_keyboard else {
            return;
        };

        let mut close_modal = false;
        let mut save_binding = false;

        egui::Window::new(format!("Change Keyboard Shortcut — {}", target.title()))
            .collapsible(false)
            .resizable(false)
            .anchor(egui::Align2::CENTER_CENTER, [0.0, 0.0])
            .fixed_size([430.0, 290.0])
            .show(ctx, |ui| {
                let note = if target.allows_single_key() {
                    "Supports any 1-key shortcut (e.g. F9) or 2-4 key combo (e.g. Ctrl+Shift+S)."
                } else {
                    "Supports any 2-4 key combo (e.g. Ctrl+Space, Ctrl+Shift+Alt+P) or F1-F12."
                };
                ui.add(egui::Label::new(note).wrap(true));
                ui.add_space(8.0);

                if self.capturing_live_key {
                    ctx.input(|i| {
                        for ev in &i.events {
                            if let egui::Event::Key {
                                key,
                                pressed: true,
                                modifiers,
                                ..
                            } = ev
                            {
                                if *key == egui::Key::Escape
                                    && !modifiers.ctrl
                                    && !modifiers.shift
                                    && !modifiers.alt
                                {
                                    self.capturing_live_key = false;
                                    break;
                                }
                                if let Some(vk) = egui_key_to_vk(*key) {
                                    self.draft_ctrl = modifiers.ctrl || modifiers.command;
                                    self.draft_shift = modifiers.shift;
                                    self.draft_alt = modifiers.alt;
                                    self.draft_win = false;
                                    self.draft_key_vk = vk;
                                    self.capturing_live_key = false;
                                    break;
                                }
                            }
                        }
                    });
                }

                ui.group(|ui| {
                    ui.set_width(400.0);
                    ui.horizontal(|ui| {
                        if self.capturing_live_key {
                            ui.colored_label(
                                egui::Color32::from_rgb(80, 180, 255),
                                "Listening... Press any key combination now!",
                            );
                            if ui.button("Stop").clicked() {
                                self.capturing_live_key = false;
                            }
                        } else {
                            ui.label("Live Key Capture:");
                            if ui.button("Record Key Combo").clicked() {
                                self.capturing_live_key = true;
                            }
                        }
                    });
                });

                ui.add_space(8.0);

                ui.horizontal(|ui| {
                    ui.label("Modifiers:");
                    ui.checkbox(&mut self.draft_ctrl, "Ctrl");
                    ui.checkbox(&mut self.draft_shift, "Shift");
                    ui.checkbox(&mut self.draft_alt, "Alt");
                    ui.checkbox(&mut self.draft_win, "Win");
                });

                ui.horizontal(|ui| {
                    ui.label("Trigger Key:");
                    egui::ComboBox::from_id_source("modal_key_combo")
                        .selected_text(vk_display_name(self.draft_key_vk))
                        .show_ui(ui, |ui| {
                            for &(name, vk) in &COMMON_KEYS {
                                ui.selectable_value(&mut self.draft_key_vk, vk, name);
                            }
                        });
                });

                let draft_chord = self.build_keyboard_draft();
                ui.add_space(8.0);
                ui.horizontal(|ui| {
                    ui.label("Selected Chord:");
                    ui.label(egui::RichText::new(draft_chord.to_string()).strong());
                });

                let validation =
                    ShortcutCatalog::validate_for(&draft_chord, target.allows_single_key());
                let can_save = match &validation {
                    CollisionSeverity::Allowed => {
                        ui.colored_label(egui::Color32::from_rgb(46, 204, 113), "✓ Safe to bind");
                        true
                    }
                    CollisionSeverity::Warning(w) => {
                        ui.add(
                            egui::Label::new(
                                egui::RichText::new(format!("Warning: {w}"))
                                    .color(egui::Color32::from_rgb(241, 196, 15)),
                            )
                            .wrap(true),
                        );
                        true
                    }
                    CollisionSeverity::HardBlocked(b) => {
                        ui.add(
                            egui::Label::new(
                                egui::RichText::new(format!("Blocked: {b}"))
                                    .color(egui::Color32::from_rgb(231, 76, 60)),
                            )
                            .wrap(true),
                        );
                        false
                    }
                };

                ui.add_space(10.0);
                ui.horizontal(|ui| {
                    if ui
                        .add_enabled(can_save, egui::Button::new("Save & Bind"))
                        .clicked()
                    {
                        save_binding = true;
                        close_modal = true;
                    }
                    if ui.button("Cancel").clicked() {
                        close_modal = true;
                    }
                });
            });

        if save_binding {
            let new_chord = self.build_keyboard_draft();
            self.binding_mut(target).keyboard = new_chord;
            self.apply_and_save_shortcuts(&format!(
                "Updated keyboard shortcut for {} (active immediately).",
                target.title()
            ));
        }
        if close_modal {
            self.editing_keyboard = None;
            self.capturing_live_key = false;
        }
    }

    fn render_secondary_viewports(&mut self, ctx: &egui::Context) {
        // Native Reader View secondary viewport (Alt + R)
        if let Ok(mut guard) = self.reader_request.lock() {
            if let Some(text) = guard.take() {
                self.reader_window = Some(ReaderViewWindow::new(
                    text,
                    Arc::clone(&self.tts),
                    self.config.bionic.fixation_ratio,
                ));
            }
        }

        if let Some(ref mut rw) = self.reader_window {
            let reader_id = egui::ViewportId::from_hash_of("speakthat_reader");
            let mut reader_vp = egui::ViewportBuilder::default()
                .with_title("SpeakThat Native Reader View")
                .with_inner_size([820.0, 620.0])
                .with_min_inner_size([520.0, 420.0]);
            if let Some(ref icon) = self.app_icon {
                reader_vp = reader_vp.with_icon(Arc::clone(icon));
            }

            let mut should_close = false;
            ctx.show_viewport_immediate(reader_id, reader_vp, |reader_ctx, _class| {
                if reader_ctx.input(|i| i.viewport().close_requested() || i.key_pressed(egui::Key::Escape)) {
                    should_close = true;
                } else {
                    rw.render_ui(reader_ctx);
                }
            });

            if should_close {
                ctx.send_viewport_cmd_to(reader_id, egui::ViewportCommand::Close);
                self.reader_window = None;
            }
        }
    }
}

impl eframe::App for SettingsDashboard {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        // Explicit app termination via System Tray -> Exit SpeakThat
        if self.quit_requested.load(Ordering::SeqCst) {
            ctx.send_viewport_cmd(egui::ViewportCommand::Close);
            return;
        }

        // Restore & focus when requested by System Tray or Open Home Dashboard hotkey
        if self.show_dashboard_req.swap(false, Ordering::SeqCst) {
            ctx.send_viewport_cmd(egui::ViewportCommand::Visible(true));
            ctx.send_viewport_cmd(egui::ViewportCommand::Minimized(false));
            ctx.send_viewport_cmd(egui::ViewportCommand::Focus);
        }

        // Close-to-tray: hide window instead of terminating process
        if ctx.input(|i| i.viewport().close_requested()) && !self.quit_requested.load(Ordering::SeqCst)
        {
            ctx.send_viewport_cmd(egui::ViewportCommand::CancelClose);
            ctx.send_viewport_cmd(egui::ViewportCommand::Visible(false));
        }

        // Keep secondary viewports (Floating Stop Pill HUD & Reader View) updated even if Dashboard is hidden
        self.render_secondary_viewports(ctx);

        // Pinned Footer Panel (always anchored to window bottom on every tab)
        egui::TopBottomPanel::bottom("footer_panel")
            .frame(
                egui::Frame::side_top_panel(&ctx.style())
                    .inner_margin(egui::Margin::symmetric(16.0, 10.0)),
            )
            .show(ctx, |ui| {
                ui.horizontal(|ui| {
                    if ui.button("Save All Settings").clicked() {
                        self.tts.set_voice(&self.config.tts.voice_id);
                        self.tts.set_speed(self.config.tts.speed);
                        self.tts.set_volume(self.config.tts.volume);
                        self.apply_and_save_shortcuts("All settings saved successfully.");
                    }
                    if let Some(msg) = &self.status_message {
                        ui.colored_label(egui::Color32::from_rgb(100, 200, 255), msg);
                    }
                });
            });

        let panel_frame = egui::Frame::central_panel(&ctx.style())
            .inner_margin(egui::Margin::same(16.0));

        egui::CentralPanel::default().frame(panel_frame).show(ctx, |ui| {
            ui.heading("SpeakThat + ADHD Bionic Reader Settings");
            ui.label("Unified Windows Accessibility Suite (v0.2.1 · Pure Rust)");
            ui.add_space(4.0);
            ui.separator();

            let prev_tab = self.active_tab;
            ui.horizontal_wrapped(|ui| {
                ui.selectable_value(&mut self.active_tab, DashboardTab::Shortcuts, "Shortcuts");
                ui.selectable_value(&mut self.active_tab, DashboardTab::Voice, "Voice (Paradee)");
                ui.selectable_value(&mut self.active_tab, DashboardTab::Bionic, "Bionic Reader");
                ui.selectable_value(&mut self.active_tab, DashboardTab::Dictation, "Dictation (STT)");
                ui.selectable_value(&mut self.active_tab, DashboardTab::Browsers, "Browsers");
            });
            if self.active_tab != prev_tab {
                self.status_message = None;
            }
            ui.separator();
            ui.add_space(6.0);

            egui::ScrollArea::vertical().show(ui, |ui| match self.active_tab {
                DashboardTab::Shortcuts => {
                    ui.subheading("Global Shortcuts (Keyboard + Mouse)");
                    ui.label(
                        "Every action supports BOTH an active keyboard shortcut (2-4 keys, or 1 key for Open Home)\nand an optional multi-button mouse binding simultaneously.",
                    );
                    ui.add_space(10.0);

                    let mut open_kb_modal: Option<(EditingShortcut, InputChord)> = None;
                    let mut mouse_changed = false;

                    let col_w_action = 138.0;
                    let col_w_kb = 188.0;
                    let col_w_mouse = 228.0;
                    let col_w_status = 185.0;

                    egui::Grid::new("shortcuts_grid")
                        .num_columns(4)
                        .striped(true)
                        .spacing([10.0, 12.0])
                        .show(ui, |ui| {
                            ui.allocate_ui(egui::vec2(col_w_action, 20.0), |ui| {
                                ui.label(egui::RichText::new("Action").strong());
                            });
                            ui.allocate_ui(egui::vec2(col_w_kb, 20.0), |ui| {
                                ui.label(egui::RichText::new("Keyboard Shortcut").strong());
                            });
                            ui.allocate_ui(egui::vec2(col_w_mouse, 20.0), |ui| {
                                ui.label(egui::RichText::new("Mouse Button (Optional)").strong());
                            });
                            ui.allocate_ui(egui::vec2(col_w_status, 20.0), |ui| {
                                ui.label(egui::RichText::new("Status").strong());
                            });
                            ui.end_row();

                            let targets = [
                                EditingShortcut::SpeakSelection,
                                EditingShortcut::StopSpeaking,
                                EditingShortcut::PushToTalk,
                                EditingShortcut::OpenHome,
                                EditingShortcut::ToggleBionic,
                                EditingShortcut::ToggleReader,
                            ];

                            for (idx, target) in targets.into_iter().enumerate() {
                                let dup_warning = self.count_duplicate_bindings(target);
                                let binding_snapshot = self.binding_mut(target).clone();

                                ui.allocate_ui(egui::vec2(col_w_action, 28.0), |ui| {
                                    ui.add(
                                        egui::Label::new(egui::RichText::new(target.title()).strong())
                                            .wrap(true),
                                    );
                                });

                                ui.allocate_ui(egui::vec2(col_w_kb, 28.0), |ui| {
                                    ui.horizontal(|ui| {
                                        ui.label(binding_snapshot.keyboard.to_string());
                                        if ui.button("Change").clicked() {
                                            open_kb_modal =
                                                Some((target, binding_snapshot.keyboard.clone()));
                                        }
                                    });
                                });

                                ui.allocate_ui(egui::vec2(col_w_mouse, 28.0), |ui| {
                                    ui.horizontal(|ui| {
                                        let mut selected_btn = binding_snapshot.mouse_button();
                                        let mut hold_ms = binding_snapshot.mouse_hold_ms();

                                        egui::ComboBox::from_id_source(format!("mouse_combo_{idx}"))
                                            .width(128.0)
                                            .selected_text(mouse_btn_label(selected_btn))
                                            .show_ui(ui, |ui| {
                                                ui.selectable_value(&mut selected_btn, None, "None");
                                                ui.selectable_value(
                                                    &mut selected_btn,
                                                    Some(4),
                                                    "Mouse 4 (Back)",
                                                );
                                                ui.selectable_value(
                                                    &mut selected_btn,
                                                    Some(5),
                                                    "Mouse 5 (Forward)",
                                                );
                                                ui.selectable_value(
                                                    &mut selected_btn,
                                                    Some(3),
                                                    "Mouse Middle",
                                                );
                                            });

                                        if selected_btn != binding_snapshot.mouse_button() {
                                            self.binding_mut(target).mouse = selected_btn.map(|btn| {
                                                InputChord::mouse_hold(
                                                    btn,
                                                    Duration::from_millis(0),
                                                )
                                            });
                                            mouse_changed = true;
                                        } else if let Some(btn) = selected_btn {
                                            ui.label("Hold:");
                                            let resp = ui.add(
                                                egui::DragValue::new(&mut hold_ms)
                                                    .clamp_range(0..=500)
                                                    .speed(5)
                                                    .suffix(" ms"),
                                            );
                                            if resp.changed() {
                                                self.binding_mut(target).mouse = Some(
                                                    InputChord::mouse_hold(
                                                        btn,
                                                        Duration::from_millis(hold_ms),
                                                    ),
                                                );
                                                mouse_changed = true;
                                            }
                                        }
                                    });
                                });

                                ui.allocate_ui(egui::vec2(col_w_status, 28.0), |ui| {
                                    ui.set_width(col_w_status);
                                    let validation = ShortcutCatalog::validate_for(
                                        &binding_snapshot.keyboard,
                                        target.allows_single_key(),
                                    );
                                    match (validation, dup_warning) {
                                        (CollisionSeverity::HardBlocked(b), _) => {
                                            ui.add(
                                                egui::Label::new(
                                                    egui::RichText::new(format!("Blocked: {b}"))
                                                        .color(egui::Color32::from_rgb(231, 76, 60)),
                                                )
                                                .wrap(true),
                                            );
                                        }
                                        (CollisionSeverity::Warning(w), _) => {
                                            ui.add(
                                                egui::Label::new(
                                                    egui::RichText::new(format!("Warning: {w}"))
                                                        .color(egui::Color32::from_rgb(241, 196, 15)),
                                                )
                                                .wrap(true),
                                            );
                                        }
                                        (CollisionSeverity::Allowed, Some(dup)) => {
                                            ui.add(
                                                egui::Label::new(
                                                    egui::RichText::new(format!("Warning: {dup}"))
                                                        .color(egui::Color32::from_rgb(241, 196, 15)),
                                                )
                                                .wrap(true),
                                            );
                                        }
                                        (CollisionSeverity::Allowed, None) => {
                                            ui.add(
                                                egui::Label::new(
                                                    egui::RichText::new("✓ Safe")
                                                        .color(egui::Color32::from_rgb(46, 204, 113)),
                                                )
                                                .wrap(true),
                                            );
                                        }
                                    }
                                });

                                ui.end_row();
                            }
                        });

                    if let Some((target, kb_chord)) = open_kb_modal {
                        self.init_keyboard_draft(&kb_chord);
                        self.editing_keyboard = Some(target);
                    }
                    if mouse_changed {
                        self.apply_and_save_shortcuts(
                            "Mouse binding updated and saved (active immediately).",
                        );
                    }
                }

                DashboardTab::Voice => {
                    ui.subheading("Paradee 8M Neural Text-to-Speech");
                    ui.label("Ultra-lightweight (8.5 MB) pure-Rust offline text-to-speech with natural prosody.");
                    ui.add_space(10.0);

                    ui.horizontal_wrapped(|ui| {
                        ui.label(egui::RichText::new("Voice:").strong());
                        let voices = [
                            ("bf_isabella", "Isabella (British Female)"),
                            ("af_heart", "Heart (American Female)"),
                            ("am_puck", "Puck (American Male)"),
                            ("bm_fable", "Fable (British Male)"),
                        ];
                        for (id, label) in voices {
                            if ui.selectable_label(self.config.tts.voice_id == id, label).clicked() {
                                self.config.tts.voice_id = id.to_string();
                                self.tts.set_voice(id);
                            }
                        }
                    });

                    ui.add_space(10.0);
                    egui::Grid::new("voice_sliders_grid")
                        .num_columns(2)
                        .spacing([16.0, 10.0])
                        .show(ui, |ui| {
                            ui.spacing_mut().slider_width = 260.0;

                            ui.label(egui::RichText::new("Speech Speed:").strong());
                            if ui
                                .add(egui::Slider::new(&mut self.config.tts.speed, 0.6..=2.5).suffix("x"))
                                .changed()
                            {
                                self.tts.set_speed(self.config.tts.speed);
                            }
                            ui.end_row();

                            ui.label(egui::RichText::new("Volume:").strong());
                            if ui
                                .add(egui::Slider::new(&mut self.config.tts.volume, 0.0..=1.0))
                                .changed()
                            {
                                self.tts.set_volume(self.config.tts.volume);
                            }
                            ui.end_row();
                        });

                    ui.add_space(14.0);
                    ui.label(egui::RichText::new("Test Playback:").strong());
                    ui.add_space(4.0);
                    ui.add(
                        egui::TextEdit::singleline(&mut self.test_text)
                            .desired_width(f32::INFINITY),
                    );
                    ui.add_space(6.0);
                    ui.horizontal(|ui| {
                        if ui.button("▶ Listen to Preview").clicked() {
                            self.tts.speak(&self.test_text);
                        }
                        if ui.button("⏹ Stop").clicked() {
                            self.tts.stop();
                        }
                    });
                }

                DashboardTab::Bionic => {
                    ui.subheading("ADHD Bionic Reading Settings");
                    ui.label(
                        "Highlights the first few letters of words to guide the eye and improve reading focus.",
                    );
                    ui.add_space(10.0);

                    ui.horizontal(|ui| {
                        ui.spacing_mut().slider_width = 240.0;
                        ui.label(egui::RichText::new("Fixation Ratio:").strong());
                        ui.add(egui::Slider::new(&mut self.config.bionic.fixation_ratio, 0.2..=0.8));
                    });

                    ui.add_space(12.0);
                    ui.label(egui::RichText::new("Native Windows Preview (In-Place Injection Format):").strong());
                    ui.add_space(4.0);
                    let engine = crate::bionic::BionicEngine::new(self.config.bionic.fixation_ratio);
                    let preview = engine.to_unicode_bionic(
                        "Reading is the cognitive process of looking at written symbols and translating them into meaning.",
                    );
                    ui.add(
                        egui::Label::new(
                            egui::RichText::new(preview).color(egui::Color32::from_rgb(100, 180, 255)),
                        )
                        .wrap(true),
                    );
                }

                DashboardTab::Dictation => {
                    ui.subheading("Offline Speech-to-Text (NVIDIA Parakeet-TDT 0.6B v3)");
                    ui.label("Completely offline, on-demand speech-to-text with zero cloud telemetry.");
                    ui.add_space(10.0);

                    let mut is_downloading = false;
                    let mut current_progress = 0.0;
                    let mut dl_status = String::new();

                    if let Some(rx) = &self.stt_rx {
                        let state = rx.borrow().clone();
                        match state {
                            DownloadState::NotInstalled => {}
                            DownloadState::Downloading {
                                progress,
                                bytes_downloaded,
                                total_bytes,
                                speed_bps,
                            } => {
                                is_downloading = true;
                                current_progress = progress;
                                dl_status = format!(
                                    "{:.1} MB / {:.1} MB ({:.2} MB/s)",
                                    bytes_downloaded as f32 / 1_000_000.0,
                                    total_bytes as f32 / 1_000_000.0,
                                    speed_bps as f32 / 1_000_000.0
                                );
                            }
                            DownloadState::VerifyingHash => {
                                is_downloading = true;
                                current_progress = 1.0;
                                dl_status = "Verifying SHA-256 hash integrity...".to_string();
                            }
                            DownloadState::Installed => {
                                self.config.stt.model_installed = true;
                            }
                            DownloadState::Error(err) => {
                                dl_status = format!("Download failed: {err}");
                            }
                            DownloadState::Paused { .. } => {}
                        }
                    }

                    let installed =
                        ModelDownloader::is_model_installed() || self.config.stt.model_installed;
                    if installed {
                        ui.colored_label(
                            egui::Color32::from_rgb(46, 204, 113),
                            "✓ Parakeet-TDT 0.6B Model is Installed & Ready",
                        );
                        ui.label(
                            "Click Mouse 5 or press your Push-to-Talk keyboard shortcut to start/stop dictation anywhere on Windows.",
                        );
                    } else if is_downloading {
                        ui.label("Downloading NVIDIA Parakeet-TDT 0.6B model:");
                        ui.add(egui::ProgressBar::new(current_progress).show_percentage());
                        ui.label(&dl_status);
                        ctx.request_repaint();
                    } else {
                        ui.colored_label(
                            egui::Color32::from_rgb(230, 126, 34),
                            "Model is not yet downloaded (~600 MB INT8 ONNX)",
                        );
                        ui.label(
                            "Speech-to-text runs entirely offline on your GPU/CPU once downloaded.",
                        );
                        ui.add_space(6.0);
                        if ui.button("Download Model Now").clicked() {
                            let (downloader, rx) = ModelDownloader::new();
                            self.stt_rx = Some(rx);
                            let dl = Arc::new(downloader);
                            tokio::spawn(async move {
                                let _ = dl.start_download().await;
                            });
                        }
                    }
                }

                DashboardTab::Browsers => {
                    ui.subheading("Multi-Browser Extension Manager");
                    ui.label("Detected browsers and unpacked extension loader folders:");
                    ui.add_space(10.0);

                    let card_width = (ui.available_width() - 16.0).max(400.0);
                    for b in &self.browsers {
                        let ext_str = b.extension_folder.display().to_string();
                        egui::Frame::group(ui.style())
                            .inner_margin(egui::Margin::same(12.0))
                            .show(ui, |ui| {
                                ui.set_min_width(card_width);
                                ui.label(egui::RichText::new(b.name).size(14.5).strong());
                                ui.add_space(2.0);
                                ui.add(
                                    egui::Label::new(format!("Extension Folder: {ext_str}"))
                                        .wrap(true),
                                );
                                ui.label(format!("Extensions Page: {}", b.install_url));
                                ui.add_space(6.0);
                                ui.horizontal(|ui| {
                                    if ui.button("Copy Path").clicked() {
                                        ui.output_mut(|o| o.copied_text = ext_str.clone());
                                        self.status_message = Some(format!(
                                            "Copied {} extension path to clipboard.",
                                            b.name
                                        ));
                                    }
                                    if ui.button("Open Extensions Page").clicked() {
                                        ui.output_mut(|o| o.copied_text = ext_str.clone());
                                        let exe = b.executable_path.clone();
                                        let url = b.install_url;
                                        std::thread::spawn(move || {
                                            let _ = std::process::Command::new(&exe)
                                                .arg(url)
                                                .spawn();
                                        });
                                        self.status_message = Some(format!(
                                            "Opening {} (extension path copied to clipboard).",
                                            b.name
                                        ));
                                    }
                                });
                            });
                        ui.add_space(6.0);
                    }
                }
            });
        });

        self.render_keyboard_modal(ctx);
    }
}

trait SubheadingExt {
    fn subheading(&mut self, text: &str);
}

impl SubheadingExt for egui::Ui {
    fn subheading(&mut self, text: &str) {
        self.label(egui::RichText::new(text).size(16.0).strong());
    }
}
