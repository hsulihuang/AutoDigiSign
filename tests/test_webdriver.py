import io
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

from autodigisign.webdriver.catalog import (  # noqa: E402
    resolve_edge_download,
    validate_official_url,
)
from autodigisign.webdriver.detection import (  # noqa: E402
    DriverPlatform,
    WebDriverManagementError,
    extract_version,
    get_driver_platform,
    versions_are_compatible,
)
from autodigisign.webdriver.installer import download_webdriver  # noqa: E402
from autodigisign.webdriver.manager import ensure_webdriver  # noqa: E402


class FakeResponse:
    def __init__(self, payload=None, content=b'', url=''):
        self._payload = payload
        self._content = content
        self.url = url
        self.headers = {'Content-Length': str(len(content))}
        self.closed = False

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload

    def close(self):
        self.closed = True

    def iter_content(self, chunk_size):
        yield self._content


class WebDriverTests(unittest.TestCase):
    def test_version_and_platform_logic(self):
        self.assertEqual(extract_version('Edge 134.0.3124.93'), '134.0.3124.93')
        self.assertTrue(
            versions_are_compatible('134.0.3124.93', '134.0.3124.51')
        )
        self.assertFalse(
            versions_are_compatible('134.0.3124.93', '135.0.3179.1')
        )
        self.assertEqual(
            get_driver_platform('windows', 'AMD64').label,
            'windows-x64',
        )
        self.assertEqual(
            get_driver_platform('macos', 'arm64').label,
            'macos-arm64',
        )

    def test_non_official_download_url_is_rejected(self):
        with self.assertRaises(WebDriverManagementError):
            validate_official_url(
                'https://attacker.example/driver.zip',
                {'msedgedriver.microsoft.com'},
            )

    def test_historical_edge_catalog_selects_matching_build(self):
        platform = DriverPlatform('windows-x64', 'win64', 'win64')
        response = FakeResponse(
            payload={
                'items': [
                    {'name': '134.0.3124.51/edgedriver_win64.zip'},
                    {'name': '135.0.3179.1/edgedriver_win64.zip'},
                ]
            },
            url='https://msedgedriver.microsoft.com/listing.json',
        )
        client = MagicMock()
        client.get.return_value = response

        version, url = resolve_edge_download(
            '134.0.3124.93',
            platform,
            client,
        )

        self.assertEqual(version, '134.0.3124.51')
        self.assertEqual(
            url,
            'https://msedgedriver.microsoft.com/'
            '134.0.3124.51/edgedriver_win64.zip',
        )
        self.assertTrue(response.closed)

    def test_ensure_rejects_unknown_browser_before_network_access(self):
        client = MagicMock()
        with self.assertRaisesRegex(ValueError, 'Unsupported browser'):
            ensure_webdriver(
                '/tmp/project',
                'firefox',
                'macos',
                browser_version='1.2.3.4',
                http_client=client,
            )
        client.get.assert_not_called()

    def test_download_uses_versioned_path_and_writes_metadata(self):
        archive_buffer = io.BytesIO()
        with zipfile.ZipFile(archive_buffer, mode='w') as archive:
            archive.writestr('driver/msedgedriver', b'binary')
        download_url = (
            'https://msedgedriver.microsoft.com/'
            '134.0.3124.51/edgedriver_mac64_m1.zip'
        )
        response = FakeResponse(
            content=archive_buffer.getvalue(),
            url=download_url,
        )
        client = MagicMock()
        client.get.return_value = response
        platform = DriverPlatform('macos-arm64', 'mac64_m1', 'mac-arm64')

        with tempfile.TemporaryDirectory() as temporary_directory:
            with patch(
                'autodigisign.webdriver.installer.get_webdriver_version',
                return_value='134.0.3124.51',
            ):
                driver_path = download_webdriver(
                    temporary_directory,
                    'edge',
                    'macos',
                    '134.0.3124.93',
                    '134.0.3124.51',
                    platform,
                    download_url,
                    client,
                )

            self.assertEqual(
                driver_path.relative_to(temporary_directory),
                Path('webdrivers/edge/macos-arm64/134.0.3124.51/msedgedriver'),
            )
            self.assertTrue(driver_path.is_file())
            self.assertTrue(
                (driver_path.parent / 'webdriver_metadata.json').is_file()
            )


if __name__ == '__main__':
    unittest.main()
