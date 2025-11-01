import time
import wave

import cv2
import numpy as np
import soundcard as sc
from PIL import ImageGrab
import warnings

# --- Configuration ---
FPS = 1  # Target FPS for the output video
WEBCAM_SCALE = 0.35  # Scale of the webcam overlay (35%)
WEBCAM_MARGIN = 20   # Margin from the corner
RESOLUTION_SCALE = 0.5 # Scale of the screen recording resolution

def _record_audio(output_filename, sample_rate, stop_recording_flag):
    """Records system audio and microphone to a WAV file in a separate thread."""
    try:
        # Find loopback device
        loopback_mic = None
        mics = sc.all_microphones(include_loopback=True)
        for mic in mics:
            if mic.isloopback:
                loopback_mic = mic
                break
        
        if not loopback_mic:
            print("[Audio] Error: No loopback device found. System audio will not be recorded.")
            return

        default_mic = sc.default_microphone()
        if not default_mic:
            print("[Audio] Error: No default microphone found. System audio will not be recorded.")
            return

        # Use smaller chunks to avoid buffer overflow
        # Recording 0.1 seconds at a time (10 chunks per second)
        chunk_size = sample_rate // 10  # 4800 frames = 0.1 seconds

        with loopback_mic.recorder(samplerate=sample_rate, blocksize=chunk_size) as loopback_rec, \
             default_mic.recorder(samplerate=sample_rate, blocksize=chunk_size) as mic_rec, \
             wave.open(output_filename, 'wb') as wav_file:

            print("[Audio] Recording audio... (System + Mic)")
            wav_file.setnchannels(2)  # write stereo output
            wav_file.setsampwidth(2)  # 16-bit PCM
            wav_file.setframerate(sample_rate)

            while not stop_recording_flag.is_set():
                try:
                    # Record smaller chunks from speaker and microphone
                    loopback_data = loopback_rec.record(numframes=chunk_size)
                    mic_data = mic_rec.record(numframes=chunk_size)

                    # Mix audio by averaging. Ensure they have the same shape.
                    min_len = min(len(loopback_data), len(mic_data))
                    if min_len == 0:
                        continue
                    loopback_chunk = loopback_data[:min_len]
                    mic_chunk = mic_data[:min_len]

                    if loopback_chunk.ndim == 1:
                        loopback_chunk = loopback_chunk[:, np.newaxis]
                    if mic_chunk.ndim == 1:
                        mic_chunk = mic_chunk[:, np.newaxis]

                    min_channels = min(loopback_chunk.shape[1], mic_chunk.shape[1])
                    if min_channels == 0:
                        continue
                    loopback_chunk = loopback_chunk[:, :min_channels]
                    mic_chunk = mic_chunk[:, :min_channels]

                    mixed_data = (loopback_chunk + mic_chunk) / 2.0

                    # Ensure stereo by duplicating mono channel if necessary
                    if mixed_data.shape[1] == 1:
                        mixed_data = np.repeat(mixed_data, 2, axis=1)
                    elif mixed_data.shape[1] > 2:
                        mixed_data = mixed_data[:, :2]

                    pcm_data = np.clip(mixed_data, -1.0, 1.0)
                    pcm_data = (pcm_data * 32767).astype(np.int16)
                    wav_file.writeframes(pcm_data.tobytes())
                
                except Exception as chunk_error:
                    # Continue recording even if one chunk fails
                    continue

    except Exception as e:
        print(f"[Audio] Error: {e}. Audio will not be recorded.")

    print("[Audio] Recording stopped.")

def record_frame(video_frames, screen_size, webcam, webcam_w, webcam_h):
    print(f"Recording frame at {time.strftime('%H:%M:%S')}")

    # Capture screen
    screen_frame_pil = ImageGrab.grab()
    
    # Resize frame
    width, height = screen_frame_pil.size
    new_width = int(width * RESOLUTION_SCALE)
    new_height = int(height * RESOLUTION_SCALE)
    resized_screen_pil = screen_frame_pil.resize((new_width, new_height))

    screen_frame_np = np.array(resized_screen_pil)
    screen_frame_bgr = cv2.cvtColor(screen_frame_np, cv2.COLOR_RGB2BGR)

    # Capture and overlay webcam
    if webcam:
        ret, webcam_frame = webcam.read()
        if ret:
            webcam_resized = cv2.resize(webcam_frame, (webcam_w, webcam_h))
            # Place webcam in the top-right corner
            y_offset = WEBCAM_MARGIN # Top margin
            x_offset = new_width - webcam_w - WEBCAM_MARGIN # Right margin
            screen_frame_bgr[y_offset:y_offset+webcam_h, x_offset:x_offset+webcam_w] = webcam_resized

            # Add timestamp
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.5
            font_color = (255, 255, 255) # White
            line_type = 1
            text = time.strftime('%Y-%m-%d %H:%M:%S')
            text_size = cv2.getTextSize(text, font, font_scale, line_type)[0]
            text_x = x_offset
            text_y = y_offset + webcam_h + text_size[1] + 5 # 5 pixels margin
            cv2.putText(screen_frame_bgr, text, (text_x, text_y), font, font_scale, font_color, line_type)

    video_frames.append(cv2.cvtColor(screen_frame_bgr, cv2.COLOR_BGR2RGB))
