use eframe::egui;
use std::sync::Arc;
use crate::audio::TtsEngine;
use crate::config::AppConfig;
use crate::downloader::ModelDownloader;
use crate::input::ShortcutCatalog;
use crate::ui::browser_detect::{BrowserDetector, InstalledBrowser};

#[derive(PartialEq, Eq)]
enum DashboardTab {
    Shortcuts,
    Voice,
    Bionic,
    Dictation,
    Browsers,
}

pub struct SettingsDashboard {
    config: AppConfig,
    active_tab: DashboardTab,
    tts: Arc<TtsEngine>,
    browsers: Vec<InstalledBrowser>,
    test_text: String,
    stt_download_in_progress: bool,
    stt_progress: f32,
    status_message: Option<String>,
}

impl SettingsDashboard {
    pub fn new(config: AppConfig, tts: Arc<TtsEngine>) -> Self {
        let browsers = BrowserDetector::detect_all();
        Self {
            config,
            active_tab: DashboardTab::Shortcuts,
            tts,
            browsers,
            test_text: "Hello! This is offline neural speech powered by Paradee 8M.".to_string(),
            stt_download_in_progress: false,
            stt_progress: 0.0,
            status_message: None,
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
                    ui.label("Customize 2 to 4 key composite chords or dedicated mouse side buttons.");

                    egui::Grid::new("shortcuts_grid").striped(true).min_col_width(180.0).show(ui, |ui| {
                        ui.label(egui::RichText::new("Action").strong());
                        ui.label(egui::RichText::new("Current Shortcut").strong());
                        ui.label(egui::RichText::new("Safety Status").strong());
                        ui.end_row();

                        let rows = [
                            ("Speak Selection", &self.config.shortcuts.speak_selection),
                            ("Push-to-Talk (STT)", &self.config.shortcuts.push_to_talk),
                            ("Open Home Dashboard", &self.config.shortcuts.open_home),
                            ("Toggle Bionic Reading", &self.config.shortcuts.toggle_bionic),
                            ("Toggle Reader View", &self.config.shortcuts.toggle_reader),
                        ];

                        for (name, chord) in rows {
                            ui.label(name);
                            ui.label(chord.to_string());
                            match ShortcutCatalog::validate(chord) {
                                crate::input::CollisionSeverity::Allowed => {
                                    ui.colored_label(egui::Color32::from_rgb(46, 204, 113), "✓ Protected & Safe");
                                }
                                crate::input::CollisionSeverity::Warning(w) => {
                                    ui.colored_label(egui::Color32::from_rgb(241, 196, 15), format!("⚠ Conflict: {w}"));
                                }
                                crate::input::CollisionSeverity::HardBlocked(b) => {
                                    ui.colored_label(egui::Color32::from_rgb(231, 76, 60), format!("⛔ Blocked: {b}"));
                                }
                            }
                            ui.end_row();
                        }
                    });
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
                            self.tts.set_volume(self.config.tts.volume as f32);
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

                    let installed = ModelDownloader::is_model_installed();
                    if installed {
                        ui.colored_label(egui::Color32::from_rgb(46, 204, 113), "✓ Parakeet-TDT 0.6B Model is Installed & Ready");
                    } else {
                        ui.colored_label(egui::Color32::from_rgb(230, 126, 34), "Model is not yet downloaded (~600 MB INT8 ONNX)");
                        if !self.stt_download_in_progress {
                            if ui.button("⬇ Download Model Now").clicked() {
                                self.stt_download_in_progress = true;
                                self.status_message = Some("Starting download...".to_string());
                            }
                        } else {
                            ui.add(egui::ProgressBar::new(self.stt_progress).show_percentage());
                            ui.label("Downloading from Hugging Face CDN with SHA-256 verification...");
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
