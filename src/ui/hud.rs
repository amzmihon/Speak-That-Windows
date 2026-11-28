use std::sync::atomic::{AtomicIsize, Ordering};
use std::sync::{Arc, OnceLock};
use windows::core::w;
use windows::Win32::Foundation::{COLORREF, HWND, LPARAM, LRESULT, RECT, WPARAM};
use windows::Win32::Graphics::Gdi::{
    BeginPaint, CreateFontW, CreatePen, CreateRoundRectRgn, CreateSolidBrush, DeleteObject,
    DrawTextW, EndPaint, FillRect, InvalidateRect, RoundRect, SelectObject, SetBkMode, SetTextColor,
    SetWindowRgn, CLIP_DEFAULT_PRECIS, DEFAULT_CHARSET, DEFAULT_PITCH, DEFAULT_QUALITY, DT_CENTER,
    DT_END_ELLIPSIS, DT_LEFT, DT_SINGLELINE, DT_VCENTER, FW_BOLD, FW_NORMAL, HBRUSH,
    OUT_DEFAULT_PRECIS, PAINTSTRUCT, PS_SOLID, TRANSPARENT,
};
use windows::Win32::UI::WindowsAndMessaging::{
    CreateWindowExW, DefWindowProcW, DispatchMessageW, GetSystemMetrics, PostMessageW,
    RegisterClassW, SetWindowPos, ShowWindow, TranslateMessage, HWND_TOPMOST, MSG, SM_CXSCREEN,
    SM_CYSCREEN, SWP_NOACTIVATE, SWP_NOMOVE, SWP_NOSIZE, SWP_SHOWWINDOW, SW_HIDE, WNDCLASSW,
    WM_LBUTTONUP, WM_PAINT, WS_EX_NOACTIVATE, WS_EX_TOOLWINDOW, WS_EX_TOPMOST, WS_POPUP,
};

use crate::audio::{PlaybackState, TtsEngine};

const HUD_W: i32 = 304;
const HUD_H: i32 = 46;
const WM_HUD_SHOW: u32 = 0x8000 + 201;
const WM_HUD_HIDE: u32 = 0x8000 + 202;
const WM_HUD_REFRESH: u32 = 0x8000 + 203;

static HUD_HWND: AtomicIsize = AtomicIsize::new(0);
static HUD_TTS: OnceLock<Arc<TtsEngine>> = OnceLock::new();

pub struct FloatingPillHud;

impl FloatingPillHud {
    /// Spawns the lightweight Win32 non-activating topmost pill HUD on its own message thread.
    pub fn spawn(tts: Arc<TtsEngine>) {
        let _ = HUD_TTS.set(tts);
        std::thread::spawn(|| unsafe {
            let class_name = w!("SpeakThatFloatingHudClass");
            let mut wc = WNDCLASSW::default();
            wc.lpfnWndProc = Some(hud_wnd_proc);
            wc.lpszClassName = class_name;
            let _ = RegisterClassW(&wc);

            let hwnd = CreateWindowExW(
                WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE,
                class_name,
                w!("SpeakThat Controls"),
                WS_POPUP,
                100,
                100,
                HUD_W,
                HUD_H,
                HWND(std::ptr::null_mut()),
                None,
                None,
                None,
            )
            .unwrap_or_default();

            if !hwnd.is_invalid() {
                let rgn = CreateRoundRectRgn(0, 0, HUD_W, HUD_H, 22, 22);
                let _ = SetWindowRgn(hwnd, rgn, true);
                HUD_HWND.store(hwnd.0 as isize, Ordering::SeqCst);

                let mut msg = MSG::default();
                while windows::Win32::UI::WindowsAndMessaging::GetMessageW(&mut msg, None, 0, 0)
                    .as_bool()
                {
                    let _ = TranslateMessage(&msg);
                    DispatchMessageW(&msg);
                }
            }
        });
    }

    /// Shows the pill beside screen coordinates `(cursor_x, cursor_y)` without stealing focus.
    pub fn show_at(cursor_x: i32, cursor_y: i32) {
        let raw = HUD_HWND.load(Ordering::SeqCst);
        if raw == 0 {
            return;
        }
        unsafe {
            let scr_w = GetSystemMetrics(SM_CXSCREEN).max(640);
            let scr_h = GetSystemMetrics(SM_CYSCREEN).max(480);
            let x = (cursor_x + 16).clamp(12, scr_w - HUD_W - 12);
            let y = (cursor_y + 20).clamp(12, scr_h - HUD_H - 56);
            let packed = ((y as u32) << 16) | ((x as u32) & 0xFFFF);
            let _ = PostMessageW(
                HWND(raw as *mut std::ffi::c_void),
                WM_HUD_SHOW,
                WPARAM(packed as usize),
                LPARAM(0),
            );
        }
    }

