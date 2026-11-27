use std::sync::atomic::{AtomicU32, AtomicU64, Ordering};
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::mpsc;
use tracing::{debug, info, trace};
use windows::Win32::Foundation::{HINSTANCE, LPARAM, LRESULT, WPARAM};
use windows::Win32::UI::Input::KeyboardAndMouse::GetAsyncKeyState;
use windows::Win32::UI::WindowsAndMessaging::{
    CallNextHookEx, DispatchMessageW, GetMessageW, SetWindowsHookExW, TranslateMessage,
    UnhookWindowsHookEx, HHOOK, KBDLLHOOKSTRUCT, MSLLHOOKSTRUCT, MSG, WH_KEYBOARD_LL,
    WH_MOUSE_LL, WM_KEYDOWN, WM_KEYUP, WM_MBUTTONDOWN, WM_MBUTTONUP, WM_SYSKEYDOWN,
    WM_SYSKEYUP, WM_XBUTTONDOWN, WM_XBUTTONUP,
};

use super::chord::{InputChord, ModifierKey};

const LLKHF_INJECTED_FLAG: u32 = 0x10;

#[derive(Debug, Clone)]
pub enum HookEvent {
    ChordTriggered(InputChord),
    MouseButtonDown(u32), // 3: Middle, 4: XButton1 (Back), 5: XButton2 (Forward)
    MouseButtonUp(u32, Duration),
}

pub struct InputHookManager {
    event_tx: mpsc::UnboundedSender<HookEvent>,
}

impl InputHookManager {
    pub fn new(event_tx: mpsc::UnboundedSender<HookEvent>) -> Self {
        Self { event_tx }
    }

    /// Atomically updates which mouse buttons (bit N = button N) should be intercepted by WH_MOUSE_LL.
    pub fn update_bound_mouse_mask(mask: u32) {
        BOUND_MOUSE_MASK.store(mask, Ordering::SeqCst);
        info!("Updated bound mouse button hook mask: 0x{:02X}", mask);
    }

    /// Spawns the native Win32 low-level message loop hook on a dedicated thread.
    pub fn start_listening(self: Arc<Self>) -> std::thread::JoinHandle<()> {
        std::thread::spawn(move || unsafe {
            let h_instance = HINSTANCE(std::ptr::null_mut());

            let kbd_hook = SetWindowsHookExW(
                WH_KEYBOARD_LL,
                Some(low_level_keyboard_proc),
                h_instance,
                0,
            );

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
        })
    }
}

static mut GLOBAL_HOOK_TX: Option<mpsc::UnboundedSender<HookEvent>> = None;
static BOUND_MOUSE_MASK: AtomicU32 = AtomicU32::new(0);
static HELD_KEYS_BITMAP: [AtomicU64; 4] = [
    AtomicU64::new(0),
    AtomicU64::new(0),
    AtomicU64::new(0),
    AtomicU64::new(0),
];
static MOUSE_DOWN_TIME_MS: [AtomicU32; 8] = [
    AtomicU32::new(0),
    AtomicU32::new(0),
    AtomicU32::new(0),
    AtomicU32::new(0),
    AtomicU32::new(0),
    AtomicU32::new(0),
    AtomicU32::new(0),
    AtomicU32::new(0),
];

fn is_modifier_vk(vk: u16) -> bool {
    matches!(
        vk,
        0x10 | 0xA0 | 0xA1 // VK_SHIFT, VK_LSHIFT, VK_RSHIFT
        | 0x11 | 0xA2 | 0xA3 // VK_CONTROL, VK_LCONTROL, VK_RCONTROL
        | 0x12 | 0xA4 | 0xA5 // VK_MENU, VK_LMENU, VK_RMENU
        | 0x5B | 0x5C // VK_LWIN, VK_RWIN
    )
}

