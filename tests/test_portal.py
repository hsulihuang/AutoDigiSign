import logging
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from selenium.common.exceptions import NoSuchElementException, TimeoutException


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

from autodigisign.captcha import CaptchaCaptureError  # noqa: E402
from autodigisign.portal import (  # noqa: E402
    LOGIN_REJECTED,
    LOGIN_SUCCEEDED,
    PortalNavigationError,
    _detect_login_outcome,
    navigate,
    retry_login,
)


class PortalTests(unittest.TestCase):
    def test_login_retries_timeout_then_succeeds(self):
        driver = MagicMock()
        captcha_loader = MagicMock(return_value='AB12C3')
        wait = MagicMock()
        wait.until.side_effect = [TimeoutException(), LOGIN_SUCCEEDED]

        with patch('autodigisign.portal.login') as login:
            with patch('autodigisign.portal.WebDriverWait', return_value=wait):
                result = retry_login(
                    driver,
                    'username',
                    'password',
                    max_retries=2,
                    captcha_loader=captcha_loader,
                )

        self.assertTrue(result)
        self.assertEqual(login.call_count, 2)
        self.assertEqual(captcha_loader.call_count, 2)
        driver.refresh.assert_called_once_with()

    def test_explicit_rejection_retries_without_waiting_for_timeout(self):
        driver = MagicMock()
        captcha_loader = MagicMock(side_effect=['AB12C3', 'DE45F6'])
        wait = MagicMock()
        wait.until.side_effect = [LOGIN_REJECTED, LOGIN_SUCCEEDED]

        with patch('autodigisign.portal.login') as login:
            with patch('autodigisign.portal.WebDriverWait', return_value=wait):
                result = retry_login(
                    driver,
                    'username',
                    'password',
                    max_retries=2,
                    captcha_loader=captcha_loader,
                )

        self.assertTrue(result)
        self.assertEqual(login.call_count, 2)
        driver.refresh.assert_not_called()

    def test_login_retries_browser_captcha_capture_failure(self):
        driver = MagicMock()
        captcha_loader = MagicMock(
            side_effect=[
                CaptchaCaptureError(
                    'capture failed\nStacktrace:\ndriver frame details'
                ),
                'AB12C3',
            ]
        )
        wait = MagicMock()
        wait.until.return_value = LOGIN_SUCCEEDED

        with self.assertLogs(level='DEBUG') as captured_logs:
            with patch('autodigisign.portal.login') as login:
                with patch('autodigisign.portal.WebDriverWait', return_value=wait):
                    result = retry_login(
                        driver,
                        'username',
                        'password',
                        max_retries=2,
                        captcha_loader=captcha_loader,
                    )

        self.assertTrue(result)
        self.assertEqual(captcha_loader.call_count, 2)
        driver.refresh.assert_called_once_with()
        login.assert_called_once_with(
            driver,
            'username',
            'password',
            'AB12C3',
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

    def test_unexpected_login_programming_error_is_not_hidden(self):
        def broken_loader(*args):
            raise RuntimeError('unexpected')

        with self.assertRaisesRegex(RuntimeError, 'unexpected'):
            retry_login(
                MagicMock(),
                'username',
                'password',
                max_retries=1,
                captcha_loader=broken_loader,
            )

    def test_outcome_detector_identifies_success(self):
        driver = MagicMock()

        self.assertEqual(_detect_login_outcome(driver), LOGIN_SUCCEEDED)
        self.assertEqual(driver.find_element.call_count, 1)

    def test_outcome_detector_identifies_new_blank_login_form_as_rejected(self):
        driver = MagicMock()
        verify_code = MagicMock()
        verify_code.get_attribute.return_value = ''
        driver.find_element.side_effect = [
            NoSuchElementException(),
            verify_code,
        ]

        self.assertEqual(_detect_login_outcome(driver), LOGIN_REJECTED)

    def test_navigate_requires_session_and_does_not_guess(self):
        driver = MagicMock()
        driver.current_url = 'https://portal.example/home'
        with self.assertRaises(PortalNavigationError):
            navigate(driver)

        driver.current_url = 'https://portal.example/home?SESSION=abc123'
        navigate(driver)
        driver.get.assert_called_once_with(
            'https://ihisaw.ntuh.gov.tw/WebApplication/'
            'DigitalSignature/DsQuery.aspx?SESSION=abc123'
        )


if __name__ == '__main__':
    unittest.main()
