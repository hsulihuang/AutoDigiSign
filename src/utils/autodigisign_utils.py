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
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Function to handle stale and missing elements in Document Object Model (DOM)
def safe_find(driver, by, value, retries=3, delay=1):
    for _ in range(retries):
        try:
            elem = driver.find_element(by, value)
            return elem
        except (StaleElementReferenceException, NoSuchElementException):
            time.sleep(delay)
    raise Exception(f"Element not found or went stale after retries: {value}")

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
    img_element = safe_find(driver, By.XPATH, '//*[@id="imgVerifyCode"]')

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
    UserID = safe_find(driver, By.XPATH, '//*[@id="txtUserID"]')
    UserID.clear()
    UserID.send_keys(USERNAME)
    
    UserPW = safe_find(driver, By.XPATH, '//*[@id="txtPass"]')
    UserPW.clear()
    UserPW.send_keys(PASSWORD)
    
    VerifyCode = safe_find(driver, By.XPATH, '//*[@id="txtVerifyCode"]')
    VerifyCode.clear()
    VerifyCode.send_keys(captcha_text)
    
    login_button = safe_find(driver, By.XPATH, '//*[@id="imgBtnSubmitNew"]')
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
    with open(employee_list_filepath, 'r', encoding='utf-8') as file:
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

# Function to check whether there is a dialog-form for delay-sign
def handle_delay_sign_dialog(driver):
    try:
        # Attempt to locate the dialog-form by its ID
        dialog = safe_find(driver, By.XPATH, '//*[@id="dialog-form"]')

        try:
            # Check if the dialog is actually displayed
            if dialog.is_displayed():
                logging.info("Delay-sign dialog is visible.")

                # Try to click the '確定' button with a retry mechanism
                for _ in range(2):
                    try:
                        delay_sign_button = safe_find(driver, By.XPATH, "//button[span[text()='確定']]")
                        delay_sign_button.click()
                        break  # Success
                    except StaleElementReferenceException:
                        logging.warning("Stale reference when clicking delay-sign confirm button; retrying...")

                # Re-click the sign button
                for _ in range(2):
                    try:
                        sign_button = safe_find(driver, By.XPATH, '//*[@id="NTUHWeb1_btnDoSignatureByCrossBroswer"]')
                        sign_button.click()
                        break
                    except StaleElementReferenceException:
                        logging.warning("Stale reference when re-clicking sign button; retrying...")

                logging.info("Delay-sign dialog found and confirmed.")
            else:
                logging.info("Delay-sign dialog found but not visible.")

        except StaleElementReferenceException as e:
            logging.warning(f"Stale reference when checking dialog visibility: {e}")

    except NoSuchElementException:
        logging.info("No delay-sign dialog was present.")
    except Exception as e:
        logging.warning(f"An unexpected error occurred while handling delay-sign: {e}")