    pub fn refresh() {
        let raw = HUD_HWND.load(Ordering::SeqCst);
        if raw != 0 {
            unsafe {
                let _ = PostMessageW(
                    HWND(raw as *mut std::ffi::c_void),
                    WM_HUD_REFRESH,
                    WPARAM(0),
                    LPARAM(0),
                );
            }
        }
    }

    pub fn hide() {
        let raw = HUD_HWND.load(Ordering::SeqCst);
        if raw != 0 {
            unsafe {
                let _ = PostMessageW(
                    HWND(raw as *mut std::ffi::c_void),
                    WM_HUD_HIDE,
                    WPARAM(0),
                    LPARAM(0),
                );
            }
        }
    }
}

unsafe fn draw_hud(hwnd: HWND) {
    let mut ps = PAINTSTRUCT::default();
    let hdc = BeginPaint(hwnd, &mut ps);
    if hdc.is_invalid() {
        return;
    }

    // Background pill fill (#18181E)
    let bg_rect = RECT {
        left: 0,
        top: 0,
        right: HUD_W,
        bottom: HUD_H,
    };
    let bg_brush = CreateSolidBrush(COLORREF(0x001E_1818));
    FillRect(hdc, &bg_rect, bg_brush);
    let _ = DeleteObject(bg_brush);

    // Rounded border frame
    let border_pen = CreatePen(PS_SOLID, 1, COLORREF(0x006E_524E));
    let old_pen = SelectObject(hdc, border_pen);
    let inner_brush = CreateSolidBrush(COLORREF(0x001E_1818));
    let old_brush = SelectObject(hdc, inner_brush);
    let _ = RoundRect(hdc, 0, 0, HUD_W - 1, HUD_H - 1, 22, 22);
    SelectObject(hdc, old_brush);
    SelectObject(hdc, old_pen);
    let _ = DeleteObject(border_pen);
    let _ = DeleteObject(inner_brush);

    let _ = SetBkMode(hdc, TRANSPARENT);

    let font_regular = CreateFontW(
        15,
        0,
        0,
        0,
        FW_NORMAL.0 as i32,
        0,
        0,
        0,
        DEFAULT_CHARSET.0 as u32,
        OUT_DEFAULT_PRECIS.0 as u32,
        CLIP_DEFAULT_PRECIS.0 as u32,
        DEFAULT_QUALITY.0 as u32,
        DEFAULT_PITCH.0 as u32,
        w!("Segoe UI Symbol"),
    );
    let font_bold = CreateFontW(
        15,
        0,
        0,
        0,
        FW_BOLD.0 as i32,
        0,
        0,
        0,
        DEFAULT_CHARSET.0 as u32,
        OUT_DEFAULT_PRECIS.0 as u32,
        CLIP_DEFAULT_PRECIS.0 as u32,
        DEFAULT_QUALITY.0 as u32,
        DEFAULT_PITCH.0 as u32,
        w!("Segoe UI"),
    );

    // Play/Pause button pill (x: 8..42, y: 8..38)
    let pp_brush = CreateSolidBrush(COLORREF(0x003D_3330));
    let pp_pen = CreatePen(PS_SOLID, 1, COLORREF(0x0068_5850));
    let p_old = SelectObject(hdc, pp_pen);
    let b_old = SelectObject(hdc, pp_brush);
    let _ = RoundRect(hdc, 8, 8, 42, 38, 12, 12);
    SelectObject(hdc, b_old);
    SelectObject(hdc, p_old);
    let _ = DeleteObject(pp_brush);
    let _ = DeleteObject(pp_pen);

    let is_playing = HUD_TTS
        .get()
        .map(|t| t.playback_state() == PlaybackState::Playing)
        .unwrap_or(true);
    let pp_label = if is_playing { "||" } else { ">" };
    let mut pp_utf16: Vec<u16> = pp_label.encode_utf16().collect();
    let f_old = SelectObject(hdc, font_bold);
    SetTextColor(hdc, COLORREF(0x00FF_FFFF));
    let mut pp_rect = RECT {
        left: 8,
        top: 8,
        right: 42,
        bottom: 38,
    };
    DrawTextW(
        hdc,
        &mut pp_utf16,
        &mut pp_rect,
        DT_CENTER | DT_VCENTER | DT_SINGLELINE,
    );

    // Clear Red Stop button pill (x: 48..116, y: 8..38) -> RGB(214, 54, 56) = 0x003836D6
    let stop_brush = CreateSolidBrush(COLORREF(0x0038_36D6));
    let stop_pen = CreatePen(PS_SOLID, 1, COLORREF(0x0046_44EA));
    let p2_old = SelectObject(hdc, stop_pen);
    let b2_old = SelectObject(hdc, stop_brush);
    let _ = RoundRect(hdc, 48, 8, 116, 38, 12, 12);
    SelectObject(hdc, b2_old);
    SelectObject(hdc, p2_old);
    let _ = DeleteObject(stop_brush);
    let _ = DeleteObject(stop_pen);

    let mut stop_utf16: Vec<u16> = "Stop".encode_utf16().collect();
    let mut stop_rect = RECT {
        left: 48,
        top: 8,
        right: 116,
        bottom: 38,
    };
    DrawTextW(
        hdc,
        &mut stop_utf16,
        &mut stop_rect,
        DT_CENTER | DT_VCENTER | DT_SINGLELINE,
    );

    // Live sentence preview (x: 124..294)
    SelectObject(hdc, font_regular);
    SetTextColor(hdc, COLORREF(0x00EA_E2DE));
    let sentence = HUD_TTS
        .get()
        .map(|t| t.current_sentence())
        .unwrap_or_default();
    let display = if sentence.trim().is_empty() {
        "Speaking...".to_string()
    } else {
        sentence.trim().to_string()
    };
    let mut txt_utf16: Vec<u16> = display.encode_utf16().collect();
    let mut txt_rect = RECT {
        left: 124,
        top: 8,
        right: HUD_W - 10,
        bottom: HUD_H - 8,
    };
    DrawTextW(
        hdc,
        &mut txt_utf16,
        &mut txt_rect,
        DT_LEFT | DT_VCENTER | DT_SINGLELINE | DT_END_ELLIPSIS,
    );

    SelectObject(hdc, f_old);
    let _ = DeleteObject(font_regular);
    let _ = DeleteObject(font_bold);
    let _ = EndPaint(hwnd, &ps);
}

