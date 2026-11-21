use eframe::egui;
use std::sync::Arc;
use tokio::sync::watch;
use crate::audio::TtsEngine;
use crate::config::AppConfig;
use crate::downloader::{DownloadState, ModelDownloader};
use crate::input::{InputChord, ModifierKey, ShortcutCatalog, TriggerMode, TriggerSource};
use crate::ui::browser_detect::{BrowserDetector, InstalledBrowser};

#[derive(PartialEq, Eq)]
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
    PushToTalk,
    OpenHome,
    ToggleBionic,
    ToggleReader,
}

pub struct SettingsDashboard {
    config: AppConfig,
    active_tab: DashboardTab,
    tts: Arc<TtsEngine>,
    browsers: Vec<InstalledBrowser>,
    test_text: String,
    stt_rx: Option<watch::Receiver<DownloadState>>,
    status_message: Option<String>,
    editing_shortcut: Option<EditingShortcut>,
    // Editor draft state
    draft_is_mouse: bool,
    draft_ctrl: bool,
    draft_shift: bool,
    draft_alt: bool,
    draft_win: bool,
    draft_key_idx: usize,
    draft_mouse_btn: u32,
    draft_mouse_duration_ms: u64,
}

const COMMON_KEYS: [(&str, u16); 30] = [
    ("Space", 0x20),
    ("Return / Enter", 0x0D),
    ("Tab", 0x09),
    ("Escape", 0x1B),
    ("A", 0x41), ("B", 0x42), ("C", 0x43), ("D", 0x44), ("E", 0x45),
    ("F", 0x46), ("G", 0x47), ("H", 0x48), ("I", 0x49), ("J", 0x4A),
    ("K", 0x4B), ("L", 0x4C), ("M", 0x4D), ("N", 0x4E), ("O", 0x4F),
    ("P", 0x50), ("Q", 0x51), ("R", 0x52), ("S", 0x53), ("T", 0x54),
    ("U", 0x55), ("V", 0x56), ("W", 0x57), ("X", 0x58), ("Y", 0x59),
    ("Z", 0x5A),
];

impl SettingsDashboard {
    pub fn new(config: AppConfig, tts: Arc<TtsEngine>) -> Self {
        let browsers = BrowserDetector::detect_all();
        Self {
            config,
            active_tab: DashboardTab::Shortcuts,
            tts,
            browsers,
            test_text: "Hello! This is offline neural speech powered by Paradee 8M.".to_string(),
            stt_rx: None,
            status_message: None,
            editing_shortcut: None,
            draft_is_mouse: false,
            draft_ctrl: true,
            draft_shift: false,
            draft_alt: false,
            draft_win: false,
            draft_key_idx: 0,
            draft_mouse_btn: 1, // XButton1 (Back)
            draft_mouse_duration_ms: 200,
        }
    }

    fn init_draft_from_chord(&mut self, chord: &InputChord) {
        self.draft_ctrl = chord.modifiers.contains(&ModifierKey::Control);
        self.draft_shift = chord.modifiers.contains(&ModifierKey::Shift);
        self.draft_alt = chord.modifiers.contains(&ModifierKey::Alt);
        self.draft_win = chord.modifiers.contains(&ModifierKey::Win);

        match chord.trigger {
            TriggerSource::Key(vk) => {
                self.draft_is_mouse = false;
                self.draft_key_idx = COMMON_KEYS
                    .iter()
                    .position(|(_, k)| *k == vk)
                    .unwrap_or(0);
            }
            TriggerSource::MouseButton(btn) => {
                self.draft_is_mouse = true;
                self.draft_mouse_btn = btn;
            }
        }

        if let TriggerMode::Hold(d) = chord.trigger_mode {
            self.draft_mouse_duration_ms = d.as_millis() as u64;
        } else {
            self.draft_mouse_duration_ms = 200;
        }
    }