# Function to perform Digital Signature
def digital_signature(EMPLOYEE_ID, EMPLOYEE_NAME, PINCODE, driver):
    # Remember the main window at the very beginning
    main_window = driver.current_window_handle

    # 1. Enter employee ID
    EmployeeID = safe_find(driver, By.XPATH, '//*[@id="NTUHWeb1_txbEmpNO"]')
    EmployeeID.clear()
    EmployeeID = safe_find(driver, By.XPATH, '//*[@id="NTUHWeb1_txbEmpNO"]')
    EmployeeID.send_keys(EMPLOYEE_ID, Keys.ENTER)
    time.sleep(1)

    # 2. Enter PIN
    EmployeePincode = safe_find(driver, By.XPATH, '//*[@id="NTUHWeb1_txbPinCode"]')
    EmployeePincode.clear()
    EmployeePincode.send_keys(PINCODE)
    time.sleep(1)

    # 3. Click the sign button
    sign_button = safe_find(driver, By.XPATH, '//*[@id="NTUHWeb1_btnDoSignatureByCrossBroswer"]')
    sign_button.click()

    # 4. Wait briefly for popup to appear
    time.sleep(1)

    # 5. Find the popup window (if any)
    popup_handle = None
    for handle in driver.window_handles:
        if handle != main_window:
            popup_handle = handle
            break

    if not popup_handle:
        logging.warning(f"No pop-up window detected for Employee ID: {EMPLOYEE_ID}, Name: {EMPLOYEE_NAME}")
        return

    driver.switch_to.window(popup_handle)
    logging.info(f"Switch to the pop-up window:, {driver.title}")

    try:
        # Try to find the main message element (dsInfo)
        try:
            message_element = safe_find(driver, By.XPATH, '//*[@id="dsInfo"]')
            message_text = message_element.text
        except Exception as e:
            # This is exactly what happened in your log with title 'ShowInfo'
            logging.error(
                f"Employee ID: {EMPLOYEE_ID}, Name: {EMPLOYEE_NAME}: "
                f"Failed to locate dsInfo element in popup: {e}"
            )
            # Fallback: log some info and exit gracefully
            try:
                logging.debug(f"Popup page source (truncated): {driver.page_source[:1000]}")
            except Exception:
                pass
            return  # Exit the try-block; finally will still run and clean up

        # --- Original pattern checking logic ---
        pattern_1 = '查無待簽章電子病歷資料'  # Web Message: <div id="dsInfo">[CrossBrowser]查無待簽章電子病歷資料</div>
        pattern_2 = '簽章完成'  # Web Message: [CrossBrowser] 簽章完成, 共完成7筆簽章
        pattern_3 = 'ServiSign主程式-未安裝完成'  # Web Message: 載入失敗，錯誤代碼:[61001] 一般性錯誤，ServiSign主程式-未安裝完成，請重新安裝試試看.
        pattern_4 = '初始化密碼模組失敗'  # Web Message: 初始化密碼模組失敗:9056
        pattern_5 = '批次電子簽章作業中'  # Web Message: 批次電子簽章作業中，請勿於中途取出醫事人員卡，待簽章完成後再取出卡片。

        flag = True

        if re.search(pattern_1, message_text):
            logging.info(f"Employee ID: {EMPLOYEE_ID}, Name: {EMPLOYEE_NAME}, Web message: {message_text}")
            flag = False
        elif re.search(pattern_2, message_text):
            logging.info(f"Employee ID: {EMPLOYEE_ID}, Name: {EMPLOYEE_NAME}, Web message: {message_text}")
            flag = False
        elif re.search(pattern_3, message_text):
            logging.error(f"Employee ID: {EMPLOYEE_ID}, Name: {EMPLOYEE_NAME}, Web message: {message_text}")
            flag = False
        elif re.search(pattern_4, message_text):
            logging.error(f"Employee ID: {EMPLOYEE_ID}, Name: {EMPLOYEE_NAME}, Web message: {message_text}")
            flag = False
        elif re.search(pattern_5, message_text):
            logging.info(f"Employee ID: {EMPLOYEE_ID}, Name: {EMPLOYEE_NAME}, Web message: {message_text}")
        else:
            logging.warning(f"Employee ID: {EMPLOYEE_ID}, Name: {EMPLOYEE_NAME}, Web message: {message_text}")
            logging.warning('AutoDigiSign message: Warning: Exception #1')

        # If we still need to wait for signing to complete, poll dsInfo
        while flag:
            try:
                time.sleep(3)
                new_message_text = safe_find(driver, By.XPATH, '//*[@id="dsInfo"]').text

                if re.search(pattern_2, new_message_text):
                    logging.info(
                        f"Employee ID: {EMPLOYEE_ID}, Name: {EMPLOYEE_NAME}, "
                        f"Web message: {new_message_text}"
                    )
                    flag = False

            except (StaleElementReferenceException, NoSuchElementException) as e:
                logging.warning(
                    f"Employee ID: {EMPLOYEE_ID}, Name: {EMPLOYEE_NAME}, "
                    f"AutoDigiSign message: Warning: Exception #2. Error: {e}"
                )
                # Break out to avoid infinite loop if the element disappears permanently
                break

    finally:
        # 6. ALWAYS try to close popup and go back to main window,
        #    even if any error occurred above.
        try:
            try:
                # Preferred way: click confirm button if present
                close_button = safe_find(driver, By.XPATH, '//*[@id="confirmBtn"]', retries=1, delay=0.5)
                close_button.click()
                time.sleep(0.5)
            except Exception as e:
                logging.warning(f"Could not click confirmBtn on popup: {e}. Trying to close popup window directly.")
                try:
                    driver.close()
                except Exception as e2:
                    logging.warning(f"Could not close popup window: {e2}")
        except Exception as e:
            logging.warning(f"Unexpected error when closing popup: {e}")

        # Ensure we end up back in the main window (where txbEmpNO lives)
        try:
            driver.switch_to.window(main_window)
            logging.info(f"Back to the main window:, {driver.title}")
        except Exception as e:
            logging.error(f"Failed to switch back to the main window after popup: {e}")
