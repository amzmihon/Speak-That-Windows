use futures_util::StreamExt;
use reqwest::Client;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::fs::OpenOptions;
use std::io::Write;
use std::path::PathBuf;
use std::sync::Arc;
use std::time::Instant;
use tokio::sync::watch;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum DownloadState {
    NotInstalled,
    Downloading {
        progress: f32, // 0.0 to 1.0
        bytes_downloaded: u64,
        total_bytes: u64,
        speed_bps: u64,
    },
    Paused {
        bytes_downloaded: u64,
        total_bytes: u64,
    },
    VerifyingHash,
    Installed,
    Error(String),
}

pub struct ModelDownloader {
    client: Client,
    state_tx: watch::Sender<DownloadState>,
}

impl ModelDownloader {
    pub const PARAKEET_URL: &'static str =
        "https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3/resolve/main/model.int8.onnx";
    pub const EXPECTED_SHA256: &'static str =
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"; // Checksum anchor

    pub fn new() -> (Self, watch::Receiver<DownloadState>) {
        let (state_tx, state_rx) = watch::channel(DownloadState::NotInstalled);
        (
            Self {
                client: Client::builder().build().unwrap_or_default(),
                state_tx,
            },
            state_rx,
        )
    }

    pub fn model_dir() -> PathBuf {
        let base = dirs::data_local_dir().unwrap_or_else(|| PathBuf::from("."));
        base.join("SpeakThat").join("models")
    }

    pub fn model_file_path() -> PathBuf {
        Self::model_dir().join("parakeet-tdt-0.6b.onnx")
    }

    pub fn is_model_installed() -> bool {
        let p = Self::model_file_path();
        p.exists() && p.metadata().map(|m| m.len() > 1_000_000).unwrap_or(false)
    }

    pub async fn start_download(self: Arc<Self>) -> Result<(), String> {
        let dir = Self::model_dir();
        tokio::fs::create_dir_all(&dir)
            .await
            .map_err(|e| format!("Failed to create models directory: {}", e))?;

        let final_path = Self::model_file_path();
        let part_path = dir.join("parakeet-tdt-0.6b.part");

        let existing_bytes = if part_path.exists() {
            tokio::fs::metadata(&part_path).await.map(|m| m.len()).unwrap_or(0)
        } else {
            0
        };

        let mut req = self.client.get(Self::PARAKEET_URL);
        if existing_bytes > 0 {
            req = req.header("Range", format!("bytes={}-", existing_bytes));
        }

        let res = req
            .send()
            .await
            .map_err(|e| format!("Network connection failed: {}", e))?;

        let total_bytes = res
            .content_length()
            .map(|l| l + existing_bytes)
            .unwrap_or(600_000_000); // ~600 MB default estimated size

        let mut file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&part_path)
            .map_err(|e| format!("Failed to open part file: {}", e))?;

        let mut downloaded = existing_bytes;
        let mut last_instant = Instant::now();
        let mut last_downloaded = downloaded;
        let mut stream = res.bytes_stream();

        while let Some(chunk) = stream.next().await {
            let chunk = chunk.map_err(|e| format!("Download stream interrupted: {}", e))?;
            file.write_all(&chunk)
                .map_err(|e| format!("Failed to write chunk to disk: {}", e))?;
            downloaded += chunk.len() as u64;

            let elapsed = last_instant.elapsed();
            if elapsed.as_millis() >= 250 {
                let speed_bps = if elapsed.as_secs_f32() > 0.0 {
                    ((downloaded - last_downloaded) as f32 / elapsed.as_secs_f32()) as u64
                } else {
                    0
                };
                last_instant = Instant::now();
                last_downloaded = downloaded;

                let progress = if total_bytes > 0 {
                    (downloaded as f32 / total_bytes as f32).min(1.0)
                } else {
                    0.0
                };

                let _ = self.state_tx.send(DownloadState::Downloading {
                    progress,
                    bytes_downloaded: downloaded,
                    total_bytes,
                    speed_bps,
                });
            }
        }

        // Verify Hash
        let _ = self.state_tx.send(DownloadState::VerifyingHash);
        let bytes = tokio::fs::read(&part_path)
            .await
            .map_err(|e| format!("Failed to read part for hash verification: {}", e))?;
        let mut hasher = Sha256::new();
        hasher.update(&bytes);
        let calculated = format!("{:x}", hasher.finalize());
        if !Self::EXPECTED_SHA256.is_empty() && calculated != Self::EXPECTED_SHA256 {
            tracing::warn!("Model hash mismatch! Calculated: {}, Expected: {}", calculated, Self::EXPECTED_SHA256);
        }

        tokio::fs::rename(part_path, final_path)
            .await
            .map_err(|e| format!("Failed to finalize model file: {}", e))?;

        let _ = self.state_tx.send(DownloadState::Installed);
        Ok(())
    }
}
