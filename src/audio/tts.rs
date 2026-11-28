use ort::session::Session;
use ort::value::Tensor;
use rodio::buffer::SamplesBuffer;
use rodio::{OutputStream, Sink};
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, AtomicU32, AtomicU64, Ordering};
use std::sync::{Arc, Mutex, RwLock};
use tokio::sync::{mpsc, watch};
use tracing::{debug, error, info};
use windows::Win32::Foundation::POINT;
use windows::Win32::UI::WindowsAndMessaging::GetCursorPos;

use crate::audio::g2p::MisakiG2p;
use crate::ui::{BrowserDetector, FloatingPillHud};

const PARADEE_SAMPLE_RATE: u32 = 24_000;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PlaybackState {
    Stopped,
    Playing,
    Paused,
}

enum TtsCommand {
    Speak { job_id: u64, text: String },
    Stop,
    TogglePause,
}

pub struct TtsEngine {
    state_tx: watch::Sender<PlaybackState>,
    sentence_tx: watch::Sender<String>,
    is_paused: Arc<AtomicBool>,
    cmd_tx: mpsc::UnboundedSender<TtsCommand>,
    active_job_id: Arc<AtomicU64>,
    voice: Arc<Mutex<String>>,
    speed_bits: Arc<AtomicU32>,
    volume_bits: Arc<AtomicU32>,
    active_sink: Arc<Mutex<Option<Arc<Sink>>>>,
    hud_anchor: Arc<Mutex<Option<(i32, i32)>>>,
    egui_ctx: Arc<RwLock<Option<eframe::egui::Context>>>,
}

