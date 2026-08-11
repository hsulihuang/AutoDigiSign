import logging
import os
import sys

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.service import Service as EdgeService

from autodigisign.logging_config import format_exception_summary
from autodigisign.webdriver.manager import ensure_webdriver


def detect_operating_system(platform_name=None):
    """Return the supported operating system for the current Python runtime."""
    platform_name = platform_name or sys.platform
    if platform_name == 'darwin':
        return 'macos'
    if platform_name == 'win32':
        return 'windows'
    raise EnvironmentError(
        f"Unsupported operating system: {platform_name}. "
        "AutoDigiSign supports macOS and Windows."
    )


def start_browser(browser, driver_path):
    """Start one supported browser with its validated local WebDriver."""
    if browser == 'edge':
        os.environ['MSEDGEDRIVER_TELEMETRY_OPTOUT'] = '1'
        return webdriver.Edge(service=EdgeService(str(driver_path)))
    if browser == 'chrome':
        return webdriver.Chrome(service=ChromeService(str(driver_path)))
    raise ValueError(f"Unsupported browser: {browser}")


def initialize_driver(project_root, operating_system=None):
    """Initialize Edge with Chrome as fallback on a supported OS."""
    operating_system = operating_system or detect_operating_system()

    initialization_failures = []
    driver = None
    driver_selection = None
    for browser in ('edge', 'chrome'):
        try:
            selection = ensure_webdriver(
                project_root,
                browser,
                operating_system,
            )
            driver = start_browser(browser, selection.driver_path)
            driver_selection = selection
            break
        except Exception as error:
            initialization_failures.append(
                f"{browser.title()} could not be initialized: "
                f"{format_exception_summary(error)}"
            )
            logging.debug(
                "%s WebDriver initialization traceback",
                browser.title(),
                exc_info=(type(error), error, error.__traceback__),
            )

    if driver is None:
        raise RuntimeError(
            "Unable to initialize Edge or Chrome. "
            + " ".join(initialization_failures)
        )
    if driver_selection.browser == 'chrome' and initialization_failures:
        logging.warning(
            "Edge was unavailable; using Chrome fallback. %s",
            initialization_failures[0],
        )

    capabilities = driver.capabilities
    logging.info(
        "WebDriver initialized: operating_system=%s, selected_browser=%s, "
        "detected_browser_version=%s, webdriver_version=%s, "
        "webdriver_source=%s, browser=%s, launched_browser_version=%s, platform=%s",
        operating_system,
        driver_selection.browser,
        driver_selection.browser_version,
        driver_selection.driver_version,
        driver_selection.source,
        capabilities.get('browserName', 'unknown'),
        capabilities.get('browserVersion', 'unknown'),
        capabilities.get('platformName', 'unknown'),
    )
    return driver
