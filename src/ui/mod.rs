pub mod browser_detect;
pub mod dashboard;
pub mod hud;
pub mod reader_view;
pub mod tray;

pub use browser_detect::{BrowserDetector, BrowserKind, InstalledBrowser};
pub use dashboard::SettingsDashboard;
pub use hud::FloatingPillHud;
pub use reader_view::{ReaderTheme, ReaderViewWindow};
pub use tray::{
    TrayIcon, TrayManager, IDM_EXIT, IDM_OPEN_DASHBOARD, IDM_STOP_SPEECH, IDM_TOGGLE_BIONIC,
};