impl TtsEngine {
    pub fn new() -> (Self, watch::Receiver<PlaybackState>) {
        let (state_tx, state_rx) = watch::channel(PlaybackState::Stopped);
        let (sentence_tx, _sentence_rx) = watch::channel(String::new());
        let is_paused = Arc::new(AtomicBool::new(false));
        let (cmd_tx, mut cmd_rx) = mpsc::unbounded_channel::<TtsCommand>();
        let active_job_id = Arc::new(AtomicU64::new(0));
        let voice = Arc::new(Mutex::new("bf_isabella".to_string()));
        let speed_bits = Arc::new(AtomicU32::new(1.05_f32.to_bits()));
        let volume_bits = Arc::new(AtomicU32::new(1.0_f32.to_bits()));
        let active_sink: Arc<Mutex<Option<Arc<Sink>>>> = Arc::new(Mutex::new(None));
        let hud_anchor: Arc<Mutex<Option<(i32, i32)>>> = Arc::new(Mutex::new(None));
        let egui_ctx: Arc<RwLock<Option<eframe::egui::Context>>> = Arc::new(RwLock::new(None));

        let state_tx_worker = state_tx.clone();
        let sentence_tx_worker = sentence_tx.clone();
        let is_paused_worker = Arc::clone(&is_paused);
        let job_id_worker = Arc::clone(&active_job_id);
        let voice_worker = Arc::clone(&voice);
        let speed_worker = Arc::clone(&speed_bits);
        let volume_worker = Arc::clone(&volume_bits);
        let sink_worker = Arc::clone(&active_sink);
        let ctx_worker = Arc::clone(&egui_ctx);

        let notify_ui = move || {
            FloatingPillHud::refresh();
            if let Ok(guard) = ctx_worker.read() {
                if let Some(ref c) = *guard {
                    c.request_repaint();
                }
            }
        };

        // Pure-Rust ONNX + Misaki G2P + Rodio WASAPI playback thread (zero Python)
        std::thread::spawn(move || {
            let g2p = match MisakiG2p::load_embedded() {
                Ok(g) => {
                    info!("Loaded embedded Misaki English US+GB G2P lexicons.");
                    g
                }
                Err(e) => {
                    error!("Failed to load Misaki G2P: {e}");
                    return;
                }
            };

            let dll_path = Self::find_onnxruntime_dll();
            info!("Initializing native ONNX Runtime from: {:?}", dll_path);
            let env = match ort::init_from(&dll_path) {
                Ok(builder) => match builder.with_name("SpeakThat").build() {
                    Ok(e) => e,
                    Err(err) => {
                        error!("Failed to build ONNX Runtime environment: {err}");
                        return;
                    }
                },
                Err(e) => {
                    error!("Failed to dynamically load onnxruntime.dll ({dll_path:?}): {e}");
                    return;
                }
            };

            let model_path = Self::find_model_path();
            info!("Loading Paradee 8M INT8 model: {:?}", model_path);
            let mut session = match Session::builder(&env) {
                Ok(b) => match b.with_intra_threads(1) {
                    Ok(mut b2) => match b2.commit_from_file(&model_path) {
                        Ok(s) => s,
                        Err(e) => {
                            error!("Failed to load Paradee ONNX model ({model_path:?}): {e}");
                            return;
                        }
                    },
                    Err(e) => {
                        error!("Failed to configure ORT intra threads: {e}");
                        return;
                    }
                },
                Err(e) => {
                    error!("Failed to create ORT SessionBuilder: {e}");
                    return;
                }
            };

            let _ = Self::run_inference(&mut session, &g2p, "Ready.", "bf_isabella", 1.0);
            info!("Pure-Rust Paradee 8M ONNX TTS engine is initialized and ready (zero Python).");

            let stream_tuple = match OutputStream::try_default() {
                Ok(st) => st,
                Err(e) => {
                    error!("Failed to open default audio output device: {e}");
                    return;
                }
            };
            let (_stream, stream_handle) = stream_tuple;

            while let Some(cmd) = cmd_rx.blocking_recv() {
                match cmd {
                    TtsCommand::Speak { job_id, text } => {
                        if job_id != job_id_worker.load(Ordering::SeqCst) {
                            continue;
                        }

                        if let Ok(mut guard) = sink_worker.lock() {
                            if let Some(prev) = guard.take() {
                                prev.stop();
                            }
                        }

                        let sink = match Sink::try_new(&stream_handle) {
                            Ok(s) => Arc::new(s),
                            Err(e) => {
                                error!("Failed to create audio sink: {e}");
                                let _ = state_tx_worker.send(PlaybackState::Stopped);
                                let _ = sentence_tx_worker.send(String::new());
                                notify_ui();
                                continue;
                            }
                        };
                        sink.set_volume(f32::from_bits(volume_worker.load(Ordering::SeqCst)));

                        if let Ok(mut guard) = sink_worker.lock() {
                            *guard = Some(Arc::clone(&sink));
                        }

                        is_paused_worker.store(false, Ordering::SeqCst);
                        let _ = state_tx_worker.send(PlaybackState::Playing);
                        notify_ui();

                        let sentences = MisakiG2p::split_sentences(&text);
                        for sentence in sentences {
                            if job_id != job_id_worker.load(Ordering::SeqCst) {
                                sink.stop();
                                break;
                            }

                            let _ = sentence_tx_worker.send(sentence.clone());
                            notify_ui();

                            let cur_voice = voice_worker
                                .lock()
                                .map(|g| g.clone())
                                .unwrap_or_else(|_| "bf_isabella".to_string());
                            let cur_speed =
                                f32::from_bits(speed_worker.load(Ordering::SeqCst)).clamp(0.5, 2.5);

                            info!(
                                "Paradee synthesizing sentence ({cur_voice} @ {cur_speed:.2}x): \"{sentence}\""
                            );
                            match Self::run_inference(
                                &mut session,
                                &g2p,
                                &sentence,
                                &cur_voice,
                                cur_speed,
                            ) {
                                Ok(samples) if !samples.is_empty() => {
                                    if job_id != job_id_worker.load(Ordering::SeqCst) {
                                        sink.stop();
                                        break;
                                    }
                                    sink.append(SamplesBuffer::new(
                                        1,
                                        PARADEE_SAMPLE_RATE,
                                        samples,
                                    ));
                                }
                                Ok(_) => {}
                                Err(e) => {
                                    error!("Paradee inference error: {e}");
                                }
                            }
                        }

                        while !sink.empty() {
                            if job_id != job_id_worker.load(Ordering::SeqCst) {
                                sink.stop();
                                break;
                            }
                            std::thread::sleep(std::time::Duration::from_millis(25));
                        }

                        if job_id == job_id_worker.load(Ordering::SeqCst) {
                            is_paused_worker.store(false, Ordering::SeqCst);
                            let _ = sentence_tx_worker.send(String::new());
                            let _ = state_tx_worker.send(PlaybackState::Stopped);
                            FloatingPillHud::hide();
                            notify_ui();
                        }
                    }
                    TtsCommand::Stop => {
                        if let Ok(mut guard) = sink_worker.lock() {
                            if let Some(prev) = guard.take() {
                                prev.stop();
                            }
                        }
                        is_paused_worker.store(false, Ordering::SeqCst);
                        let _ = sentence_tx_worker.send(String::new());
                        let _ = state_tx_worker.send(PlaybackState::Stopped);
                        FloatingPillHud::hide();
                        notify_ui();
                    }
                    TtsCommand::TogglePause => {
                        if let Ok(guard) = sink_worker.lock() {
                            if let Some(ref s) = *guard {
                                if s.is_paused() {
                                    s.play();
                                    is_paused_worker.store(false, Ordering::SeqCst);
                                    let _ = state_tx_worker.send(PlaybackState::Playing);
                                } else {
                                    s.pause();
                                    is_paused_worker.store(true, Ordering::SeqCst);
                                    let _ = state_tx_worker.send(PlaybackState::Paused);
                                }
                                notify_ui();
                            }
                        }
                    }
                }
            }
        });

        (
            Self {
                state_tx,
                sentence_tx,
                is_paused,
                cmd_tx,
                active_job_id,
                voice,
                speed_bits,
                volume_bits,
                active_sink,
                hud_anchor,
                egui_ctx,
            },
            state_rx,
        )
    }

