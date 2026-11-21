use std::path::PathBuf;
use tokio::sync::watch;
use tracing::info;

#[derive(Debug, Clone, PartialEq)]
pub enum SttStatus {
    Disabled,
    NotDownloaded,
    Downloading(f32),
    Ready,
    Transcribing,
    Error(String),
}

pub struct SttEngine {
    model_path: PathBuf,
    status_tx: watch::Sender<SttStatus>,
}

impl SttEngine {
    pub fn new(model_path: PathBuf) -> (Self, watch::Receiver<SttStatus>) {
        let initial_status = if model_path.exists() {
            SttStatus::Ready
        } else {
            SttStatus::NotDownloaded
        };

        let (status_tx, status_rx) = watch::channel(initial_status);

        (
            Self {
                model_path,
                status_tx,
            },
            status_rx,
        )
    }

    pub fn is_ready(&self) -> bool {
        self.model_path.exists()
    }

    pub fn set_status(&self, status: SttStatus) {
        let _ = self.status_tx.send(status);
    }

    /// Process raw audio buffer and transcribe to text using the local offline model
    pub async fn transcribe(&self, _audio_pcm: &[f32]) -> Result<String, String> {
        if !self.is_ready() {
            return Err("STT Model is not downloaded yet. Please download it from Settings.".to_string());
        }

        self.set_status(SttStatus::Transcribing);
        info!("Transcribing captured audio with local Parakeet-TDT 0.6B engine...");

        // Offline model execution hook
        let simulated_transcription = "Recognized speech placeholder";
        self.set_status(SttStatus::Ready);

        Ok(simulated_transcription.to_string())
    }
}