unsafe extern "system" fn hud_wnd_proc(
    hwnd: HWND,
    msg: u32,
    wparam: WPARAM,
    lparam: LPARAM,
) -> LRESULT {
    match msg {
        WM_HUD_SHOW => {
            let x = (wparam.0 & 0xFFFF) as i16 as i32;
            let y = ((wparam.0 >> 16) & 0xFFFF) as i16 as i32;
            let _ = SetWindowPos(
                hwnd,
                HWND_TOPMOST,
                x,
                y,
                HUD_W,
                HUD_H,
                SWP_NOACTIVATE | SWP_SHOWWINDOW,
            );
            let _ = InvalidateRect(hwnd, None, true);
            LRESULT(0)
        }
        WM_HUD_HIDE => {
            let _ = ShowWindow(hwnd, SW_HIDE);
            LRESULT(0)
        }
        WM_HUD_REFRESH => {
            let _ = SetWindowPos(
                hwnd,
                HWND_TOPMOST,
                0,
                0,
                0,
                0,
                SWP_NOACTIVATE | SWP_NOMOVE | SWP_NOSIZE,
            );
            let _ = InvalidateRect(hwnd, None, true);
            LRESULT(0)
        }
        WM_PAINT => {
            draw_hud(hwnd);
            LRESULT(0)
        }
        WM_LBUTTONUP => {
            let click_x = (lparam.0 & 0xFFFF) as i16 as i32;
            if let Some(tts) = HUD_TTS.get() {
                if (8..=44).contains(&click_x) {
                    tts.toggle_pause();
                } else if (46..=118).contains(&click_x) {
                    tts.stop();
                }
            }
            LRESULT(0)
        }
        _ => DefWindowProcW(hwnd, msg, wparam, lparam),
    }
}