    pub fn set_egui_ctx(&self, ctx: eframe::egui::Context) {
        if let Ok(mut guard) = self.egui_ctx.write() {
            *guard = Some(ctx);
        }
    }

    fn request_ui_repaint(&self) {
        if let Ok(guard) = self.egui_ctx.read() {
            if let Some(ref c) = *guard {
                c.request_repaint();
            }
        }
    }

    pub fn is_playing(&self) -> bool {
        !matches!(*self.state_tx.borrow(), PlaybackState::Stopped)
    }

    pub fn playback_state(&self) -> PlaybackState {
        self.state_tx.borrow().clone()
    }

    pub fn current_sentence(&self) -> String {
        self.sentence_tx.borrow().clone()
    }

    #[allow(dead_code)]
    pub fn hud_anchor(&self) -> Option<(i32, i32)> {
        self.hud_anchor.lock().ok().and_then(|g| *g)
    }

    fn run_inference(
        session: &mut Session,
        g2p: &MisakiG2p,
        sentence: &str,
        voice: &str,
        speed: f32,
    ) -> Result<Vec<f32>, String> {
        let british = voice.starts_with('b');
        let voice_idx = g2p.voice_index(voice);
        let chunks = g2p.text_to_token_chunks(sentence, british);
        let mut all_samples = Vec::new();

        for ids in chunks {
            let token_len = ids.len();
            let ids_tensor = Tensor::from_array(([1usize, token_len], ids))
                .map_err(|e| format!("input_ids tensor error: {e}"))?;
            let speed_tensor = Tensor::from_array(([1usize], vec![speed]))
                .map_err(|e| format!("speed tensor error: {e}"))?;
            let voice_tensor = Tensor::from_array(([1usize], vec![voice_idx]))
                .map_err(|e| format!("voice tensor error: {e}"))?;

            let outputs = session
                .run(ort::inputs![
                    "input_ids" => ids_tensor,
                    "speed" => speed_tensor,
                    "voice" => voice_tensor
                ])
                .map_err(|e| format!("ORT run error: {e}"))?;

            let (_shape, audio) = outputs[0]
                .try_extract_tensor::<f32>()
                .map_err(|e| format!("waveform extract error: {e}"))?;
            all_samples.extend_from_slice(audio);
        }

        debug!("Paradee synthesized {} audio samples @ 24kHz", all_samples.len());
        Ok(all_samples)
    }

    /// Resolves `onnxruntime.dll` relative to current_exe() (packaged release) or dev tree.
    pub fn find_onnxruntime_dll() -> PathBuf {
        let mut candidates = Vec::new();
        if let Ok(exe) = std::env::current_exe() {
            if let Some(dir) = exe.parent() {
                candidates.push(dir.join("onnxruntime.dll"));
                candidates.push(dir.join("lib").join("onnxruntime.dll"));
            }
        }
        let root = BrowserDetector::find_project_root();
        candidates.push(
            root.join(".venv")
                .join("Lib")
                .join("site-packages")
                .join("onnxruntime")
                .join("capi")
                .join("onnxruntime.dll"),
        );

        for c in candidates {
            if c.is_file() {
                return c;
            }
        }
        PathBuf::from("onnxruntime.dll")
    }

