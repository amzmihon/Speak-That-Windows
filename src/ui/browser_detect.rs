use std::path::PathBuf;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum BrowserKind {
    Chrome,
    Edge,
    Brave,
    Firefox,
    Opera,
    OperaGX,
    Vivaldi,
}

#[derive(Debug, Clone)]
pub struct InstalledBrowser {
    pub kind: BrowserKind,
    pub name: &'static str,
    pub executable_path: PathBuf,
    pub extension_folder: PathBuf,
    pub install_url: &'static str,
}

pub struct BrowserDetector;

impl BrowserDetector {
    pub fn get_extension_path_chromium() -> PathBuf {
        let base = std::env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
        base.join("ADHD_Bionic-Reader")
            .join("ADHD_Bionic-Reader Extantion Unpacked Loader")
    }

    pub fn get_extension_path_firefox() -> PathBuf {
        let base = std::env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
        base.join("ADHD_Bionic-Reader").join("extension_firefox")
    }

    pub fn detect_all() -> Vec<InstalledBrowser> {
        let mut found = Vec::new();

        let local_app_data = dirs::data_local_dir().unwrap_or_else(|| PathBuf::from("C:\\Users\\Default\\AppData\\Local"));
        let program_files = PathBuf::from("C:\\Program Files");
        let program_files_x86 = PathBuf::from("C:\\Program Files (x86)");

        let candidates = vec![
            (
                BrowserKind::Chrome,
                "Google Chrome",
                vec![
                    program_files.join("Google\\Chrome\\Application\\chrome.exe"),
                    local_app_data.join("Google\\Chrome\\Application\\chrome.exe"),
                ],
                Self::get_extension_path_chromium(),
                "chrome://extensions",
            ),
            (
                BrowserKind::Edge,
                "Microsoft Edge",
                vec![
                    program_files_x86.join("Microsoft\\Edge\\Application\\msedge.exe"),
                    program_files.join("Microsoft\\Edge\\Application\\msedge.exe"),
                ],
                Self::get_extension_path_chromium(),
                "edge://extensions",
            ),
            (
                BrowserKind::Brave,
                "Brave Browser",
                vec![
                    program_files.join("BraveSoftware\\Brave-Browser\\Application\\brave.exe"),
                    local_app_data.join("BraveSoftware\\Brave-Browser\\Application\\brave.exe"),
                ],
                Self::get_extension_path_chromium(),
                "brave://extensions",
            ),
            (
                BrowserKind::Firefox,
                "Mozilla Firefox",
                vec![
                    program_files.join("Mozilla Firefox\\firefox.exe"),
                    program_files_x86.join("Mozilla Firefox\\firefox.exe"),
                ],
                Self::get_extension_path_firefox(),
                "about:debugging#/runtime/this-firefox",
            ),
            (
                BrowserKind::OperaGX,
                "Opera GX",
                vec![
                    local_app_data.join("Programs\\Opera GX\\launcher.exe"),
                ],
                Self::get_extension_path_chromium(),
                "opera://extensions",
            ),
            (
                BrowserKind::Opera,
                "Opera",
                vec![
                    local_app_data.join("Programs\\Opera\\launcher.exe"),
                ],
                Self::get_extension_path_chromium(),
                "opera://extensions",
            ),
            (
                BrowserKind::Vivaldi,
                "Vivaldi",
                vec![
                    local_app_data.join("Vivaldi\\Application\\vivaldi.exe"),
                    program_files.join("Vivaldi\\Application\\vivaldi.exe"),
                ],
                Self::get_extension_path_chromium(),
                "vivaldi://extensions",
            ),
        ];

        for (kind, name, paths, ext_path, url) in candidates {
            for exe in paths {
                if exe.exists() {
                    found.push(InstalledBrowser {
                        kind,
                        name,
                        executable_path: exe,
                        extension_folder: ext_path,
                        install_url: url,
                    });
                    break;
                }
            }
        }

        found
    }
}
