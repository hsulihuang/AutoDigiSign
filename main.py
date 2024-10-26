# main.py
"""
Auto Digital Signature for NTUH
By Hsu-Li Huang (huang.hsuli@gmail.com)
Version: 1.3.0
Released: 2024-10-26
Python Version: 3.9.13
Dependencies:
    - Selenium
    - Tesseract OCR
    - Requests
    - OpenCV
Changelog:
    - V1.3.0 (2024-10-26): Encapsulate new functions and refactor functions into separate modules.
    - v1.2.2 (2024-10-24): Update email body summary.
    - v1.2.1 (2024-10-23): Update checking email sent successfully before closing the script.
    - v1.2.0 (2024-10-23): Update automatically sending the log file after finishing.
    - v1.1.0 (2024-10-23): Update logging settings.
    - v1.0.0 (2024-10-22): Initial release with automated login, CAPTCHA solving, digital signature functionality.
"""

# ========================
# Imports and Dependencies
# ========================

# Standard Library Imports
import logging
import os
import sys
import time
from datetime import datetime

# Third-Party Imports
import pytesseract
from selenium import webdriver
from selenium.webdriver.edge.service import Service

# Local Application Imports
from logging_utils import setup_logging, redirect_console_output, restore_console_output
from email_utils import generate_email_body, send_email_with_attachment
from autodigisign_utils import get_credentials, get_captcha_text, login, retry_login, navigate, digital_signature

# ======================
# Configuration Settings
# ======================

# Set working directory to the project root based on the operating system
# The use of os.name helps determine if the code is running on POSIX-compliant systems (like macOS or Linux, where os.name is 'posix') or on Windows (os.name is 'nt').
os.chdir('/Users/hsulihuang/programming/AutoDigiSign' if os.name == 'posix' else fr'D:\Users\ntuhuser\Desktop\AutoDigiSign')

# Get the current date and time in a formatted string
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # e.g., 20241021_103015

# ================
# Logging Settings
# ================

# Set up logging
log_filepath_debug, log_filepath_info = setup_logging(timestamp=timestamp, log_directory='logs')

# Redirect stdout and stderr to the console log file
log_filepath_console, original_stdout, original_stderr = redirect_console_output(log_directory='logs', timestamp=timestamp)

# Log a start message
logging.info(f"AutoDigiSign Started: {timestamp}")

# ================================
# Tesseract and WebDriver Settings
# ================================

# Set the path to the Tesseract executable
if os.name == 'posix':
    pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'  # For macOS/Linux
elif os.name == 'nt':
    pytesseract.pytesseract.tesseract_cmd = fr'D:\Users\ntuhuser\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'  # For Windows
else:
    logging.error("Unsupported Operating System for Tesseract setup.")
    raise EnvironmentError("Unsupported Operating System for Tesseract setup.")

# Set up the Selenium WebDriver path
if os.name == 'posix':
    # For macOS-arm64 with ChromeDriver (version 130)
    driver_path = os.path.join('WebDriver', 'chromedriver-mac-arm64-v130', 'chromedriver')
elif os.name == 'nt':
    # For Windows-x64 with Microsoft Edge WebDriver (version 125)
    driver_path = os.path.join('WebDriver', 'edgedriver_win64_v125', 'msedgedriver.exe')
else:
    logging.error("Unsupported Operating System for WebDriver setup.")
    raise EnvironmentError("Unsupported Operating System for WebDriver setup.")

# Set up the WebDriver
driver = webdriver.Edge(service=Service(driver_path))

# ================
# Main Application
# ================

# Open the specified URL
driver.get('https://portal.ntuh.gov.tw/General/Login.aspx')

# Get credentials including USERNAME, PASSWORD, PINCODE from a config file
USERNAME, PASSWORD, PINCODE = get_credentials()

# Retry login until successful
if not retry_login(driver, timestamp, USERNAME, PASSWORD, max_retries=30):
    logging.error("Exiting the script due to unsuccessful login.")
    sys.exit(1)  # Exit with failure code

# Navigate to the DigitalSignature page
navigate(driver)

# Read employee IDs from the text file
with open('employee_ids.txt', 'r') as file:
    employee_ids = [line.strip() for line in file]
##employee_ids = ['113900', '119377']  # this line for testing

# Loop through each employee ID in the list to try DigitalSignature
for EMPLOYEE in employee_ids:
    try:
        # Try DigitalSignature
        digital_signature(EMPLOYEE, PINCODE, driver)

    except Exception as e:
        logging.error(f"An error occurred while checking employee ID {EMPLOYEE}: {e}")

    # Optional: Pause for a moment before the next lookup (to avoid overwhelming the server)
    time.sleep(1)

# Close the WebDriver after finishing
driver.quit()

# ================
# Logging Settings
# ================

# Log a finish message
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
logging.info(f"AutoDigiSign Finished: {timestamp}")

# After script completion, restore stdout and stderr to the terminal
restore_console_output(original_stdout, original_stderr)

# ==============
# Email Settings
# ==============

# Generate email body using custom function
email_body = generate_email_body(log_filepath_info)

# Send the logs after completing the script
try:
    send_email_with_attachment(
        subject=f"{timestamp} AutoDigiSign Finished Successfully",
        body=email_body,
        log_filepath_info=log_filepath_info,
        log_filepath_debug=log_filepath_debug,
        log_filepath_console=log_filepath_console
    )
    print("Email sent successfully.")
    sys.exit(0)  # Exit with success code
except Exception as e:
    print(f"Failed to send email. Error: {e}")
    sys.exit(1)  # Exit with failure code