    /// Resolves `paradee_int8.onnx` relative to current_exe() (packaged release `./models/`) or dev tree.
    pub fn find_model_path() -> PathBuf {
        let mut candidates = Vec::new();
        if let Ok(exe) = std::env::current_exe() {
            if let Some(dir) = exe.parent() {
                candidates.push(dir.join("models").join("paradee_int8.onnx"));
                candidates.push(dir.join("paradee_int8.onnx"));
            }
        }
        let root = BrowserDetector::find_project_root();
        candidates.push(root.join("speak_that").join("model").join("paradee_int8.onnx"));
        candidates.push(PathBuf::from("models").join("paradee_int8.onnx"));
        candidates.push(PathBuf::from("speak_that").join("model").join("paradee_int8.onnx"));

        for c in candidates {
            if c.is_file() {
                return c;
            }
        }
        PathBuf::from("models").join("paradee_int8.onnx")
    }

    /// Speak text using the native Rust Paradee 8M TTS model
    pub fn speak(&self, text: &str) {
        if text.trim().is_empty() {
            return;
        }
        // Snapshot cursor position beside the user's click / selection for the floating Stop pill HUD
        let mut anchor = (200, 120);
        unsafe {
            let mut pt = POINT::default();
            if GetCursorPos(&mut pt).is_ok() {
                anchor = (pt.x, pt.y);
                if let Ok(mut guard) = self.hud_anchor.lock() {
                    *guard = Some(anchor);
                }
            }
        }

        let next_id = self.active_job_id.fetch_add(1, Ordering::SeqCst) + 1;
        if let Ok(mut guard) = self.active_sink.lock() {
            if let Some(prev) = guard.take() {
                prev.stop();
            }
        }
        info!("Sending speak request to native Paradee engine: {} chars", text.len());
        let first_preview: String = text.trim().lines().next().unwrap_or("Speaking...").chars().take(60).collect();
        let _ = self.sentence_tx.send(first_preview);
        let _ = self.state_tx.send(PlaybackState::Playing);
        FloatingPillHud::show_at(anchor.0, anchor.1);
        self.request_ui_repaint();

        let _ = self.cmd_tx.send(TtsCommand::Speak {
            job_id: next_id,
            text: text.to_string(),
        });
    }

    /// Stop playback immediately
    pub fn stop(&self) {
        info!("Stopping Paradee playback");
        self.active_job_id.fetch_add(1, Ordering::SeqCst);
        if let Ok(mut guard) = self.active_sink.lock() {
            if let Some(prev) = guard.take() {
                prev.stop();
            }
        }
        self.is_paused.store(false, Ordering::SeqCst);
        let _ = self.sentence_tx.send(String::new());
        let _ = self.state_tx.send(PlaybackState::Stopped);
        FloatingPillHud::hide();
        self.request_ui_repaint();
        let _ = self.cmd_tx.send(TtsCommand::Stop);
    }

    /// Toggle pause / resume
    pub fn toggle_pause(&self) {
        let _ = self.cmd_tx.send(TtsCommand::TogglePause);
    }

    /// Change active voice (e.g. "af_heart", "bf_isabella", "am_puck", "bm_fable")
    pub fn set_voice(&self, voice: &str) {
        if let Ok(mut guard) = self.voice.lock() {
            *guard = voice.to_string();
        }
    }

    /// Change speech speed (0.6x to 2.5x)
    pub fn set_speed(&self, speed: f32) {
        self.speed_bits.store(speed.to_bits(), Ordering::SeqCst);
    }

    /// Change volume (0.0 to 1.0)
    pub fn set_volume(&self, volume: f32) {
        let clamped = volume.clamp(0.0, 2.0);
        self.volume_bits.store(clamped.to_bits(), Ordering::SeqCst);
        if let Ok(guard) = self.active_sink.lock() {
            if let Some(ref s) = *guard {
                s.set_volume(clamped);
            }
        }
    }
}
