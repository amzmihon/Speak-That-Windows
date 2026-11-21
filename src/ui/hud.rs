use eframe::egui;
use std::sync::Arc;
use crate::audio::{PlaybackState, TtsEngine};

pub struct FloatingPillHud {
    tts: Arc<TtsEngine>,
    current_sentence: String,
    state: PlaybackState,
}

impl FloatingPillHud {
    pub fn new(tts: Arc<TtsEngine>) -> Self {
        Self {
            tts,
            current_sentence: String::new(),
            state: PlaybackState::Stopped,
        }
    }

    pub fn set_sentence(&mut self, sentence: String) {
        self.current_sentence = sentence;
    }

    pub fn set_state(&mut self, state: PlaybackState) {
        self.state = state;
    }
}

impl eframe::App for FloatingPillHud {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        let frame = egui::Frame::none()
            .fill(egui::Color32::from_rgba_premultiplied(25, 25, 30, 240))
            .rounding(egui::Rounding::same(24.0))
            .stroke(egui::Stroke::new(1.0_f32, egui::Color32::from_rgb(60, 60, 75)))
            .inner_margin(egui::Margin::symmetric(14.0, 8.0));

        egui::CentralPanel::default().frame(frame).show(ctx, |ui| {
            ui.horizontal(|ui| {
                // Play/Pause button
                let is_playing = self.state == PlaybackState::Playing;
                let play_pause_icon = if is_playing { "⏸" } else { "▶" };
                if ui.button(play_pause_icon).clicked() {
                    self.tts.toggle_pause();
                }

                // Stop button
                if ui.button("⏹").clicked() {
                    self.tts.stop();
                }

                ui.separator();

                // Sentence or status preview
                let preview = if !self.current_sentence.is_empty() {
                    let chars: String = self.current_sentence.chars().take(35).collect();
                    format!("\"{chars}...\"")
                } else if is_playing {
                    "Speaking...".to_string()
                } else {
                    "Ready".to_string()
                };

                ui.colored_label(egui::Color32::from_rgb(220, 220, 230), preview);
            });
        });
    }
}
