import csv
import os

class CsvLogger:
    """
    A utility class to handle writing logs to a CSV file.
    """
    def __init__(self, filename='activity_log.csv', header=None):
        """
        Initializes the logger.
        
        Args:
            filename (str): The name of the CSV file to write to.
            header (list): The header row for the CSV file.
        """
        self.filename = filename
        self.file_exists = os.path.isfile(self.filename)
        self.file = open(self.filename, 'a', newline='', encoding='utf-8')
        self.writer = csv.writer(self.file)
        
        if not self.file_exists and header:
            self.write_row(header)

    def write_row(self, row_data):
        """Writes a single row of data to the CSV file."""
        self.writer.writerow(row_data)
        self.file.flush()

    def close(self):
        """Closes the file handle."""
        self.file.close()
