# Gemini Dayflow CLI - Activity Logger

This project contains a Python script to log computer activity on Windows. It records the active application and window title, saving the data to a CSV file.

## Setup

1.  Clone the repository.
2.  Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

To start logging your activity, run the main script:
```bash
python main.py
```

The script will create an `activity_log.csv` file in the root directory. Logging will continue until you press `Ctrl+C` in the terminal.
