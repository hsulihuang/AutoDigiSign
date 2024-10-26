# autodigisign_utils.py
import configparser
import cv2
import logging
import numpy as np
import os
import pytesseract
import re
import requests
import time
from PIL import Image
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Function to get credentials from a config file
def get_credentials(credentials_filepath):
    # Create a ConfigParser instance
    config = configparser.ConfigParser()
    
    # Read the config file
    config.read(credentials_filepath)
    
    # Get credentials from the config file
    USERNAME = config['credentials']['username']
    PASSWORD = config['credentials']['password']
    PINCODE = config['credentials']['pincode']
    
    return USERNAME, PASSWORD, PINCODE

# Function to download the CAPTCHA image and extract text
def get_captcha_text(driver, timestamp, captcha_folderpath):
    # Locate the image element
    img_element = driver.find_element(By.XPATH, '//*[@id="imgVerifyCode"]')

    # Get the 'src' attribute of the image element
    img_url = img_element.get_attribute('src')
    logging.info(f"CAPTCHA image source URL: {img_url}")

    # Send a request to get the image
    response = requests.get(img_url)

    # Check the response status
    if response.status_code == 200:
        # Specify the file name using the timestamp and location where to save the image
        img_file_path = os.path.join(captcha_folderpath, f'captcha_image_{timestamp}.gif')
        # Open a file in binary write mode and save the content
        with open(img_file_path, 'wb') as img_file:
            img_file.write(response.content)
        logging.info(f"Image successfully downloaded and saved as '{img_file_path}'")
    else:
        logging.error(f"Failed to download the image. Status code: {response.status_code}")

    # Convert GIF to a supported format
    with Image.open(img_file_path) as img:
        img = img.convert("RGB")
        converted_path = os.path.join(captcha_folderpath, f'captcha_image_{timestamp}.png')
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
    preprocessed_image_path = os.path.join(captcha_folderpath, f'captcha_image_{timestamp}_preprocessed.png')
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
    logging.info(f"Recognized CAPTCHA text: {filtered_text.strip()}")
    
    # Return extracted text from the CAPTCHA
    captcha_text = filtered_text
    return captcha_text.strip()

# Function to perform login
def login(driver, USERNAME, PASSWORD, captcha_text):
    # Enter credentials
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

# Function to retry login until successful or maximum retries reached
def retry_login(driver, timestamp, captcha_folderpath, USERNAME, PASSWORD, max_retries=30):
    retry_count = 0
    wait = WebDriverWait(driver, 1)  # Wait for page to load, adjust as needed

    while retry_count < max_retries:
        try:
            # Extract CAPTCHA text
            captcha_text = get_captcha_text(driver, timestamp, captcha_folderpath)
            logging.info(f"Attempt #{retry_count + 1}: CAPTCHA text extracted: {captcha_text}")

            # Wait 
            time.sleep(1)  # Adjust as needed

            # Perform login
            login(driver, USERNAME, PASSWORD, captcha_text)

            # Wait and check if login is successful
            time.sleep(1)  # Adjust as needed
            
            # Check if login was successful by looking for a specific element (e.g., the logout button)
            try:
                wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="TopButtonLogOutDIV"]')))
                logging.info("Login successful!")
                return True  # Exit the function if login is successful
            except:
                # If the success element isn't found, assume login failed
                logging.info("Login failed. Retrying...")
                retry_count += 1

        except Exception as e:
            logging.error(f"Error during login attempt #{retry_count + 1}: {e}")
            retry_count += 1

    if retry_count == max_retries:
        logging.error("Maximum retry attempts reached. Unable to log in.")
        return False
    else:
        logging.info("Successfully logged in.")
        return True

# Function to navigate to the DigitalSignature page
def navigate(driver):
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

