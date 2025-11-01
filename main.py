import sys
import time
from datetime import datetime

from src.core.activity import get_active_window_info
from src.utils.file_handler import CsvLogger
import src.utils.analyze as analyze
from src.core.recorder import ScreenRecorder
from src.config import FPS

def start_logging_and_recording():
    """
    Main loop to log activity and record screen.
    """
    header = ['Timestamp', 'Application', 'Window Title', 'URL', 'File Path']
    logger = CsvLogger('activity_log.csv', header=header)
    last_state = None
    
    print("Starting activity logging and recording... Press Ctrl+C to stop.")

    recorder = ScreenRecorder()

    try:
        while True:
            current_state = get_active_window_info()
            app = current_state[0]

            if current_state != last_state and app is not None:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                logger.write_row([timestamp] + list(current_state))
                last_state = current_state

                if not recorder.is_recording:
                    recorder.start_recording()

            if recorder.is_recording:
                recorder.record_frame()

            time.sleep(1 / FPS)
            
    except KeyboardInterrupt:
        print("\nStopping activity logging and recording.")
    finally:
        if recorder.is_recording:
            recorder.stop_recording()
            recorder.save_recording()
        
        logger.close()
        print("Log file closed.")

# --- Execution Router ---

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        if command == 'analyze':
            analyze.analyze_activity()
    else:
        start_logging_and_recording()