/// Marks `vk` as held; returns `true` if it was ALREADY held (OS key repeat).
fn mark_key_down_and_was_held(vk: u16) -> bool {
    let idx = (vk as usize) / 64;
    if idx >= HELD_KEYS_BITMAP.len() {
        return false;
    }
    let bit = 1u64 << ((vk as usize) % 64);
    let prev = HELD_KEYS_BITMAP[idx].fetch_or(bit, Ordering::SeqCst);
    (prev & bit) != 0
}

fn mark_key_up(vk: u16) {
    let idx = (vk as usize) / 64;
    if idx < HELD_KEYS_BITMAP.len() {
        let bit = 1u64 << ((vk as usize) % 64);
        HELD_KEYS_BITMAP[idx].fetch_and(!bit, Ordering::SeqCst);
    }
}

unsafe extern "system" fn low_level_keyboard_proc(
    n_code: i32,
    w_param: WPARAM,
    l_param: LPARAM,
) -> LRESULT {
    if n_code >= 0 {
        let msg = w_param.0 as u32;
        let kbd = *(l_param.0 as *const KBDLLHOOKSTRUCT);

        // Ignore synthetic/injected keystrokes (so our own Ctrl+C or TextInjector never feeds back)
        if (kbd.flags.0 & LLKHF_INJECTED_FLAG) != 0 {
            return CallNextHookEx(HHOOK(std::ptr::null_mut()), n_code, w_param, l_param);
        }

        let vk = kbd.vkCode as u16;

        if msg == WM_KEYUP || msg == WM_SYSKEYUP {
            mark_key_up(vk);
        } else if msg == WM_KEYDOWN || msg == WM_SYSKEYDOWN {
            // Only evaluate chord when a non-modifier key is freshly pressed (skip OS auto-repeat)
            if !is_modifier_vk(vk) && !mark_key_down_and_was_held(vk) {
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
                trace!("Hook captured key chord: {}", chord);

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

        let (is_down, btn_id): (bool, u32) = match msg {
            WM_XBUTTONDOWN => {
                let xb = (ms.mouseData >> 16) & 0xFFFF;
                (true, if xb == 1 { 4 } else if xb == 2 { 5 } else { 0 })
            }
            WM_XBUTTONUP => {
                let xb = (ms.mouseData >> 16) & 0xFFFF;
                (false, if xb == 1 { 4 } else if xb == 2 { 5 } else { 0 })
            }
            WM_MBUTTONDOWN => (true, 3),
            WM_MBUTTONUP => (false, 3),
            _ => (false, 0),
        };

        if btn_id >= 3 && (btn_id as usize) < MOUSE_DOWN_TIME_MS.len() {
            let bound = (BOUND_MOUSE_MASK.load(Ordering::Relaxed) & (1u32 << btn_id)) != 0;
            if bound {
                if is_down {
                    MOUSE_DOWN_TIME_MS[btn_id as usize].store(ms.time, Ordering::SeqCst);
                    debug!("Hook captured bound mouse button {} DOWN", btn_id);
                    if let Some(ref tx) = GLOBAL_HOOK_TX {
                        let _ = tx.send(HookEvent::MouseButtonDown(btn_id));
                    }
                } else {
                    let start_ms = MOUSE_DOWN_TIME_MS[btn_id as usize].swap(0, Ordering::SeqCst);
                    let duration_ms = if start_ms > 0 {
                        ms.time.saturating_sub(start_ms)
                    } else {
                        0
                    };
                    debug!(
                        "Hook captured bound mouse button {} UP ({}ms)",
                        btn_id, duration_ms
                    );
                    if let Some(ref tx) = GLOBAL_HOOK_TX {
                        let _ = tx.send(HookEvent::MouseButtonUp(
                            btn_id,
                            Duration::from_millis(duration_ms as u64),
                        ));
                    }
                }
                // Intercept both DOWN and UP for bound mouse buttons so target apps do not navigate Back or lose selection
                return LRESULT(1);
            }
        }
    }
    CallNextHookEx(HHOOK(std::ptr::null_mut()), n_code, w_param, l_param)
}
