use super::chord::{InputChord, ModifierKey, TriggerSource};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CollisionSeverity {
    Allowed,
    Warning(String),
    HardBlocked(String),
}

pub struct ShortcutCatalog;

impl ShortcutCatalog {
    /// Validates an input chord against Windows OS and application shortcuts.
    ///
    /// Rules:
    /// - Combinations with 2 to 4 keys are permitted.
    /// - Single keys are only permitted for Mouse Buttons or non-critical Function keys.
    /// - Critical OS operations (Lock, Task Manager, Clipboard, Close) are hard-blocked.
    /// - Common editor/browser keys (Save, Find, Print) produce soft warnings.
    pub fn validate(chord: &InputChord) -> CollisionSeverity {
        let total_keys = chord.total_keys_count();

        // 1. Validate key length range: 1 (for mouse/F-key) to 4 keys
        if total_keys > 4 {
            return CollisionSeverity::HardBlocked(
                "Shortcuts cannot exceed 4 keys (e.g. Ctrl + Shift + Alt + Key).".into(),
            );
        }

        let has_ctrl = chord.modifiers.contains(&ModifierKey::Control);
        let has_alt = chord.modifiers.contains(&ModifierKey::Alt);
        let has_shift = chord.modifiers.contains(&ModifierKey::Shift);
        let has_win = chord.modifiers.contains(&ModifierKey::Win);

        if let TriggerSource::Key(vk) = chord.trigger {
            // Prevent single typing keys without modifiers (except F1-F12)
            if chord.modifiers.is_empty() && !(0x70..=0x7B).contains(&vk) {
                return CollisionSeverity::HardBlocked(
                    "Single typing keys cannot be bound globally without a modifier (Ctrl, Alt, Win, or Shift).".into(),
                );
            }

            // --- HARD BLOCKS (Windows OS Critical) ---
            // Win + L: Lock Workstation
            if has_win && vk == 0x4C && !has_ctrl && !has_alt && !has_shift {
                return CollisionSeverity::HardBlocked("Win + L is reserved by Windows (Lock Workstation).".into());
            }

            // Alt + F4: Close Window
            if has_alt && vk == 0x73 && !has_ctrl && !has_shift {
                return CollisionSeverity::HardBlocked("Alt + F4 is reserved by Windows (Close Window).".into());
            }

            // Ctrl + Alt + Del: Windows Security (trapped by OS kernel anyway)
            if has_ctrl && has_alt && vk == 0x2E {
                return CollisionSeverity::HardBlocked("Ctrl + Alt + Delete is reserved by Windows Security.".into());
            }

            // Win + D: Show Desktop
            if has_win && vk == 0x44 && !has_ctrl && !has_alt {
                return CollisionSeverity::HardBlocked("Win + D is reserved by Windows (Show Desktop).".into());
            }

            // Ctrl + C, Ctrl + V, Ctrl + X, Ctrl + Z, Ctrl + A: Universal Edit Operations
            if has_ctrl && !has_alt && !has_win {
                match vk {
                    0x43 if !has_shift => {
                        return CollisionSeverity::HardBlocked("Ctrl + C is reserved for Universal Copy.".into());
                    }
                    0x56 if !has_shift => {
                        return CollisionSeverity::HardBlocked("Ctrl + V is reserved for Universal Paste.".into());
                    }
                    0x58 if !has_shift => {
                        return CollisionSeverity::HardBlocked("Ctrl + X is reserved for Universal Cut.".into());
                    }
                    0x5A if !has_shift => {
                        return CollisionSeverity::HardBlocked("Ctrl + Z is reserved for Universal Undo.".into());
                    }
                    0x41 if !has_shift => {
                        return CollisionSeverity::HardBlocked("Ctrl + A is reserved for Universal Select All.".into());
                    }
                    _ => {}
                }
            }

            // --- SOFT WARNINGS (Productivity Applications) ---
            if has_ctrl && !has_alt && !has_win {
                match vk {
                    0x53 => {
                        return CollisionSeverity::Warning(
                            "Ctrl + S is commonly used for Save in text editors and Office apps.".into(),
                        );
                    }
                    0x46 => {
                        return CollisionSeverity::Warning(
                            "Ctrl + F is commonly used for Find / Search in browsers and document viewers.".into(),
                        );
                    }
                    0x50 => {
                        return CollisionSeverity::Warning(
                            "Ctrl + P is commonly used for Print in browsers and office software.".into(),
                        );
                    }
                    0x54 => {
                        return CollisionSeverity::Warning(
                            "Ctrl + T is commonly used for New Tab in web browsers.".into(),
                        );
                    }
                    0x57 => {
                        return CollisionSeverity::Warning(
                            "Ctrl + W is commonly used for Close Tab in web browsers.".into(),
                        );
                    }
                    _ => {}
                }
            }
        }

        CollisionSeverity::Allowed
    }
}
