"""
Auto Digital Signature for NTUH
By Hsu-Li Huang (huang.hsuli@gmail.com)
Version: 1.0.0
Released: 2024-10-22
Python Version: 3.9.13
Dependencies:
    - Selenium
    - Tesseract OCR
    - Requests
    - OpenCV
Changelog:
    - v1.0.0 (2024-10-22): Initial release with automated login, CAPTCHA solving, digital signature functionality.
"""

# ========================
# Imports and Dependencies
# ========================

# Standard Library Imports
import configparser
import logging
import os
import re
import time
from datetime import datetime

# Third-Party Imports
import cv2
import numpy as np
import pytesseract
import requests
from PIL import Image
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.edge.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Local Application Imports
# (if any custom modules in the future)

# ======================
# Configuration Settings
# ======================

# Set working directory to the project root based on the operating system
# The use of os.name helps determine if the code is running on POSIX-compliant systems (like macOS or Linux, where os.name is 'posix') or on Windows (os.name is 'nt').
os.chdir('/Users/hsulihuang/programming/AutoDigiSign' if os.name == 'posix' else fr'D:\Users\ntuhuser\Desktop\AutoDigiSign')

# Get the current date and time in a formatted string
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # e.g., 20241021_103015

# Set up logging to log to a file with a timestamp in the name, and also print to console
log_filename = f"autodigisign_{timestamp}.log"
logging.basicConfig(
    level=logging.INFO,  # Set the minimum logging level; (Messages of Severity: DEBUG < INFO < WARNING < ERROR < CRITICAL)
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join('logs', log_filename), mode='w'),  # Write logs to a file; ('w' to overwrite each time, 'a' to append)
        logging.StreamHandler()  # Print logs to the console
    ]
)

# Log a start message
logging.info(f"AutoDigiSign Started: {timestamp}")

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

# Login credentials
# Create a ConfigParser instance
config = configparser.ConfigParser()

# Read the config file
config.read('credentials.ini')

# Get credentials from the config file
USERNAME = config['credentials']['username']
PASSWORD = config['credentials']['password']
PINCODE = config['credentials']['pincode']

# Read employee IDs from the text file
with open('employee_ids.txt', 'r') as file:
    employee_ids = [line.strip() for line in file]
#employee_ids = ['113900', '119377', '121260']  # for testing

# ====================
# Function Definitions
# ====================

# Function to download the CAPTCHA image and extract text
def get_captcha_text(driver):
    # Locate the image element by its ID
    img_element = driver.find_element(By.ID, 'imgVerifyCode')

    # Get the 'src' attribute of the image element
    img_url = img_element.get_attribute('src')
    logging.info(f"CAPTCHA image source URL: {img_url}")

    # Send a request to get the image
    response = requests.get(img_url)

    # Check the response status
    if response.status_code == 200:
        # Specify the file name using the timestamp and location where to save the image
        img_file_path = os.path.join('captcha', f'captcha_image_{timestamp}.gif')
        # Open a file in binary write mode and save the content
        with open(img_file_path, 'wb') as img_file:
            img_file.write(response.content)
        logging.info(f"Image successfully downloaded and saved as '{img_file_path}'")
    else:
        logging.error(f"Failed to download the image. Status code: {response.status_code}")

    # Convert GIF to a supported format
    with Image.open(img_file_path) as img:
        img = img.convert("RGB")
        converted_path = os.path.join('captcha', f'captcha_image_{timestamp}.png')
        img.save(converted_path)    

    # Load the converted image with OpenCV
    image = cv2.imread(converted_path)

    # Check if the image loaded correctly
    if image is None:
        logging.error("Could not load the converted image. Please check the file path.")
        raise FileNotFoundError("Could not load the converted image. Please check the file path.")

    # Convert the image to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply thresholding to preprocess for better OCR results
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Use morphological operations to remove noise. For example, you can use opening to remove small speckles and closing to fill in gaps.
    # Kernel for morphological operations
    kernel = np.ones((2, 2), np.uint8)
    # Apply morphological opening (removes small noise)
    opened = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
    # Apply morphological closing (fills in small holes in characters)
    closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel)

    # Dilation to thicken characters
    dilated = cv2.dilate(closed, kernel, iterations=1)

    # Save Preprocessed Image
    preprocessed_image_path = os.path.join('captcha', f'captcha_image_{timestamp}_preprocessed.png')
    cv2.imwrite(preprocessed_image_path, dilated)

    # Open the preprocessed image
    preprocessed_img = Image.open(preprocessed_image_path)

    # Custom configuration to improve OCR accuracy
    # psm 8 is good for single characters or a row of characters
    # Limit Tesseract to recognize only A-Z and 0-9
    custom_config = r'--oem 3 --psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    extracted_text = pytesseract.image_to_string(preprocessed_img, config=custom_config)

    # Character Filtering
    import re
    filtered_text = re.sub(r'[^A-Z0-9]', '', extracted_text)  # Keep only alphanumeric characters
    logging.info("Recognized CAPTCHA text:", filtered_text.strip())
    
    # Return extracted text from the CAPTCHA
    captcha_text = filtered_text
    return captcha_text.strip()

