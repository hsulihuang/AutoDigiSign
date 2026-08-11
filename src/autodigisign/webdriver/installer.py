import hashlib
import json
import os
import shutil
import stat
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from autodigisign.webdriver.catalog import (
    ALLOWED_DOWNLOAD_HOSTS,
    HTTP_TIMEOUT,
    validate_official_url,
)
from autodigisign.webdriver.detection import (
    WebDriverManagementError,
    browser_executable_name,
    get_webdriver_version,
    versions_are_compatible,
)


MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 200 * 1024 * 1024


def _download_archive(http_client, url, archive_path):
    validate_official_url(url, ALLOWED_DOWNLOAD_HOSTS)
    response = http_client.get(url, timeout=HTTP_TIMEOUT, stream=True)
    archive_hash = hashlib.sha256()
    downloaded_bytes = 0
    try:
        response.raise_for_status()
        validate_official_url(
            getattr(response, 'url', url),
            ALLOWED_DOWNLOAD_HOSTS,
        )
        content_length = response.headers.get('Content-Length')
        try:
            declared_size = int(content_length) if content_length else None
        except (TypeError, ValueError) as error:
            raise WebDriverManagementError(
                "WebDriver download returned an invalid Content-Length header."
            ) from error
        if declared_size is not None and declared_size > MAX_DOWNLOAD_BYTES:
            raise WebDriverManagementError(
                "WebDriver download exceeded the permitted size."
            )
        with archive_path.open('wb') as archive_file:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                downloaded_bytes += len(chunk)
                if downloaded_bytes > MAX_DOWNLOAD_BYTES:
                    raise WebDriverManagementError(
                        "WebDriver download exceeded the permitted size."
                    )
                archive_hash.update(chunk)
                archive_file.write(chunk)
    finally:
        response.close()
    return archive_hash.hexdigest()


def _unique_backup_path(destination_path):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = destination_path.with_name(
        f"{destination_path.name}.invalid-{timestamp}"
    )
    counter = 1
    while backup_path.exists():
        backup_path = destination_path.with_name(
            f"{destination_path.name}.invalid-{timestamp}-{counter}"
        )
        counter += 1
    return backup_path


def download_webdriver(
    project_root,
    browser,
    operating_system,
    browser_version,
    driver_version,
    driver_platform,
    download_url,
    http_client,
):
    """Download, verify, and retain a version-labelled WebDriver executable."""
    webdriver_root = Path(project_root) / 'webdrivers'
    webdriver_root.mkdir(parents=True, exist_ok=True)
    executable_name = browser_executable_name(browser, operating_system)
    destination_directory = (
        webdriver_root / browser / driver_platform.label / driver_version
    )
    destination_path = destination_directory / executable_name

    with tempfile.TemporaryDirectory(
        prefix='.webdriver-download-',
        dir=str(webdriver_root),
    ) as temporary_directory:
        temporary_path = Path(temporary_directory)
        archive_path = temporary_path / 'webdriver.zip'
        archive_sha256 = _download_archive(
            http_client,
            download_url,
            archive_path,
        )

        try:
            with zipfile.ZipFile(archive_path) as archive:
                total_uncompressed_size = sum(
                    member.file_size for member in archive.infolist()
                )
                if total_uncompressed_size > MAX_UNCOMPRESSED_BYTES:
                    raise WebDriverManagementError(
                        "WebDriver archive exceeded the permitted extracted size."
                    )
                corrupt_member = archive.testzip()
                if corrupt_member:
                    raise WebDriverManagementError(
                        f"Downloaded WebDriver archive is corrupt: {corrupt_member}"
                    )
                executable_members = [
                    member
                    for member in archive.infolist()
                    if not member.is_dir()
                    and member.filename.replace('\\', '/').rsplit('/', 1)[-1]
                    == executable_name
                ]
                if len(executable_members) != 1:
                    raise WebDriverManagementError(
                        "Downloaded archive did not contain exactly one "
                        f"{executable_name}."
                    )
                executable_member = executable_members[0]
                if executable_member.file_size > MAX_DOWNLOAD_BYTES:
                    raise WebDriverManagementError(
                        "WebDriver executable exceeded the permitted size."
                    )
                extracted_path = temporary_path / executable_name
                with archive.open(executable_member) as source_file:
                    with extracted_path.open('wb') as destination_file:
                        shutil.copyfileobj(source_file, destination_file)
        except zipfile.BadZipFile as error:
            raise WebDriverManagementError(
                "Downloaded WebDriver file was not a valid ZIP archive."
            ) from error

        extracted_path.chmod(
            extracted_path.stat().st_mode
            | stat.S_IXUSR
            | stat.S_IXGRP
            | stat.S_IXOTH
        )
        actual_driver_version = get_webdriver_version(
            extracted_path,
            operating_system,
        )
        if actual_driver_version != driver_version:
            raise WebDriverManagementError(
                f"Downloaded driver reported version {actual_driver_version}; "
                f"expected {driver_version}."
            )
        if not versions_are_compatible(browser_version, actual_driver_version):
            raise WebDriverManagementError(
                f"Downloaded driver {actual_driver_version} is not compatible with "
                f"{browser.title()} {browser_version}."
            )

        destination_directory.mkdir(parents=True, exist_ok=True)
        staging_path = destination_directory / (
            f".installing-{uuid.uuid4().hex}-{executable_name}"
        )
        try:
            shutil.copy2(extracted_path, staging_path)
            if destination_path.exists():
                destination_path.replace(_unique_backup_path(destination_path))
            os.replace(staging_path, destination_path)
        finally:
            if staging_path.exists():
                staging_path.unlink()

    metadata = {
        'browser': browser,
        'detected_browser_version': browser_version,
        'webdriver_version': driver_version,
        'operating_system': operating_system,
        'platform': driver_platform.label,
        'source_url': download_url,
        'archive_sha256': archive_sha256,
        'downloaded_at_utc': datetime.now(timezone.utc).isoformat(),
    }
    metadata_path = destination_directory / 'webdriver_metadata.json'
    metadata_staging_path = destination_directory / (
        f".webdriver-metadata-{uuid.uuid4().hex}.tmp"
    )
    try:
        metadata_staging_path.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False) + '\n',
            encoding='utf-8',
        )
        os.replace(metadata_staging_path, metadata_path)
    finally:
        if metadata_staging_path.exists():
            metadata_staging_path.unlink()
    return destination_path
