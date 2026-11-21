use std::ffi::c_void;
use std::time::Duration;
use windows::Win32::Foundation::{HANDLE, HGLOBAL, HWND};
use windows::Win32::System::DataExchange::{
    CloseClipboard, EmptyClipboard, GetClipboardData, OpenClipboard, SetClipboardData,
};
use windows::Win32::System::Memory::{GlobalAlloc, GlobalLock, GlobalUnlock, GHND};
use windows::Win32::UI::Input::KeyboardAndMouse::{
    SendInput, INPUT, INPUT_0, INPUT_KEYBOARD, KEYBDINPUT, KEYEVENTF_KEYUP, VK_C, VK_CONTROL,
};

const CF_UNICODETEXT: u32 = 13;

pub struct SelectionCapture;

impl SelectionCapture {
    /// Read Unicode text currently stored in the Windows clipboard
    pub fn read_clipboard_text() -> Option<String> {
        unsafe {
            if OpenClipboard(HWND(std::ptr::null_mut())).is_err() {
                return None;
            }

            let handle = match GetClipboardData(CF_UNICODETEXT) {
                Ok(h) => h,
                Err(_) => {
                    let _ = CloseClipboard();
                    return None;
                }
            };

            if handle.is_invalid() {
                let _ = CloseClipboard();
                return None;
            }

            let ptr = GlobalLock(HGLOBAL(handle.0)) as *const u16;
            if ptr.is_null() {
                let _ = CloseClipboard();
                return None;
            }

            // Find null terminator
            let mut len = 0;
            while *ptr.add(len) != 0 {
                len += 1;
            }

            let slice = std::slice::from_raw_parts(ptr, len);
            let text = String::from_utf16_lossy(slice);

            let _ = GlobalUnlock(HGLOBAL(handle.0));
            let _ = CloseClipboard();

            Some(text)
        }
    }

    /// Write Unicode text directly to the Windows clipboard
    pub fn write_clipboard_text(text: &str) -> Result<(), String> {
        let utf16: Vec<u16> = text.encode_utf16().chain(std::iter::once(0)).collect();
        let bytes_len = utf16.len() * std::mem::size_of::<u16>();

        unsafe {
            let h_mem = GlobalAlloc(GHND, bytes_len).map_err(|e| format!("GlobalAlloc failed: {e:?}"))?;
            let ptr = GlobalLock(h_mem) as *mut u16;
            if ptr.is_null() {
                return Err("GlobalLock failed".to_string());
            }

            std::ptr::copy_nonoverlapping(utf16.as_ptr(), ptr, utf16.len());
            let _ = GlobalUnlock(h_mem);

            OpenClipboard(HWND(std::ptr::null_mut())).map_err(|e| format!("OpenClipboard failed: {e:?}"))?;
            let _ = EmptyClipboard();
            let _ = SetClipboardData(CF_UNICODETEXT, HANDLE(h_mem.0));
            let _ = CloseClipboard();
        }

        Ok(())
    }

    /// Synthesize Ctrl+C to capture active selection from the foreground window,
    /// preserving the user's previous clipboard contents.
    pub async fn capture_selected_text_synthetic(timeout: Duration) -> Result<String, String> {
        let backup = Self::read_clipboard_text();

        // Clear clipboard temporarily so we can reliably detect newly copied text
        unsafe {
            if OpenClipboard(HWND(std::ptr::null_mut())).is_ok() {
                let _ = EmptyClipboard();
                let _ = CloseClipboard();
            }
        }

        // Simulate Ctrl+C
        let inputs = [
            INPUT {
                r#type: INPUT_KEYBOARD,
                Anonymous: INPUT_0 {
                    ki: KEYBDINPUT {
                        wVk: VK_CONTROL,
                        wScan: 0,
                        dwFlags: Default::default(),
                        time: 0,
                        dwExtraInfo: 0,
                    },
                },
            },
            INPUT {
                r#type: INPUT_KEYBOARD,
                Anonymous: INPUT_0 {
                    ki: KEYBDINPUT {
                        wVk: VK_C,
                        wScan: 0,
                        dwFlags: Default::default(),
                        time: 0,
                        dwExtraInfo: 0,
                    },
                },
            },
            INPUT {
                r#type: INPUT_KEYBOARD,
                Anonymous: INPUT_0 {
                    ki: KEYBDINPUT {
                        wVk: VK_C,
                        wScan: 0,
                        dwFlags: KEYEVENTF_KEYUP,
                        time: 0,
                        dwExtraInfo: 0,
                    },
                },
            },
            INPUT {
                r#type: INPUT_KEYBOARD,
                Anonymous: INPUT_0 {
                    ki: KEYBDINPUT {
                        wVk: VK_CONTROL,
                        wScan: 0,
                        dwFlags: KEYEVENTF_KEYUP,
                        time: 0,
                        dwExtraInfo: 0,
                    },
                },
            },
        ];

        unsafe {
            SendInput(&inputs, std::mem::size_of::<INPUT>() as i32);
        }

        // Poll for newly populated clipboard text up to timeout
        let start = std::time::Instant::now();
        let mut captured: Option<String> = None;

        while start.elapsed() < timeout {
            tokio::time::sleep(Duration::from_millis(15)).await;
            if let Some(text) = Self::read_clipboard_text() {
                if !text.trim().is_empty() {
                    captured = Some(text);
                    break;
                }
            }
        }

        let result = captured.ok_or_else(|| "No text selected in active window".to_string());

        // Restore previous clipboard text if needed
        if let Some(old) = backup {
            let _ = Self::write_clipboard_text(&old);
        }

        result
    }
}
