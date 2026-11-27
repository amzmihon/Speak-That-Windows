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
    /// - Keyboard combinations of 2 to 4 keys are permitted (1-key allowed when `allow_single_key` is true, or for F1-F12 / Mouse).
    /// - Critical OS operations (Lock, Task Manager, Clipboard, Close) use exact modifier-set matching and are hard-blocked.
    /// - Common editor/browser shortcuts (Ctrl+S, Ctrl+F, etc.) use exact modifier-set matching and produce soft warnings.
    pub fn validate(chord: &InputChord) -> CollisionSeverity {
        Self::validate_for(chord, false)
    }

    pub fn validate_for(chord: &InputChord, allow_single_key: bool) -> CollisionSeverity {
        let total_keys = chord.total_keys_count();

        // Validate key length range: max 4 keys
        if total_keys > 4 {
            return CollisionSeverity::HardBlocked(
                "Shortcuts cannot exceed 4 keys (e.g. Ctrl + Shift + Alt + Key).".into(),
            );
        }

        let has_ctrl = chord.modifiers.contains(&ModifierKey::Control);
        let has_alt = chord.modifiers.contains(&ModifierKey::Alt);
        let has_shift = chord.modifiers.contains(&ModifierKey::Shift);
        let has_win = chord.modifiers.contains(&ModifierKey::Win);

        let exact_mods = |ctrl: bool, shift: bool, alt: bool, win: bool| -> bool {
            has_ctrl == ctrl && has_shift == shift && has_alt == alt && has_win == win
        };

        if let TriggerSource::Key(vk) = chord.trigger {
            // Single key rule: F1-F12 always allowed; single keys allowed for Home Dashboard when opted in
            if chord.modifiers.is_empty() && !(0x70..=0x7B).contains(&vk) && !allow_single_key {
                return CollisionSeverity::HardBlocked(
                    "Requires 2-4 keys (add Ctrl, Alt, Win, or Shift), or use F1-F12.".into(),
                );
            }

            // --- HARD BLOCKS (Exact modifier-set matching for Windows OS Critical) ---
            if exact_mods(false, false, false, true) && vk == 0x4C {
                return CollisionSeverity::HardBlocked("Win + L is reserved by Windows (Lock).".into());
            }
            if exact_mods(false, false, true, false) && vk == 0x73 {
                return CollisionSeverity::HardBlocked("Alt + F4 is reserved by Windows (Close Window).".into());
            }
            if exact_mods(true, false, true, false) && vk == 0x2E {
                return CollisionSeverity::HardBlocked("Ctrl + Alt + Delete is reserved by Windows Security.".into());
            }
            if exact_mods(false, false, false, true) && vk == 0x44 {
                return CollisionSeverity::HardBlocked("Win + D is reserved by Windows (Show Desktop).".into());
            }
            if exact_mods(true, true, false, false) && vk == 0x1B {
                return CollisionSeverity::HardBlocked("Ctrl + Shift + Esc is reserved for Task Manager.".into());
            }
            if exact_mods(false, false, true, false) && vk == 0x09 {
                return CollisionSeverity::HardBlocked("Alt + Tab is reserved for window switching.".into());
            }

            // Universal Edit Operations (strictly Ctrl+<Key>, NOT Ctrl+Shift+<Key>)
            if exact_mods(true, false, false, false) {
                match vk {
                    0x43 => return CollisionSeverity::HardBlocked("Ctrl + C is reserved for Copy.".into()),
                    0x56 => return CollisionSeverity::HardBlocked("Ctrl + V is reserved for Paste.".into()),
                    0x58 => return CollisionSeverity::HardBlocked("Ctrl + X is reserved for Cut.".into()),
                    0x5A => return CollisionSeverity::HardBlocked("Ctrl + Z is reserved for Undo.".into()),
                    0x41 => return CollisionSeverity::HardBlocked("Ctrl + A is reserved for Select All.".into()),
                    // --- SOFT WARNINGS (Exact modifier-set matching) ---
                    0x53 => {
                        return CollisionSeverity::Warning(
                            "Ctrl + S is commonly used for Save in editors and Office apps.".into(),
                        );
                    }
                    0x46 => {
                        return CollisionSeverity::Warning(
                            "Ctrl + F is commonly used for Find in browsers and viewers.".into(),
                        );
                    }
                    0x50 => {
                        return CollisionSeverity::Warning(
                            "Ctrl + P is commonly used for Print in browsers and office apps.".into(),
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

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::AppConfig;

    #[test]
    fn default_shortcuts_have_no_false_positive_warnings() {
        let cfg = AppConfig::default();
        assert_eq!(
            ShortcutCatalog::validate_for(&cfg.shortcuts.speak_selection.keyboard, false),
            CollisionSeverity::Allowed
        );
        assert_eq!(
            ShortcutCatalog::validate_for(&cfg.shortcuts.stop_speaking.keyboard, false),
            CollisionSeverity::Allowed
        );
        assert_eq!(
            ShortcutCatalog::validate_for(&cfg.shortcuts.push_to_talk.keyboard, false),
            CollisionSeverity::Allowed
        );
        assert_eq!(
            ShortcutCatalog::validate_for(&cfg.shortcuts.open_home.keyboard, true),
            CollisionSeverity::Allowed
        );
        assert_eq!(
            ShortcutCatalog::validate_for(&cfg.shortcuts.toggle_bionic.keyboard, false),
            CollisionSeverity::Allowed
        );
        assert_eq!(
            ShortcutCatalog::validate_for(&cfg.shortcuts.toggle_reader.keyboard, false),
            CollisionSeverity::Allowed
        );
    }

    #[test]
    fn exact_modifier_equality_prevents_ctrl_shift_s_false_positive() {
        let ctrl_s = InputChord::key_press(vec![ModifierKey::Control], 0x53);
        let ctrl_shift_s = InputChord::key_press(vec![ModifierKey::Control, ModifierKey::Shift], 0x53);
        assert!(matches!(ShortcutCatalog::validate(&ctrl_s), CollisionSeverity::Warning(_)));
        assert_eq!(ShortcutCatalog::validate(&ctrl_shift_s), CollisionSeverity::Allowed);
    }

    #[test]
    fn open_home_allows_single_key() {
        let f9 = InputChord::key_press(vec![], 0x78);
        let h = InputChord::key_press(vec![], 0x48);
        assert_eq!(ShortcutCatalog::validate_for(&f9, true), CollisionSeverity::Allowed);
        assert_eq!(ShortcutCatalog::validate_for(&h, true), CollisionSeverity::Allowed);
        assert!(matches!(ShortcutCatalog::validate_for(&h, false), CollisionSeverity::HardBlocked(_)));
    }
}
