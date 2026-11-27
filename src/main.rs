use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, RwLock};
use std::time::Duration;
use tokio::sync::mpsc;
use tracing::{info, warn};

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

fn trigger_speak_selection(tts: Arc<TtsEngine>) {
    tokio::spawn(async move {
        match SelectionCapture::capture_selected_text_synthetic(Duration::from_millis(150)).await {
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
        match SelectionCapture::capture_selected_text_synthetic(Duration::from_millis(150)).await {
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

fn trigger_reader_view(tts: Arc<TtsEngine>, ratio: f32) {
    tokio::spawn(async move {
        let text = match SelectionCapture::capture_selected_text_synthetic(Duration::from_millis(150)).await {
            Ok(t) if !t.trim().is_empty() => t,
            _ => "Highlight any text in any Windows app and press Alt+R to open it here in clean, distraction-free reader mode.\n\nYou can switch themes (Dark, OLED Black, Sepia, Light), scale font size, toggle Bionic reading, or listen aloud with neural speech.".to_string(),
        };

        std::thread::spawn(move || {
            let mut viewport = eframe::egui::ViewportBuilder::default()
                .with_inner_size([800.0, 600.0])
                .with_min_inner_size([500.0, 400.0]);
            if let Some(icon) = load_app_icon() {
                viewport = viewport.with_icon(Arc::new(icon));
            }
            let native_options = eframe::NativeOptions {
                viewport,
                ..Default::default()
            };
            let _ = eframe::run_native(
                "SpeakThat Native Reader View",
                native_options,
                Box::new(move |cc| {
                    ui::dashboard::configure_windows_fonts(&cc.egui_ctx);
                    Box::new(ui::ReaderViewWindow::new(text, tts, ratio))
                }),
            );
        });
    });
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // 1. Initialize logging
    tracing_subscriber::fmt()
        .with_env_filter("info,speakthat=debug")
        .init();

    info!("=== SpeakThat + ADHD Bionic Reader Suite v0.2.0 ===");
    info!("Starting native Windows client in Rust...");

    // 2. Load Configuration
    let config = AppConfig::load();
    info!("Configuration loaded from: {:?}", AppConfig::config_path());
    info!("Shortcuts bound (Keyboard + Mouse active simultaneously):");
    info!("  - Speak Selection: {}", format_binding_log(&config.shortcuts.speak_selection));
    info!("  - Push-to-Talk (STT): {}", format_binding_log(&config.shortcuts.push_to_talk));
    info!("  - Open Home Dashboard: {}", format_binding_log(&config.shortcuts.open_home));
    info!("  - Toggle Bionic Reading: {}", format_binding_log(&config.shortcuts.toggle_bionic));
    info!("  - Toggle Reader View: {}", format_binding_log(&config.shortcuts.toggle_reader));

    // 3. Validate Shortcuts via Exact-Match Shortcut Collision Protection
    let checks = [
        ("Speak Selection", &config.shortcuts.speak_selection, false),
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
        info!("    Extension Path: {:?}", b.extension_folder);
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
    let (mic_manager, _ptt_rx, _duck_rx) = MicrophoneManager::new();
    let model_path = dirs::data_local_dir()
        .unwrap_or_else(|| std::path::PathBuf::from("."))
        .join("SpeakThat")
        .join("models")
        .join("parakeet-tdt-0.6b-v3.onnx");
    let (stt_engine, _stt_rx) = SttEngine::new(model_path);
    let bionic_engine = BionicEngine::new(config.bionic.fixation_ratio);

    let tts_engine = Arc::new(tts_engine);
    let mic_manager = Arc::new(mic_manager);
    let _stt_engine = Arc::new(stt_engine);
    let bionic_engine = Arc::new(bionic_engine);

    // Shared hot-reloadable shortcut configuration
    let shared_shortcuts: Arc<RwLock<ShortcutConfig>> =
        Arc::new(RwLock::new(config.shortcuts.clone()));

    // 7. Initialize Low-Level Input Hooks & Mouse Bitmask
    InputHookManager::update_bound_mouse_mask(config.shortcuts.bound_mouse_mask());
    let (event_tx, mut event_rx) = mpsc::unbounded_channel::<HookEvent>();
    let hook_mgr = Arc::new(InputHookManager::new(event_tx));
    let _hook_handle = hook_mgr.start_listening();
    info!("Low-level Windows keyboard and mouse hooks initialized.");

    // 8. Spawn background event receiver loop in Tokio (hot-reloads shared_shortcuts)
    let loop_shortcuts = Arc::clone(&shared_shortcuts);
    let loop_tts = Arc::clone(&tts_engine);
    let loop_bionic = Arc::clone(&bionic_engine);
    let loop_mic = Arc::clone(&mic_manager);
    let loop_ratio = config.bionic.fixation_ratio;
    let ptt_kb_active = Arc::new(AtomicBool::new(false));

    rt.spawn(async move {
        while let Some(event) = event_rx.recv().await {
            let shortcuts = loop_shortcuts.read().unwrap().clone();

            match event {
                HookEvent::ChordTriggered(chord) => {
                    info!("Hook event received key chord: {}", chord);

                    if shortcuts.speak_selection.matches_keyboard(&chord) {
                        info!("🔥 [HOTKEY MATCHED] Speak Selection (Keyboard): {}", chord);
                        trigger_speak_selection(Arc::clone(&loop_tts));
                    } else if shortcuts.toggle_bionic.matches_keyboard(&chord) {
                        info!(
                            "🔥 [HOTKEY MATCHED] Native Bionic In-Place Transformation (Keyboard): {}",
                            chord
                        );
                        trigger_bionic_transform(Arc::clone(&loop_bionic));
                    } else if shortcuts.open_home.matches_keyboard(&chord) {
                        info!("🔥 [HOTKEY MATCHED] Open Home Dashboard (Keyboard): {}", chord);
                    } else if shortcuts.toggle_reader.matches_keyboard(&chord) {
                        info!("🔥 [HOTKEY MATCHED] Native Reader View (Keyboard): {}", chord);
                        trigger_reader_view(Arc::clone(&loop_tts), loop_ratio);
                    } else if shortcuts.push_to_talk.matches_keyboard(&chord) {
                        let was_active = ptt_kb_active.fetch_xor(true, Ordering::SeqCst);
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
                    } else {
                        tracing::debug!("Key chord '{}' received (no shortcut match)", chord);
                    }
                }
                HookEvent::MouseButtonDown(btn) => {
                    info!("🔥 [MOUSE DOWN] Button {} pressed", btn);
                    if shortcuts.push_to_talk.matches_mouse(btn) {
                        info!(
                            "🔥 [HOTKEY MATCHED] Push-to-Talk Dictation (Mouse Button {}): Start Listening",
                            btn
                        );
                        loop_mic.on_ptt_press();
                    }
                }
                HookEvent::MouseButtonUp(btn, duration) => {
                    let dur_ms = duration.as_millis() as u64;
                    info!("🔥 [MOUSE UP] Button {} released after {}ms", btn, dur_ms);

                    if shortcuts.push_to_talk.matches_mouse(btn) {
                        let threshold = shortcuts.push_to_talk.mouse_hold_ms();
                        info!(
                            "🔥 [HOTKEY MATCHED] Push-to-Talk Dictation (Mouse Button {}): Release ({}ms, threshold {}ms)",
                            btn, dur_ms, threshold
                        );
                        loop_mic.on_ptt_release();
                    } else if shortcuts.speak_selection.matches_mouse(btn) {
                        let threshold = shortcuts.speak_selection.mouse_hold_ms();
                        if dur_ms >= threshold {
                            info!(
                                "🔥 [HOTKEY MATCHED] Speak Selection (Mouse Button {}, {}ms >= {}ms)",
                                btn, dur_ms, threshold
                            );
                            trigger_speak_selection(Arc::clone(&loop_tts));
                        } else {
                            info!(
                                "Mouse Button {} released before {}ms hold threshold ({}ms)",
                                btn, threshold, dur_ms
                            );
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
                        }
                    } else if shortcuts.toggle_reader.matches_mouse(btn) {
                        let threshold = shortcuts.toggle_reader.mouse_hold_ms();
                        if dur_ms >= threshold {
                            info!(
                                "🔥 [HOTKEY MATCHED] Native Reader View (Mouse Button {}, {}ms)",
                                btn, dur_ms
                            );
                            trigger_reader_view(Arc::clone(&loop_tts), loop_ratio);
                        }
                    }
                }
            }
        }
    });

    // 9. Initialize Windows System Tray Icon
    let tray_tts = Arc::clone(&tts_engine);
    let tray_bionic = Arc::clone(&bionic_engine);
    let _tray = ui::TrayManager::spawn(move |action| match action {
        ui::IDM_OPEN_DASHBOARD => {}
        ui::IDM_TOGGLE_BIONIC => {
            let engine = Arc::clone(&tray_bionic);
            let _ = std::thread::spawn(move || {
                let rt = tokio::runtime::Runtime::new().unwrap();
                rt.block_on(async {
                    if let Ok(text) =
                        SelectionCapture::capture_selected_text_synthetic(Duration::from_millis(150))
                            .await
                    {
                        let bionic_text = engine.to_unicode_bionic(&text);
                        let _ = TextInjector::inject_text(&bionic_text);
                    }
                });
            });
        }
        ui::IDM_STOP_SPEECH => {
            tray_tts.stop();
        }
        ui::IDM_EXIT => {
            std::process::exit(0);
        }
        _ => {}
    });

    info!("Application background services initialized. Launching egui Settings Dashboard on main thread...");

    // 10. Run egui Dashboard on the Main Thread with Custom Brand Icon
    let mut viewport = eframe::egui::ViewportBuilder::default()
        .with_inner_size([880.0, 620.0])
        .with_min_inner_size([760.0, 480.0]);
    if let Some(icon) = load_app_icon() {
        viewport = viewport.with_icon(Arc::new(icon));
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
    let gui_tts = Arc::clone(&tts_engine);
    eframe::run_native(
        "SpeakThat Settings Dashboard",
        native_options,
        Box::new(move |cc| {
            Box::new(ui::SettingsDashboard::new(
                cc,
                gui_config,
                gui_shortcuts,
                gui_tts,
            ))
        }),
    )
    .map_err(|e| Box::new(e) as Box<dyn std::error::Error>)?;

    Ok(())
}
