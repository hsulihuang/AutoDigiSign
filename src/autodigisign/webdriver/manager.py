"""Coordinate compatible local WebDriver selection and installation."""

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

import requests

from autodigisign.webdriver.catalog import (
    resolve_chrome_download,
    resolve_edge_download,
    resolve_webdriver_download,
)
from autodigisign.webdriver.detection import (
    DriverPlatform,
    WebDriverManagementError,
    browser_executable_name,
    detect_browser_version,
    extract_version,
    get_driver_platform,
    get_webdriver_version,
    validate_browser,
    version_tuple,
    versions_are_compatible,
)
from autodigisign.webdriver.installer import download_webdriver


@dataclass(frozen=True)
class WebDriverSelection:
    browser: str
    browser_version: str
    driver_version: str
    driver_path: Path
    platform: str
    source: str


def find_compatible_local_webdriver(
    project_root,
    browser,
    operating_system,
    browser_version,
    driver_platform,
):
    """Return the newest executable whose reported build matches the browser."""
    validate_browser(browser)
    executable_name = browser_executable_name(browser, operating_system)
    driver_directory = Path(project_root) / 'webdrivers'
    compatible_candidates = []
    for candidate_path in driver_directory.rglob(executable_name):
        if not candidate_path.is_file():
            continue
        try:
            driver_version = get_webdriver_version(
                candidate_path,
                operating_system,
            )
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            logging.debug(
                "Ignored unreadable %s WebDriver candidate: %s",
                browser.title(),
                error,
            )
            continue
        if versions_are_compatible(browser_version, driver_version):
            platform_match = driver_platform.label in str(candidate_path.parent)
            compatible_candidates.append(
                (
                    platform_match,
                    version_tuple(driver_version),
                    str(candidate_path),
                    candidate_path,
                    driver_version,
                )
            )
    if not compatible_candidates:
        return None
    selected = max(compatible_candidates)
    return selected[3], selected[4]


def _display_project_path(path, project_root):
    try:
        return str(Path(path).relative_to(Path(project_root)))
    except ValueError:
        return Path(path).name


def ensure_webdriver(
    project_root,
    browser,
    operating_system,
    browser_version=None,
    machine_name=None,
    http_client=None,
):
    """Use a compatible local driver or download and retain the correct version."""
    validate_browser(browser)
    http_client = http_client or requests
    browser_version = browser_version or detect_browser_version(
        browser,
        operating_system,
    )
    browser_version = extract_version(browser_version)
    driver_platform = get_driver_platform(operating_system, machine_name)
    logging.info(
        "Browser detected: browser=%s, version=%s, operating_system=%s, platform=%s",
        browser,
        browser_version,
        operating_system,
        driver_platform.label,
    )

    local_selection = find_compatible_local_webdriver(
        project_root,
        browser,
        operating_system,
        browser_version,
        driver_platform,
    )
    if local_selection:
        driver_path, driver_version = local_selection
        logging.info(
            "Using compatible local WebDriver: browser=%s, browser_version=%s, "
            "webdriver_version=%s, file=%s",
            browser,
            browser_version,
            driver_version,
            _display_project_path(driver_path, project_root),
        )
        return WebDriverSelection(
            browser,
            browser_version,
            driver_version,
            driver_path,
            driver_platform.label,
            'local',
        )

    logging.info(
        "No compatible local WebDriver found: browser=%s, browser_version=%s. "
        "Checking the official version catalog.",
        browser,
        browser_version,
    )
    driver_version, download_url = resolve_webdriver_download(
        browser,
        browser_version,
        driver_platform,
        http_client,
    )
    driver_path = download_webdriver(
        project_root,
        browser,
        operating_system,
        browser_version,
        driver_version,
        driver_platform,
        download_url,
        http_client,
    )
    logging.info(
        "Downloaded compatible WebDriver: browser=%s, browser_version=%s, "
        "webdriver_version=%s, file=%s",
        browser,
        browser_version,
        driver_version,
        _display_project_path(driver_path, project_root),
    )
    return WebDriverSelection(
        browser,
        browser_version,
        driver_version,
        driver_path,
        driver_platform.label,
        'downloaded',
    )


__all__ = (
    'DriverPlatform',
    'WebDriverManagementError',
    'WebDriverSelection',
    'detect_browser_version',
    'download_webdriver',
    'ensure_webdriver',
    'extract_version',
    'find_compatible_local_webdriver',
    'get_driver_platform',
    'get_webdriver_version',
    'resolve_chrome_download',
    'resolve_edge_download',
    'resolve_webdriver_download',
    'version_tuple',
    'versions_are_compatible',
)
