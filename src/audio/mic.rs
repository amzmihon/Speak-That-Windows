use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use tokio::sync::watch;
use tracing::info;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PushToTalkState {
    Idle,
    Listening,
    Processing,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AudioDuckingState {
    Normal,
    Ducked, // -24 dB or paused when PTT is held
}

pub struct MicrophoneManager {
    ptt_state: watch::Sender<PushToTalkState>,
    ducking_state: watch::Sender<AudioDuckingState>,
    is_active: Arc<AtomicBool>,
}

impl MicrophoneManager {
    pub fn new() -> (Self, watch::Receiver<PushToTalkState>, watch::Receiver<AudioDuckingState>) {
        let (ptt_tx, ptt_rx) = watch::channel(PushToTalkState::Idle);
        let (duck_tx, duck_rx) = watch::channel(AudioDuckingState::Normal);
        let is_active = Arc::new(AtomicBool::new(false));

        (
            Self {
                ptt_state: ptt_tx,
                ducking_state: duck_tx,
                is_active,
            },
            ptt_rx,
            duck_rx,
        )
    }

    /// Called when Push-to-Talk key is pressed down
    pub fn on_ptt_press(&self) {
        if !self.is_active.swap(true, Ordering::SeqCst) {
            info!("Push-to-Talk engaged: ducking audio and listening");
            let _ = self.ducking_state.send(AudioDuckingState::Ducked);
            let _ = self.ptt_state.send(PushToTalkState::Listening);
        }
    }

    /// Called when Push-to-Talk key is released
    pub fn on_ptt_release(&self) {
        if self.is_active.swap(false, Ordering::SeqCst) {
            info!("Push-to-Talk released: processing audio and restoring volume");
            let _ = self.ptt_state.send(PushToTalkState::Processing);
            let _ = self.ducking_state.send(AudioDuckingState::Normal);
            let _ = self.ptt_state.send(PushToTalkState::Idle);
        }
    }
}
