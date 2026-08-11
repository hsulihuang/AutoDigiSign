import logging
import re
import time

from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from autodigisign.logging_config import format_exception_summary
from autodigisign.selenium_helpers import safe_find


SIGNATURE_POLL_INTERVAL_SECONDS = 3
POPUP_CLOSE_WAIT_SECONDS = 3
EMPLOYEE_POSTBACK_WAIT_SECONDS = 1
FIELD_ACTION_RETRIES = 3
FIELD_RETRY_DELAY_SECONDS = 0.2
DETACHED_NODE_POSTBACK_ERROR = (
    'Node with given id does not belong to the document'
)
POSSIBLE_READER_TYPE_ERROR_MESSAGE = '[-1]查無錯誤代碼定義'
SIGNATURE_IN_PROGRESS_MESSAGE = '批次電子簽章作業中'
SIGNATURE_BUTTON_ID = 'NTUHWeb1_btnDoSignatureByPCSC'
SIGNATURE_POPUP_TIMEOUT_SECONDS = 30
SIGNATURE_PROCESSING_TIMEOUT_SECONDS = 180


class SignatureError(RuntimeError):
    """Base error for a signing operation that did not complete."""


class SignatureReaderTypeError(SignatureError):
    """PCSC signing was rejected, possibly because of the reader type."""


class SignatureTimeoutError(SignatureError):
    """A signing stage did not reach its required state before its deadline."""


class SignatureOperationError(SignatureError):
    """The signing popup returned a known terminal error."""


class SignatureInputError(SignatureError):
    """A signing-page input could not be completed after bounded retries."""


class SignatureDriverStateError(SignatureError):
    """The popup could not be closed or the main signing window was lost."""


def _evaluate_signature_message(
    message,
    employee_id,
    employee_name,
):
    log_context = (
        f"Employee ID: {employee_id}, Name: {employee_name}, "
        f"Web message: {message}"
    )
    if POSSIBLE_READER_TYPE_ERROR_MESSAGE in message:
        logging.error(log_context)
        raise SignatureReaderTypeError(
            "The PCSC signing request was rejected for "
            f"Employee ID: {employee_id}, Name: {employee_name}. "
            "The connected reader may be the wrong type or may not support "
            "PCSC signing."
        )
    if re.search(r'查無待簽章電子病歷資料|簽章完成', message):
        logging.info(log_context)
        return True
    component_error_pattern = (
        r'ServiSign主程式-未安裝完成|初始化密碼模組失敗'
    )
    if re.search(component_error_pattern, message):
        logging.error(log_context)
        raise SignatureOperationError(
            f"The signing component returned an error for Employee ID: "
            f"{employee_id}, Name: {employee_name}."
        )
    if SIGNATURE_IN_PROGRESS_MESSAGE in message:
        logging.info(log_context)
    else:
        logging.warning(log_context)
    return False


def _wait_for_popup(driver, main_window, deadline):
    while time.monotonic() < deadline:
        popup_handle = next(
            (
                handle
                for handle in driver.window_handles
                if handle != main_window
            ),
            None,
        )
        if popup_handle:
            return popup_handle
        remaining = deadline - time.monotonic()
        time.sleep(min(0.25, max(remaining, 0)))
    return None


def _start_processing_deadline(message, processing_deadline):
    """Start the processing timeout once; repeated progress does not extend it."""
    if (
        processing_deadline is None
        and SIGNATURE_IN_PROGRESS_MESSAGE in message
    ):
        return time.monotonic() + SIGNATURE_PROCESSING_TIMEOUT_SECONDS
    return processing_deadline


def _log_signature_elapsed(employee_id, employee_name, started_at):
    logging.info(
        "PCSC signing reached a successful terminal result for Employee ID: "
        "%s, Name: %s, elapsed_seconds=%.3f",
        employee_id,
        employee_name,
        time.monotonic() - started_at,
    )


