use std::time::Duration;
use tracing::info;
use windows::Win32::Foundation::{HANDLE, HGLOBAL, HWND};
use windows::Win32::System::DataExchange::{
    CloseClipboard, EmptyClipboard, GetClipboardData, GetClipboardSequenceNumber, OpenClipboard,
    SetClipboardData,
};
use windows::Win32::System::Memory::{GlobalAlloc, GlobalLock, GlobalUnlock, GHND};
use windows::Win32::UI::Input::KeyboardAndMouse::{
    MapVirtualKeyW, SendInput, INPUT, INPUT_0, INPUT_KEYBOARD, KEYBDINPUT, KEYEVENTF_EXTENDEDKEY,
    KEYEVENTF_KEYUP, MAPVK_VK_TO_VSC, VIRTUAL_KEY, VK_C, VK_CONTROL, VK_LCONTROL, VK_LMENU,
    VK_LSHIFT, VK_LWIN, VK_RCONTROL, VK_RMENU, VK_RSHIFT, VK_RWIN,
};
use windows::Win32::UI::WindowsAndMessaging::{GetForegroundWindow, GetWindowTextW};

const CF_UNICODETEXT: u32 = 13;

pub struct SelectionCapture;

impl SelectionCapture {
    fn foreground_window_title() -> String {
        unsafe {
            let hwnd = GetForegroundWindow();
            if hwnd.0.is_null() {
                return String::from("<none>");
            }
            let mut buf = [0u16; 256];
            let len = GetWindowTextW(hwnd, &mut buf);
            if len <= 0 {
                return String::from("<untitled>");
            }
            String::from_utf16_lossy(&buf[..len as usize])
        }
    }

    fn key_input(vk: VIRTUAL_KEY, up: bool, extended: bool) -> INPUT {
        let scan = unsafe { MapVirtualKeyW(vk.0 as u32, MAPVK_VK_TO_VSC) as u16 };
        let mut flags = Default::default();
        if up {
            flags |= KEYEVENTF_KEYUP;
        }
        if extended {
            flags |= KEYEVENTF_EXTENDEDKEY;
        }
        INPUT {
            r#type: INPUT_KEYBOARD,
            Anonymous: INPUT_0 {
                ki: KEYBDINPUT {
                    wVk: vk,
                    wScan: scan,
                    dwFlags: flags,
                    time: 0,
                    dwExtraInfo: 0,
                },
            },
        }
    }

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
            let h_mem =
                GlobalAlloc(GHND, bytes_len).map_err(|e| format!("GlobalAlloc failed: {e:?}"))?;
            let ptr = GlobalLock(h_mem) as *mut u16;
            if ptr.is_null() {
                return Err("GlobalLock failed".to_string());
            }

            std::ptr::copy_nonoverlapping(utf16.as_ptr(), ptr, utf16.len());
            let _ = GlobalUnlock(h_mem);

            OpenClipboard(HWND(std::ptr::null_mut()))
                .map_err(|e| format!("OpenClipboard failed: {e:?}"))?;
            let _ = EmptyClipboard();
            let _ = SetClipboardData(CF_UNICODETEXT, HANDLE(h_mem.0));
            let _ = CloseClipboard();
        }

        Ok(())
    }

    /// Releases any held modifier keys, sends a clean synthetic Ctrl+C, and polls
    /// `GetClipboardSequenceNumber()` before reading the newly copied selection.
    pub async fn capture_selected_text_synthetic(timeout: Duration) -> Result<String, String> {
        let fg_title = Self::foreground_window_title();
        let backup = Self::read_clipboard_text();

        // Clear clipboard temporarily so stale data cannot bleed through
        unsafe {
            if OpenClipboard(HWND(std::ptr::null_mut())).is_ok() {
                let _ = EmptyClipboard();
                let _ = CloseClipboard();
            }
        }

        // 1. Explicitly release all held modifier keys so the target app sees a clean Ctrl+C
        let release_mods = [
            Self::key_input(VK_LWIN, true, true),
            Self::key_input(VK_RWIN, true, true),
            Self::key_input(VK_LMENU, true, false),
            Self::key_input(VK_RMENU, true, true),
            Self::key_input(VK_LSHIFT, true, false),
            Self::key_input(VK_RSHIFT, true, false),
            Self::key_input(VK_LCONTROL, true, false),
            Self::key_input(VK_RCONTROL, true, true),
        ];
        unsafe {
            SendInput(&release_mods, std::mem::size_of::<INPUT>() as i32);
        }

        // Brief settle delay so Windows / foreground app processes modifier releases
        tokio::time::sleep(Duration::from_millis(25)).await;

        let seq_before = unsafe { GetClipboardSequenceNumber() };

        // 2. Send clean Ctrl + C with hardware scan codes
        let copy_inputs = [
            Self::key_input(VK_CONTROL, false, false),
            Self::key_input(VK_C, false, false),
            Self::key_input(VK_C, true, false),
            Self::key_input(VK_CONTROL, true, false),
        ];
        let sent_count = unsafe { SendInput(&copy_inputs, std::mem::size_of::<INPUT>() as i32) };

        // 3. Poll every 15ms up to max(timeout, 300ms) until clipboard sequence increments
        let max_wait = timeout.max(Duration::from_millis(300));
        let start = std::time::Instant::now();
        let mut captured: Option<String> = None;
        let mut seq_after = seq_before;

        while start.elapsed() < max_wait {
            tokio::time::sleep(Duration::from_millis(15)).await;
            let seq_now = unsafe { GetClipboardSequenceNumber() };
            if seq_now != seq_before {
                seq_after = seq_now;
                if let Some(text) = Self::read_clipboard_text() {
                    if !text.trim().is_empty() {
                        captured = Some(text);
                        break;
                    }
                }
            }
        }

        info!(
            "SelectionCapture fg=\"{}\" send_input={}/{} seq={}->{} captured_chars={}",
            fg_title,
            sent_count,
            copy_inputs.len(),
            seq_before,
            seq_after,
            captured.as_ref().map(|s| s.len()).unwrap_or(0)
        );

        let result = captured.ok_or_else(|| "No text selected in active window".to_string());

        // Restore previous clipboard text if present
        if let Some(old) = backup {
            let _ = Self::write_clipboard_text(&old);
        }

        result
    }
}