# Function to perform login
def login(driver, UserID, UserPW, captcha_text):
    UserID = driver.find_element(By.XPATH, '//*[@id="txtUserID"]')
    UserID.clear()
    UserID.send_keys(USERNAME)
    
    UserPW = driver.find_element(By.XPATH, '//*[@id="txtPass"]')
    UserPW.clear()
    UserPW.send_keys(PASSWORD)
    
    VerifyCode = driver.find_element(By.XPATH, '//*[@id="txtVerifyCode"]')
    VerifyCode.clear()
    VerifyCode.send_keys(captcha_text)
    
    login_button = driver.find_element(By.XPATH, '//*[@id="imgBtnSubmitNew"]')
    login_button.click()

# Function to navigate to the DigitalSignature page
def navigate():
    # Get the current URL (of the Homepage)
    homepage_url = driver.current_url
    logging.info(f"Homepage URL: {homepage_url}")

    # Get the SESSION ID
    session_value = homepage_url.split("SESSION=")[-1]
    logging.info(f"Current SESSION ID: {session_value}")

    # Navigate to the DigitalSignature page
    DigitalSignature_url = f'https://ihisaw.ntuh.gov.tw/WebApplication/DigitalSignature/DsQuery.aspx?SESSION={session_value}'
    logging.info(f"DigitalSignature page URL: {DigitalSignature_url}")
    driver.get(DigitalSignature_url)

