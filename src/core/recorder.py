# src/core/recorder.py

import os
import threading
import time
import wave
from datetime import datetime
import logging

import cv2
import numpy as np
from moviepy.video.io.ImageSequenceClip import ImageSequenceClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from PIL import ImageGrab

from src.config import (CRF, FPS, PRESET, RESOLUTION_SCALE, WEBCAM_MARGIN,
                        WEBCAM_SCALE, SAMPLE_RATE, TEMP_AUDIO_FILENAME, OUTPUT_FILENAME)

try:
    import soundcard as sc
except (ImportError, AssertionError) as e:
    logging.warning(f"Soundcard library not available or failed to initialize: {e}. Audio will not be recorded.")
    sc = None


class ScreenRecorder:
    def __init__(self):
        self.is_recording = False
        self.video_frames = []
        self.audio_thread = None
        self.stop_event = threading.Event()
        self.screen_available = True

        try:
            self.screen_size = ImageGrab.grab().size
        except OSError as e:
            logging.error(f"Failed to connect to X server: {e}. Screen recording will not be available.")
            self.screen_available = False
            self.screen_size = (0, 0)

        self.webcam = self._setup_webcam()

    def _setup_webcam(self):
        webcam = cv2.VideoCapture(0)
        if not webcam.isOpened():
            logging.warning("[Webcam] Error: Webcam not found.")
            return None
        return webcam

    def _record_audio(self):
        """Records system (loopback) audio to a WAV file."""
        if not sc:
            return

        try:
            loopback_mic = sc.get_microphone(id=str(sc.default_speaker().name), include_loopback=True)

            chunk_size = SAMPLE_RATE // 10

            with loopback_mic.recorder(samplerate=SAMPLE_RATE, blocksize=chunk_size) as loopback_rec, \
                 wave.open(TEMP_AUDIO_FILENAME, 'wb') as wav_file:

                logging.info("[Audio] Recording audio... (System Only)")
                wav_file.setnchannels(2)
                wav_file.setsampwidth(2)
                wav_file.setframerate(SAMPLE_RATE)

                while not self.stop_event.is_set():
                    try:
                        data = loopback_rec.record(numframes=chunk_size)
                        if len(data) == 0:
                            continue

                        # Ensure stereo: expand mono, limit >2ch to first two
                        if getattr(data, 'ndim', 1) == 1:
                            data = data.reshape(-1, 1)
                        if data.shape[1] == 1:
                            data = np.repeat(data, 2, axis=1)
                        elif data.shape[1] > 2:
                            data = data[:, :2]

                        pcm_data = (np.clip(data, -1.0, 1.0) * 32767).astype(np.int16)
                        wav_file.writeframes(pcm_data.tobytes())
                    except Exception:
                        continue
        except Exception as e:
            logging.error(f"[Audio] Error: {e}. Audio will not be recorded.")
        logging.info("[Audio] Recording stopped.")

    def record_frame(self):
        """Captures a single frame of the screen and webcam."""
        if not self.screen_available:
            return

        screen_frame_pil = ImageGrab.grab()

        width, height = screen_frame_pil.size
        new_width = int(width * RESOLUTION_SCALE)
        new_height = int(height * RESOLUTION_SCALE)
        resized_screen_pil = screen_frame_pil.resize((new_width, new_height))

        screen_frame_bgr = cv2.cvtColor(np.array(resized_screen_pil), cv2.COLOR_RGB2BGR)

        if self.webcam:
            ret, webcam_frame = self.webcam.read()
            if ret:
                webcam_w = int(self.webcam.get(cv2.CAP_PROP_FRAME_WIDTH) * WEBCAM_SCALE)
                webcam_h = int(self.webcam.get(cv2.CAP_PROP_FRAME_HEIGHT) * WEBCAM_SCALE)
                webcam_resized = cv2.resize(webcam_frame, (webcam_w, webcam_h))

                y_offset = WEBCAM_MARGIN
                x_offset = new_width - webcam_w - WEBCAM_MARGIN
                screen_frame_bgr[y_offset:y_offset+webcam_h, x_offset:x_offset+webcam_w] = webcam_resized

                # Add timestamp
                text = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                font = cv2.FONT_HERSHEY_SIMPLEX
                cv2.putText(screen_frame_bgr, text, (x_offset, y_offset + webcam_h + 20), font, 0.5, (255, 255, 255), 1)

        self.video_frames.append(cv2.cvtColor(screen_frame_bgr, cv2.COLOR_BGR2RGB))

    def start_recording(self):
        if not self.screen_available:
            return

        if self.is_recording:
            logging.info("Already recording.")
            return

        self.is_recording = True
        self.stop_event.clear()

        if sc:
            self.audio_thread = threading.Thread(target=self._record_audio)
            self.audio_thread.start()

        logging.info("Recording started.")

    def stop_recording(self):
        if not self.is_recording:
            logging.info("Not recording.")
            return

        self.is_recording = False
        self.stop_event.set()
        if self.audio_thread:
            self.audio_thread.join()
        if self.webcam:
            self.webcam.release()

        logging.info("Recording stopped.")

    def save_recording(self):
        logging.info("Encoding video... this may take a moment.")
        if not self.video_frames:
            logging.warning("No frames to save.")
            return

        try:
            clip = ImageSequenceClip(self.video_frames, fps=FPS)
            if os.path.exists(TEMP_AUDIO_FILENAME):
                audio_clip = AudioFileClip(TEMP_AUDIO_FILENAME)
                final_clip = clip.with_audio(audio_clip)
                final_clip.write_videofile(OUTPUT_FILENAME, codec="libx264", audio_codec="aac", ffmpeg_params=['-crf', CRF, '-preset', PRESET])
                os.remove(TEMP_AUDIO_FILENAME)
            else:
                clip.write_videofile(OUTPUT_FILENAME, codec="libx264", ffmpeg_params=['-crf', CRF, '-preset', PRESET])

            logging.info(f"\nRecording saved to {OUTPUT_FILENAME}")

        except Exception as e:
            logging.error(f"\nError during final encoding: {e}")
