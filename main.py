import sys
import os
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
            video_path = recorder.save_recording()
        
        logger.close()
        print("Log file closed.")

        # --- Auto upload and analyze video ---
        try:
            if 'video_path' in locals() and video_path:
                from src.api.files import upload_file, wait_until_active, analyze_file_resource

                print("\nUploading recording to Gemini Files API...")
                meta = upload_file(video_path, display_name=os.path.basename(video_path))
                file_name = meta.get('name')
                if not file_name:
                    print("Upload returned no file resource name; skipping analysis.")
                    return

                print("Waiting for file to become ACTIVE...")
                wait_until_active(file_name)

                default_prompt = (
                    "请分析视频中我在做什么，按时间轴总结关键活动。"
                    "右上角有我的webcam：评估是否专注（如是否注视屏幕、明显分心动作）。"
                    "webcam下方显示现实时间：请识别关键片段的时间戳并在报告中标注，时间格式统一为MM:SS。"
                    "输出结构：\n1) 总览\n2) 关键事件（含时间戳）\n3) 专注度评估\n4) 其他观察\n5) 总结与建议。"
                )

                print("Analyzing video with Gemini...")
                analysis_text = analyze_file_resource(
                    file_name,
                    prompt=default_prompt,
                    model="gemini-2.5-flash",
                )

                logs_dir = os.path.join("output", "dailylogs")
                os.makedirs(logs_dir, exist_ok=True)
                base = os.path.splitext(os.path.basename(video_path))[0]
                out_path = os.path.join(logs_dir, f"{base}.txt")
                with open(out_path, "w", encoding="utf-8") as fh:
                    fh.write(analysis_text)
                print(f"Analysis saved: {out_path}")
        except Exception as e:
            print(f"Auto upload/analyze failed: {e}")

# --- Execution Router ---

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        if command == 'analyze':
            analyze.analyze_activity()
    else:
        start_logging_and_recording()
