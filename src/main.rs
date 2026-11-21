use std::sync::Arc;
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
use config::AppConfig;
use downloader::ModelDownloader;
use input::{HookEvent, InputHookManager, ShortcutCatalog, TextInjector};
use ui::BrowserDetector;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // 1. Initialize logging
    tracing_subscriber::fmt()
        .with_env_filter("info,speakthat=debug")
        .init();

    info!("=== SpeakThat + ADHD Bionic Reader Suite v0.2.0 ===");
    info!("Starting native Windows client in Rust...");

    // 2. Load Configuration
    let config = AppConfig::load();
    info!("Configuration loaded from: {:?}", AppConfig::config_path());
    info!("Shortcuts bound:");
    info!("  - Speak Selection: {}", config.shortcuts.speak_selection);
    info!("  - Push-to-Talk Dictation: {}", config.shortcuts.push_to_talk);
    info!("  - Open Home Dashboard: {}", config.shortcuts.open_home);
    info!("  - Toggle Bionic Reading: {}", config.shortcuts.toggle_bionic);
    info!("  - Toggle Reader View: {}", config.shortcuts.toggle_reader);

    // 3. Validate Shortcuts via Shortcut Collision Protection System
    let checks = [
        ("Speak Selection", &config.shortcuts.speak_selection),
        ("Push-to-Talk", &config.shortcuts.push_to_talk),
        ("Open Home", &config.shortcuts.open_home),
        ("Toggle Bionic", &config.shortcuts.toggle_bionic),
        ("Toggle Reader", &config.shortcuts.toggle_reader),
    ];

    for (name, chord) in checks {
        match ShortcutCatalog::validate(chord) {
            input::CollisionSeverity::Allowed => {
                info!("  ✓ Shortcut [{}] validated: OK", name);
            }
            input::CollisionSeverity::Warning(msg) => {
                warn!("  ⚠️ Shortcut [{}] warning: {}", name, msg);
            }
            input::CollisionSeverity::HardBlocked(msg) => {
                panic!("FATAL: Shortcut [{}] is hard-blocked by OS policy: {}", name, msg);
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

    // 5. Initialize Audio & Bionic Engines
    let stt_installed = ModelDownloader::is_model_installed();
    info!("Speech-to-Text (Parakeet-TDT 0.6B) Model Status: {}", if stt_installed { "Installed" } else { "Not Installed (On-Demand in-app download available)" });

    let (tts_engine, _tts_rx) = TtsEngine::new();
    let (mic_manager, _ptt_rx, _duck_rx) = MicrophoneManager::new();
    let model_path = dirs::data_local_dir()
        .unwrap_or_else(|| std::path::PathBuf::from("."))
        .join("SpeakThat")
        .join("models")
        .join("parakeet-tdt-0.6b-v3.onnx");
    let (stt_engine, _stt_rx) = SttEngine::new(model_path);
    let bionic_engine = BionicEngine::new(0.4);

    let tts_engine = Arc::new(tts_engine);
    let mic_manager = Arc::new(mic_manager);
    let _stt_engine = Arc::new(stt_engine);
    let bionic_engine = Arc::new(bionic_engine);

    // 6. Initialize Low-Level Input Hooks
    let (event_tx, mut event_rx) = mpsc::unbounded_channel::<HookEvent>();
    let hook_mgr = Arc::new(InputHookManager::new(event_tx));
    let _hook_handle = hook_mgr.start_listening();
    info!("Low-level Windows keyboard and mouse hooks initialized.");

    info!("Application successfully initialized in background. Ready for input.");

    // Event loop receiving chord triggers and side mouse events
    while let Some(event) = event_rx.recv().await {
        match event {
            HookEvent::ChordTriggered(chord) => {
                info!("Chord triggered: {}", chord);

                if chord == config.shortcuts.speak_selection {
                    info!("Action: Speak Selection triggered");
                    let tts = Arc::clone(&tts_engine);
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
                } else if chord == config.shortcuts.toggle_bionic {
                    info!("Action: Native Windows Bionic In-Place Transformation triggered");
                    let engine = Arc::clone(&bionic_engine);
                    tokio::spawn(async move {
                        match SelectionCapture::capture_selected_text_synthetic(Duration::from_millis(150)).await {
                            Ok(text) => {
                                let bionic_text = engine.to_unicode_bionic(&text);
                                info!("Transformed {} chars to native Bionic Unicode format", bionic_text.len());
                                if let Err(e) = TextInjector::inject_text(&bionic_text) {
                                    warn!("Failed to inject bionic text: {}", e);
                                }
                            }
                            Err(e) => {
                                warn!("Could not capture selection for Bionic reading: {}", e);
                            }
                        }
                    });
                } else if chord == config.shortcuts.open_home {
                    info!("Action: Open Home Dashboard triggered");
                    let cfg = config.clone();
                    let tts = Arc::clone(&tts_engine);
                    std::thread::spawn(move || {
                        let native_options = eframe::NativeOptions {
                            viewport: eframe::egui::ViewportBuilder::default()
                                .with_inner_size([740.0, 540.0])
                                .with_min_inner_size([620.0, 420.0]),
                            ..Default::default()
                        };
                        let _ = eframe::run_native(
                            "SpeakThat Settings Dashboard",
                            native_options,
                            Box::new(|_cc| Box::new(ui::SettingsDashboard::new(cfg, tts))),
                        );
                    });
                } else if chord == config.shortcuts.push_to_talk {
                    info!("Action: Push-to-Talk triggered via keyboard shortcut");
                    mic_manager.on_ptt_press();
                }
            }
            HookEvent::SideButtonHoldStart(btn) => {
                info!("Side mouse button {} pressed (Push-to-Talk listening...)", btn);
                mic_manager.on_ptt_press();
            }
            HookEvent::SideButtonHoldEnd(btn, duration) => {
                info!(
                    "Side mouse button {} released after {}ms",
                    btn,
                    duration.as_millis()
                );
                mic_manager.on_ptt_release();
            }
        }
    }

    Ok(())
}
