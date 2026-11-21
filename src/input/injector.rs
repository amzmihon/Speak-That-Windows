use windows::Win32::UI::Input::KeyboardAndMouse::{
    SendInput, INPUT, INPUT_0, INPUT_KEYBOARD, KEYBDINPUT, KEYEVENTF_KEYUP, KEYEVENTF_UNICODE,
};

pub struct TextInjector;

impl TextInjector {
    /// Injects text directly into the active Windows window using `SendInput`
    /// with `KEYEVENTF_UNICODE`.
    ///
    /// Correctly splits astral plane Unicode characters (emojis, complex symbols)
    /// into high and low UTF-16 surrogate pairs, each paired with down and up events.
    pub fn inject_text(text: &str) -> Result<(), String> {
        let mut inputs = Vec::new();

        for ch in text.chars() {
            let mut utf16_buf = [0u16; 2];
            let encoded = ch.encode_utf16(&mut utf16_buf);

            for &unit in encoded.iter() {
                // Key Down Event
                inputs.push(INPUT {
                    r#type: INPUT_KEYBOARD,
                    Anonymous: INPUT_0 {
                        ki: KEYBDINPUT {
                            wVk: Default::default(),
                            wScan: unit,
                            dwFlags: KEYEVENTF_UNICODE,
                            time: 0,
                            dwExtraInfo: 0,
                        },
                    },
                });

                // Key Up Event
                inputs.push(INPUT {
                    r#type: INPUT_KEYBOARD,
                    Anonymous: INPUT_0 {
                        ki: KEYBDINPUT {
                            wVk: Default::default(),
                            wScan: unit,
                            dwFlags: KEYEVENTF_UNICODE | KEYEVENTF_KEYUP,
                            time: 0,
                            dwExtraInfo: 0,
                        },
                    },
                });
            }
        }

        if inputs.is_empty() {
            return Ok(());
        }

        let sent = unsafe {
            SendInput(
                &inputs,
                std::mem::size_of::<INPUT>() as i32,
            )
        };

        if sent != inputs.len() as u32 {
            return Err(format!(
                "Failed to inject full text: sent {} of {} input events",
                sent,
                inputs.len()
            ));
        }

        Ok(())
    }
}
