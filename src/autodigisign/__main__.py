import logging
import sys
from datetime import datetime
from pathlib import Path

from autodigisign.browser import detect_operating_system, initialize_driver
from autodigisign.config import (
    load_credentials_settings,
    resolve_project_paths,
)
from autodigisign.email_delivery import (
    generate_email_body,
    generate_email_subject,
    load_email_settings,
    send_email_with_attachment,
)
from autodigisign.employees import get_employees
from autodigisign.logging_config import (
    LOG_TIMESTAMP_FORMAT,
    log_exception,
    setup_logging,
)
from autodigisign.portal import navigate, retry_login
from autodigisign.signing import (
    SIGNATURE_BUTTON_ID,
    SIGNATURE_POPUP_TIMEOUT_SECONDS,
    SIGNATURE_PROCESSING_TIMEOUT_SECONDS,
)
from autodigisign.signing_workflow import process_employees
from autodigisign.tesseract import configure_pytesseract


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PORTAL_LOGIN_URL = 'https://portal.ntuh.gov.tw/General/Login.aspx'
REQUIRED_PYTHON_VERSION = (3, 14)


def get_log_directory(project_root, timestamp):
    """Return the year/month directory for one timestamped run."""
    return (
        Path(project_root)
        / 'outputs'
        / 'logs'
        / timestamp[:4]
        / timestamp[4:6]
    )


def validate_python_version(version_info=None):
    version_info = sys.version_info if version_info is None else version_info
    detected_version = tuple(version_info[:2])
    if detected_version != REQUIRED_PYTHON_VERSION:
        required = '.'.join(str(part) for part in REQUIRED_PYTHON_VERSION)
        detected = '.'.join(str(part) for part in detected_version)
        raise RuntimeError(
            f'AutoDigiSign requires Python {required}.x; '
            f'detected Python {detected}.'
        )


def main():
    timestamp = datetime.now().strftime(LOG_TIMESTAMP_FORMAT)
    log_directory = get_log_directory(PROJECT_ROOT, timestamp)
    debug_log_filepath, info_log_filepath = setup_logging(
        log_directory=str(log_directory),
        timestamp=timestamp,
    )
    logging.info("AutoDigiSign Started: %s", timestamp)
    logging.info("Project root: %s", PROJECT_ROOT)

    driver = None
    project_paths = None
    email_settings = None
    exit_code = 0

    try:
        validate_python_version()
        # Validate every local input before downloading a driver, opening a
        # browser, or attempting to log in to the hospital portal.
        project_paths = resolve_project_paths(PROJECT_ROOT)
        credentials = load_credentials_settings(project_paths.credentials)
        employees = get_employees(project_paths.employee_list)
        if project_paths.email_config is not None:
            email_settings = load_email_settings(project_paths.email_config)
            logging.info("Optional email configuration loaded successfully.")
        else:
            logging.info(
                "Log email skipped: optional email_config.ini was not found."
            )

        logging.info("Credentials configuration validated successfully.")
        logging.info(
            "Signature workflow: method=PCSC, button_id=%s, "
            "popup_timeout_seconds=%d, processing_timeout_seconds=%d",
            SIGNATURE_BUTTON_ID,
            SIGNATURE_POPUP_TIMEOUT_SECONDS,
            SIGNATURE_PROCESSING_TIMEOUT_SECONDS,
        )
        if not employees:
            logging.warning(
                "No permanent or current-month employees were selected."
            )

        operating_system = detect_operating_system()
        tesseract_selection = configure_pytesseract(operating_system)
        logging.info(
            "Tesseract initialized: version=%s, source=%s, executable=%s",
            tesseract_selection.version,
            tesseract_selection.source,
            tesseract_selection.executable_path.name,
        )

        driver = initialize_driver(
            project_root=PROJECT_ROOT,
            operating_system=operating_system,
        )
        driver.get(PORTAL_LOGIN_URL)
        if not retry_login(
            driver,
            credentials.username,
            credentials.password,
            max_retries=30,
        ):
            logging.error("Exiting the script due to unsuccessful login.")
            exit_code = 1
        else:
            navigate(driver)
            failed_employee_count = process_employees(
                driver,
                employees,
                credentials.pincode,
            )
            if failed_employee_count:
                logging.error(
                    "Signing batch completed with %d employee failure(s).",
                    failed_employee_count,
                )
                exit_code = 1
    except KeyboardInterrupt as error:
        log_exception("AutoDigiSign interrupted", error)
        exit_code = 130
    except Exception as error:
        log_exception("AutoDigiSign failed unexpectedly", error)
        exit_code = 1
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception as error:
                log_exception("Failed to close WebDriver", error)
                exit_code = 1
        logging.info(
            "AutoDigiSign Finished: %s",
            datetime.now().strftime(LOG_TIMESTAMP_FORMAT),
        )

    # Email delivery remains optional. If configured and validated, send both
    # logs even after a signing failure so remote diagnosis remains possible.
    if project_paths is not None and email_settings is not None:
        try:
            email_subject = generate_email_subject(info_log_filepath, timestamp)
            email_body = generate_email_body(info_log_filepath)
            send_email_with_attachment(
                email_config_filepath=project_paths.email_config,
                subject=email_subject,
                body=email_body,
                info_log_filepath=info_log_filepath,
                debug_log_filepath=debug_log_filepath,
                settings=email_settings,
            )
        except Exception as error:
            log_exception("Failed to send log email", error)
            exit_code = 1

    logging.shutdown()
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
