use std::path::PathBuf;
use std::process::Stdio;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tokio::process::Command;
use tokio::sync::{mpsc, watch};
use tracing::{debug, error, info, warn};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PlaybackState {
    Stopped,
    Playing,
    Paused,
}

pub struct TtsEngine {
    state_tx: watch::Sender<PlaybackState>,
    is_paused: Arc<AtomicBool>,
    cmd_tx: mpsc::UnboundedSender<String>,
}

impl TtsEngine {
    pub fn new() -> (Self, watch::Receiver<PlaybackState>) {
        let (state_tx, state_rx) = watch::channel(PlaybackState::Stopped);
        let is_paused = Arc::new(AtomicBool::new(false));
        let (cmd_tx, mut cmd_rx) = mpsc::unbounded_channel::<String>();

        let state_tx_clone = state_tx.clone();
        let is_paused_clone = Arc::clone(&is_paused);

        // Spawn background worker process
        tokio::spawn(async move {
            let python_path = Self::find_python_path();
            let worker_path = Self::find_worker_path();

            info!("Starting Paradee TTS Worker: {:?} with script {:?}", python_path, worker_path);

            let mut child = match Command::new(&python_path)
                .arg(&worker_path)
                .stdin(Stdio::piped())
                .stdout(Stdio::piped())
                .stderr(Stdio::inherit())
                .spawn()
            {
                Ok(c) => c,
                Err(e) => {
                    error!("Failed to spawn Paradee TTS worker: {e}");
                    return;
                }
            };

            let mut stdin = child.stdin.take().expect("Failed to open worker stdin");
            let stdout = child.stdout.take().expect("Failed to open worker stdout");

            // Worker stdin writer loop
            tokio::spawn(async move {
                while let Some(msg) = cmd_rx.recv().await {
                    let mut data = msg.into_bytes();
                    data.push(b'\n');
                    if let Err(e) = stdin.write_all(&data).await {
                        warn!("Error writing command to TTS worker stdin: {e}");
                        break;
                    }
                    if let Err(e) = stdin.flush().await {
                        warn!("Error flushing TTS worker stdin: {e}");
                        break;
                    }
                }
            });

            // Worker stdout reader loop
            let mut reader = BufReader::new(stdout).lines();
            while let Ok(Some(line)) = reader.next_line().await {
                let trimmed = line.trim();
                if trimmed.is_empty() {
                    continue;
                }

                if let Ok(val) = serde_json::from_str::<serde_json::Value>(trimmed) {
                    if let Some(event) = val.get("event").and_then(|v| v.as_str()) {
                        match event {
                            "ready" => {
                                info!("Paradee 8M TTS engine is initialized and ready for real-time speech!");
                            }
                            "sentence" => {
                                let sentence = val.get("data").and_then(|v| v.as_str()).unwrap_or("");
                                info!("Paradee speaking sentence: \"{}\"", sentence);
                                is_paused_clone.store(false, Ordering::SeqCst);
                                let _ = state_tx_clone.send(PlaybackState::Playing);
                            }
                            "complete" => {
                                info!("Paradee playback completed");
                                is_paused_clone.store(false, Ordering::SeqCst);
                                let _ = state_tx_clone.send(PlaybackState::Stopped);
                            }
                            "status" => {
                                let st = val.get("data").and_then(|v| v.as_str()).unwrap_or("");
                                debug!("TTS worker status: {}", st);
                            }
                            "error" => {
                                let err = val.get("error").and_then(|v| v.as_str()).unwrap_or("");
                                error!("TTS worker reported error: {}", err);
                            }
                            _ => {}
                        }
                    }
                }
            }

            warn!("Paradee TTS worker process terminated.");
        });

        (
            Self {
                state_tx,
                is_paused,
                cmd_tx,
            },
            state_rx,
        )
    }

    fn find_project_root() -> PathBuf {
        crate::ui::BrowserDetector::find_project_root()
    }

    fn find_python_path() -> PathBuf {
        let root = Self::find_project_root();
        let candidates = [
            root.join(".venv\\Scripts\\python.exe"),
            PathBuf::from("E:\\Speak-That-Windows\\.venv\\Scripts\\python.exe"),
            PathBuf::from(".venv\\Scripts\\python.exe"),
            PathBuf::from("python.exe"),
        ];

        for c in &candidates {
            if c.exists() {
                return c.clone();
            }
        }
        PathBuf::from("python")
    }

    fn find_worker_path() -> PathBuf {
        let root = Self::find_project_root();
        let candidates = [
            root.join("src\\audio\\tts_worker.py"),
            PathBuf::from("E:\\Speak-That-Windows\\src\\audio\\tts_worker.py"),
            PathBuf::from("src\\audio\\tts_worker.py"),
            PathBuf::from("tts_worker.py"),
        ];

        for c in &candidates {
            if c.exists() {
                return c.clone();
            }
        }
        PathBuf::from("src\\audio\\tts_worker.py")
    }

    /// Speak text using the Paradee 8M TTS model
    pub fn speak(&self, text: &str) {
        if text.trim().is_empty() {
            return;
        }

        info!("Sending speak request to Paradee engine: {} chars", text.len());
        let req = serde_json::json!({
            "cmd": "speak",
            "text": text,
        });

        let _ = self.cmd_tx.send(req.to_string());
        self.is_paused.store(false, Ordering::SeqCst);
        let _ = self.state_tx.send(PlaybackState::Playing);
    }

    /// Stop playback immediately
    pub fn stop(&self) {
        info!("Stopping Paradee playback");
        let req = serde_json::json!({ "cmd": "stop" });
        let _ = self.cmd_tx.send(req.to_string());
        self.is_paused.store(false, Ordering::SeqCst);
        let _ = self.state_tx.send(PlaybackState::Stopped);
    }

    /// Toggle pause / resume
    pub fn toggle_pause(&self) {
        let paused = self.is_paused.fetch_xor(true, Ordering::SeqCst);
        let cmd = if !paused { "pause" } else { "resume" };
        let next_state = if !paused {
            PlaybackState::Paused
        } else {
            PlaybackState::Playing
        };
        info!("Toggling playback -> {next_state:?}");
        let req = serde_json::json!({ "cmd": cmd });
        let _ = self.cmd_tx.send(req.to_string());
        let _ = self.state_tx.send(next_state);
    }

    /// Change active voice (e.g. "af_heart", "bf_isabella", "am_puck", "bm_fable")
    pub fn set_voice(&self, voice: &str) {
        let req = serde_json::json!({ "cmd": "set_voice", "voice": voice });
        let _ = self.cmd_tx.send(req.to_string());
    }

    /// Change speech speed (0.6x to 2.5x)
    pub fn set_speed(&self, speed: f32) {
        let req = serde_json::json!({ "cmd": "set_speed", "speed": speed });
        let _ = self.cmd_tx.send(req.to_string());
    }

    /// Change volume (0.0 to 1.0)
    pub fn set_volume(&self, volume: f32) {
        let req = serde_json::json!({ "cmd": "set_volume", "volume": volume });
        let _ = self.cmd_tx.send(req.to_string());
    }
}
