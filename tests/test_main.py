import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

from autodigisign import __main__ as main  # noqa: E402
from autodigisign.config import (  # noqa: E402
    CredentialsSettings,
    ProjectPaths,
)


class MainTests(unittest.TestCase):
    def logging_paths(self, directory):
        info_log = Path(directory) / 'info.log'
        debug_log = Path(directory) / 'debug.log'
        info_log.write_text('', encoding='utf-8')
        debug_log.write_text('', encoding='utf-8')
        return str(debug_log), str(info_log)

    def test_python_314_is_required(self):
        main.validate_python_version((3, 14, 6))

        with self.assertRaisesRegex(
            RuntimeError,
            r'requires Python 3\.14\.x; detected Python 3\.13',
        ):
            main.validate_python_version((3, 13, 11))

    def test_logs_are_grouped_by_year_and_month(self):
        self.assertEqual(
            main.get_log_directory(
                Path('/project'),
                '20260810T213359',
            ),
            Path('/project/outputs/logs/2026/08'),
        )

    def test_required_input_failure_happens_before_browser_start(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            with patch(
                'autodigisign.__main__.setup_logging',
                return_value=self.logging_paths(temporary_directory),
            ):
                with patch(
                    'autodigisign.__main__.resolve_project_paths',
                    side_effect=FileNotFoundError('missing credentials'),
                ):
                    with patch(
                        'autodigisign.__main__.initialize_driver'
                    ) as initialize_driver:
                        with patch('autodigisign.__main__.logging.shutdown'):
                            exit_code = main.main()

        self.assertEqual(exit_code, 1)
        initialize_driver.assert_not_called()

    def test_optional_email_absence_does_not_change_success(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            paths = ProjectPaths(
                credentials=root / 'credentials.ini',
                employee_list=root / 'employee_list.txt',
                email_config=None,
            )
            credentials = CredentialsSettings(
                username='user',
                password='password',
                pincode='1234',
            )
            employees = [{'id': '1', 'name': 'One'}]
            driver = MagicMock()

            with patch(
                'autodigisign.__main__.setup_logging',
                return_value=self.logging_paths(temporary_directory),
            ):
                with patch(
                    'autodigisign.__main__.resolve_project_paths',
                    return_value=paths,
                ):
                    with patch(
                        'autodigisign.__main__.load_credentials_settings',
                        return_value=credentials,
                    ):
                        with patch(
                            'autodigisign.__main__.get_employees',
                            return_value=employees,
                        ):
                            with patch(
                                'autodigisign.__main__.initialize_driver',
                                return_value=driver,
                            ):
                                with patch(
                                    'autodigisign.__main__.retry_login',
                                    return_value=True,
                                ):
                                    with patch(
                                        'autodigisign.__main__.navigate'
                                    ) as navigate:
                                        with patch(
                                            'autodigisign.__main__.process_employees',
                                            return_value=0,
                                        ) as process_employees:
                                            with patch(
                                                'autodigisign.__main__.'
                                                'send_email_with_attachment'
                                            ) as send_email:
                                                with patch(
                                                    'autodigisign.__main__.'
                                                    'logging.shutdown'
                                                ):
                                                    exit_code = main.main()

        self.assertEqual(exit_code, 0)
        driver.get.assert_called_once_with(main.PORTAL_LOGIN_URL)
        driver.quit.assert_called_once()
        navigate.assert_called_once_with(driver)
        process_employees.assert_called_once_with(
            driver,
            employees,
            '1234',
        )
        send_email.assert_not_called()

    def test_employee_failures_return_nonzero_exit_code(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            paths = ProjectPaths(
                credentials=root / 'credentials.ini',
                employee_list=root / 'employee_list.txt',
                email_config=None,
            )
            credentials = CredentialsSettings(
                username='user',
                password='password',
                pincode='1234',
            )
            driver = MagicMock()

            with patch(
                'autodigisign.__main__.setup_logging',
                return_value=self.logging_paths(temporary_directory),
            ):
                with patch(
                    'autodigisign.__main__.resolve_project_paths',
                    return_value=paths,
                ):
                    with patch(
                        'autodigisign.__main__.load_credentials_settings',
                        return_value=credentials,
                    ):
                        with patch(
                            'autodigisign.__main__.get_employees',
                            return_value=[{'id': '1', 'name': 'One'}],
                        ):
                            with patch(
                                'autodigisign.__main__.initialize_driver',
                                return_value=driver,
                            ):
                                with patch(
                                    'autodigisign.__main__.retry_login',
                                    return_value=True,
                                ):
                                    with patch('autodigisign.__main__.navigate'):
                                        with patch(
                                            'autodigisign.__main__.process_employees',
                                            return_value=1,
                                        ):
                                            with patch(
                                                'autodigisign.__main__.'
                                                'logging.shutdown'
                                            ):
                                                exit_code = main.main()

        self.assertEqual(exit_code, 1)
        driver.quit.assert_called_once()


if __name__ == '__main__':
    unittest.main()
