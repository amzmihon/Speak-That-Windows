use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;
use std::time::Duration;

use crate::input::chord::{InputChord, ModifierKey, TriggerMode, TriggerSource};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    pub tts: TtsSettings,
    pub stt: SttSettings,
    pub bionic: BionicSettings,
    pub shortcuts: ShortcutConfig,
    pub process_blacklist: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BionicSettings {
    pub enabled: bool,
    pub fixation_ratio: f32,
    pub allowed_scripts: Vec<String>,
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

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ActionBinding {
    pub keyboard: InputChord,
    pub mouse: Option<InputChord>,
}

impl ActionBinding {
    pub fn new(keyboard: InputChord, mouse: Option<InputChord>) -> Self {
        Self { keyboard, mouse }
    }

    pub fn matches_keyboard(&self, chord: &InputChord) -> bool {
        self.keyboard.matches(chord)
    }

    pub fn matches_mouse(&self, btn: u32) -> bool {
        if let Some(ref m) = self.mouse {
            matches!(m.trigger, TriggerSource::MouseButton(b) if b == btn)
        } else {
            false
        }
    }

    pub fn mouse_button(&self) -> Option<u32> {
        self.mouse.as_ref().and_then(|m| match m.trigger {
            TriggerSource::MouseButton(b) => Some(b),
            _ => None,
        })
    }

    pub fn mouse_hold_ms(&self) -> u64 {
        self.mouse
            .as_ref()
            .map(|m| match m.trigger_mode {
                TriggerMode::Hold(d) => d.as_millis() as u64,
                _ => 0,
            })
            .unwrap_or(0)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ShortcutConfig {
    pub speak_selection: ActionBinding,
    pub push_to_talk: ActionBinding,
    pub open_home: ActionBinding,
    pub toggle_bionic: ActionBinding,
    pub toggle_reader: ActionBinding,
}

impl ShortcutConfig {
    /// Returns bitmask of bound mouse buttons (bit N = mouse button N)
    pub fn bound_mouse_mask(&self) -> u32 {
        let mut mask = 0u32;
        for b in [
            &self.speak_selection,
            &self.push_to_talk,
            &self.open_home,
            &self.toggle_bionic,
            &self.toggle_reader,
        ] {
            if let Some(btn) = b.mouse_button() {
                if btn < 32 {
                    mask |= 1u32 << btn;
                }
            }
        }
        mask
    }
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            tts: TtsSettings {
                speed: 1.05,
                volume: 1.0,
                voice_id: "bf_isabella".into(),
                auto_resume_after_dictation: false,
            },
            stt: SttSettings {
                enabled: true,
                model_installed: false,
                hold_threshold_ms: 200,
                audio_ducking_db: -24.0,
            },
            bionic: BionicSettings {
                enabled: true,
                fixation_ratio: 0.4,
                allowed_scripts: vec!["Latin".to_string()],
            },
            shortcuts: ShortcutConfig {
                // Speak Selection: Ctrl + Space AND Mouse Button 4 (XButton1)
                speak_selection: ActionBinding::new(
                    InputChord::new(
                        vec![ModifierKey::Control],
                        TriggerSource::Key(0x20), // VK_SPACE
                        TriggerMode::Press,
                    ),
                    Some(InputChord::mouse_hold(4, Duration::from_millis(0))),
                ),
                // Push-to-Talk (STT): Ctrl + Shift + D AND Mouse Button 5 (XButton2)
                push_to_talk: ActionBinding::new(
                    InputChord::new(
                        vec![ModifierKey::Control, ModifierKey::Shift],
                        TriggerSource::Key(0x44), // VK_D
                        TriggerMode::Press,
                    ),
                    Some(InputChord::mouse_hold(5, Duration::from_millis(200))),
                ),
                // Open Home Dashboard: Ctrl + Shift + S (single key also permitted in editor)
                open_home: ActionBinding::new(
                    InputChord::new(
                        vec![ModifierKey::Control, ModifierKey::Shift],
                        TriggerSource::Key(0x53), // VK_S
                        TriggerMode::Press,
                    ),
                    None,
                ),
                // Toggle Bionic Reading: Alt + B
                toggle_bionic: ActionBinding::new(
                    InputChord::new(
                        vec![ModifierKey::Alt],
                        TriggerSource::Key(0x42), // VK_B
                        TriggerMode::Press,
                    ),
                    None,
                ),
                // Toggle Native Reader View: Alt + R
                toggle_reader: ActionBinding::new(
                    InputChord::new(
                        vec![ModifierKey::Alt],
                        TriggerSource::Key(0x52), // VK_R
                        TriggerMode::Press,
                    ),
                    None,
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
