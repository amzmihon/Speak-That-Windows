#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::fs::OpenOptions;
use std::io::Write;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex, RwLock};
use std::time::Duration;
use tokio::sync::mpsc;
use tracing::{info, warn};
use tracing_subscriber::fmt::writer::MakeWriter;
use windows::core::w;
use windows::Win32::UI::WindowsAndMessaging::{
    FindWindowW, SetForegroundWindow, ShowWindow, SW_RESTORE, SW_SHOW,
};

mod audio;
mod bionic;
mod clipboard;
mod config;
mod downloader;
mod input;
mod ui;

use audio::{MicrophoneManager, SttEngine, TtsEngine};
use bionic::BionicEngine;
use clipboard::SelectionCapture;
use config::{ActionBinding, AppConfig, ShortcutConfig};
use downloader::ModelDownloader;
use input::{HookEvent, InputHookManager, ShortcutCatalog, TextInjector};
use ui::BrowserDetector;

#[derive(Clone)]
struct SharedLogFile(Arc<Mutex<std::fs::File>>);

struct LogFileGuard(Arc<Mutex<std::fs::File>>);

impl Write for LogFileGuard {
    fn write(&mut self, buf: &[u8]) -> std::io::Result<usize> {
        if let Ok(mut f) = self.0.lock() {
            f.write(buf)
        } else {
            Ok(buf.len())
        }
    }

    fn flush(&mut self) -> std::io::Result<()> {
        if let Ok(mut f) = self.0.lock() {
            f.flush()
        } else {
            Ok(())
        }
    }
}

impl<'a> MakeWriter<'a> for SharedLogFile {
    type Writer = LogFileGuard;

    fn make_writer(&'a self) -> Self::Writer {
        LogFileGuard(Arc::clone(&self.0))
    }
}

fn init_logging() {
    if cfg!(debug_assertions) {
        tracing_subscriber::fmt()
            .with_env_filter("info,speakthat=debug")
            .init();
    } else {
        let log_path = dirs::data_local_dir()
            .unwrap_or_else(|| std::path::PathBuf::from("."))
            .join("SpeakThat")
            .join("speakthat.log");
        if let Some(parent) = log_path.parent() {
            let _ = std::fs::create_dir_all(parent);
        }
        if let Ok(file) = OpenOptions::new()
            .create(true)
            .write(true)
            .truncate(true)
            .open(&log_path)
        {
            let writer = SharedLogFile(Arc::new(Mutex::new(file)));
            tracing_subscriber::fmt()
                .with_ansi(false)
                .with_env_filter("info,speakthat=info")
                .with_writer(writer)
                .init();
        } else {
            tracing_subscriber::fmt()
                .with_ansi(false)
                .with_env_filter("info,speakthat=info")
                .init();
        }
    }
}

fn load_app_icon() -> Option<eframe::egui::IconData> {
    eframe::icon_data::from_png_bytes(include_bytes!(
        "../brand/production/speakthat-symbol-app-icon-64.png"
    ))
    .ok()
}

fn format_binding_log(binding: &ActionBinding) -> String {
    match &binding.mouse {
        Some(m) => format!("Keyboard: [{}] | Mouse: [{}]", binding.keyboard, m),
        None => format!("Keyboard: [{}] | Mouse: [None]", binding.keyboard),
    }
}

struct InFlightReset(Arc<AtomicBool>);

impl Drop for InFlightReset {
    fn drop(&mut self) {
        self.0.store(false, Ordering::SeqCst);
    }
}

fn trigger_speak_selection(tts: Arc<TtsEngine>, in_flight: Arc<AtomicBool>) {
    if in_flight.swap(true, Ordering::SeqCst) {
        tracing::debug!("Speak Selection capture already in flight; debouncing duplicate trigger.");
        return;
    }

    tokio::spawn(async move {
        let _reset = InFlightReset(in_flight);
        match SelectionCapture::capture_selected_text_synthetic(Duration::from_millis(300)).await {
            Ok(text) => {
                info!("Captured selected text: {} chars", text.len());
                tts.speak(&text);
            }
            Err(e) => {
                warn!("Could not capture selection: {}", e);
            }
        }
    });
}

