use eframe::egui;
use std::sync::Arc;
use crate::audio::TtsEngine;
use crate::bionic::{BionicEngine, BionicToken};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ReaderTheme {
    Dark,
    Black,
    Sepia,
    Light,
}

impl ReaderTheme {
    pub fn bg_color(&self) -> egui::Color32 {
        match self {
            Self::Dark => egui::Color32::from_rgb(31, 31, 35),
            Self::Black => egui::Color32::from_rgb(0, 0, 0),
            Self::Sepia => egui::Color32::from_rgb(244, 236, 216),
            Self::Light => egui::Color32::from_rgb(251, 251, 251),
        }
    }

    pub fn text_color(&self) -> egui::Color32 {
        match self {
            Self::Dark => egui::Color32::from_rgb(230, 230, 230),
            Self::Black => egui::Color32::from_rgb(222, 222, 222),
            Self::Sepia => egui::Color32::from_rgb(60, 50, 38),
            Self::Light => egui::Color32::from_rgb(34, 34, 34),
        }
    }

    pub fn bold_color(&self) -> egui::Color32 {
        match self {
            Self::Dark => egui::Color32::from_rgb(255, 255, 255),
            Self::Black => egui::Color32::from_rgb(255, 255, 255),
            Self::Sepia => egui::Color32::from_rgb(20, 15, 10),
            Self::Light => egui::Color32::from_rgb(0, 0, 0),
        }
    }

    pub fn toolbar_bg(&self) -> egui::Color32 {
        match self {
            Self::Dark => egui::Color32::from_rgba_premultiplied(40, 40, 46, 240),
            Self::Black => egui::Color32::from_rgba_premultiplied(20, 20, 20, 245),
            Self::Sepia => egui::Color32::from_rgba_premultiplied(232, 222, 202, 240),
            Self::Light => egui::Color32::from_rgba_premultiplied(240, 240, 243, 240),
        }
    }
}

pub struct ReaderViewWindow {
    text: String,
    theme: ReaderTheme,
    font_size: f32,
    bionic_enabled: bool,
    fixation_ratio: f32,
    tts: Arc<TtsEngine>,
}

impl ReaderViewWindow {
    pub fn new(text: String, tts: Arc<TtsEngine>, fixation_ratio: f32) -> Self {
        Self {
            text,
            theme: ReaderTheme::Dark,
            font_size: 19.0,
            bionic_enabled: true,
            fixation_ratio,
            tts,
        }
    }
}

impl eframe::App for ReaderViewWindow {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        // Handle Escape key to exit
        if ctx.input(|i| i.key_pressed(egui::Key::Escape)) {
            ctx.send_viewport_cmd(egui::ViewportCommand::Close);
        }

        let bg = self.theme.bg_color();
        let text_color = self.theme.text_color();
        let bold_color = self.theme.bold_color();

        let panel_frame = egui::Frame::none().fill(bg).inner_margin(egui::Margin::symmetric(32.0, 24.0));

        egui::CentralPanel::default().frame(panel_frame).show(ctx, |ui| {
            // Floating Toolbar
            let toolbar_frame = egui::Frame::none()
                .fill(self.theme.toolbar_bg())
                .rounding(egui::Rounding::same(20.0))
                .inner_margin(egui::Margin::symmetric(14.0, 6.0));

            toolbar_frame.show(ui, |ui| {
                ui.horizontal(|ui| {
                    // Theme Switcher
                    ui.label(egui::RichText::new("Theme:").size(12.0).color(text_color));
                    let themes = [
                        (ReaderTheme::Dark, "Dark"),
                        (ReaderTheme::Black, "Black"),
                        (ReaderTheme::Sepia, "Sepia"),
                        (ReaderTheme::Light, "Light"),
                    ];
                    for (t, label) in themes {
                        if ui.selectable_label(self.theme == t, label).clicked() {
                            self.theme = t;
                        }
                    }

                    ui.separator();

                    // Font Size Controls
                    ui.label(egui::RichText::new("Size:").size(12.0).color(text_color));
                    if ui.button("A−").clicked() && self.font_size > 14.0 {
                        self.font_size -= 1.0;
                    }
                    ui.label(egui::RichText::new(format!("{:.0}px", self.font_size)).size(12.0).color(text_color));
                    if ui.button("A+").clicked() && self.font_size < 36.0 {
                        self.font_size += 1.0;
                    }

                    ui.separator();

                    // Bionic Toggle
                    let bionic_label = if self.bionic_enabled { "Bionic: ON" } else { "Bionic: OFF" };
                    if ui.selectable_label(self.bionic_enabled, bionic_label).clicked() {
                        self.bionic_enabled = !self.bionic_enabled;
                    }

                    ui.separator();

                    // Listen Aloud
                    if ui.button("▶ Listen").clicked() {
                        self.tts.speak(&self.text);
                    }

                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        if ui.button("✕ Close (Esc)").clicked() {
                            ctx.send_viewport_cmd(egui::ViewportCommand::Close);
                        }
                    });
                });
            });

            ui.add_space(20.0);
            ui.separator();
            ui.add_space(16.0);

            // Article Content Scroll Area
            egui::ScrollArea::vertical().auto_shrink([false; 2]).show(ui, |ui| {
                ui.style_mut().spacing.item_spacing.y = 12.0;

                if !self.bionic_enabled {
                    ui.label(
                        egui::RichText::new(&self.text)
                            .size(self.font_size)
                            .color(text_color)
                            .line_height(Some(self.font_size * 1.7)),
                    );
                } else {
                    // Render Bionic tokens
                    let engine = BionicEngine::new(self.fixation_ratio);
                    let paragraphs = self.text.split("\n\n");

                    for p in paragraphs {
                        if p.trim().is_empty() {
                            continue;
                        }
                        ui.horizontal_wrapped(|ui| {
                            ui.spacing_mut().item_spacing.x = 0.0;
                            let tokens = engine.tokenize(p);

                            for token in tokens {
                                match token {
                                    BionicToken::Word(w) => {
                                        ui.label(
                                            egui::RichText::new(&w.bold)
                                                .size(self.font_size)
                                                .strong()
                                                .color(bold_color),
                                        );
                                        ui.label(
                                            egui::RichText::new(&w.rest)
                                                .size(self.font_size)
                                                .color(text_color),
                                        );
                                    }
                                    BionicToken::NonWord(nw) => {
                                        ui.label(
                                            egui::RichText::new(&nw)
                                                .size(self.font_size)
                                                .color(text_color),
                                        );
                                    }
                                }
                            }
                        });
                        ui.add_space(8.0);
                    }
                }
            });
        });
    }
}
