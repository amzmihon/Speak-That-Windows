use std::cell::RefCell;
use std::mem::size_of;
use std::sync::atomic::{AtomicIsize, Ordering};
use tracing::info;
use windows::core::{w, PCWSTR};
use windows::Win32::Foundation::{HWND, LPARAM, LRESULT, POINT, WPARAM};
use windows::Win32::UI::Shell::{
    Shell_NotifyIconW, NIF_ICON, NIF_MESSAGE, NIF_TIP, NIM_ADD, NIM_DELETE, NOTIFYICONDATAW,
};
use windows::Win32::UI::WindowsAndMessaging::{
    AppendMenuW, CreateIconFromResourceEx, CreatePopupMenu, CreateWindowExW, DefWindowProcW,
    DestroyMenu, DispatchMessageW, GetCursorPos, GetMessageW, LoadIconW, PostMessageW,
    RegisterClassW, SetForegroundWindow, TrackPopupMenu, TranslateMessage, HICON, IDI_APPLICATION,
    LR_DEFAULTCOLOR, MF_SEPARATOR, MF_STRING, MSG, TPM_BOTTOMALIGN, TPM_LEFTALIGN, TPM_RETURNCMD,
    WM_LBUTTONDBLCLK, WM_NULL, WM_RBUTTONUP, WNDCLASSW,
};

pub const WM_TRAYICON: u32 = 0x8000 + 100; // WM_APP + 100
const WM_TRAY_CLEANUP_EXIT: u32 = 0x8000 + 101;

pub const IDM_OPEN_DASHBOARD: usize = 1001;
pub const IDM_TOGGLE_BIONIC: usize = 1002;
pub const IDM_STOP_SPEECH: usize = 1003;
pub const IDM_EXIT: usize = 1004;

const TRAY_ICO_BYTES: &[u8] = include_bytes!("../../brand/production/favicon.ico");
static TRAY_HWND_PTR: AtomicIsize = AtomicIsize::new(0);

thread_local! {
    static GLOBAL_TRAY: RefCell<Option<TrayIcon>> = RefCell::new(None);
    static ACTION_CALLBACK: RefCell<Option<Box<dyn Fn(usize)>>> = RefCell::new(None);
}

fn load_embedded_tray_icon() -> HICON {
    // Parse ICO directory and select best 32x32 frame
    if TRAY_ICO_BYTES.len() >= 6 {
        let count = u16::from_le_bytes([TRAY_ICO_BYTES[4], TRAY_ICO_BYTES[5]]) as usize;
        let mut chosen: Option<(usize, usize)> = None;
        for i in 0..count {
            let entry_off = 6 + i * 16;
            if entry_off + 16 > TRAY_ICO_BYTES.len() {
                break;
            }
            let w = TRAY_ICO_BYTES[entry_off];
            let size = u32::from_le_bytes([
                TRAY_ICO_BYTES[entry_off + 8],
                TRAY_ICO_BYTES[entry_off + 9],
                TRAY_ICO_BYTES[entry_off + 10],
                TRAY_ICO_BYTES[entry_off + 11],
            ]) as usize;
            let offset = u32::from_le_bytes([
                TRAY_ICO_BYTES[entry_off + 12],
                TRAY_ICO_BYTES[entry_off + 13],
                TRAY_ICO_BYTES[entry_off + 14],
                TRAY_ICO_BYTES[entry_off + 15],
            ]) as usize;
            if offset + size <= TRAY_ICO_BYTES.len() {
                if w == 32 || chosen.is_none() {
                    chosen = Some((offset, size));
                    if w == 32 {
                        break;
                    }
                }
            }
        }
        if let Some((offset, size)) = chosen {
            unsafe {
                if let Ok(hicon) = CreateIconFromResourceEx(
                    &TRAY_ICO_BYTES[offset..offset + size],
                    true,
                    0x0003_0000,
                    32,
                    32,
                    LR_DEFAULTCOLOR,
                ) {
                    if !hicon.is_invalid() {
                        return hicon;
                    }
                }
            }
        }
    }

    unsafe { LoadIconW(None, IDI_APPLICATION).unwrap_or_default() }
}

pub struct TrayIcon {
    nid: NOTIFYICONDATAW,
}

impl TrayIcon {
    pub fn new(hwnd: HWND) -> Self {
        let mut nid = NOTIFYICONDATAW::default();
        nid.cbSize = size_of::<NOTIFYICONDATAW>() as u32;
        nid.hWnd = hwnd;
        nid.uID = 1;
        nid.uFlags = NIF_ICON | NIF_MESSAGE | NIF_TIP;
        nid.uCallbackMessage = WM_TRAYICON;
        nid.hIcon = load_embedded_tray_icon();

        let tip = "SpeakThat + ADHD Bionic Reader";
        let tip_utf16: Vec<u16> = tip.encode_utf16().chain(std::iter::once(0)).collect();
        for (i, &c) in tip_utf16.iter().enumerate().take(127) {
            nid.szTip[i] = c;
        }

        unsafe {
            let _ = Shell_NotifyIconW(NIM_ADD, &nid);
        }
        info!("System tray icon registered in Windows Notification Area");

        Self { nid }
    }

