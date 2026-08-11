import logging
from urllib.parse import parse_qs, urlencode, urlsplit

from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from autodigisign.captcha import RetryableCaptchaError, get_captcha_text
from autodigisign.logging_config import format_exception_summary
from autodigisign.selenium_helpers import safe_find


LOGIN_SUCCESS_TIMEOUT_SECONDS = 3
LOGIN_SUCCEEDED = 'success'
LOGIN_REJECTED = 'rejected'
DIGITAL_SIGNATURE_URL = (
    'https://ihisaw.ntuh.gov.tw/WebApplication/'
    'DigitalSignature/DsQuery.aspx'
)


class PortalNavigationError(RuntimeError):
    """The portal did not provide the session information needed to continue."""


def login(driver, username, password, captcha_text):
    """Submit one login attempt without recording credentials in logs."""
    user_id = safe_find(driver, By.ID, 'txtUserID')
    user_id.clear()
    user_id.send_keys(username)

    user_password = safe_find(driver, By.ID, 'txtPass')
    user_password.clear()
    user_password.send_keys(password)

    verify_code = safe_find(driver, By.ID, 'txtVerifyCode')
    verify_code.clear()
    verify_code.send_keys(captcha_text)

    safe_find(driver, By.ID, 'imgBtnSubmitNew').click()


def _detect_login_outcome(driver):
    """Return a completed login outcome or False while navigation continues."""
    try:
        driver.find_element(By.ID, 'TopButtonLogOutDIV')
        return LOGIN_SUCCEEDED
    except (NoSuchElementException, StaleElementReferenceException):
        pass

    try:
        verify_code = driver.find_element(By.ID, 'txtVerifyCode')
        if not (verify_code.get_attribute('value') or '').strip():
            return LOGIN_REJECTED
    except (NoSuchElementException, StaleElementReferenceException):
        pass
    return False


def _refresh_login_page_for_retry(driver, attempt, max_retries):
    if attempt < max_retries:
        logging.debug("Refreshing the portal login page before retrying.")
        driver.refresh()


def retry_login(
    driver,
    username,
    password,
    max_retries=30,
    success_timeout_seconds=LOGIN_SUCCESS_TIMEOUT_SECONDS,
    captcha_loader=None,
):
    """Retry only expected CAPTCHA and short-lived DOM failures."""
    if max_retries <= 0:
        raise ValueError("max_retries must be greater than zero.")
    captcha_loader = captcha_loader or get_captcha_text

    for attempt in range(1, max_retries + 1):
        try:
            captcha_text = captcha_loader(driver)
            logging.info(
                "Attempt #%d: CAPTCHA recognition completed.",
                attempt,
            )
            login(driver, username, password, captcha_text)
            outcome = WebDriverWait(
                driver,
                success_timeout_seconds,
            ).until(
                _detect_login_outcome
            )
            if outcome == LOGIN_REJECTED:
                logging.info(
                    "Login attempt #%d was rejected; retrying.",
                    attempt,
                )
                continue
        except TimeoutException:
            logging.info(
                "Login attempt #%d did not complete within %.1f seconds; "
                "retrying.",
                attempt,
                success_timeout_seconds,
            )
            _refresh_login_page_for_retry(driver, attempt, max_retries)
            continue
        except (
            RetryableCaptchaError,
            NoSuchElementException,
            StaleElementReferenceException,
        ) as error:
            logging.warning(
                "Retryable login error on attempt #%d: %s",
                attempt,
                format_exception_summary(error),
            )
            logging.debug(
                "Retryable login error on attempt #%d traceback",
                attempt,
                exc_info=(type(error), error, error.__traceback__),
            )
            _refresh_login_page_for_retry(driver, attempt, max_retries)
            continue

        logging.info("Login successful on attempt #%d.", attempt)
        return True

    logging.error(
        "Maximum retry attempts reached. Unable to log in after %d attempts.",
        max_retries,
    )
    return False


def navigate(driver):
    """Open the signature page using the session ID from the portal URL."""
    query = parse_qs(urlsplit(driver.current_url).query)
    session_values = query.get('SESSION')
    if not session_values or not session_values[0]:
        raise PortalNavigationError(
            "The portal login URL did not contain a SESSION value."
        )

    destination = f"{DIGITAL_SIGNATURE_URL}?{urlencode({'SESSION': session_values[0]})}"
    logging.info("Navigating to the DigitalSignature page.")
    driver.get(destination)
