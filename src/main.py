# main.py

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
from utils.autodigisign_utils import get_credentials, retry_login, navigate, get_employees, digital_signature
from utils.email_utils import generate_email_body, send_email_with_attachment
from utils.item_locator import find_item
from utils.logging_utils import setup_logging, redirect_console_output, restore_console_output

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
log_directory = os.path.join('outputs', 'logs')
debug_log_filepath, info_log_filepath = setup_logging(log_directory=log_directory, timestamp=timestamp)

# Redirect stdout and stderr to the console log file
console_log_filepath, original_stdout, original_stderr = redirect_console_output(log_directory=log_directory, timestamp=timestamp)

# Log a start message
logging.info(f"AutoDigiSign Started: {timestamp}")

# ===============================
# Files and Folders Path Settings
# ===============================

skip_dirs = ['captcha', 'logs', 'storehouse', 'WebDriver']
credentials_filepath = find_item('credentials.ini', skip_dirs=skip_dirs)
email_config_filepath = find_item('email_config.ini', skip_dirs=skip_dirs)
employee_list_filepath = find_item('employee_list.txt', skip_dirs=skip_dirs)

captcha_folderpath = os.path.join('outputs', 'captcha')
logs_folderpath = os.path.join('outputs', 'logs')

# =====================================
# Tesseract and WebDriver Path Settings
# =====================================

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

# ================
# Main Application
# ================

# Set up the WebDriver
driver = webdriver.Edge(service=Service(driver_path))

# Open the specified URL
driver.get('https://portal.ntuh.gov.tw/General/Login.aspx')

# Get credentials including USERNAME, PASSWORD, PINCODE from a config file
USERNAME, PASSWORD, PINCODE = get_credentials(credentials_filepath)

# Retry login until successful
if not retry_login(driver, timestamp, USERNAME, PASSWORD, max_retries=30):
    logging.error("Exiting the script due to unsuccessful login.")
    sys.exit(1)  # Exit with failure code

# Navigate to the DigitalSignature page
navigate(driver)

# Read employee IDs and names from the text file
employees = get_employees(employee_list_filepath)

# Iterate through the employee list as follows
for employee in employees:
    EMPLOYEE_ID = employee['id']
    EMPLOYEE_NAME = employee['name']
    try:
        # Perform digital signature operation with EMPLOYEE_ID
        digital_signature(EMPLOYEE_ID, PINCODE, driver)
        # Optionally log or print the name for better context
        logging.info(f"Digital signature performed for Employee ID: {EMPLOYEE_ID}, Name: {EMPLOYEE_NAME}")
    except Exception as e:
        logging.error(f"An error occurred while processing Employee ID: {EMPLOYEE_ID}, Name: {EMPLOYEE_NAME}: {e}")

    # Optional: Pause for a moment before the next lookup (to avoid overwhelming the server)
    time.sleep(1)

# Close the WebDriver after finishing
driver.quit()

# ================
# Logging Settings
# ================

# Log a finish message
timestamp_finish = datetime.now().strftime("%Y%m%d_%H%M%S")
logging.info(f"AutoDigiSign Finished: {timestamp_finish}")

# After script completion, restore stdout and stderr to the terminal
restore_console_output(original_stdout, original_stderr)

# ==============
# Email Settings
# ==============

# Generate email body using custom function
email_body = generate_email_body(info_log_filepath)

# Send the logs after completing the script
try:
    send_email_with_attachment(
        email_config_filepath=email_config_filepath,
        subject=f"{timestamp} AutoDigiSign Finished Successfully",
        body=email_body,
        info_log_filepath=info_log_filepath,
        debug_log_filepath=debug_log_filepath,
        console_log_filepath=console_log_filepath
    )
    print("Email sent successfully.")
    sys.exit(0)  # Exit with success code
except Exception as e:
    print(f"Failed to send email. Error: {e}")
    sys.exit(1)  # Exit with failure code
