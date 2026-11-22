use std::sync::atomic::{AtomicU32, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::mpsc;
use tracing::{debug, info};
use windows::Win32::Foundation::{HINSTANCE, LPARAM, LRESULT, WPARAM};
use windows::Win32::UI::Input::KeyboardAndMouse::GetAsyncKeyState;
use windows::Win32::UI::WindowsAndMessaging::{
    CallNextHookEx, DispatchMessageW, GetMessageW, SetWindowsHookExW, TranslateMessage,
    UnhookWindowsHookEx, HHOOK, KBDLLHOOKSTRUCT, MSLLHOOKSTRUCT, MSG, WH_KEYBOARD_LL,
    WH_MOUSE_LL, WM_KEYDOWN, WM_SYSKEYDOWN, WM_XBUTTONDOWN, WM_XBUTTONUP,
};

use super::chord::{InputChord, ModifierKey};

#[derive(Debug, Clone)]
pub enum HookEvent {
    ChordTriggered(InputChord),
    SideButtonHoldStart(u32), // 4: XButton1, 5: XButton2
    SideButtonHoldEnd(u32, Duration),
}

pub struct InputHookManager {
    event_tx: mpsc::UnboundedSender<HookEvent>,
}

impl InputHookManager {
    pub fn new(event_tx: mpsc::UnboundedSender<HookEvent>) -> Self {
        Self { event_tx }
    }

    /// Spawns the native Win32 low-level message loop hook on a dedicated thread.
    pub fn start_listening(self: Arc<Self>) -> std::thread::JoinHandle<()> {
        std::thread::spawn(move || {
            unsafe {
                let h_instance = HINSTANCE(std::ptr::null_mut());

                // Set low-level keyboard hook
                let kbd_hook = SetWindowsHookExW(
                    WH_KEYBOARD_LL,
                    Some(low_level_keyboard_proc),
                    h_instance,
                    0,
                );

                // Set low-level mouse hook
                let mouse_hook = SetWindowsHookExW(
                    WH_MOUSE_LL,
                    Some(low_level_mouse_proc),
                    h_instance,
                    0,
                );

                match (kbd_hook, mouse_hook) {
                    (Ok(kh), Ok(mh)) => {
                        info!("Win32 WH_KEYBOARD_LL and WH_MOUSE_LL hooks registered successfully.");
                        GLOBAL_HOOK_TX = Some(self.event_tx.clone());

                        let mut msg = MSG::default();
                        while GetMessageW(&mut msg, None, 0, 0).as_bool() {
                            let _ = TranslateMessage(&msg);
                            DispatchMessageW(&msg);
                        }

                        let _ = UnhookWindowsHookEx(kh);
                        let _ = UnhookWindowsHookEx(mh);
                    }
                    (Err(e1), _) => {
                        tracing::error!("Failed to register WH_KEYBOARD_LL hook: {e1}");
                    }
                    (_, Err(e2)) => {
                        tracing::error!("Failed to register WH_MOUSE_LL hook: {e2}");
                    }
                }
            }
        })
    }
}

static mut GLOBAL_HOOK_TX: Option<mpsc::UnboundedSender<HookEvent>> = None;
static MOUSE_DOWN_INSTANT: AtomicU32 = AtomicU32::new(0);
static MOUSE_ACTIVE_BTN: AtomicU32 = AtomicU32::new(0);

fn is_modifier_vk(vk: u16) -> bool {
    matches!(
        vk,
        0x10 | 0xA0 | 0xA1 // VK_SHIFT, VK_LSHIFT, VK_RSHIFT
        | 0x11 | 0xA2 | 0xA3 // VK_CONTROL, VK_LCONTROL, VK_RCONTROL
        | 0x12 | 0xA4 | 0xA5 // VK_MENU, VK_LMENU, VK_RMENU
        | 0x5B | 0x5C // VK_LWIN, VK_RWIN
    )
}

unsafe extern "system" fn low_level_keyboard_proc(
    n_code: i32,
    w_param: WPARAM,
    l_param: LPARAM,
) -> LRESULT {
    if n_code >= 0 {
        let msg = w_param.0 as u32;

        if msg == WM_KEYDOWN || msg == WM_SYSKEYDOWN {
            let kbd = *(l_param.0 as *const KBDLLHOOKSTRUCT);
            let vk = kbd.vkCode as u16;

            // Only evaluate chord when a non-modifier key is pressed
            if !is_modifier_vk(vk) {
                let ctrl_down = (GetAsyncKeyState(0x11) as u16 & 0x8000) != 0
                    || (GetAsyncKeyState(0xA2) as u16 & 0x8000) != 0
                    || (GetAsyncKeyState(0xA3) as u16 & 0x8000) != 0;

                let shift_down = (GetAsyncKeyState(0x10) as u16 & 0x8000) != 0
                    || (GetAsyncKeyState(0xA0) as u16 & 0x8000) != 0
                    || (GetAsyncKeyState(0xA1) as u16 & 0x8000) != 0;

                let alt_down = (GetAsyncKeyState(0x12) as u16 & 0x8000) != 0
                    || (GetAsyncKeyState(0xA4) as u16 & 0x8000) != 0
                    || (GetAsyncKeyState(0xA5) as u16 & 0x8000) != 0
                    || msg == WM_SYSKEYDOWN;

                let win_down = (GetAsyncKeyState(0x5B) as u16 & 0x8000) != 0
                    || (GetAsyncKeyState(0x5C) as u16 & 0x8000) != 0;

                let mut modifiers = Vec::new();
                if ctrl_down {
                    modifiers.push(ModifierKey::Control);
                }
                if shift_down {
                    modifiers.push(ModifierKey::Shift);
                }
                if alt_down {
                    modifiers.push(ModifierKey::Alt);
                }
                if win_down {
                    modifiers.push(ModifierKey::Win);
                }

                let chord = InputChord::key_press(modifiers, vk);
                debug!("Hook captured key chord: {}", chord);

                if let Some(ref tx) = GLOBAL_HOOK_TX {
                    let _ = tx.send(HookEvent::ChordTriggered(chord));
                }
            }
        }
    }
    CallNextHookEx(HHOOK(std::ptr::null_mut()), n_code, w_param, l_param)
}

unsafe extern "system" fn low_level_mouse_proc(
    n_code: i32,
    w_param: WPARAM,
    l_param: LPARAM,
) -> LRESULT {
    if n_code >= 0 {
        let msg = w_param.0 as u32;
        let ms = *(l_param.0 as *const MSLLHOOKSTRUCT);

        if msg == WM_XBUTTONDOWN {
            let xbutton = (ms.mouseData >> 16) as u32; // 1: XButton1, 2: XButton2
            let btn_id = if xbutton == 1 { 4 } else { 5 };

            MOUSE_ACTIVE_BTN.store(btn_id, Ordering::SeqCst);
            let now_ms = (Instant::now().elapsed().as_millis() & 0xFFFFFFFF) as u32;
            MOUSE_DOWN_INSTANT.store(now_ms, Ordering::SeqCst);

            if let Some(ref tx) = GLOBAL_HOOK_TX {
                let _ = tx.send(HookEvent::SideButtonHoldStart(btn_id));
            }

            return LRESULT(1);
        } else if msg == WM_XBUTTONUP {
            let xbutton = (ms.mouseData >> 16) as u32;
            let btn_id = if xbutton == 1 { 4 } else { 5 };

            let start_ms = MOUSE_DOWN_INSTANT.swap(0, Ordering::SeqCst);
            MOUSE_ACTIVE_BTN.store(0, Ordering::SeqCst);

            let now_ms = (Instant::now().elapsed().as_millis() & 0xFFFFFFFF) as u32;
            let duration_ms = now_ms.saturating_sub(start_ms);

            if let Some(ref tx) = GLOBAL_HOOK_TX {
                let _ = tx.send(HookEvent::SideButtonHoldEnd(
                    btn_id,
                    Duration::from_millis(duration_ms as u64),
                ));
            }

            return LRESULT(1);
        }
    }
    CallNextHookEx(HHOOK(std::ptr::null_mut()), n_code, w_param, l_param)
}