    pub fn remove(&self) {
        unsafe {
            let _ = Shell_NotifyIconW(NIM_DELETE, &self.nid);
        }
    }

    pub fn show_context_menu(&self, hwnd: HWND) -> Option<usize> {
        unsafe {
            let menu = match CreatePopupMenu() {
                Ok(m) => m,
                Err(_) => return None,
            };

            let _ = AppendMenuW(
                menu,
                MF_STRING,
                IDM_OPEN_DASHBOARD,
                windows::core::w!("Open Dashboard"),
            );
            let _ = AppendMenuW(
                menu,
                MF_STRING,
                IDM_TOGGLE_BIONIC,
                windows::core::w!("Toggle Bionic Reading"),
            );
            let _ = AppendMenuW(
                menu,
                MF_STRING,
                IDM_STOP_SPEECH,
                windows::core::w!("Stop Speaking"),
            );
            let _ = AppendMenuW(menu, MF_SEPARATOR, 0, PCWSTR::null());
            let _ = AppendMenuW(menu, MF_STRING, IDM_EXIT, windows::core::w!("Exit SpeakThat"));

            let mut pt = POINT::default();
            let _ = GetCursorPos(&mut pt);
            let _ = SetForegroundWindow(hwnd);

            let cmd = TrackPopupMenu(
                menu,
                TPM_LEFTALIGN | TPM_BOTTOMALIGN | TPM_RETURNCMD,
                pt.x,
                pt.y,
                0,
                hwnd,
                None,
            );
            let _ = PostMessageW(hwnd, WM_NULL, WPARAM(0), LPARAM(0));
            let _ = DestroyMenu(menu);

            if cmd.0 != 0 {
                Some(cmd.0 as usize)
            } else {
                None
            }
        }
    }
}

impl Drop for TrayIcon {
    fn drop(&mut self) {
        self.remove();
    }
}

unsafe extern "system" fn tray_wnd_proc(
    hwnd: HWND,
    msg: u32,
    wparam: WPARAM,
    lparam: LPARAM,
) -> LRESULT {
    if msg == WM_TRAY_CLEANUP_EXIT {
        GLOBAL_TRAY.with(|cell| {
            *cell.borrow_mut() = None;
        });
        return LRESULT(0);
    }

    if msg == WM_TRAYICON {
        let event = lparam.0 as u32;
        if event == WM_RBUTTONUP {
            let selected = GLOBAL_TRAY.with(|cell| {
                cell.borrow()
                    .as_ref()
                    .and_then(|tray| tray.show_context_menu(hwnd))
            });
            if let Some(action) = selected {
                ACTION_CALLBACK.with(|cb_cell| {
                    if let Some(cb) = cb_cell.borrow().as_ref() {
                        cb(action);
                    }
                });
            }
            return LRESULT(0);
        } else if event == WM_LBUTTONDBLCLK {
            ACTION_CALLBACK.with(|cb_cell| {
                if let Some(cb) = cb_cell.borrow().as_ref() {
                    cb(IDM_OPEN_DASHBOARD);
                }
            });
            return LRESULT(0);
        }
    }

    DefWindowProcW(hwnd, msg, wparam, lparam)
}

pub struct TrayManager;

impl TrayManager {
    pub fn cleanup() {
        let raw = TRAY_HWND_PTR.load(Ordering::SeqCst);
        if raw != 0 {
            unsafe {
                let _ = PostMessageW(
                    HWND(raw as *mut std::ffi::c_void),
                    WM_TRAY_CLEANUP_EXIT,
                    WPARAM(0),
                    LPARAM(0),
                );
            }
        }
    }

    pub fn spawn<F>(on_action: F)
    where
        F: Fn(usize) + Send + 'static,
    {
        std::thread::spawn(move || unsafe {
            let class_name = w!("SpeakThatTrayMsgClass");
            let mut wc = WNDCLASSW::default();
            wc.lpfnWndProc = Some(tray_wnd_proc);
            wc.lpszClassName = class_name;
            let _ = RegisterClassW(&wc);

            let hwnd = CreateWindowExW(
                Default::default(),
                class_name,
                w!("SpeakThatTrayWindow"),
                Default::default(),
                0,
                0,
                0,
                0,
                HWND(std::ptr::null_mut()),
                None,
                None,
                None,
            )
            .unwrap_or_default();

            if !hwnd.is_invalid() {
                TRAY_HWND_PTR.store(hwnd.0 as isize, Ordering::SeqCst);
                let tray = TrayIcon::new(hwnd);
                GLOBAL_TRAY.with(|cell| {
                    *cell.borrow_mut() = Some(tray);
                });
                ACTION_CALLBACK.with(|cell| {
                    *cell.borrow_mut() = Some(Box::new(on_action));
                });

                let mut msg = MSG::default();
                while GetMessageW(&mut msg, None, 0, 0).as_bool() {
                    let _ = TranslateMessage(&msg);
                    DispatchMessageW(&msg);
                }
            }
        });
    }
}