def _replace_input_value(driver, field_id, value, *trailing_keys):
    """Enter a value while tolerating ASP.NET replacement of the input DOM."""
    last_error = None
    for attempt in range(FIELD_ACTION_RETRIES):
        try:
            field = safe_find(driver, By.ID, field_id)
            current_value = field.get_attribute('value') or ''
            if current_value:
                field.clear()
                try:
                    WebDriverWait(
                        driver,
                        EMPLOYEE_POSTBACK_WAIT_SECONDS,
                    ).until(EC.staleness_of(field))
                except TimeoutException:
                    # Some page versions clear in place. Re-find either way so
                    # a replacement occurring after clear() is not reused.
                    pass
                field = safe_find(driver, By.ID, field_id)

            field.send_keys(value, *trailing_keys)
            return field
        except (
            NoSuchElementException,
            StaleElementReferenceException,
        ) as error:
            last_error = error
            logging.debug(
                "Signing input field %s was unavailable on attempt %d/%d; "
                "re-finding it before signature submission.",
                field_id,
                attempt + 1,
                FIELD_ACTION_RETRIES,
            )
            if attempt + 1 < FIELD_ACTION_RETRIES:
                time.sleep(FIELD_RETRY_DELAY_SECONDS)

    raise SignatureInputError(
        f"Could not enter a value into {field_id} after "
        f"{FIELD_ACTION_RETRIES} attempts."
    ) from last_error


def _restore_main_window(driver, main_window, popup_handle):
    """Close the popup and prove the driver is ready for the next employee."""
    cleanup_errors = []
    try:
        handles = driver.window_handles
    except Exception as error:
        raise SignatureDriverStateError(
            "WebDriver window state could not be inspected after signing."
        ) from error

    if popup_handle in handles:
        try:
            driver.switch_to.window(popup_handle)
            try:
                safe_find(
                    driver,
                    By.ID,
                    'confirmBtn',
                    retries=1,
                    delay=0,
                ).click()
            except (NoSuchElementException, StaleElementReferenceException):
                driver.close()
        except Exception as error:
            # A missing or stale confirm button is not itself fatal if the
            # popup can still be closed directly and the main window survives.
            logging.warning(
                "Could not use the signing popup confirmation button: %s. "
                "Trying a direct popup close.",
                format_exception_summary(error),
            )
            logging.debug(
                "Signing popup confirmation failure traceback",
                exc_info=(type(error), error, error.__traceback__),
            )
            try:
                driver.switch_to.window(popup_handle)
                driver.close()
            except Exception as close_error:
                cleanup_errors.append(
                    "could not close signing popup: "
                    f"{type(close_error).__name__}: {close_error}"
                )

    close_deadline = time.monotonic() + POPUP_CLOSE_WAIT_SECONDS
    while time.monotonic() < close_deadline:
        try:
            if popup_handle not in driver.window_handles:
                break
        except Exception as error:
            cleanup_errors.append(
                f"could not verify popup closure: {type(error).__name__}: {error}"
            )
            break
        time.sleep(0.1)

    try:
        remaining_handles = driver.window_handles
        if popup_handle in remaining_handles:
            driver.switch_to.window(popup_handle)
            driver.close()
            remaining_handles = driver.window_handles
        if main_window not in remaining_handles:
            raise SignatureDriverStateError(
                "The main signing window no longer exists."
            )
        driver.switch_to.window(main_window)
    except SignatureDriverStateError:
        raise
    except Exception as error:
        cleanup_errors.append(
            f"could not return to main window: {type(error).__name__}: {error}"
        )

    if cleanup_errors:
        raise SignatureDriverStateError('; '.join(cleanup_errors))
    logging.info("Returned to the main signing window.")


def _wait_for_employee_postback(driver, employee_field):
    """Wait for the employee field to be replaced after the legacy postback."""
    # Edge may report a detached DOM node as a generic WebDriverException
    # instead of Selenium's normal StaleElementReferenceException. Only that
    # exact inspector condition is safe to treat as a completed postback.
    try:
        WebDriverWait(driver, EMPLOYEE_POSTBACK_WAIT_SECONDS).until(
            EC.staleness_of(employee_field)
        )
    except TimeoutException:
        pass
    except WebDriverException as error:
        if DETACHED_NODE_POSTBACK_ERROR not in str(error):
            raise
        logging.debug(
            "Employee field detached during postback; continuing with a "
            "fresh field lookup."
        )


