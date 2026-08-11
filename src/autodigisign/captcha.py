import logging
import re
import time

import cv2
import numpy as np
import pytesseract
from selenium.common.exceptions import (
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from autodigisign.selenium_helpers import safe_find


PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'
CAPTCHA_IMAGE_LOAD_TIMEOUT_SECONDS = 5
CAPTCHA_LENGTH = 6
CAPTCHA_PATTERN = re.compile(r'^[A-Z0-9]{6}$')
CAPTCHA_SCALE_FACTOR = 3
CAPTCHA_WHITELIST = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
CAPTCHA_OCR_STRATEGIES = (
    ('otsu-psm8', 'otsu', 8),
    ('adaptive-psm7', 'adaptive', 7),
    ('otsu-psm13', 'otsu', 13),
)


class CaptchaError(RuntimeError):
    """Base error for CAPTCHA capture or recognition failures."""


class RetryableCaptchaError(CaptchaError):
    """A new CAPTCHA or DOM attempt may recover from this failure."""


class CaptchaCaptureError(RetryableCaptchaError):
    """The current browser-rendered CAPTCHA image could not be captured."""


class CaptchaRecognitionError(RetryableCaptchaError):
    """The captured CAPTCHA image could not be processed or recognized."""


def capture_captcha_bytes(image_element):
    """Return the exact CAPTCHA currently rendered by the Selenium browser."""
    if image_element is None:
        raise CaptchaCaptureError("The CAPTCHA image element was not available.")

    try:
        image_bytes = image_element.screenshot_as_png
    except WebDriverException as error:
        raise CaptchaCaptureError(
            f"Could not capture the browser-rendered CAPTCHA image: {error}"
        ) from error

    if (
        not isinstance(image_bytes, (bytes, bytearray))
        or not image_bytes.startswith(PNG_SIGNATURE)
    ):
        raise CaptchaCaptureError(
            "The browser did not return a valid PNG CAPTCHA screenshot."
        )
    return bytes(image_bytes)


def decode_captcha_image(image_bytes):
    """Decode PNG bytes directly into a grayscale OpenCV image."""
    try:
        encoded_image = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(encoded_image, cv2.IMREAD_GRAYSCALE)
    except (TypeError, ValueError, cv2.error) as error:
        raise CaptchaRecognitionError(
            f"OpenCV could not decode the captured CAPTCHA image: {error}"
        ) from error
    if image is None or image.size == 0:
        raise CaptchaRecognitionError(
            "OpenCV could not decode the captured CAPTCHA image."
        )
    return image


def preprocess_captcha(image, method):
    """Scale and binarize one in-memory CAPTCHA image."""
    try:
        scaled = cv2.resize(
            image,
            None,
            fx=CAPTCHA_SCALE_FACTOR,
            fy=CAPTCHA_SCALE_FACTOR,
            interpolation=cv2.INTER_CUBIC,
        )
        if method == 'otsu':
            _, processed = cv2.threshold(
                scaled,
                0,
                255,
                cv2.THRESH_BINARY + cv2.THRESH_OTSU,
            )
        elif method == 'adaptive':
            denoised = cv2.GaussianBlur(scaled, (3, 3), 0)
            processed = cv2.adaptiveThreshold(
                denoised,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                31,
                9,
            )
        else:
            raise ValueError(f"Unsupported CAPTCHA preprocessing method: {method}")
    except cv2.error as error:
        raise CaptchaRecognitionError(
            f"OpenCV could not preprocess the CAPTCHA image: {error}"
        ) from error

    # Tesseract is more reliable with dark text on a predominantly light
    # background. Normalize the polarity without assuming the portal colors.
    if float(np.mean(processed)) < 127:
        processed = cv2.bitwise_not(processed)
    return np.ascontiguousarray(processed)


def recognize_captcha(processed_image, page_segmentation_mode):
    """Return a filtered uppercase alphanumeric CAPTCHA candidate."""
    config = (
        f'--oem 3 --psm {page_segmentation_mode} '
        f'-c tessedit_char_whitelist={CAPTCHA_WHITELIST}'
    )
    try:
        extracted_text = pytesseract.image_to_string(
            processed_image,
            config=config,
        )
    except (TypeError, ValueError, pytesseract.TesseractError) as error:
        raise CaptchaRecognitionError(
            f"Tesseract could not recognize the CAPTCHA image: {error}"
        ) from error

    filtered_text = re.sub(r'[^A-Z0-9]', '', extracted_text.upper()).strip()
    return filtered_text


def _wait_for_captcha_image(driver):
    image_element = safe_find(driver, By.ID, 'imgVerifyCode')
    logging.debug("CAPTCHA image element located.")
    try:
        WebDriverWait(
            driver,
            CAPTCHA_IMAGE_LOAD_TIMEOUT_SECONDS,
        ).until(
            lambda current_driver: current_driver.execute_script(
                "return Boolean(arguments[0] && arguments[0].complete "
                "&& arguments[0].naturalWidth > 0 "
                "&& arguments[0].naturalHeight > 0);",
                image_element,
            )
        )
    except (
        StaleElementReferenceException,
        TimeoutException,
        WebDriverException,
    ) as error:
        raise CaptchaCaptureError(
            "The browser-rendered CAPTCHA image did not finish loading."
        ) from error
    return image_element


def get_captcha_text(driver):
    """Capture and recognize the displayed CAPTCHA without writing files."""
    started_at = time.monotonic()
    image_element = _wait_for_captcha_image(driver)
    image_bytes = capture_captcha_bytes(image_element)
    image = decode_captcha_image(image_bytes)
    logging.debug(
        "CAPTCHA capture and decode completed: elapsed_ms=%.1f",
        (time.monotonic() - started_at) * 1000,
    )
    processed_images = {}

    for strategy_name, preprocessing_method, page_segmentation_mode in (
        CAPTCHA_OCR_STRATEGIES
    ):
        if preprocessing_method not in processed_images:
            preprocessing_started_at = time.monotonic()
            processed_images[preprocessing_method] = preprocess_captcha(
                image,
                preprocessing_method,
            )
            logging.debug(
                "CAPTCHA preprocessing completed: method=%s, elapsed_ms=%.1f",
                preprocessing_method,
                (time.monotonic() - preprocessing_started_at) * 1000,
            )
        attempt_started_at = time.monotonic()
        candidate = recognize_captcha(
            processed_images[preprocessing_method],
            page_segmentation_mode,
        )
        is_valid = CAPTCHA_PATTERN.fullmatch(candidate) is not None
        logging.debug(
            "CAPTCHA OCR strategy completed: method=%s, elapsed_ms=%.1f, "
            "candidate_length=%d, format_valid=%s",
            strategy_name,
            (time.monotonic() - attempt_started_at) * 1000,
            len(candidate),
            is_valid,
        )
        if is_valid:
            logging.debug(
                "CAPTCHA recognition selected method=%s, total_elapsed_ms=%.1f",
                strategy_name,
                (time.monotonic() - started_at) * 1000,
            )
            return candidate

    logging.debug(
        "CAPTCHA recognition exhausted all strategies: total_elapsed_ms=%.1f",
        (time.monotonic() - started_at) * 1000,
    )
    raise CaptchaRecognitionError(
        f"Tesseract did not produce an exact {CAPTCHA_LENGTH}-character "
        "uppercase alphanumeric CAPTCHA candidate."
    )
