import csv
from datetime import datetime, timedelta

def format_timedelta(td):
    """Formats a timedelta object into a HH:MM:SS string."""
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"

def analyze_activity(filepath='activity_log.csv'):
    """
    Reads the activity log CSV, calculates the duration of each activity,
    and prints a summary of time spent on each task.
    """
    try:
        with open(filepath, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)  # Skip header
            records = []
            for row in reader:
                try:
                    timestamp = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S')
                    # Columns: Timestamp, Application, Window Title, ...
                    records.append({'timestamp': timestamp, 'app': row[1], 'title': row[2]})
                except (ValueError, IndexError):
                    # Skip malformed rows
                    continue
    except FileNotFoundError:
        print(f"Error: Log file not found at '{filepath}'")
        print("Please run 'python main.py' first to generate some activity data.")
        return
    except Exception as e:
        print(f"An error occurred while reading the file: {e}")
        return

    if len(records) < 2:
        print("Not enough data to analyze. At least two log entries are required.")
        return

    title_summary = {}
    app_summary = {}  # For app-level aggregation
    
    # Iterate up to the second-to-last record
    for i in range(len(records) - 1):
        current_rec = records[i]
        next_rec = records[i+1]
        
        duration = next_rec['timestamp'] - current_rec['timestamp']
        
        # Aggregate by (app, title)
        title_key = (current_rec['app'], current_rec['title'])
        title_summary[title_key] = title_summary.get(title_key, timedelta(0)) + duration
        
        # Aggregate by app name
        app_key = current_rec['app']
        app_summary[app_key] = app_summary.get(app_key, timedelta(0)) + duration

    # --- Detailed Summary by Title ---
    sorted_title_summary = sorted(title_summary.items(), key=lambda item: item[1], reverse=True)

    print("\n--- Detailed Activity Summary ---")
    for (app, title), duration in sorted_title_summary:
        formatted_duration = format_timedelta(duration)
        display_title = title if len(title) < 70 else title[:67] + "..."
        print(f"[{formatted_duration}] {app:<20} - {display_title}")

    # --- Summary by Application ---
    sorted_app_summary = sorted(app_summary.items(), key=lambda item: item[1], reverse=True)
    
    print("\n--- Application Time Summary ---")
    for app, duration in sorted_app_summary:
        formatted_duration = format_timedelta(duration)
        print(f"[{formatted_duration}] {app}")

if __name__ == "__main__":
    analyze_activity()