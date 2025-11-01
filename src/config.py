# src/config.py

# --- Video ---
# 5 seconds per frame => 0.2 FPS
FPS = 0.2  # Target FPS for the output video
RESOLUTION_SCALE = 0.5 # (unused now) Scale factor
WEBCAM_SCALE = 0.35  # Scale of the webcam overlay (35%)
WEBCAM_MARGIN = 20   # Margin from the corner

# --- Audio ---
SAMPLE_RATE = 48000
TEMP_AUDIO_FILENAME = "temp_audio.wav"

# --- Encoding ---

CRF = "28"  # Constant Rate Factor (lower value = higher quality, larger file size)
PRESET = "medium"  # Encoding speed vs. compression ratio (e.g., ultrafast, superfast, medium, slow)
