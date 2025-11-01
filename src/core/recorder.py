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
from PIL import ImageGrab

from src.config import (CRF, FPS, PRESET, WEBCAM_MARGIN,
                        WEBCAM_SCALE)

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
        """Audio recording disabled for MVP."""
        return

    def record_frame(self):
        """Captures a single frame of the screen and webcam."""
        if not self.screen_available:
            return

        screen_frame_pil = ImageGrab.grab()

        # Resize to 480p (height=480), keep aspect ratio; ensure even width for encoder
        width, height = screen_frame_pil.size
        target_height = 480
        new_width = int(width * (target_height / height))
        new_width -= new_width % 2  # even width for codec compatibility
        resized_screen_pil = screen_frame_pil.resize((new_width, target_height))

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

        # Audio disabled in MVP: no audio thread

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
        logging.info("Encoding video (H.265, 480p)... this may take a moment.")
        if not self.video_frames:
            logging.warning("No frames to save.")
            return None

        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        output_dir = os.path.join("output", "videos")
        os.makedirs(output_dir, exist_ok=True)
        output_filename = os.path.join(output_dir, f"dayflow_{timestamp}.mp4")

        try:
            clip = ImageSequenceClip(self.video_frames, fps=FPS)
            # Write video only, H.265 codec
            clip.write_videofile(
                output_filename,
                codec="libx265",
                audio=False,
                ffmpeg_params=['-crf', CRF, '-preset', PRESET]
            )

            logging.info(f"\nRecording saved to {output_filename}")
            # Remember the last output path and return it for callers
            self.output_filename = output_filename
            return output_filename

        except Exception as e:
            logging.error(f"\nError during final encoding: {e}")
            return None
