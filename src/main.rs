use std::sync::Arc;
use tokio::sync::mpsc;
use tracing::{info, warn};

mod config;
mod downloader;
mod input;
mod ui;

use config::AppConfig;
use downloader::ModelDownloader;
use input::{HookEvent, InputHookManager, ShortcutCatalog};
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

    // 5. Check Offline Models Status
    let stt_installed = ModelDownloader::is_model_installed();
    info!("Speech-to-Text (Parakeet-TDT 0.6B) Model Status: {}", if stt_installed { "Installed" } else { "Not Installed (On-Demand in-app download available)" });

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
            }
            HookEvent::SideButtonHoldStart(btn) => {
                info!("Side mouse button {} pressed (Push-to-Talk listening...)", btn);
            }
            HookEvent::SideButtonHoldEnd(btn, duration) => {
                info!(
                    "Side mouse button {} released after {}ms",
                    btn,
                    duration.as_millis()
                );
            }
        }
    }

    Ok(())
}