fn trigger_bionic_transform(engine: Arc<BionicEngine>) {
    tokio::spawn(async move {
        match SelectionCapture::capture_selected_text_synthetic(Duration::from_millis(300)).await {
            Ok(text) => {
                let bionic_text = engine.to_unicode_bionic(&text);
                info!(
                    "Transformed {} chars to native Bionic Unicode format",
                    bionic_text.len()
                );
                if let Err(e) = TextInjector::inject_text(&bionic_text) {
                    warn!("Failed to inject bionic text: {}", e);
                }
            }
            Err(e) => {
                warn!("Could not capture selection for Bionic reading: {}", e);
            }
        }
    });
}

fn trigger_reader_view(
    reader_request: Arc<Mutex<Option<String>>>,
    show_req: Arc<AtomicBool>,
    shared_ctx: Arc<RwLock<Option<eframe::egui::Context>>>,
) {
    tokio::spawn(async move {
        let text = match SelectionCapture::capture_selected_text_synthetic(Duration::from_millis(300)).await {
            Ok(t) if !t.trim().is_empty() => t,
            _ => "Highlight any text in any Windows app and press Alt+R to open it here in clean, distraction-free reader mode.\n\nYou can switch themes (Dark, OLED Black, Sepia, Light), scale font size, toggle Bionic reading, or listen aloud with neural speech.".to_string(),
        };

        if let Ok(mut guard) = reader_request.lock() {
            *guard = Some(text);
        }
        request_show_dashboard(&show_req, &shared_ctx);
    });
}

