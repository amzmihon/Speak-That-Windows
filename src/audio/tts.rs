use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use tokio::sync::watch;
use tracing::info;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PlaybackState {
    Stopped,
    Playing,
    Paused,
}

pub struct TtsEngine {
    state_tx: watch::Sender<PlaybackState>,
    is_paused: Arc<AtomicBool>,
}

impl TtsEngine {
    pub fn new() -> (Self, watch::Receiver<PlaybackState>) {
        let (state_tx, state_rx) = watch::channel(PlaybackState::Stopped);
        let is_paused = Arc::new(AtomicBool::new(false));

        (
            Self {
                state_tx,
                is_paused,
            },
            state_rx,
        )
    }

    pub fn speak(&self, text: &str) {
        if text.trim().is_empty() {
            return;
        }

        info!("TTS synthesizing speech: \"{}\"", text.chars().take(40).collect::<String>());
        self.is_paused.store(false, Ordering::SeqCst);
        let _ = self.state_tx.send(PlaybackState::Playing);
    }

    pub fn toggle_pause(&self) {
        let paused = self.is_paused.fetch_xor(true, Ordering::SeqCst);
        let next_state = if !paused {
            PlaybackState::Paused
        } else {
            PlaybackState::Playing
        };
        info!("TTS toggle pause -> {next_state:?}");
        let _ = self.state_tx.send(next_state);
    }

    pub fn stop(&self) {
        self.is_paused.store(false, Ordering::SeqCst);
        info!("TTS stopped");
        let _ = self.state_tx.send(PlaybackState::Stopped);
    }
}
