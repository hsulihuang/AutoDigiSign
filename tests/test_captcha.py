import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import cv2
import numpy as np
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

from autodigisign.captcha import (  # noqa: E402
    CAPTCHA_IMAGE_LOAD_TIMEOUT_SECONDS,
    PNG_SIGNATURE,
    CaptchaCaptureError,
    CaptchaRecognitionError,
    _wait_for_captcha_image,
    capture_captcha_bytes,
    decode_captcha_image,
    get_captcha_text,
    preprocess_captcha,
    recognize_captcha,
)


class _BrokenScreenshotElement:
    @property
    def screenshot_as_png(self):
        raise WebDriverException('browser capture failed')


class CaptchaTests(unittest.TestCase):
    def test_capture_returns_browser_rendered_png_bytes(self):
        image_element = MagicMock()
        image_element.screenshot_as_png = PNG_SIGNATURE + b'image-data'

        result = capture_captcha_bytes(image_element)

        self.assertEqual(result, PNG_SIGNATURE + b'image-data')

    def test_browser_capture_failure_is_retryable(self):
        with self.assertRaisesRegex(
            CaptchaCaptureError,
            'browser-rendered CAPTCHA',
        ):
            capture_captcha_bytes(_BrokenScreenshotElement())

    def test_invalid_browser_screenshot_is_capture_error(self):
        image_element = MagicMock()
        image_element.screenshot_as_png = b'not-a-png'

        with self.assertRaisesRegex(CaptchaCaptureError, 'valid PNG'):
            capture_captcha_bytes(image_element)

    def test_decode_and_preprocess_image_without_files(self):
        original = np.full((20, 80), 255, dtype=np.uint8)
        cv2.putText(
            original,
            'AB12C3',
            (1, 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            0,
            1,
            cv2.LINE_AA,
        )
        encoded, image_buffer = cv2.imencode('.png', original)
        self.assertTrue(encoded)

        decoded = decode_captcha_image(image_buffer.tobytes())
        otsu = preprocess_captcha(decoded, 'otsu')
        adaptive = preprocess_captcha(decoded, 'adaptive')

        self.assertEqual(decoded.shape, original.shape)
        self.assertEqual(otsu.shape, (60, 240))
        self.assertEqual(adaptive.shape, (60, 240))

    def test_recognition_filters_to_allowed_uppercase_characters(self):
        with patch(
            'autodigisign.captcha.pytesseract.image_to_string',
            return_value='ab-12c3\n',
        ) as image_to_string:
            result = recognize_captcha(np.zeros((10, 10)), 8)

        self.assertEqual(result, 'AB12C3')
        config = image_to_string.call_args.kwargs['config']
        self.assertIn('--psm 8', config)
        self.assertIn(
            'tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
            config,
        )

    def test_waits_until_displayed_captcha_is_loaded(self):
        driver = MagicMock()
        image_element = MagicMock()
        wait = MagicMock()

        with patch(
            'autodigisign.captcha.safe_find',
            return_value=image_element,
        ) as safe_find:
            with patch(
                'autodigisign.captcha.WebDriverWait',
                return_value=wait,
            ) as wait_constructor:
                result = _wait_for_captcha_image(driver)

        self.assertIs(result, image_element)
        safe_find.assert_called_once_with(driver, By.ID, 'imgVerifyCode')
        wait_constructor.assert_called_once_with(
            driver,
            CAPTCHA_IMAGE_LOAD_TIMEOUT_SECONDS,
        )
        load_predicate = wait.until.call_args.args[0]
        driver.execute_script.return_value = True
        self.assertTrue(load_predicate(driver))
        driver.execute_script.assert_called_once()

    def test_image_load_timeout_is_retryable(self):
        wait = MagicMock()
        wait.until.side_effect = TimeoutException()

        with patch('autodigisign.captcha.safe_find', return_value=MagicMock()):
            with patch(
                'autodigisign.captcha.WebDriverWait',
                return_value=wait,
            ):
                with self.assertRaisesRegex(
                    CaptchaCaptureError,
                    'did not finish loading',
                ):
                    _wait_for_captcha_image(MagicMock())

    def test_valid_six_character_primary_result_stops_fallbacks(self):
        driver = MagicMock()
        image_element = MagicMock()
        decoded_image = object()
        processed_image = object()

        with patch(
            'autodigisign.captcha._wait_for_captcha_image',
            return_value=image_element,
        ):
            with patch(
                'autodigisign.captcha.capture_captcha_bytes',
                return_value=PNG_SIGNATURE,
            ) as capture:
                with patch(
                    'autodigisign.captcha.decode_captcha_image',
                    return_value=decoded_image,
                ):
                    with patch(
                        'autodigisign.captcha.preprocess_captcha',
                        return_value=processed_image,
                    ) as preprocess:
                        with patch(
                            'autodigisign.captcha.recognize_captcha',
                            return_value='AB12C3',
                        ) as recognize:
                            result = get_captcha_text(driver)

        self.assertEqual(result, 'AB12C3')
        capture.assert_called_once_with(image_element)
        preprocess.assert_called_once_with(decoded_image, 'otsu')
        recognize.assert_called_once_with(processed_image, 8)

    def test_invalid_results_use_fallbacks_and_reuse_preprocessing(self):
        otsu_image = object()
        adaptive_image = object()

        with patch(
            'autodigisign.captcha._wait_for_captcha_image',
            return_value=MagicMock(),
        ):
            with patch(
                'autodigisign.captcha.capture_captcha_bytes',
                return_value=PNG_SIGNATURE,
            ):
                with patch(
                    'autodigisign.captcha.decode_captcha_image',
                    return_value=object(),
                ) as decode:
                    with patch(
                        'autodigisign.captcha.preprocess_captcha',
                        side_effect=[otsu_image, adaptive_image],
                    ) as preprocess:
                        with patch(
                            'autodigisign.captcha.recognize_captcha',
                            side_effect=['AB12', 'CD34E', 'EF56G7'],
                        ) as recognize:
                            result = get_captcha_text(MagicMock())

        self.assertEqual(result, 'EF56G7')
        decoded_image = decode.return_value
        self.assertEqual(
            preprocess.call_args_list,
            [
                call(decoded_image, 'otsu'),
                call(decoded_image, 'adaptive'),
            ],
        )
        self.assertEqual(
            recognize.call_args_list,
            [
                call(otsu_image, 8),
                call(adaptive_image, 7),
                call(otsu_image, 13),
            ],
        )

    def test_all_non_six_character_results_are_rejected(self):
        with patch(
            'autodigisign.captcha._wait_for_captcha_image',
            return_value=MagicMock(),
        ):
            with patch(
                'autodigisign.captcha.capture_captcha_bytes',
                return_value=PNG_SIGNATURE,
            ):
                with patch(
                    'autodigisign.captcha.decode_captcha_image',
                    return_value=object(),
                ):
                    with patch(
                        'autodigisign.captcha.preprocess_captcha',
                        return_value=object(),
                    ):
                        with patch(
                            'autodigisign.captcha.recognize_captcha',
                            side_effect=['ABCDE', 'ABCDEFG', '12_ABC'],
                        ):
                            with self.assertRaisesRegex(
                                CaptchaRecognitionError,
                                'exact 6-character',
                            ):
                                get_captcha_text(MagicMock())


if __name__ == '__main__':
    unittest.main()
