import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

from autodigisign.email_delivery import (  # noqa: E402
    EmailConfigurationError,
    generate_email_subject,
    load_email_settings,
    send_email_with_attachment,
)


class EmailDeliveryTests(unittest.TestCase):
    def write_config(self, directory, contents):
        path = Path(directory) / 'email_config.ini'
        path.write_text(contents, encoding='utf-8')
        return path

    def valid_config(self):
        return (
            '[email]\n'
            'smtp_server=smtp.example.com\n'
            'smtp_port=587\n'
            'sender_email=sender@example.com\n'
            'sender_password=app-password\n'
            'recipients=one@example.com, two@example.com\n'
        )

    def test_loads_and_normalizes_recipients(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            settings = load_email_settings(
                self.write_config(temporary_directory, self.valid_config())
            )

        self.assertEqual(settings.smtp_port, 587)
        self.assertEqual(
            settings.recipients,
            ('one@example.com', 'two@example.com'),
        )

    def test_missing_section_and_recipients_are_explicit(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            missing_section = self.write_config(
                temporary_directory,
                '[other]\nvalue=1\n',
            )
            with self.assertRaisesRegex(EmailConfigurationError, r'\[email\]'):
                load_email_settings(missing_section)

            missing_recipients = self.write_config(
                temporary_directory,
                self.valid_config().replace(
                    'recipients=one@example.com, two@example.com\n',
                    '',
                ),
            )
            with self.assertRaisesRegex(
                EmailConfigurationError,
                r'email\.recipients',
            ):
                load_email_settings(missing_recipients)

    def test_smtp_uses_timeout_tls_and_both_attachments(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            config_path = self.write_config(directory, self.valid_config())
            info_log = directory / 'info.log'
            debug_log = directory / 'debug.log'
            info_log.write_text('info', encoding='utf-8')
            debug_log.write_text('debug', encoding='utf-8')

            smtp_server = unittest.mock.MagicMock()
            with patch(
                'autodigisign.email_delivery.smtplib.SMTP',
                return_value=smtp_server,
            ) as smtp:
                send_email_with_attachment(
                    config_path,
                    'subject',
                    'body',
                    info_log,
                    debug_log,
                )

            smtp.assert_called_once_with(
                'smtp.example.com',
                587,
                timeout=30,
            )
            smtp_server.starttls.assert_called_once()
            smtp_server.login.assert_called_once_with(
                'sender@example.com',
                'app-password',
            )
            sent_message = smtp_server.sendmail.call_args.args[2]
            self.assertIn('filename=info.log', sent_message)
            self.assertIn('filename=debug.log', sent_message)
            smtp_server.quit.assert_called_once()
            smtp_server.close.assert_called_once()

    def test_smtp_close_does_not_hide_delivery_error(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            config_path = self.write_config(directory, self.valid_config())
            info_log = directory / 'info.log'
            debug_log = directory / 'debug.log'
            info_log.write_text('info', encoding='utf-8')
            debug_log.write_text('debug', encoding='utf-8')
            smtp_server = unittest.mock.MagicMock()
            smtp_server.sendmail.side_effect = RuntimeError('delivery failed')
            smtp_server.close.side_effect = RuntimeError('close failed')

            with patch(
                'autodigisign.email_delivery.smtplib.SMTP',
                return_value=smtp_server,
            ):
                with self.assertRaisesRegex(RuntimeError, 'delivery failed'):
                    send_email_with_attachment(
                        config_path,
                        'subject',
                        'body',
                        info_log,
                        debug_log,
                    )

            smtp_server.quit.assert_not_called()

    def test_subject_alert_uses_log_level_field_not_message_keyword(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            info_log = Path(temporary_directory) / 'info.log'
            info_log.write_text(
                '2026 - INFO - root - no error occurred\n',
                encoding='utf-8',
            )
            self.assertNotIn(
                '[Alert]',
                generate_email_subject(info_log, 'timestamp'),
            )
            info_log.write_text(
                '2026 - ERROR - root - failure\n',
                encoding='utf-8',
            )
            self.assertIn(
                '[Alert]',
                generate_email_subject(info_log, 'timestamp'),
            )


if __name__ == '__main__':
    unittest.main()
