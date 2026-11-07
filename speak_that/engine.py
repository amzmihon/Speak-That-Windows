"""Paradee Text-To-Speech Engine with Sentence Streaming and Async Audio Playback."""

import os
import queue
import re
import threading
import time
import numpy as np
import sounddevice as sd
from paradee import Paradee, SAMPLE_RATE, VOICES


class TTSEngine:
    """High-performance Paradee TTS engine with streaming sentence playback."""

    def __init__(self, voice="bf_isabella", speed=1.05, volume=1.0):
        self.voice = voice
        self.speed = speed
        self.volume = volume

        # Paradee instance
        self.model = None
        self._is_ready = False

        # Queues & Threading
        self._text_queue = queue.Queue()
        self._audio_queue = queue.Queue(maxsize=15)
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()  # cleared when paused, set when running
        self._pause_event.set()

        self._is_speaking = False
        self._current_sentence = ""

        # Callbacks
        self.on_status_change = None  # fn(status: str)
        self.on_sentence = None       # fn(sentence: str)
        self.on_complete = None       # fn()

        # Initialize and pre-warm in background thread
        self._init_thread = threading.Thread(target=self._initialize_model, daemon=True)
        self._init_thread.start()

        # Background worker threads
        self._synth_thread = threading.Thread(target=self._synthesis_worker, daemon=True)
        self._synth_thread.start()

        self._play_thread = threading.Thread(target=self._playback_worker, daemon=True)
        self._play_thread.start()

    def _initialize_model(self):
        """Loads Paradee ONNX graph and pre-warms phonemizers."""
        try:
            self._notify_status("Loading Paradee TTS model...")

            # 1. Prefer local bundled model in package directory
            base_dir = os.path.dirname(os.path.abspath(__file__))
            local_model = os.path.join(base_dir, "model", "paradee_int8.onnx")
            local_config = os.path.join(base_dir, "model", "config.json")

            model_path, config_path = None, None
            if os.path.exists(local_model) and os.path.exists(local_config):
                model_path, config_path = local_model, local_config

            # 2. Attempt offline load from HuggingFace cache if local bundle not present
            if not model_path or not config_path:
                try:
                    from huggingface_hub import hf_hub_download
                    model_path = hf_hub_download("sahilmahendrakar/Paradee-8M-v1.2", "onnx/paradee_int8.onnx", revision="v1.2", local_files_only=True)
                    config_path = hf_hub_download("sahilmahendrakar/Paradee-8M-v1.2", "config.json", revision="v1.2", local_files_only=True)
                except Exception:
                    model_path, config_path = None, None

            if model_path and config_path:
                self.model = Paradee(version="1.2", quantized=True, model_path=model_path, config_path=config_path)
            else:
                self.model = Paradee(version="1.2", quantized=True)

            # Pre-warm G2P for both American and British accents
            self.model.g2p(british=False)
            self.model.g2p(british=True)

            # Run a tiny warmup inference
            _ = self.model("Ready.", voice="bf_isabella", speed=1.0)
            self._is_ready = True
            self._notify_status("Ready")
        except Exception as e:
            print(f"[TTSEngine] Initialization error: {e}")
            self._notify_status(f"Error loading model: {e}")

    def is_ready(self):
        return self._is_ready

    def _notify_status(self, status):
        if self.on_status_change:
            try:
                self.on_status_change(status)
            except Exception:
                pass

    def _notify_sentence(self, sentence):
        self._current_sentence = sentence
        if self.on_sentence:
            try:
                self.on_sentence(sentence)
            except Exception:
                pass

    def _notify_complete(self):
        self._is_speaking = False
        self._current_sentence = ""
        self._notify_status("Ready")
        if self.on_complete:
            try:
                self.on_complete()
            except Exception:
                pass

    def set_voice(self, voice):
        if voice in VOICES.get("1.2", []):
            self.voice = voice

    def set_speed(self, speed):
        self.speed = max(0.6, min(2.5, float(speed)))

    def set_volume(self, volume):
        self.volume = max(0.0, min(1.0, float(volume)))

    def get_voices(self):
        return VOICES.get("1.2", ["af_heart", "bf_isabella", "am_puck", "bm_fable"])

    @staticmethod
    def split_sentences(text):
        """Clean and split text into speakable sentence chunks."""
        text = text.strip()
        # Clean up repeated whitespace
        text = re.sub(r'[ \t]+', ' ', text)
        # Split on sentence terminals or newlines
        raw_parts = re.split(r'(?<=[.!?…;])\s+|\n+', text)
        sentences = []
        for p in raw_parts:
            p = p.strip()
            if not p:
                continue
            # If a sentence is extraordinarily long (>350 chars), break at commas or clauses
            if len(p) > 350:
                sub_parts = re.split(r'(?<=[,:])\s+', p)
                curr = ""
                for sp in sub_parts:
                    if len(curr) + len(sp) > 300 and curr:
                        sentences.append(curr.strip())
                        curr = sp
                    else:
                        curr = f"{curr} {sp}".strip()
                if curr:
                    sentences.append(curr.strip())
            else:
                sentences.append(p)
        return sentences

    def speak(self, text):
        """Cancel any ongoing speech and start speaking the new text immediately."""
        if not text or not text.strip():
            return

        self.stop()
        time.sleep(0.02)  # allow workers to acknowledge stop

        self._stop_event.clear()
        self._pause_event.set()
        self._is_speaking = True

        sentences = self.split_sentences(text)
        if not sentences:
            self._notify_complete()
            return

        self._notify_status("Synthesizing...")
        for s in sentences:
            self._text_queue.put(s)

        # Sentinel to signal end of stream
        self._text_queue.put(None)

    def pause(self):
        if self._is_speaking and self._pause_event.is_set():
            self._pause_event.clear()
            self._notify_status("Paused")

    def resume(self):
        if self._is_speaking and not self._pause_event.is_set():
            self._pause_event.set()
            self._notify_status("Speaking")

    def toggle_pause(self):
        if self._pause_event.is_set():
            self.pause()
        else:
            self.resume()

    def is_paused(self):
        return self._is_speaking and not self._pause_event.is_set()

    def is_speaking(self):
        return self._is_speaking

    def stop(self):
        """Immediately halts all synthesis and audio playback."""
        self._stop_event.set()
        self._pause_event.set()

        # Flush text queue
        try:
            while True:
                self._text_queue.get_nowait()
                self._text_queue.task_done()
        except queue.Empty:
            pass

        # Flush audio queue
        try:
            while True:
                self._audio_queue.get_nowait()
                self._audio_queue.task_done()
        except queue.Empty:
            pass

        if self._is_speaking:
            self._notify_complete()

    def _synthesis_worker(self):
        """Synthesizes text sentences into audio arrays and feeds the playback queue."""
        while True:
            try:
                sentence = self._text_queue.get()
                if self._stop_event.is_set():
                    self._text_queue.task_done()
                    continue

                if sentence is None:
                    # End of current reading job
                    self._audio_queue.put(None)
                    self._text_queue.task_done()
                    continue

                # Wait if model is still downloading/initializing
                while not self._is_ready:
                    if self._stop_event.is_set():
                        break
                    time.sleep(0.1)

                if self._stop_event.is_set():
                    self._text_queue.task_done()
                    continue

                # Generate speech with Paradee
                try:
                    audio = self.model(sentence, speed=self.speed, voice=self.voice)
                except Exception as e:
                    print(f"[TTSEngine] Synthesis error for '{sentence[:20]}...': {e}")
                    audio = np.zeros(0, dtype=np.float32)

                if not self._stop_event.is_set():
                    self._audio_queue.put((sentence, audio))

                self._text_queue.task_done()
            except Exception as e:
                print(f"[TTSEngine] Synthesis worker error: {e}")
                time.sleep(0.1)

    def _playback_worker(self):
        """Streams audio chunks to sounddevice output."""
        while True:
            try:
                item = self._audio_queue.get()
                if self._stop_event.is_set():
                    self._audio_queue.task_done()
                    continue

                if item is None:
                    # Completed speaking all queued sentences
                    self._notify_complete()
                    self._audio_queue.task_done()
                    continue

                sentence, audio = item
                if len(audio) == 0:
                    self._audio_queue.task_done()
                    continue

                # Apply volume scaling
                scaled_audio = (audio * self.volume).astype(np.float32)
                np.clip(scaled_audio, -1.0, 1.0, out=scaled_audio)

                self._notify_status("Speaking")
                self._notify_sentence(sentence)

                # Play via sounddevice stream with pause & stop responsiveness
                try:
                    with sd.OutputStream(samplerate=SAMPLE_RATE, channels=1, dtype='float32') as stream:
                        chunk_size = 2400  # 100ms slices for responsive pause/stop
                        idx = 0
                        total_samples = len(scaled_audio)

                        while idx < total_samples and not self._stop_event.is_set():
                            # Handle Pause
                            while not self._pause_event.is_set() and not self._stop_event.is_set():
                                time.sleep(0.04)

                            if self._stop_event.is_set():
                                break

                            end = min(idx + chunk_size, total_samples)
                            slice_data = scaled_audio[idx:end]
                            stream.write(slice_data)
                            idx = end

                except Exception as e:
                    print(f"[TTSEngine] Playback error: {e}")

                self._audio_queue.task_done()
            except Exception as e:
                print(f"[TTSEngine] Playback worker error: {e}")
                time.sleep(0.1)
