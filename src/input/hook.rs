use std::sync::atomic::{AtomicU32, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::mpsc;
use windows::Win32::Foundation::{HINSTANCE, LPARAM, LRESULT, WPARAM};
use windows::Win32::UI::WindowsAndMessaging::{
    CallNextHookEx, DispatchMessageW, GetMessageW, SetWindowsHookExW, UnhookWindowsHookEx,
    HHOOK, KBDLLHOOKSTRUCT, MSLLHOOKSTRUCT, MSG, WH_KEYBOARD_LL, WH_MOUSE_LL, WM_KEYDOWN,
    WM_SYSKEYDOWN, WM_XBUTTONDOWN, WM_XBUTTONUP,
};

use super::chord::InputChord;

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

                if let (Ok(kh), Ok(mh)) = (kbd_hook, mouse_hook) {
                    GLOBAL_HOOK_TX = Some(self.event_tx.clone());

                    let mut msg = MSG::default();
                    while GetMessageW(&mut msg, None, 0, 0).as_bool() {
                        DispatchMessageW(&msg);
                    }

                    let _ = UnhookWindowsHookEx(kh);
                    let _ = UnhookWindowsHookEx(mh);
                }
            }
        })
    }
}

static mut GLOBAL_HOOK_TX: Option<mpsc::UnboundedSender<HookEvent>> = None;
static MOUSE_DOWN_INSTANT: AtomicU32 = AtomicU32::new(0);
static MOUSE_ACTIVE_BTN: AtomicU32 = AtomicU32::new(0);

unsafe extern "system" fn low_level_keyboard_proc(
    n_code: i32,
    w_param: WPARAM,
    l_param: LPARAM,
) -> LRESULT {
    if n_code >= 0 {
        let msg = w_param.0 as u32;
        let kbd = *(l_param.0 as *const KBDLLHOOKSTRUCT);

        if msg == WM_KEYDOWN || msg == WM_SYSKEYDOWN {
            let _vk = kbd.vkCode as u16;
            // Check modifier state asynchronously
            // (Full chord state evaluation is dispatched)
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

            // Suppress original button event to intercept hold-to-talk
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
