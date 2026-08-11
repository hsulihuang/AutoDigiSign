import time

from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
)


def safe_find(driver, by, value, retries=3, delay=1):
    """Find an element while tolerating short-lived DOM replacement."""
    if retries <= 0:
        raise ValueError("retries must be greater than zero.")
    if delay < 0:
        raise ValueError("delay must not be negative.")

    last_error = None
    for attempt in range(retries):
        try:
            return driver.find_element(by, value)
        except (StaleElementReferenceException, NoSuchElementException) as error:
            last_error = error
            if attempt + 1 < retries and delay:
                time.sleep(delay)
    raise last_error