# Function to get the list of employees from a txet file
def get_employees(employee_list_filepath):
    # Read employee IDs and names from the text file
    employees = []
    with open(employee_list_filepath, 'r') as file:
        for line in file:
            line = line.strip()  # Remove leading/trailing whitespaces
            if line:  # Skip empty lines
                emp_id, emp_name = line.split(maxsplit=1)  # Split by whitespace; maxsplit=1 to avoid splitting names with spaces
                employees.append({'id': emp_id, 'name': emp_name})
    return employees
    # Now `employees` is a list of dictionaries, e.g.
    # [
    #     {'id': '123456', 'name': 'name1'},
    #     {'id': '110022', 'name': 'name2'},
    #     ...
    # ]

# Function to perform Digital Signature
def digital_signature(EMPLOYEE_ID, EMPLOYEE_NAME, PINCODE, driver):
    # Enter credentials
    EmployeeID = driver.find_element(By.XPATH, '//*[@id="NTUHWeb1_txbEmpNO"]')
    EmployeeID.clear()
    EmployeeID = driver.find_element(By.XPATH, '//*[@id="NTUHWeb1_txbEmpNO"]')
    EmployeeID.send_keys(EMPLOYEE_ID, Keys.ENTER)
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
    logging.info(f"Switch to the pop-up window:, {driver.title}")

    # Locate the message and print it
        # Web Message #1: <div id="dsInfo">[CrossBrowser]查無待簽章電子病歷資料</div>
        # Web Message #2: [CrossBrowser] 簽章完成, 共完成7筆簽章
        # Web Message #3: 載入失敗，錯誤代碼:[61001] 一般性錯誤，ServiSign主程式-未安裝完成，請重新安裝試試看.
        # Web Message #4: 初始化密碼模組失敗:9056
        # Web Message #5: 批次電子簽章作業中，請勿於中途取出醫事人員卡，待簽章完成後再取出卡片。
    message_element = driver.find_element(By.XPATH, '//*[@id="dsInfo"]')
    message_text = message_element.text

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
        logging.info(f"Employee ID: {EMPLOYEE_ID}, Name: {EMPLOYEE_NAME}, Web message: {message_text}")
        flag = False  # No further action needed
    elif re.search(pattern_2, message_text):
        logging.info(f"Employee ID: {EMPLOYEE_ID}, Name: {EMPLOYEE_NAME}, Web message: {message_text}")
        flag = False  # No further action needed
    elif re.search(pattern_3, message_text):
        logging.error(f"Employee ID: {EMPLOYEE_ID}, Name: {EMPLOYEE_NAME}, Web message: {message_text}")
        flag = False  # Stop since ServiSign is not installed
    elif re.search(pattern_4, message_text):
        logging.error(f"Employee ID: {EMPLOYEE_ID}, Name: {EMPLOYEE_NAME}, Web message: {message_text}")
        flag = False  # Stop since ServiSign is not installed
    elif re.search(pattern_5, message_text):
        logging.info(f"Employee ID: {EMPLOYEE_ID}, Name: {EMPLOYEE_NAME}, Web message: {message_text}")  ### This line is not working for some reason. Suspect a diffent XPATH
    else:
        logging.warning(f"Employee ID: {EMPLOYEE_ID}, Name: {EMPLOYEE_NAME}, Web message: {message_text}")
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
                logging.info(f"Employee ID: {EMPLOYEE_ID}, Name: {EMPLOYEE_NAME}, Web message: {message_text}")
                flag = False  # Stop the loop once signing is complete

        except (NoSuchElementException, StaleElementReferenceException) as e:
            # Handle specific exceptions that may occur during element retrieval
            logging.warning(f"Employee ID: {EMPLOYEE_ID}, Name: {EMPLOYEE_NAME}, Web message: {message_text}")
            logging.warning(f'AutoDigiSign message: Warning: Exception #2. Error: {e}')

    # Click the close button on the pop-up window
    close_button = driver.find_element(By.XPATH, '//*[@id="confirmBtn"]')
    close_button.click()

    # At this point, the pop-up window is closed
    # Now switch back to the main window
    driver.switch_to.window(main_window)

    # Confirm you are back in the main window
    logging.info(f"Back to the main window:, {driver.title}")
