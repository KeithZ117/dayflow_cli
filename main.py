import sys
import time
from datetime import datetime
import os
import threading

import cv2
from PIL import ImageGrab
from moviepy import AudioFileClip, ImageSequenceClip

# Local imports
from src.core.activity import get_active_window_info
from src.utils.file_handler import CsvLogger
import src.utils.analyze as analyze
from src.core.recording_logic import _record_audio, record_frame, FPS, WEBCAM_SCALE

def start_logging_and_recording(output_filename="output.mp4"):
    """
    Main loop to log activity and record screen based on activity.
    """
    header = ['Timestamp', 'Application', 'Window Title', 'URL', 'File Path']
    logger = CsvLogger('activity_log.csv', header=header)
    last_state = None
    
    print("Starting activity logging and recording... Press Ctrl+C to stop.")

    # --- Video Setup ---
    screen_size = ImageGrab.grab().size
    video_frames = []

    # --- Webcam Setup ---
    webcam = cv2.VideoCapture(0)
    if not webcam.isOpened():
        print("[Webcam] Error: Webcam not found.")
        webcam = None
    else:
        webcam_w = int(webcam.get(cv2.CAP_PROP_FRAME_WIDTH) * WEBCAM_SCALE)
        webcam_h = int(webcam.get(cv2.CAP_PROP_FRAME_HEIGHT) * WEBCAM_SCALE)

    # --- Audio Setup ---
    sample_rate = 48000
    temp_audio_file = "temp_audio.wav"
    stop_recording_flag = threading.Event()
    audio_thread = threading.Thread(target=_record_audio, args=(temp_audio_file, sample_rate, stop_recording_flag))
    audio_thread.start()

    last_frame_time = 0
    recording_started = False

    try:
        while True:
            current_state = get_active_window_info()
            app = current_state[0]

            if current_state != last_state and app is not None:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                logger.write_row([timestamp] + list(current_state))
                last_state = current_state

                if not recording_started:
                    recording_started = True
                
                last_frame_time = time.time()
                record_frame(video_frames, screen_size, webcam, webcam_w, webcam_h)


            if recording_started:
                current_time = time.time()
                if current_time - last_frame_time >= 1.0:
                    last_frame_time = current_time
                    record_frame(video_frames, screen_size, webcam, webcam_w, webcam_h)

            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nStopping activity logging and recording.")
    finally:
        stop_recording_flag.set()
        if webcam:
            webcam.release()
        audio_thread.join()
        
        logger.close()
        print("Log file closed.")

        # --- Final Encoding ---
        print("Encoding video... this may take a moment.")
        if video_frames:
            try:
                clip = ImageSequenceClip(video_frames, fps=FPS)
                if os.path.exists(temp_audio_file):
                    audio_clip = AudioFileClip(temp_audio_file)
                    final_clip = clip.with_audio(audio_clip)
                    final_clip.write_videofile(output_filename, codec="libx264", audio_codec="aac", ffmpeg_params=['-crf', '28', '-preset', 'medium'])
                    os.remove(temp_audio_file)
                else:
                    clip.write_videofile(output_filename, codec="libx264", ffmpeg_params=['-crf', '28', '-preset', 'medium'])
                
                print(f"\nRecording saved to {output_filename}")

            except Exception as e:
                print(f"\nError during final encoding: {e}")

# --- Execution Router ---

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        if command == 'analyze':
            analyze.analyze_activity()
    else:
        start_logging_and_recording()