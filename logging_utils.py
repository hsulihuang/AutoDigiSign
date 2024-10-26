# logging_utils.py
import logging
import os
import sys
from datetime import datetime

def setup_logging(timestamp=None, log_directory='logs'):
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create log filenames for DEBUG and INFO levels
    log_filename_debug = f"autodigisign_debug_{timestamp}.log"
    log_filepath_debug = os.path.join(log_directory, log_filename_debug)
    log_filename_info = f"autodigisign_info_{timestamp}.log"
    log_filepath_info = os.path.join(log_directory, log_filename_info)

    # Set up the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Set root level to DEBUG to allow all messages

    # File handler to log everything at DEBUG level with UTF-8 encoding
    file_handler_debug = logging.FileHandler(log_filepath_debug, mode='w', encoding='utf-8')
    file_handler_debug.setLevel(logging.DEBUG)  # Record all levels of logs
    file_formatter_debug = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler_debug.setFormatter(file_formatter_debug)

    # File handler to log INFO level and above with UTF-8 encoding
    file_handler_info = logging.FileHandler(log_filepath_info, mode='w', encoding='utf-8')
    file_handler_info.setLevel(logging.INFO)  # Record only INFO and above
    file_formatter_info = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler_info.setFormatter(file_formatter_info)

    # Stream handler to log to console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)  # Log all messages to console
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)

    # Add handlers to the logger
    logger.addHandler(file_handler_debug)
    logger.addHandler(file_handler_info)
    logger.addHandler(console_handler)

    # Return log file paths if needed
    return log_filepath_debug, log_filepath_info

def redirect_console_output(log_directory, timestamp):
    """
    Redirect stdout and stderr to a console log file.
    
    Args:
    log_directory (str): The directory where the log file will be stored.
    timestamp (str): A timestamp to use in the log file name.
    
    Returns:
    tuple: Original stdout and stderr.
    """
    # Create the console log filepath
    log_filepath_console = os.path.join(log_directory, f'autodigisign_console_{timestamp}.log')
    
    # Save the original stdout and stderr
    original_stdout = sys.stdout
    original_stderr = sys.stderr

    # Redirect stdout and stderr
    sys.stdout = open(log_filepath_console, 'w', encoding='utf-8')
    sys.stderr = sys.stdout

    return log_filepath_console, original_stdout, original_stderr

def restore_console_output(original_stdout, original_stderr):
    """
    Restore stdout and stderr to their original state.
    
    Args:
    original_stdout: The original stdout.
    original_stderr: The original stderr.
    """
    sys.stdout.close()  # Close the log file before restoring
    sys.stdout = original_stdout
    sys.stderr = original_stderr
    