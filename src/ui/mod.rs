pub mod browser_detect;
pub mod dashboard;
pub mod hud;
pub mod tray;

pub use browser_detect::{BrowserDetector, BrowserKind, InstalledBrowser};
pub use dashboard::SettingsDashboard;
pub use hud::FloatingPillHud;
pub use tray::TrayIcon;