fn request_show_dashboard(
    show_req: &Arc<AtomicBool>,
    shared_ctx: &Arc<RwLock<Option<eframe::egui::Context>>>,
) {
    show_req.store(true, Ordering::SeqCst);
    unsafe {
        if let Ok(hwnd) = FindWindowW(None, w!("SpeakThat Settings Dashboard")) {
            if !hwnd.is_invalid() {
                let _ = ShowWindow(hwnd, SW_SHOW);
                let _ = ShowWindow(hwnd, SW_RESTORE);
                let _ = SetForegroundWindow(hwnd);
            }
        }
    }
    if let Ok(guard) = shared_ctx.read() {
        if let Some(ref c) = *guard {
            c.request_repaint();
        }
    }
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // 1. Initialize logging (console in debug builds, %LOCALAPPDATA%\SpeakThat\speakthat.log in release)
    init_logging();

    info!("=== SpeakThat + ADHD Bionic Reader Suite v0.2.1 ===");
    info!("Starting native Windows client in pure Rust...");

    // 2. Load Configuration
    let config = AppConfig::load();
    info!("Configuration loaded from: {:?}", AppConfig::config_path());
    info!("Shortcuts bound (Keyboard + Mouse active simultaneously):");
    info!("  - Speak Selection: {}", format_binding_log(&config.shortcuts.speak_selection));
    info!("  - Stop Speaking (TTS): {}", format_binding_log(&config.shortcuts.stop_speaking));
    info!("  - Push-to-Talk (STT): {}", format_binding_log(&config.shortcuts.push_to_talk));
    info!("  - Open Home Dashboard: {}", format_binding_log(&config.shortcuts.open_home));
    info!("  - Toggle Bionic Reading: {}", format_binding_log(&config.shortcuts.toggle_bionic));
    info!("  - Toggle Reader View: {}", format_binding_log(&config.shortcuts.toggle_reader));

    // 3. Validate Shortcuts
    let checks = [
        ("Speak Selection", &config.shortcuts.speak_selection, false),
        ("Stop Speaking", &config.shortcuts.stop_speaking, false),
        ("Push-to-Talk", &config.shortcuts.push_to_talk, false),
        ("Open Home", &config.shortcuts.open_home, true),
        ("Toggle Bionic", &config.shortcuts.toggle_bionic, false),
        ("Toggle Reader", &config.shortcuts.toggle_reader, false),
    ];

    for (name, binding, allow_single) in checks {
        match ShortcutCatalog::validate_for(&binding.keyboard, allow_single) {
            input::CollisionSeverity::Allowed => {
                info!("  ✓ Shortcut [{}] validated: OK", name);
            }
            input::CollisionSeverity::Warning(msg) => {
                warn!("  Warning [{}]: {}", name, msg);
            }
            input::CollisionSeverity::HardBlocked(msg) => {
                warn!("  Blocked [{}]: {}", name, msg);
            }
        }
    }

    // 4. Multi-Browser Detection Manager
    let browsers = BrowserDetector::detect_all();
    info!("Detected {} installed browser(s):", browsers.len());
    for b in &browsers {
        info!("  - {} (Path: {:?})", b.name, b.executable_path);
        info!("    Extension Path: {}", b.extension_folder.display());
        info!("    Install helper: {}", b.install_url);
    }

    // 5. Build Tokio runtime for background workers
    let rt = tokio::runtime::Builder::new_multi_thread()
        .enable_all()
        .build()?;
    let _guard = rt.enter();

    // 6. Initialize Audio & Bionic Engines
    let stt_installed = ModelDownloader::is_model_installed();
    info!(
        "Speech-to-Text (Parakeet-TDT 0.6B) Model Status: {}",
        if stt_installed {
            "Installed"
        } else {
            "Not Installed (On-Demand in-app download available)"
        }
    );

    let (tts_engine, _tts_rx) = TtsEngine::new();
    tts_engine.set_voice(&config.tts.voice_id);
    tts_engine.set_speed(config.tts.speed);
    tts_engine.set_volume(config.tts.volume);
    let (mic_manager, _ptt_rx, _duck_rx) = MicrophoneManager::new();
    let model_path = dirs::data_local_dir()
        .unwrap_or_else(|| std::path::PathBuf::from("."))
        .join("SpeakThat")
        .join("models")
        .join("parakeet-tdt-0.6b-v3.onnx");
    let (stt_engine, _stt_rx) = SttEngine::new(model_path);
    let bionic_engine = BionicEngine::new(config.bionic.fixation_ratio);

    let tts_engine = Arc::new(tts_engine);
    ui::FloatingPillHud::spawn(Arc::clone(&tts_engine));
    let mic_manager = Arc::new(mic_manager);
    let _stt_engine = Arc::new(stt_engine);
    let bionic_engine = Arc::new(bionic_engine);

    // Shared UI / hook orchestration handles
    let shared_shortcuts: Arc<RwLock<ShortcutConfig>> =
        Arc::new(RwLock::new(config.shortcuts.clone()));
    let shared_ctx: Arc<RwLock<Option<eframe::egui::Context>>> = Arc::new(RwLock::new(None));
    let show_dashboard_req = Arc::new(AtomicBool::new(false));
    let quit_requested = Arc::new(AtomicBool::new(false));
    let reader_request: Arc<Mutex<Option<String>>> = Arc::new(Mutex::new(None));

    // 7. Initialize Low-Level Input Hooks & Mouse Bitmask
    InputHookManager::update_bound_mouse_mask(config.shortcuts.bound_mouse_mask());
    let (event_tx, mut event_rx) = mpsc::unbounded_channel::<HookEvent>();
    let hook_mgr = Arc::new(InputHookManager::new(event_tx));
    let _hook_handle = hook_mgr.start_listening();
    info!("Low-level Windows keyboard and mouse hooks initialized.");

    // 8. Spawn background event receiver loop in Tokio
    let loop_shortcuts = Arc::clone(&shared_shortcuts);
    let loop_tts = Arc::clone(&tts_engine);
    let loop_bionic = Arc::clone(&bionic_engine);
    let loop_mic = Arc::clone(&mic_manager);
    let loop_ctx = Arc::clone(&shared_ctx);
    let loop_show_req = Arc::clone(&show_dashboard_req);
    let loop_reader_req = Arc::clone(&reader_request);
    let ptt_active = Arc::new(AtomicBool::new(false));
    let speak_in_flight = Arc::new(AtomicBool::new(false));

    rt.spawn(async move {
        while let Some(event) = event_rx.recv().await {
            let shortcuts = loop_shortcuts.read().unwrap().clone();

            match event {
                HookEvent::ChordTriggered(chord) => {
                    tracing::trace!("Key chord event received: {}", chord);

                    if shortcuts.speak_selection.matches_keyboard(&chord) {
                        info!("🔥 [HOTKEY MATCHED] Speak Selection (Keyboard): {}", chord);
                        trigger_speak_selection(
                            Arc::clone(&loop_tts),
                            Arc::clone(&speak_in_flight),
                        );
                    } else if shortcuts.stop_speaking.matches_keyboard(&chord) {
                        info!("🔥 [HOTKEY MATCHED] Stop Speaking: {}", chord);
                        loop_tts.stop();
                    } else if shortcuts.toggle_bionic.matches_keyboard(&chord) {
                        info!(
                            "🔥 [HOTKEY MATCHED] Native Bionic In-Place Transformation (Keyboard): {}",
                            chord
                        );
                        trigger_bionic_transform(Arc::clone(&loop_bionic));
                    } else if shortcuts.open_home.matches_keyboard(&chord) {
                        info!("🔥 [HOTKEY MATCHED] Open Home Dashboard (Keyboard): {}", chord);
                        request_show_dashboard(&loop_show_req, &loop_ctx);
                    } else if shortcuts.toggle_reader.matches_keyboard(&chord) {
                        info!("🔥 [HOTKEY MATCHED] Native Reader View (Keyboard): {}", chord);
                        trigger_reader_view(
                            Arc::clone(&loop_reader_req),
                            Arc::clone(&loop_show_req),
                            Arc::clone(&loop_ctx),
                        );
                    } else if shortcuts.push_to_talk.matches_keyboard(&chord) {
                        let was_active = ptt_active.fetch_xor(true, Ordering::SeqCst);
                        if !was_active {
                            info!(
                                "🔥 [HOTKEY MATCHED] Push-to-Talk Dictation (Keyboard Start): {}",
                                chord
                            );
                            loop_mic.on_ptt_press();
                        } else {
                            info!(
                                "🔥 [HOTKEY MATCHED] Push-to-Talk Dictation (Keyboard Stop): {}",
                                chord
                            );
                            loop_mic.on_ptt_release();
                        }
                    }
                }
                HookEvent::MouseButtonDown(btn) => {
                    tracing::debug!("Mouse button {} pressed", btn);
                }
                HookEvent::MouseButtonUp(btn, duration) => {
                    let dur_ms = duration.as_millis() as u64;
                    tracing::debug!("Mouse button {} released after {}ms", btn, dur_ms);

                    if shortcuts.speak_selection.matches_mouse(btn) {
                        let threshold = shortcuts.speak_selection.mouse_hold_ms();
                        if dur_ms >= threshold {
                            if loop_tts.is_playing() {
                                info!(
                                    "🔥 [HOTKEY MATCHED] Speak Selection (Mouse Button {}): Stopping active TTS playback",
                                    btn
                                );
                                loop_tts.stop();
                            } else {
                                info!(
                                    "🔥 [HOTKEY MATCHED] Speak Selection (Mouse Button {}, {}ms >= {}ms): Start Speaking",
                                    btn, dur_ms, threshold
                                );
                                trigger_speak_selection(
                                    Arc::clone(&loop_tts),
                                    Arc::clone(&speak_in_flight),
                                );
                            }
                        }
                    } else if shortcuts.push_to_talk.matches_mouse(btn) {
                        let threshold = shortcuts.push_to_talk.mouse_hold_ms();
                        if dur_ms >= threshold {
                            let was_active = ptt_active.fetch_xor(true, Ordering::SeqCst);
                            if !was_active {
                                info!(
                                    "🔥 [HOTKEY MATCHED] Push-to-Talk Dictation (Mouse Button {}): Start Listening",
                                    btn
                                );
                                loop_mic.on_ptt_press();
                            } else {
                                info!(
                                    "🔥 [HOTKEY MATCHED] Push-to-Talk Dictation (Mouse Button {}): Stop Listening",
                                    btn
                                );
                                loop_mic.on_ptt_release();
                            }
                        }
                    } else if shortcuts.stop_speaking.matches_mouse(btn) {
                        let threshold = shortcuts.stop_speaking.mouse_hold_ms();
                        if dur_ms >= threshold {
                            info!(
                                "🔥 [HOTKEY MATCHED] Stop Speaking: Mouse Button {} ({}ms >= {}ms)",
                                btn, dur_ms, threshold
                            );
                            loop_tts.stop();
                        }
                    } else if shortcuts.toggle_bionic.matches_mouse(btn) {
                        let threshold = shortcuts.toggle_bionic.mouse_hold_ms();
                        if dur_ms >= threshold {
                            info!(
                                "🔥 [HOTKEY MATCHED] Toggle Bionic Reading (Mouse Button {}, {}ms)",
                                btn, dur_ms
                            );
                            trigger_bionic_transform(Arc::clone(&loop_bionic));
                        }
                    } else if shortcuts.open_home.matches_mouse(btn) {
                        let threshold = shortcuts.open_home.mouse_hold_ms();
                        if dur_ms >= threshold {
                            info!(
                                "🔥 [HOTKEY MATCHED] Open Home Dashboard (Mouse Button {}, {}ms)",
                                btn, dur_ms
                            );
                            request_show_dashboard(&loop_show_req, &loop_ctx);
                        }
                    } else if shortcuts.toggle_reader.matches_mouse(btn) {
                        let threshold = shortcuts.toggle_reader.mouse_hold_ms();
                        if dur_ms >= threshold {
                            info!(
                                "🔥 [HOTKEY MATCHED] Native Reader View (Mouse Button {}, {}ms)",
                                btn, dur_ms
                            );
                            trigger_reader_view(
                                Arc::clone(&loop_reader_req),
                                Arc::clone(&loop_show_req),
                                Arc::clone(&loop_ctx),
                            );
                        }
                    }
                }
            }
        }
    });

    // 9. Initialize Windows System Tray Icon
    let tray_tts = Arc::clone(&tts_engine);
    let tray_bionic = Arc::clone(&bionic_engine);
    let tray_rt = rt.handle().clone();
    let tray_ctx = Arc::clone(&shared_ctx);
    let tray_show_req = Arc::clone(&show_dashboard_req);
    let tray_quit_req = Arc::clone(&quit_requested);
    ui::TrayManager::spawn(move |action| match action {
        ui::IDM_OPEN_DASHBOARD => {
            info!("Tray action: Open Dashboard");
            request_show_dashboard(&tray_show_req, &tray_ctx);
        }
        ui::IDM_TOGGLE_BIONIC => {
            info!("Tray action: Toggle Bionic Reading");
            let engine = Arc::clone(&tray_bionic);
            tray_rt.spawn(async move {
                match SelectionCapture::capture_selected_text_synthetic(Duration::from_millis(300)).await {
                    Ok(text) => {
                        let bionic_text = engine.to_unicode_bionic(&text);
                        let _ = TextInjector::inject_text(&bionic_text);
                    }
                    Err(e) => warn!("Tray bionic capture skipped: {e}"),
                }
            });
        }
        ui::IDM_STOP_SPEECH => {
            info!("Tray action: Stop Speaking");
            tray_tts.stop();
        }
        ui::IDM_EXIT => {
            info!("Tray action: Exit SpeakThat");
            tray_tts.stop();
            ui::TrayManager::cleanup();
            tray_quit_req.store(true, Ordering::SeqCst);
            if let Ok(guard) = tray_ctx.read() {
                if let Some(ref c) = *guard {
                    c.request_repaint();
                }
            }
        }
        _ => {}
    });

    info!("Application background services initialized. Launching egui Settings Dashboard on main thread...");

    // 10. Run egui Dashboard on the Main Thread with Custom Brand Icon
    let app_icon = load_app_icon().map(Arc::new);
    let mut viewport = eframe::egui::ViewportBuilder::default()
        .with_inner_size([860.0, 560.0])
        .with_min_inner_size([740.0, 460.0]);
    if let Some(ref icon) = app_icon {
        viewport = viewport.with_icon(Arc::clone(icon));
        info!("Loaded custom SpeakThat brand icon for native window.");
    } else {
        warn!("Could not decode custom brand icon PNG; using default window icon.");
    }

    let native_options = eframe::NativeOptions {
        viewport,
        ..Default::default()
    };

    let gui_config = config.clone();
    let gui_shortcuts = Arc::clone(&shared_shortcuts);
    let gui_ctx = Arc::clone(&shared_ctx);
    let gui_show_req = Arc::clone(&show_dashboard_req);
    let gui_quit_req = Arc::clone(&quit_requested);
    let gui_reader_req = Arc::clone(&reader_request);
    let gui_tts = Arc::clone(&tts_engine);
    let gui_icon = app_icon;

    eframe::run_native(
        "SpeakThat Settings Dashboard",
        native_options,
        Box::new(move |cc| {
            Box::new(ui::SettingsDashboard::new(
                cc,
                gui_config,
                gui_shortcuts,
                gui_ctx,
                gui_show_req,
                gui_quit_req,
                gui_reader_req,
                gui_tts,
                gui_icon,
            ))
        }),
    )
    .map_err(|e| Box::new(e) as Box<dyn std::error::Error>)?;

    ui::TrayManager::cleanup();
    Ok(())
}
