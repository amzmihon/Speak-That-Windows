use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;
use std::time::Duration;

use crate::input::chord::{InputChord, ModifierKey, TriggerMode, TriggerSource};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    pub tts: TtsSettings,
    pub stt: SttSettings,
    pub shortcuts: ShortcutConfig,
    pub process_blacklist: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TtsSettings {
    pub speed: f32,
    pub volume: f32,
    pub voice_id: String,
    pub auto_resume_after_dictation: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SttSettings {
    pub enabled: bool,
    pub model_installed: bool,
    pub hold_threshold_ms: u64,
    pub audio_ducking_db: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ShortcutConfig {
    pub speak_selection: InputChord,
    pub push_to_talk: InputChord,
    pub open_home: InputChord,
    pub toggle_bionic: InputChord,
    pub toggle_reader: InputChord,
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            tts: TtsSettings {
                speed: 1.0,
                volume: 1.0,
                voice_id: "paradee-8m".into(),
                auto_resume_after_dictation: false,
            },
            stt: SttSettings {
                enabled: true,
                model_installed: false,
                hold_threshold_ms: 200,
                audio_ducking_db: -24.0,
            },
            shortcuts: ShortcutConfig {
                // Ctrl + Space to speak highlighted text
                speak_selection: InputChord::new(
                    vec![ModifierKey::Control],
                    TriggerSource::Key(0x20), // VK_SPACE
                    TriggerMode::Press,
                ),
                // Mouse Side Button 1 (Back) held down for Push-to-Talk
                push_to_talk: InputChord::new(
                    vec![],
                    TriggerSource::MouseButton(4), // XButton1
                    TriggerMode::Hold(Duration::from_millis(200)),
                ),
                // F9 or Ctrl + Shift + S to open Home / Settings dashboard
                open_home: InputChord::new(
                    vec![ModifierKey::Control, ModifierKey::Shift],
                    TriggerSource::Key(0x53), // VK_S
                    TriggerMode::Press,
                ),
                // Alt + B to toggle Bionic Reading
                toggle_bionic: InputChord::new(
                    vec![ModifierKey::Alt],
                    TriggerSource::Key(0x42), // VK_B
                    TriggerMode::Press,
                ),
                // Alt + R to toggle Reader View
                toggle_reader: InputChord::new(
                    vec![ModifierKey::Alt],
                    TriggerSource::Key(0x52), // VK_R
                    TriggerMode::Press,
                ),
            },
            process_blacklist: vec![
                "cs2.exe".into(),
                "valorant.exe".into(),
                "dota2.exe".into(),
                "league of legends.exe".into(),
                "blender.exe".into(),
                "acad.exe".into(),
            ],
        }
    }
}

impl AppConfig {
    pub fn config_path() -> PathBuf {
        let base = dirs::data_local_dir().unwrap_or_else(|| PathBuf::from("."));
        base.join("SpeakThat").join("config.json")
    }

    pub fn load() -> Self {
        let path = Self::config_path();
        if path.exists() {
            if let Ok(content) = fs::read_to_string(&path) {
                if let Ok(config) = serde_json::from_str(&content) {
                    return config;
                }
            }
        }
        let default_config = Self::default();
        let _ = default_config.save();
        default_config
    }

    pub fn save(&self) -> Result<(), String> {
        let path = Self::config_path();
        if let Some(parent) = path.parent() {
            let _ = fs::create_dir_all(parent);
        }
        let json = serde_json::to_string_pretty(self).map_err(|e| e.to_string())?;
        fs::write(path, json).map_err(|e| e.to_string())?;
        Ok(())
    }
}