def digital_signature(
    employee_id,
    employee_name,
    pincode,
    driver,
):
    """Perform one signature and leave WebDriver in a verified main-window state."""
    main_window = driver.current_window_handle

    employee_field = _replace_input_value(
        driver,
        'NTUHWeb1_txbEmpNO',
        employee_id,
        Keys.ENTER,
    )

    _wait_for_employee_postback(driver, employee_field)

    _replace_input_value(
        driver,
        'NTUHWeb1_txbPinCode',
        pincode,
    )

    sign_button = safe_find(
        driver,
        By.ID,
        SIGNATURE_BUTTON_ID,
    )
    signing_started_at = time.monotonic()
    popup_deadline = (
        signing_started_at + SIGNATURE_POPUP_TIMEOUT_SECONDS
    )
    logging.info(
        "PCSC signing requested for Employee ID: %s, Name: %s, "
        "popup_timeout_seconds=%d, processing_timeout_seconds=%d",
        employee_id,
        employee_name,
        SIGNATURE_POPUP_TIMEOUT_SECONDS,
        SIGNATURE_PROCESSING_TIMEOUT_SECONDS,
    )
    sign_button.click()

    popup_handle = _wait_for_popup(driver, main_window, popup_deadline)
    if not popup_handle:
        raise SignatureTimeoutError(
            "No PCSC signing popup appeared within "
            f"{SIGNATURE_POPUP_TIMEOUT_SECONDS} seconds for Employee ID: "
            f"{employee_id}, Name: {employee_name}."
        )

    try:
        driver.switch_to.window(popup_handle)
    except Exception as error:
        raise SignatureDriverStateError(
            "WebDriver could not switch to the signing popup."
        ) from error

    try:
        try:
            message = safe_find(driver, By.ID, 'dsInfo').text
        except (NoSuchElementException, StaleElementReferenceException) as error:
            logging.error(
                "Employee ID: %s, Name: %s: signing popup did not provide dsInfo.",
                employee_id,
                employee_name,
            )
            raise SignatureOperationError(
                f"The signing popup did not provide a result for Employee ID: "
                f"{employee_id}, Name: {employee_name}."
            ) from error

        if _evaluate_signature_message(
            message,
            employee_id,
            employee_name,
        ):
            _log_signature_elapsed(
                employee_id,
                employee_name,
                signing_started_at,
            )
            return

        processing_deadline = _start_processing_deadline(message, None)
        last_message = message
        while True:
            active_deadline = processing_deadline or popup_deadline
            if time.monotonic() >= active_deadline:
                break
            remaining = active_deadline - time.monotonic()
            time.sleep(
                min(SIGNATURE_POLL_INTERVAL_SECONDS, max(remaining, 0))
            )
            try:
                current_message = safe_find(driver, By.ID, 'dsInfo').text
            except (
                NoSuchElementException,
                StaleElementReferenceException,
            ) as error:
                logging.warning(
                    "Employee ID: %s, Name: %s: could not refresh signing status: %s",
                    employee_id,
                    employee_name,
                    format_exception_summary(error),
                )
                logging.debug(
                    "Employee ID: %s, Name: %s: signing-status refresh traceback",
                    employee_id,
                    employee_name,
                    exc_info=(type(error), error, error.__traceback__),
                )
                continue

            if current_message != last_message:
                if _evaluate_signature_message(
                    current_message,
                    employee_id,
                    employee_name,
                ):
                    _log_signature_elapsed(
                        employee_id,
                        employee_name,
                        signing_started_at,
                    )
                    return
                processing_deadline = _start_processing_deadline(
                    current_message,
                    processing_deadline,
                )
                last_message = current_message

        if processing_deadline is not None:
            raise SignatureTimeoutError(
                "PCSC signing remained in progress for more than "
                f"{SIGNATURE_PROCESSING_TIMEOUT_SECONDS} seconds for "
                f"Employee ID: {employee_id}, Name: {employee_name}."
            )
        raise SignatureTimeoutError(
            "PCSC signing did not reach an in-progress or terminal result "
            f"within {SIGNATURE_POPUP_TIMEOUT_SECONDS} seconds for Employee "
            f"ID: {employee_id}, Name: {employee_name}."
        )
    finally:
        _restore_main_window(driver, main_window, popup_handle)
