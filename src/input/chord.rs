use serde::{Deserialize, Serialize};
use std::fmt;
use std::time::Duration;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum ModifierKey {
    Control,
    Shift,
    Alt,
    Win,
}

impl fmt::Display for ModifierKey {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ModifierKey::Control => write!(f, "Ctrl"),
            ModifierKey::Shift => write!(f, "Shift"),
            ModifierKey::Alt => write!(f, "Alt"),
            ModifierKey::Win => write!(f, "Win"),
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum TriggerSource {
    Key(u16),         // Virtual Key Code (e.g. VK_SPACE = 0x20)
    MouseButton(u32), // 1: Left, 2: Right, 3: Middle, 4: XButton1 (Back), 5: XButton2 (Forward)
}

impl fmt::Display for TriggerSource {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            TriggerSource::Key(code) => match *code {
                0x20 => write!(f, "Space"),
                0x0D => write!(f, "Enter"),
                0x1B => write!(f, "Esc"),
                0x09 => write!(f, "Tab"),
                0x41..=0x5A => write!(f, "{}", (b'A' + (*code as u8 - 0x41)) as char),
                0x30..=0x39 => write!(f, "{}", (b'0' + (*code as u8 - 0x30)) as char),
                0x70..=0x7B => write!(f, "F{}", *code - 0x6F),
                _ => write!(f, "Key(0x{:02X})", code),
            },
            TriggerSource::MouseButton(btn) => match *btn {
                1 => write!(f, "MouseLeft"),
                2 => write!(f, "MouseRight"),
                3 => write!(f, "MouseMiddle"),
                4 => write!(f, "MouseSide1(Back)"),
                5 => write!(f, "MouseSide2(Forward)"),
                _ => write!(f, "MouseButton({})", btn),
            },
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum TriggerMode {
    Press,
    Hold(Duration),
    Click,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct InputChord {
    pub modifiers: Vec<ModifierKey>,
    pub trigger: TriggerSource,
    pub trigger_mode: TriggerMode,
}

impl InputChord {
    pub fn new(modifiers: Vec<ModifierKey>, trigger: TriggerSource, trigger_mode: TriggerMode) -> Self {
        Self {
            modifiers,
            trigger,
            trigger_mode,
        }
    }

    pub fn key_press(modifiers: Vec<ModifierKey>, vk_code: u16) -> Self {
        Self {
            modifiers,
            trigger: TriggerSource::Key(vk_code),
            trigger_mode: TriggerMode::Press,
        }
    }

    pub fn mouse_hold(btn: u32, duration: Duration) -> Self {
        Self {
            modifiers: Vec::new(),
            trigger: TriggerSource::MouseButton(btn),
            trigger_mode: TriggerMode::Hold(duration),
        }
    }

    pub fn total_keys_count(&self) -> usize {
        self.modifiers.len() + 1
    }

    /// Checks if this chord matches another chord regardless of modifier order
    pub fn matches(&self, other: &InputChord) -> bool {
        if self.trigger != other.trigger {
            return false;
        }
        if self.modifiers.len() != other.modifiers.len() {
            return false;
        }
        for m in &self.modifiers {
            if !other.modifiers.contains(m) {
                return false;
            }
        }
        true
    }
}

impl fmt::Display for InputChord {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let mut parts = Vec::new();
        for m in &self.modifiers {
            parts.push(m.to_string());
        }
        parts.push(self.trigger.to_string());
        let chord_str = parts.join(" + ");
        match self.trigger_mode {
            TriggerMode::Press => write!(f, "{}", chord_str),
            TriggerMode::Click => write!(f, "{} (Click)", chord_str),
            TriggerMode::Hold(dur) => write!(f, "{} (Hold {}ms)", chord_str, dur.as_millis()),
        }
    }
}
