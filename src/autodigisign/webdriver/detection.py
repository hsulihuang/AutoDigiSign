import logging
import os
import platform
import plistlib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


VERSION_PATTERN = re.compile(r'\d+\.\d+\.\d+\.\d+')
SUPPORTED_BROWSERS = ('edge', 'chrome')


class WebDriverManagementError(RuntimeError):
    """Raised when a compatible browser driver cannot be prepared."""


@dataclass(frozen=True)
class DriverPlatform:
    label: str
    edge_archive: str
    chrome_archive: str


def validate_browser(browser):
    if browser not in SUPPORTED_BROWSERS:
        raise ValueError(
            f"Unsupported browser: {browser!r}. Expected edge or chrome."
        )
    return browser


def extract_version(value):
    """Extract a four-part Chromium version from text."""
    match = VERSION_PATTERN.search(str(value))
    if not match:
        raise ValueError(f"No four-part version number was found in: {value}")
    return match.group(0)


def version_tuple(version):
    return tuple(int(part) for part in extract_version(version).split('.'))


def versions_are_compatible(browser_version, driver_version):
    """Chromium browsers and drivers are compatible by the first three parts."""
    return version_tuple(browser_version)[:3] == version_tuple(driver_version)[:3]


def get_driver_platform(operating_system, machine_name=None):
    """Map the current operating system and CPU to vendor archive names."""
    machine_name = (machine_name or platform.machine()).lower()
    if operating_system == 'macos':
        if machine_name in ('arm64', 'aarch64'):
            return DriverPlatform('macos-arm64', 'mac64_m1', 'mac-arm64')
        if machine_name in ('x86_64', 'amd64'):
            return DriverPlatform('macos-x64', 'mac64', 'mac-x64')
    elif operating_system == 'windows':
        if machine_name in ('arm64', 'aarch64'):
            return DriverPlatform('windows-arm64', 'arm64', 'win64')
        if machine_name in ('x86_64', 'amd64'):
            return DriverPlatform('windows-x64', 'win64', 'win64')
        if machine_name in ('x86', 'i386', 'i686'):
            return DriverPlatform('windows-x86', 'win32', 'win32')
    raise WebDriverManagementError(
        f"Unsupported {operating_system} processor architecture: {machine_name}"
    )


def browser_executable_name(browser, operating_system):
    validate_browser(browser)
    if operating_system == 'windows':
        return 'msedgedriver.exe' if browser == 'edge' else 'chromedriver.exe'
    if operating_system == 'macos':
        return 'msedgedriver' if browser == 'edge' else 'chromedriver'
    raise WebDriverManagementError(
        f"Unsupported operating system for WebDriver: {operating_system}"
    )


def _detect_macos_browser_version(browser):
    application_name = {
        'edge': 'Microsoft Edge.app',
        'chrome': 'Google Chrome.app',
    }[browser]
    application_paths = (
        Path('/Applications') / application_name,
        Path.home() / 'Applications' / application_name,
    )
    for application_path in application_paths:
        plist_path = application_path / 'Contents' / 'Info.plist'
        if not plist_path.is_file():
            continue
        try:
            with plist_path.open('rb') as plist_file:
                application_info = plistlib.load(plist_file)
            return extract_version(
                application_info.get('CFBundleShortVersionString')
                or application_info.get('CFBundleVersion')
            )
        except (OSError, ValueError, plistlib.InvalidFileException) as error:
            logging.debug(
                "Could not read %s browser version from macOS metadata: %s",
                browser.title(),
                error,
            )
    return None


def _detect_windows_registry_version(browser):
    try:
        import winreg
    except ImportError:
        return None

    registry_path = {
        'edge': r'SOFTWARE\Microsoft\Edge\BLBeacon',
        'chrome': r'SOFTWARE\Google\Chrome\BLBeacon',
    }[browser]
    access_modes = [winreg.KEY_READ]
    for view_name in ('KEY_WOW64_64KEY', 'KEY_WOW64_32KEY'):
        access_mode = winreg.KEY_READ | getattr(winreg, view_name, 0)
        if access_mode not in access_modes:
            access_modes.append(access_mode)

    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for access_mode in access_modes:
            try:
                with winreg.OpenKey(
                    hive,
                    registry_path,
                    0,
                    access_mode,
                ) as registry_key:
                    version, _ = winreg.QueryValueEx(registry_key, 'version')
                return extract_version(version)
            except (OSError, ValueError):
                continue
    return None


def _windows_browser_paths(browser):
    relative_path = {
        'edge': Path('Microsoft') / 'Edge' / 'Application' / 'msedge.exe',
        'chrome': Path('Google') / 'Chrome' / 'Application' / 'chrome.exe',
    }[browser]
    roots = (
        os.environ.get('PROGRAMFILES(X86)'),
        os.environ.get('PROGRAMFILES'),
        os.environ.get('LOCALAPPDATA'),
    )
    return [Path(root) / relative_path for root in roots if root]


def _detect_windows_file_version(browser):
    for executable_path in _windows_browser_paths(browser):
        if not executable_path.is_file():
            continue
        runtime_environment = os.environ.copy()
        runtime_environment['AUTODIGISIGN_BROWSER_PATH'] = str(executable_path)
        command = (
            '$browserPath = '
            "[Environment]::GetEnvironmentVariable('AUTODIGISIGN_BROWSER_PATH'); "
            '(Get-Item -LiteralPath $browserPath).VersionInfo.ProductVersion'
        )
        try:
            completed = subprocess.run(
                [
                    'powershell.exe',
                    '-NoProfile',
                    '-NonInteractive',
                    '-Command',
                    command,
                ],
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
                env=runtime_environment,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            )
            return extract_version(completed.stdout)
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            logging.debug(
                "Could not read %s browser version from Windows executable: %s",
                browser.title(),
                error,
            )
    return None


def detect_browser_version(browser, operating_system):
    """Detect the installed stable browser version without launching it."""
    validate_browser(browser)
    if operating_system == 'macos':
        version = _detect_macos_browser_version(browser)
    elif operating_system == 'windows':
        version = (
            _detect_windows_registry_version(browser)
            or _detect_windows_file_version(browser)
        )
    else:
        raise WebDriverManagementError(
            f"Unsupported operating system for browser detection: {operating_system}"
        )
    if version is None:
        raise WebDriverManagementError(
            f"{browser.title()} is not installed or its version could not be detected."
        )
    return version


def get_webdriver_version(driver_path, operating_system):
    """Read the actual version reported by a local WebDriver executable."""
    run_options = {}
    if operating_system == 'windows':
        run_options['creationflags'] = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    completed = subprocess.run(
        [str(driver_path), '--version'],
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
        **run_options,
    )
    return extract_version(f"{completed.stdout}\n{completed.stderr}")
