use std::cell::RefCell;
use std::mem::size_of;
use tracing::info;
use windows::core::{w, PCWSTR};
use windows::Win32::Foundation::{HWND, LPARAM, LRESULT, POINT, WPARAM};
use windows::Win32::UI::Shell::{
    Shell_NotifyIconW, NIF_ICON, NIF_MESSAGE, NIF_TIP, NIM_ADD, NIM_DELETE, NOTIFYICONDATAW,
};
use windows::Win32::UI::WindowsAndMessaging::{
    AppendMenuW, CreatePopupMenu, CreateWindowExW, DefWindowProcW, DestroyMenu, DispatchMessageW,
    GetCursorPos, GetMessageW, LoadIconW, RegisterClassW, SetForegroundWindow, TrackPopupMenu,
    TranslateMessage, IDI_APPLICATION, MF_SEPARATOR, MF_STRING, MSG, TPM_BOTTOMALIGN,
    TPM_LEFTALIGN, WM_LBUTTONDBLCLK, WM_RBUTTONUP, WNDCLASSW,
};

pub const WM_TRAYICON: u32 = 0x8000 + 100; // WM_APP + 100

pub const IDM_OPEN_DASHBOARD: usize = 1001;
pub const IDM_TOGGLE_BIONIC: usize = 1002;
pub const IDM_STOP_SPEECH: usize = 1003;
pub const IDM_EXIT: usize = 1004;

thread_local! {
    static GLOBAL_TRAY: RefCell<Option<TrayIcon>> = RefCell::new(None);
    static ACTION_CALLBACK: RefCell<Option<Box<dyn Fn(usize)>>> = RefCell::new(None);
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

        unsafe {
            nid.hIcon = LoadIconW(None, IDI_APPLICATION).unwrap_or_default();
        }

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

    pub fn show_context_menu(&self, hwnd: HWND) -> Option<usize> {
        unsafe {
            let menu = match CreatePopupMenu() {
                Ok(m) => m,
                Err(_) => return None,
            };

            let _ = AppendMenuW(menu, MF_STRING, IDM_OPEN_DASHBOARD, windows::core::w!("Open Dashboard"));
            let _ = AppendMenuW(menu, MF_STRING, IDM_TOGGLE_BIONIC, windows::core::w!("Toggle Bionic Reading"));
            let _ = AppendMenuW(menu, MF_STRING, IDM_STOP_SPEECH, windows::core::w!("Stop Speaking"));
            let _ = AppendMenuW(menu, MF_SEPARATOR, 0, PCWSTR::null());
            let _ = AppendMenuW(menu, MF_STRING, IDM_EXIT, windows::core::w!("Exit SpeakThat"));

            let mut pt = POINT::default();
            let _ = GetCursorPos(&mut pt);
            let _ = SetForegroundWindow(hwnd);

            let cmd = TrackPopupMenu(
                menu,
                TPM_LEFTALIGN | TPM_BOTTOMALIGN,
                pt.x,
                pt.y,
                0,
                hwnd,
                None,
            );

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
        unsafe {
            let _ = Shell_NotifyIconW(NIM_DELETE, &self.nid);
        }
    }
}

unsafe extern "system" fn tray_wnd_proc(hwnd: HWND, msg: u32, wparam: WPARAM, lparam: LPARAM) -> LRESULT {
    if msg == WM_TRAYICON {
        let event = lparam.0 as u32;
        if event == WM_RBUTTONUP {
            GLOBAL_TRAY.with(|cell| {
                if let Some(tray) = cell.borrow().as_ref() {
                    if let Some(action) = tray.show_context_menu(hwnd) {
                        ACTION_CALLBACK.with(|cb_cell| {
                            if let Some(cb) = cb_cell.borrow().as_ref() {
                                cb(action);
                            }
                        });
                    }
                }
            });
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