# Function to perform Digital Signature
def digital_signature(EMPLOYEE, PINCODE):
    # Enter credentials
    EmployeeID = driver.find_element(By.XPATH, '//*[@id="NTUHWeb1_txbEmpNO"]')
    EmployeeID.clear()
    EmployeeID = driver.find_element(By.XPATH, '//*[@id="NTUHWeb1_txbEmpNO"]')
    EmployeeID.send_keys(EMPLOYEE, Keys.ENTER)
    time.sleep(1)

    EmployeePincode = driver.find_element(By.XPATH, '//*[@id="NTUHWeb1_txbPinCode"]')
    EmployeePincode.send_keys(PINCODE)
    time.sleep(1)

    # Submit the DigitalSignature form
    sign_button = driver.find_element(By.XPATH, '//*[@id="NTUHWeb1_btnDoSignatureByCrossBroswer"]')
    sign_button.click()
    
    # Pause briefly to allow the pop-up to open
    time.sleep(1)

    # Get the window handles and the main window handle
    window_handles = driver.window_handles
    main_window = driver.current_window_handle

    # Switch to the pop-up window
    for handle in window_handles:
        if handle != main_window:
            driver.switch_to.window(handle)
            break

    # Now, you are in the pop-up window
    # Locate the message and print it
        # Web Message #1: <div id="dsInfo">[CrossBrowser]查無待簽章電子病歷資料</div>
        # Web Message #2: [CrossBrowser] 簽章完成, 共完成7筆簽章
        # Web Message #3: 載入失敗，錯誤代碼:[61001] 一般性錯誤，ServiSign主程式-未安裝完成，請重新安裝試試看.
        # Web Message #4: 初始化密碼模組失敗:9056
        # Web Message #5: 批次電子簽章作業中，請勿於中途取出醫事人員卡，待簽章完成後再取出卡片。
    message_element = driver.find_element(By.XPATH, '//*[@id="dsInfo"]')
    message_text = message_element.text
    logging.info("Employee ID:", EMPLOYEE, "Web message:", message_text)

    # Check whether there is any medical record to be sign
    pattern_1 = '查無待簽章電子病歷資料'
    pattern_2 = '簽章完成'
    pattern_3 = 'ServiSign主程式-未安裝完成'
    pattern_4 = '初始化密碼模組失敗'
    pattern_5 = '批次電子簽章作業中'
    
    # Initially set the flag to True
    flag = True

    # Check initial state based on the patterns
    if re.search(pattern_1, message_text):
        #print('AutoDigiSign message: OK, 查無待簽章電子病歷資料')
        flag = False  # No further action needed
    elif re.search(pattern_2, message_text):
        #print('AutoDigiSign message: OK, 簽章完成')
        flag = False  # No further action needed
    elif re.search(pattern_3, message_text):
        #print('AutoDigiSign message: Error, ServiSign主程式-未安裝完成')
        flag = False  # Stop since ServiSign is not installed
    elif re.search(pattern_4, message_text):
        #print('AutoDigiSign message: Error, 初始化密碼模組失敗')
        flag = False  # Stop since ServiSign is not installed
    elif re.search(pattern_5, message_text):
        logging.info('AutoDigiSign message: Auto-signing, 批次電子簽章作業中')
    else:
        logging.warning('AutoDigiSign message: Warning: Exception #1')
    
    # Continue checking while flag is True (Warning)
    while flag:
        try:
            # Pause for a few seconds to avoid excessive requests to the server
            time.sleep(3)

            # Update the current message
            new_message_text = driver.find_element(By.XPATH, '//*[@id="dsInfo"]').text

            # Check for successful signing with regex
            if re.search(pattern_2, new_message_text):
                logging.info('AutoDigiSign message: OK, 簽章完成')
                flag = False  # Stop the loop once signing is complete

        except (NoSuchElementException, StaleElementReferenceException) as e:
            # Handle specific exceptions that may occur during element retrieval
            logging.warning(f'AutoDigiSign message: Warning: Exception #2. Error: {e}')

    # Click the close button on the pop-up window
    close_button = driver.find_element(By.XPATH, '//*[@id="confirmBtn"]')
    close_button.click()

    # At this point, the pop-up window is closed
    # Now switch back to the main window
    driver.switch_to.window(main_window)

    # Confirm you are back in the main window
    #print("Back to the main window:", driver.title)

# ================
# Main Application
# ================

# Open the specified URL
driver.get('https://portal.ntuh.gov.tw/General/Login.aspx')

# Wait for page to load
wait = WebDriverWait(driver, 1)

# Retry login until successful
retry_count = 0
MAX_RETRIES = 30

while retry_count < MAX_RETRIES:
    try:
        # Extract CAPTCHA text
        captcha_text = get_captcha_text(driver)
        print(f"Attempt #{retry_count + 1}: CAPTCHA text extracted: {captcha_text}")

        # Wait 
        time.sleep(1)  # Adjust as needed

        # Perform login
        login(driver, USERNAME, PASSWORD, captcha_text)

        # Wait and check if login is successful
        time.sleep(1)  # Adjust as needed
        
        # Check if login was successful by looking for a specific element (i.e. the logout buttom)
        try:
            wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="TopButtonLogOutDIV"]')))
            print("Login successful!")
            break  # Exit loop if login is successful
        except:
            # If the success element isn't found, assume login failed
            print("Login failed. Retrying...")
            retry_count += 1

    except Exception as e:
        print(f"Error during login attempt #{retry_count + 1}: {e}")
        retry_count += 1

if retry_count == MAX_RETRIES:
    logging.error("Maximum retry attempts reached. Unable to log in.")
else:
    logging.info("Successfully logged in.")

# Navigate to the DigitalSignature page
navigate()

# Loop through each employee ID in the list to try DigitalSignature
for EMPLOYEE in employee_ids:
    try:
        # Try DigitalSignature
        digital_signature(EMPLOYEE, PINCODE)

    except Exception as e:
        logging.error(f"An error occurred while checking employee ID {EMPLOYEE}: {e}")

    # Optional: Pause for a moment before the next lookup (to avoid overwhelming the server)
    time.sleep(1)

# Close the WebDriver after finishing
driver.quit()

# Log a finish message
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
logging.info(f"AutoDigiSign Finished: {timestamp}")