    fn build_draft_chord(&self) -> InputChord {
        if self.draft_is_mouse {
            InputChord::mouse_hold(
                self.draft_mouse_btn,
                std::time::Duration::from_millis(self.draft_mouse_duration_ms),
            )
        } else {
            let mut mods = Vec::new();
            if self.draft_ctrl { mods.push(ModifierKey::Control); }
            if self.draft_shift { mods.push(ModifierKey::Shift); }
            if self.draft_alt { mods.push(ModifierKey::Alt); }
            if self.draft_win { mods.push(ModifierKey::Win); }

            let vk = COMMON_KEYS[self.draft_key_idx].1;
            InputChord::key_press(mods, vk)
        }
    }
}

impl eframe::App for SettingsDashboard {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        egui::CentralPanel::default().show(ctx, |ui| {
            ui.heading("SpeakThat + ADHD Bionic Reader Settings");
            ui.label("Unified Windows Accessibility Suite (v0.2.0)");
            ui.separator();

            // Tab Bar
            ui.horizontal(|ui| {
                ui.selectable_value(&mut self.active_tab, DashboardTab::Shortcuts, "⌨ Shortcuts");
                ui.selectable_value(&mut self.active_tab, DashboardTab::Voice, "🔊 Voice (Paradee)");
                ui.selectable_value(&mut self.active_tab, DashboardTab::Bionic, "📖 Bionic Reader");
                ui.selectable_value(&mut self.active_tab, DashboardTab::Dictation, "🎙 Dictation (STT)");
                ui.selectable_value(&mut self.active_tab, DashboardTab::Browsers, "🌐 Browsers");
            });
            ui.separator();

            match self.active_tab {
                DashboardTab::Shortcuts => {
                    ui.subheading("Global Shortcuts Configuration");
                    ui.label("Customize 2 to 4 key composite chords, dedicated keys, or mouse side buttons.");
                    ui.add_space(8.0);

                    // If currently editing a shortcut, show interactive recorder
                    if let Some(target) = self.editing_shortcut {
                        let action_title = match target {
                            EditingShortcut::SpeakSelection => "Speak Selection",
                            EditingShortcut::PushToTalk => "Push-to-Talk (STT)",
                            EditingShortcut::OpenHome => "Open Home Dashboard",
                            EditingShortcut::ToggleBionic => "Toggle Bionic Reading",
                            EditingShortcut::ToggleReader => "Toggle Reader View",
                        };

                        ui.group(|ui| {
                            ui.label(egui::RichText::new(format!("Editing Shortcut: {action_title}")).strong());
                            ui.separator();

                            ui.horizontal(|ui| {
                                ui.radio_value(&mut self.draft_is_mouse, false, "Keyboard Shortcut");
                                ui.radio_value(&mut self.draft_is_mouse, true, "Mouse Button");
                            });

                            if !self.draft_is_mouse {
                                ui.horizontal(|ui| {
                                    ui.label("Modifiers:");
                                    ui.checkbox(&mut self.draft_ctrl, "Ctrl");
                                    ui.checkbox(&mut self.draft_shift, "Shift");
                                    ui.checkbox(&mut self.draft_alt, "Alt");
                                    ui.checkbox(&mut self.draft_win, "Win");
                                });

                                ui.horizontal(|ui| {
                                    ui.label("Key:");
                                    egui::ComboBox::from_id_source("key_combo")
                                        .selected_text(COMMON_KEYS[self.draft_key_idx].0)
                                        .show_ui(ui, |ui| {
                                            for (idx, &(name, _)) in COMMON_KEYS.iter().enumerate() {
                                                ui.selectable_value(&mut self.draft_key_idx, idx, name);
                                            }
                                        });
                                });
                            } else {
                                ui.horizontal(|ui| {
                                    ui.label("Mouse Button:");
                                    ui.radio_value(&mut self.draft_mouse_btn, 1, "MouseSide1 (Back)");
                                    ui.radio_value(&mut self.draft_mouse_btn, 2, "MouseSide2 (Forward)");
                                    ui.radio_value(&mut self.draft_mouse_btn, 3, "Middle Button");
                                });

                                ui.horizontal(|ui| {
                                    ui.label("Hold Threshold:");
                                    ui.add(egui::Slider::new(&mut self.draft_mouse_duration_ms, 100..=500).suffix(" ms"));
                                });
                            }

                            let draft_chord = self.build_draft_chord();
                            ui.add_space(6.0);
                            ui.label(format!("Proposed: {}", draft_chord));

                            // Collision check
                            let validation = ShortcutCatalog::validate(&draft_chord);
                            let can_save = match validation {
                                crate::input::CollisionSeverity::Allowed => {
                                    ui.colored_label(egui::Color32::from_rgb(46, 204, 113), "✓ Shortcut is valid and safe to use");
                                    true
                                }
                                crate::input::CollisionSeverity::Warning(w) => {
                                    ui.colored_label(egui::Color32::from_rgb(241, 196, 15), format!("⚠ Conflict: {w}"));
                                    true
                                }
                                crate::input::CollisionSeverity::HardBlocked(b) => {
                                    ui.colored_label(egui::Color32::from_rgb(231, 76, 60), format!("⛔ Reserved: {b}"));
                                    false
                                }
                            };

                            ui.horizontal(|ui| {
                                if ui.add_enabled(can_save, egui::Button::new("Save & Bind")).clicked() {
                                    match target {
                                        EditingShortcut::SpeakSelection => self.config.shortcuts.speak_selection = draft_chord,
                                        EditingShortcut::PushToTalk => self.config.shortcuts.push_to_talk = draft_chord,
                                        EditingShortcut::OpenHome => self.config.shortcuts.open_home = draft_chord,
                                        EditingShortcut::ToggleBionic => self.config.shortcuts.toggle_bionic = draft_chord,
                                        EditingShortcut::ToggleReader => self.config.shortcuts.toggle_reader = draft_chord,
                                    }
                                    self.config.save();
                                    self.editing_shortcut = None;
                                    self.status_message = Some("Shortcut updated and saved.".to_string());
                                }
                                if ui.button("Cancel").clicked() {
                                    self.editing_shortcut = None;
                                }
                            });
                        });
                        ui.add_space(10.0);
                    }

                    let mut to_edit = None;
                    // Shortcuts Table
                    egui::Grid::new("shortcuts_grid").striped(true).min_col_width(160.0).show(ui, |ui| {
                        ui.label(egui::RichText::new("Action").strong());
                        ui.label(egui::RichText::new("Current Shortcut").strong());
                        ui.label(egui::RichText::new("Status").strong());
                        ui.label(egui::RichText::new("Action").strong());
                        ui.end_row();

                        let rows = [
                            ("Speak Selection", EditingShortcut::SpeakSelection, &self.config.shortcuts.speak_selection),
                            ("Push-to-Talk (STT)", EditingShortcut::PushToTalk, &self.config.shortcuts.push_to_talk),
                            ("Open Home Dashboard", EditingShortcut::OpenHome, &self.config.shortcuts.open_home),
                            ("Toggle Bionic Reading", EditingShortcut::ToggleBionic, &self.config.shortcuts.toggle_bionic),
                            ("Toggle Reader View", EditingShortcut::ToggleReader, &self.config.shortcuts.toggle_reader),
                        ];

                        for (name, action, chord) in rows {
                            ui.label(name);
                            ui.label(chord.to_string());
                            match ShortcutCatalog::validate(chord) {
                                crate::input::CollisionSeverity::Allowed => {
                                    ui.colored_label(egui::Color32::from_rgb(46, 204, 113), "✓ Safe");
                                }
                                crate::input::CollisionSeverity::Warning(w) => {
                                    ui.colored_label(egui::Color32::from_rgb(241, 196, 15), format!("⚠ Conflict: {w}"));
                                }
                                crate::input::CollisionSeverity::HardBlocked(b) => {
                                    ui.colored_label(egui::Color32::from_rgb(231, 76, 60), format!("⛔ Blocked: {b}"));
                                }
                            }
                            if ui.button("Change").clicked() {
                                to_edit = Some((action, chord.clone()));
                            }
                            ui.end_row();
                        }
                    });

                    if let Some((action, chord)) = to_edit {
                        self.init_draft_from_chord(&chord);
                        self.editing_shortcut = Some(action);
                    }
                }

                DashboardTab::Voice => {
                    ui.subheading("Paradee 8M Neural Text-to-Speech");
                    ui.label("Ultra-lightweight (8.5 MB) offline text-to-speech with natural prosody.");
                    ui.add_space(8.0);

                    ui.horizontal(|ui| {
                        ui.label("Voice:");
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

                    ui.add_space(8.0);
                    ui.horizontal(|ui| {
                        ui.label("Speech Speed:");
                        if ui.add(egui::Slider::new(&mut self.config.tts.speed, 0.6..=2.5).suffix("x")).changed() {
                            self.tts.set_speed(self.config.tts.speed);
                        }
                    });

                    ui.horizontal(|ui| {
                        ui.label("Volume:");
                        if ui.add(egui::Slider::new(&mut self.config.tts.volume, 0.0..=1.0).suffix("")).changed() {
                            self.tts.set_volume(self.config.tts.volume);
                        }
                    });

                    ui.add_space(12.0);
                    ui.label("Test Playback:");
                    ui.text_edit_singleline(&mut self.test_text);
                    if ui.button("▶ Listen to Preview").clicked() {
                        self.tts.speak(&self.test_text);
                    }
                }

                DashboardTab::Bionic => {
                    ui.subheading("ADHD Bionic Reading Settings");
                    ui.label("Highlights the first few letters of words to guide the eye and improve reading focus.");
                    ui.add_space(8.0);

                    ui.horizontal(|ui| {
                        ui.label("Fixation Ratio:");
                        ui.add(egui::Slider::new(&mut self.config.bionic.fixation_ratio, 0.2..=0.8).suffix(""));
                    });

                    ui.add_space(10.0);
                    ui.label("Native Windows Preview (In-Place Injection Format):");
                    let engine = crate::bionic::BionicEngine::new(self.config.bionic.fixation_ratio);
                    let preview = engine.to_unicode_bionic("Reading is the cognitive process of looking at written symbols and translating them into meaning.");
                    ui.colored_label(egui::Color32::from_rgb(100, 180, 255), preview);
                }

                DashboardTab::Dictation => {
                    ui.subheading("Offline Speech-to-Text (NVIDIA Parakeet-TDT 0.6B v3)");
                    ui.label("Completely offline, on-demand speech-to-text with zero cloud telemetry.");
                    ui.add_space(8.0);

                    // Check live download state if receiver active
                    let mut is_downloading = false;
                    let mut current_progress = 0.0;
                    let mut dl_status = String::new();

                    if let Some(rx) = &self.stt_rx {
                        let state = rx.borrow().clone();
                        match state {
                            DownloadState::NotInstalled => {}
                            DownloadState::Downloading { progress, bytes_downloaded, total_bytes, speed_bps } => {
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

                    let installed = ModelDownloader::is_model_installed() || self.config.stt.model_installed;
                    if installed {
                        ui.colored_label(egui::Color32::from_rgb(46, 204, 113), "✓ Parakeet-TDT 0.6B Model is Installed & Ready");
                        ui.label("Hold your Push-to-Talk shortcut or side mouse button to dictate anywhere on Windows.");
                    } else if is_downloading {
                        ui.label("Downloading NVIDIA Parakeet-TDT 0.6B model:");
                        ui.add(egui::ProgressBar::new(current_progress).show_percentage());
                        ui.label(&dl_status);
                        ctx.request_repaint(); // Request next frame update while downloading
                    } else {
                        ui.colored_label(egui::Color32::from_rgb(230, 126, 34), "Model is not yet downloaded (~600 MB INT8 ONNX)");
                        ui.label("Speech-to-text runs entirely offline on your GPU/CPU once downloaded.");
                        if ui.button("⬇ Download Model Now").clicked() {
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
                    ui.label("Detected browsers and 1-click extension load helpers:");
                    ui.add_space(8.0);

                    for b in &self.browsers {
                        ui.group(|ui| {
                            ui.label(egui::RichText::new(b.name).strong());
                            ui.label(format!("Extension Path: {:?}", b.extension_folder));
                            ui.label(format!("Helper URL: {}", b.install_url));
                        });
                    }
                }
            }

            ui.add_space(16.0);
            ui.separator();
            ui.horizontal(|ui| {
                if ui.button("💾 Save Settings").clicked() {
                    self.config.save();
                    self.status_message = Some("Settings saved successfully.".to_string());
                }
                if let Some(msg) = &self.status_message {
                    ui.label(msg);
                }
            });
        });
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
