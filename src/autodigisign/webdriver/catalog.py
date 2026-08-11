from urllib.parse import urlparse

from autodigisign.webdriver.detection import (
    WebDriverManagementError,
    extract_version,
    validate_browser,
    version_tuple,
    versions_are_compatible,
)


EDGE_CATALOG_URL = 'https://msedgedriver.microsoft.com/listing.json'
EDGE_DOWNLOAD_ROOT = 'https://msedgedriver.microsoft.com'
CHROME_BUILD_URL = (
    'https://googlechromelabs.github.io/chrome-for-testing/'
    'latest-patch-versions-per-build-with-downloads.json'
)
CHROME_MILESTONE_URL = (
    'https://googlechromelabs.github.io/chrome-for-testing/'
    'latest-versions-per-milestone-with-downloads.json'
)
HTTP_TIMEOUT = (10, 120)
ALLOWED_DOWNLOAD_HOSTS = {
    'msedgedriver.microsoft.com',
    'storage.googleapis.com',
    'chromedriver.storage.googleapis.com',
}
ALLOWED_METADATA_HOSTS = {
    'msedgedriver.microsoft.com',
    'googlechromelabs.github.io',
}


def validate_official_url(url, allowed_hosts):
    parsed_url = urlparse(url)
    if parsed_url.scheme != 'https' or parsed_url.hostname not in allowed_hosts:
        raise WebDriverManagementError(
            f"Refused non-official WebDriver URL: {url}"
        )


def _request_json(http_client, url):
    validate_official_url(url, ALLOWED_METADATA_HOSTS)
    response = http_client.get(url, timeout=HTTP_TIMEOUT)
    try:
        response.raise_for_status()
        validate_official_url(
            getattr(response, 'url', url),
            ALLOWED_METADATA_HOSTS,
        )
        payload = response.json()
    finally:
        response.close()
    if not isinstance(payload, (dict, list)):
        raise WebDriverManagementError(
            "Official WebDriver catalog returned an unexpected data structure."
        )
    return payload


def resolve_edge_download(browser_version, driver_platform, http_client):
    """Resolve an exact or build-compatible historical EdgeDriver download."""
    browser_build = '.'.join(browser_version.split('.')[:3])
    listing = _request_json(http_client, EDGE_CATALOG_URL)
    items = listing.get('items', listing) if isinstance(listing, dict) else listing
    if not isinstance(items, list):
        raise WebDriverManagementError(
            "Microsoft EdgeDriver catalog did not contain an item list."
        )

    archive_name = f"edgedriver_{driver_platform.edge_archive}.zip"
    candidates = []
    for item in items:
        if not isinstance(item, dict):
            continue
        item_name = item.get('name', '')
        if not isinstance(item_name, str) or not item_name.endswith(
            f'/{archive_name}'
        ):
            continue
        candidate_version = item_name.split('/', maxsplit=1)[0]
        try:
            if versions_are_compatible(browser_version, candidate_version):
                candidates.append((candidate_version, item_name))
        except ValueError:
            continue
    if not candidates:
        raise WebDriverManagementError(
            f"Microsoft does not list an EdgeDriver for Edge build {browser_build} "
            f"on {driver_platform.label}."
        )

    exact_candidates = [
        candidate for candidate in candidates if candidate[0] == browser_version
    ]
    selected_version, selected_name = max(
        exact_candidates or candidates,
        key=lambda candidate: version_tuple(candidate[0]),
    )
    download_url = f"{EDGE_DOWNLOAD_ROOT}/{selected_name}"
    validate_official_url(download_url, ALLOWED_DOWNLOAD_HOSTS)
    return selected_version, download_url


def _select_chrome_download(entry, browser_version, platform_name):
    if not isinstance(entry, dict) or 'version' not in entry:
        return None
    try:
        driver_version = extract_version(entry['version'])
    except (TypeError, ValueError):
        return None
    if not versions_are_compatible(browser_version, driver_version):
        return None
    downloads = entry.get('downloads', {}).get('chromedriver', [])
    if not isinstance(downloads, list):
        return None
    for download in downloads:
        if not isinstance(download, dict):
            continue
        if download.get('platform') == platform_name and download.get('url'):
            validate_official_url(download['url'], ALLOWED_DOWNLOAD_HOSTS)
            return driver_version, download['url']
    return None


def resolve_chrome_download(browser_version, driver_platform, http_client):
    """Resolve the official Chrome for Testing driver for installed Chrome."""
    browser_parts = browser_version.split('.')
    browser_major = int(browser_parts[0])
    if browser_major < 115:
        raise WebDriverManagementError(
            "Automatic ChromeDriver downloads require Chrome 115 or newer."
        )

    browser_build = '.'.join(browser_parts[:3])
    build_listing = _request_json(http_client, CHROME_BUILD_URL)
    if isinstance(build_listing, dict):
        build_entry = build_listing.get('builds', {}).get(browser_build)
        if build_entry:
            selected = _select_chrome_download(
                build_entry,
                browser_version,
                driver_platform.chrome_archive,
            )
            if selected:
                return selected

    milestone_listing = _request_json(http_client, CHROME_MILESTONE_URL)
    if isinstance(milestone_listing, dict):
        milestone_entry = milestone_listing.get('milestones', {}).get(
            str(browser_major)
        )
        if milestone_entry:
            selected = _select_chrome_download(
                milestone_entry,
                browser_version,
                driver_platform.chrome_archive,
            )
            if selected:
                return selected

    raise WebDriverManagementError(
        f"Google does not list a compatible ChromeDriver for Chrome build "
        f"{browser_build} on {driver_platform.label}."
    )


def resolve_webdriver_download(
    browser,
    browser_version,
    driver_platform,
    http_client,
):
    validate_browser(browser)
    if browser == 'edge':
        return resolve_edge_download(browser_version, driver_platform, http_client)
    return resolve_chrome_download(browser_version, driver_platform, http_client)
