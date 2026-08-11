import logging
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from selenium.common.exceptions import (
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.keys import Keys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

from autodigisign.signing import (  # noqa: E402
    SIGNATURE_BUTTON_ID,
    SIGNATURE_POPUP_TIMEOUT_SECONDS,
    SIGNATURE_PROCESSING_TIMEOUT_SECONDS,
    SignatureDriverStateError,
    SignatureReaderTypeError,
    SignatureTimeoutError,
    _evaluate_signature_message,
    _replace_input_value,
    _restore_main_window,
    _start_processing_deadline,
    _wait_for_employee_postback,
    _wait_for_popup,
    digital_signature,
)
from autodigisign.signing_workflow import process_employees  # noqa: E402


class FakeSwitchTo:
    def __init__(self, driver):
        self.driver = driver

    def window(self, handle):
        if handle not in self.driver.window_handles:
            raise RuntimeError('missing window')
        self.driver.current_window_handle = handle


class FakeDriver:
    def __init__(self, handles):
        self.window_handles = list(handles)
        self.current_window_handle = self.window_handles[0]
        self.switch_to = FakeSwitchTo(self)

    def close(self):
        self.window_handles.remove(self.current_window_handle)

    def find_element(self, by, value):
        raise RuntimeError(
            'no confirm button\nStacktrace:\ndriver frame details'
        )


class FakeClock:
    def __init__(self):
        self.current_time = 0

    def monotonic(self):
        return self.current_time

    def sleep(self, seconds):
        self.current_time += seconds


class DelayedPopupDriver:
    def __init__(self, clock, popup_time):
        self.clock = clock
        self.popup_time = popup_time

    @property
    def window_handles(self):
        if self.clock.current_time >= self.popup_time:
            return ['main', 'popup']
        return ['main']


class SigningTests(unittest.TestCase):
    def test_pcsc_button_and_stage_timeouts_are_fixed(self):
        self.assertEqual(
            SIGNATURE_BUTTON_ID,
            'NTUHWeb1_btnDoSignatureByPCSC',
        )
        self.assertEqual(SIGNATURE_POPUP_TIMEOUT_SECONDS, 30)
        self.assertEqual(SIGNATURE_PROCESSING_TIMEOUT_SECONDS, 180)

    def test_wrong_reader_message_stops_batch(self):
        with self.assertRaisesRegex(
            SignatureReaderTypeError,
            'reader may be the wrong type',
        ):
            _evaluate_signature_message(
                '[-1]查無錯誤代碼定義。',
                '100001',
                'User',
            )

    def test_popup_wait_uses_popup_deadline(self):
        clock = FakeClock()
        driver = DelayedPopupDriver(clock, popup_time=11)

        with patch(
            'autodigisign.signing.time.monotonic',
            side_effect=clock.monotonic,
        ):
            with patch(
                'autodigisign.signing.time.sleep',
                side_effect=clock.sleep,
            ):
                popup_handle = _wait_for_popup(
                    driver,
                    main_window='main',
                    deadline=30,
                )

        self.assertEqual(popup_handle, 'popup')
        self.assertGreaterEqual(clock.current_time, 11)
        self.assertLess(clock.current_time, 30)

    def test_processing_deadline_starts_once_and_is_not_extended(self):
        with patch(
            'autodigisign.signing.time.monotonic',
            return_value=10,
        ) as monotonic:
            deadline = _start_processing_deadline(
                '批次電子簽章作業中，請勿取出卡片。',
                None,
            )
            unchanged_deadline = _start_processing_deadline(
                '批次電子簽章作業中，請勿取出卡片。',
                deadline,
            )

        self.assertEqual(deadline, 190)
        self.assertEqual(unchanged_deadline, 190)
        monotonic.assert_called_once_with()

    def test_non_processing_message_does_not_start_processing_deadline(self):
        with patch('autodigisign.signing.time.monotonic') as monotonic:
            deadline = _start_processing_deadline(
                '簽章元件初始化中',
                None,
            )

        self.assertIsNone(deadline)
        monotonic.assert_not_called()

    def test_in_progress_signature_can_complete_after_sixty_seconds(self):
        clock = FakeClock()
        driver = MagicMock()
        driver.current_window_handle = 'main'
        sign_button = MagicMock()
        employee_field = MagicMock()
        postback_wait = MagicMock()
        postback_wait.until.side_effect = TimeoutException()

        def find_element(_driver, _by, value, **_kwargs):
            if value == SIGNATURE_BUTTON_ID:
                return sign_button
            if value == 'dsInfo':
                message = (
                    '[PCSC] 簽章完成, 共完成43筆簽章'
                    if clock.current_time >= 60
                    else '批次電子簽章作業中，請勿取出卡片。'
                )
                return SimpleNamespace(text=message)
            raise AssertionError(f'Unexpected element lookup: {value}')

        with patch(
            'autodigisign.signing._replace_input_value',
            return_value=employee_field,
        ):
            with patch(
                'autodigisign.signing.WebDriverWait',
                return_value=postback_wait,
            ):
                with patch(
                    'autodigisign.signing.safe_find',
                    side_effect=find_element,
                ):
                    with patch(
                        'autodigisign.signing._wait_for_popup',
                        return_value='popup',
                    ) as wait_for_popup:
                        with patch(
                            'autodigisign.signing._restore_main_window',
                        ):
                            with patch(
                                'autodigisign.signing.time.monotonic',
                                side_effect=clock.monotonic,
                            ):
                                with patch(
                                    'autodigisign.signing.time.sleep',
                                    side_effect=clock.sleep,
                                ):
                                    digital_signature(
                                        '100001',
                                        'User',
                                        '1234',
                                        driver,
                                    )

        self.assertGreaterEqual(clock.current_time, 60)
        self.assertLess(clock.current_time, 63)
        self.assertEqual(wait_for_popup.call_args.args[2], 30)
        sign_button.click.assert_called_once_with()

    def test_in_progress_signature_times_out_after_180_seconds(self):
        clock = FakeClock()
        driver = MagicMock()
        driver.current_window_handle = 'main'
        sign_button = MagicMock()
        employee_field = MagicMock()
        postback_wait = MagicMock()
        postback_wait.until.side_effect = TimeoutException()

        def find_element(_driver, _by, value, **_kwargs):
            if value == SIGNATURE_BUTTON_ID:
                return sign_button
            if value == 'dsInfo':
                return SimpleNamespace(
                    text='批次電子簽章作業中，請勿取出卡片。'
                )
            raise AssertionError(f'Unexpected element lookup: {value}')

        with patch(
            'autodigisign.signing._replace_input_value',
            return_value=employee_field,
        ):
            with patch(
                'autodigisign.signing.WebDriverWait',
                return_value=postback_wait,
            ):
                with patch(
                    'autodigisign.signing.safe_find',
                    side_effect=find_element,
                ):
                    with patch(
                        'autodigisign.signing._wait_for_popup',
                        return_value='popup',
                    ):
                        with patch(
                            'autodigisign.signing._restore_main_window',
                        ):
                            with patch(
                                'autodigisign.signing.time.monotonic',
                                side_effect=clock.monotonic,
                            ):
                                with patch(
                                    'autodigisign.signing.time.sleep',
                                    side_effect=clock.sleep,
                                ):
                                    with self.assertRaisesRegex(
                                        SignatureTimeoutError,
                                        'more than 180 seconds',
                                    ):
                                        digital_signature(
                                            '100001',
                                            'User',
                                            '1234',
                                            driver,
                                        )

        self.assertEqual(clock.current_time, 180)
        sign_button.click.assert_called_once_with()

    def test_input_is_refound_after_clear_can_replace_the_dom(self):
        driver = MagicMock()
        previous_field = MagicMock()
        previous_field.get_attribute.return_value = 'previous employee'
        replacement_field = MagicMock()
        wait = MagicMock()

        with patch(
            'autodigisign.signing.safe_find',
            side_effect=[previous_field, replacement_field],
        ) as safe_find:
            with patch(
                'autodigisign.signing.WebDriverWait',
                return_value=wait,
            ):
                result = _replace_input_value(
                    driver,
                    'NTUHWeb1_txbEmpNO',
                    '100001',
                    Keys.ENTER,
                )

        self.assertIs(result, replacement_field)
        self.assertEqual(safe_find.call_count, 2)
        previous_field.clear.assert_called_once_with()
        previous_field.send_keys.assert_not_called()
        replacement_field.send_keys.assert_called_once_with(
            '100001',
            Keys.ENTER,
        )
        wait.until.assert_called_once()

    def test_stale_input_action_refinds_and_retries_before_signing(self):
        driver = MagicMock()
        stale_field = MagicMock()
        stale_field.get_attribute.return_value = ''
        stale_field.send_keys.side_effect = StaleElementReferenceException(
            'replaced after lookup'
        )
        replacement_field = MagicMock()
        replacement_field.get_attribute.return_value = ''

        with patch(
            'autodigisign.signing.safe_find',
            side_effect=[stale_field, replacement_field],
        ) as safe_find:
            with patch('autodigisign.signing.time.sleep') as sleep:
                result = _replace_input_value(
                    driver,
                    'NTUHWeb1_txbEmpNO',
                    '100001',
                    Keys.ENTER,
                )

        self.assertIs(result, replacement_field)
        self.assertEqual(safe_find.call_count, 2)
        stale_field.clear.assert_not_called()
        replacement_field.clear.assert_not_called()
        replacement_field.send_keys.assert_called_once_with(
            '100001',
            Keys.ENTER,
        )
        sleep.assert_called_once()

    def test_detached_node_error_is_treated_as_completed_postback(self):
        wait = MagicMock()
        wait.until.side_effect = WebDriverException(
            'unknown error: unhandled inspector error: '
            '{"code":-32000,"message":"Node with given id does not '
            'belong to the document"}'
        )

        with patch(
            'autodigisign.signing.WebDriverWait',
            return_value=wait,
        ):
            _wait_for_employee_postback(MagicMock(), MagicMock())

        wait.until.assert_called_once()

    def test_unrelated_postback_webdriver_error_is_not_hidden(self):
        wait = MagicMock()
        wait.until.side_effect = WebDriverException(
            'disconnected: not connected to DevTools'
        )

        with patch(
            'autodigisign.signing.WebDriverWait',
            return_value=wait,
        ):
            with self.assertRaisesRegex(
                WebDriverException,
                'not connected to DevTools',
            ):
                _wait_for_employee_postback(MagicMock(), MagicMock())

    def test_cleanup_returns_to_main_window(self):
        driver = FakeDriver(['main', 'popup'])
        driver.current_window_handle = 'popup'

        with self.assertLogs(level='DEBUG') as captured_logs:
            _restore_main_window(driver, 'main', 'popup')

        self.assertEqual(driver.window_handles, ['main'])
        self.assertEqual(driver.current_window_handle, 'main')
        warning_messages = [
            record.getMessage()
            for record in captured_logs.records
            if record.levelno == logging.WARNING
        ]
        self.assertEqual(len(warning_messages), 1)
        self.assertNotIn('\n', warning_messages[0])
        self.assertNotIn('driver frame details', warning_messages[0])
        self.assertIn('driver frame details', '\n'.join(captured_logs.output))

    def test_cleanup_reports_lost_main_window(self):
        driver = FakeDriver(['popup'])

        with self.assertRaises(SignatureDriverStateError):
            _restore_main_window(driver, 'main', 'popup')

    def test_batch_continues_for_employee_error_but_stops_for_driver_state(self):
        employees = [
            {'id': '1', 'name': 'One'},
            {'id': '2', 'name': 'Two'},
        ]
        with patch(
            'autodigisign.signing_workflow.digital_signature',
            side_effect=[RuntimeError('employee failure'), None],
        ) as sign:
            failed_employee_count = process_employees(
                MagicMock(),
                employees,
                '1',
            )
        self.assertEqual(sign.call_count, 2)
        self.assertEqual(failed_employee_count, 1)

        with patch(
            'autodigisign.signing_workflow.digital_signature',
            side_effect=SignatureDriverStateError('broken'),
        ) as sign:
            with self.assertRaises(SignatureDriverStateError):
                process_employees(MagicMock(), employees, '1')
        self.assertEqual(sign.call_count, 1)


if __name__ == '__main__':
    unittest.main()
