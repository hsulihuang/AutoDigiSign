import logging
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

from autodigisign.browser import (  # noqa: E402
    detect_operating_system,
    initialize_driver,
)
from autodigisign.webdriver.manager import WebDriverSelection  # noqa: E402


class BrowserTests(unittest.TestCase):
    def test_detects_only_supported_operating_systems(self):
        self.assertEqual(detect_operating_system('darwin'), 'macos')
        self.assertEqual(detect_operating_system('win32'), 'windows')
        with self.assertRaisesRegex(EnvironmentError, 'Unsupported'):
            detect_operating_system('linux')

    def test_windows_also_prefers_edge_then_falls_back_to_chrome(self):
        chrome_selection = WebDriverSelection(
            browser='chrome',
            browser_version='151.0.7922.108',
            driver_version='151.0.7922.108',
            driver_path=Path('chromedriver.exe'),
            platform='windows-x64',
            source='local',
        )
        driver = MagicMock()
        driver.capabilities = {
            'browserName': 'chrome',
            'browserVersion': '151.0.7922.108',
            'platformName': 'windows',
        }

        edge_error = RuntimeError(
            'Edge unavailable\nStacktrace:\ndriver frame details'
        )
        with self.assertLogs(level='DEBUG') as captured_logs:
            with patch(
                'autodigisign.browser.ensure_webdriver',
                side_effect=[edge_error, chrome_selection],
            ) as ensure_webdriver:
                with patch(
                    'autodigisign.browser.start_browser',
                    return_value=driver,
                ) as start_browser:
                    result = initialize_driver(
                        PROJECT_ROOT,
                        operating_system='windows',
                    )

        self.assertIs(result, driver)
        self.assertEqual(
            [call.args[1] for call in ensure_webdriver.call_args_list],
            ['edge', 'chrome'],
        )
        start_browser.assert_called_once_with(
            'chrome',
            Path('chromedriver.exe'),
        )
        warning_messages = [
            record.getMessage()
            for record in captured_logs.records
            if record.levelno == logging.WARNING
        ]
        self.assertEqual(len(warning_messages), 1)
        self.assertNotIn('\n', warning_messages[0])
        self.assertNotIn('driver frame details', warning_messages[0])
        self.assertIn('driver frame details', '\n'.join(captured_logs.output))


if __name__ == '__main__':
    unittest.main()
