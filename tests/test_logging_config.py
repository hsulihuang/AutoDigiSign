import logging
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

from autodigisign.logging_config import (  # noqa: E402
    AUTODIGISIGN_HANDLER_ATTRIBUTE,
    SensitiveDataFilter,
    log_exception,
    setup_logging,
)


class LoggingConfigTests(unittest.TestCase):
    def tearDown(self):
        root_logger = logging.getLogger()
        for handler in list(root_logger.handlers):
            if getattr(handler, AUTODIGISIGN_HANDLER_ATTRIBUTE, False):
                root_logger.removeHandler(handler)
                handler.close()

    def test_setup_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            setup_logging(temporary_directory, timestamp='first')
            setup_logging(temporary_directory, timestamp='second')

            handlers = [
                handler
                for handler in logging.getLogger().handlers
                if getattr(handler, AUTODIGISIGN_HANDLER_ATTRIBUTE, False)
            ]

            self.assertEqual(len(handlers), 3)

    def test_timestamp_precedes_log_type_in_filenames(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            debug_log, info_log = setup_logging(
                temporary_directory,
                timestamp='20260810T201352',
            )

            self.assertEqual(
                Path(debug_log).name,
                'autodigisign_20260810T201352_debug.log',
            )
            self.assertEqual(
                Path(info_log).name,
                'autodigisign_20260810T201352_info.log',
            )

    def test_same_second_uses_shared_suffix_without_overwriting(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            first_debug, first_info = setup_logging(
                temporary_directory,
                timestamp='20260810T201352',
            )
            logging.info('first run marker')

            second_debug, second_info = setup_logging(
                temporary_directory,
                timestamp='20260810T201352',
            )

            self.assertEqual(
                Path(second_debug).name,
                'autodigisign_20260810T201352_02_debug.log',
            )
            self.assertEqual(
                Path(second_info).name,
                'autodigisign_20260810T201352_02_info.log',
            )
            self.assertIn(
                'first run marker',
                Path(first_debug).read_text(encoding='utf-8'),
            )
            self.assertIn(
                'first run marker',
                Path(first_info).read_text(encoding='utf-8'),
            )

    def test_redacts_password_pin_and_session(self):
        text = (
            'SESSION=abc123 password=secret pincode=9876 '
            'sender_password=mail-secret'
        )

        redacted = SensitiveDataFilter.redact(text)

        self.assertNotIn('abc123', redacted)
        self.assertNotIn('secret', redacted)
        self.assertNotIn('9876', redacted)
        self.assertEqual(redacted.count('[REDACTED]'), 4)

    def test_info_exception_is_single_line_while_debug_keeps_traceback(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            debug_log, info_log = setup_logging(
                temporary_directory,
                timestamp='20260810T201352',
            )
            try:
                raise RuntimeError(
                    'primary error message\n'
                    'Stacktrace:\n'
                    'driver frame details'
                )
            except RuntimeError as error:
                log_exception('Operation failed', error)

            info_text = Path(info_log).read_text(encoding='utf-8')
            debug_text = Path(debug_log).read_text(encoding='utf-8')

            self.assertIn(
                'Operation failed: RuntimeError: primary error message',
                info_text,
            )
            self.assertNotIn('Stacktrace:', info_text)
            self.assertNotIn('driver frame details', info_text)
            self.assertEqual(len(info_text.splitlines()), 1)
            self.assertIn('Stacktrace:', debug_text)
            self.assertIn('driver frame details', debug_text)


if __name__ == '__main__':
    unittest.main()
