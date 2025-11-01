try:
    import win32gui
    import win32process
    import psutil
except ImportError:
    print("Error: Missing required libraries. Please run 'pip install -r requirements.txt'")
    exit()

def get_active_window_info():
    """
    Gets information about the currently active window, including the
    application name, window title, browser URL, and editing file path.
    """
    try:
        hwnd = win32gui.GetForegroundWindow()
        pid = win32process.GetWindowThreadProcessId(hwnd)[1]
        process_name = psutil.Process(pid).name()
        window_title = win32gui.GetWindowText(hwnd)
        url = None
        file_path = None

        # --- Browser URL detection (Placeholder) ---
        if process_name.lower() in ["chrome.exe", "msedge.exe", "firefox.exe"]:
            url = "URL detection requires advanced implementation"

        # --- Editing file path detection (Simple version) ---
        elif process_name.lower() in ["code.exe", "notepad++.exe", "sublime_text.exe", "notepad.exe"]:
            if " - " in window_title:
                potential_path = window_title.split(" - ")[0]
                file_path = potential_path

        return process_name, window_title, url, file_path

    except Exception as e:
        # Return None for all fields if any error occurs (e.g., process not found)
        return None, None, None, None
