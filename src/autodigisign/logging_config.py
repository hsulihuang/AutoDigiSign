import logging
import os
import re
from datetime import datetime


AUTODIGISIGN_HANDLER_ATTRIBUTE = '_autodigisign_handler'
LOG_TIMESTAMP_FORMAT = '%Y%m%dT%H%M%S'
MAX_INFO_EXCEPTION_MESSAGE_CHARACTERS = 500

_RENDERED_SECRET_VALUE = (
    r"(?:\[REDACTED\]|'(?:\\.|[^'\\])*'|"
    r"\"(?:\\.|[^\"\\])*\"|[^,;\s&}\])]+)"
)


def _create_empty_file_exclusively(file_path):
    descriptor = os.open(
        file_path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )
    os.close(descriptor)


def _reserve_log_filepaths(log_directory, timestamp):
    """Reserve one collision-safe INFO/DEBUG filename pair for a run."""
    collision_number = 1
    while True:
        run_identifier = (
            timestamp
            if collision_number == 1
            else f'{timestamp}_{collision_number:02d}'
        )
        debug_log_filepath = os.path.join(
            log_directory,
            f'autodigisign_{run_identifier}_debug.log',
        )
        info_log_filepath = os.path.join(
            log_directory,
            f'autodigisign_{run_identifier}_info.log',
        )
        created_filepaths = []
        try:
            for file_path in (debug_log_filepath, info_log_filepath):
                _create_empty_file_exclusively(file_path)
                created_filepaths.append(file_path)
        except FileExistsError:
            for file_path in created_filepaths:
                os.remove(file_path)
            collision_number += 1
            continue
        except Exception:
            for file_path in created_filepaths:
                os.remove(file_path)
            raise
        return debug_log_filepath, info_log_filepath


class SensitiveDataFilter(logging.Filter):
    """Redact credential, authorization, and session values from logs."""

    _patterns = (
        (
            re.compile(
                r"(?i)("
                r"(?<!\w)['\"]?"
                r"(?:sender_password|password|passwd|pincode|pin|"
                r"verify(?:[\s_-]*code)|"
                r"verification(?:[\s_-]*(?:code|value))?|"
                r"session(?:[\s_-]*(?:id|token|key))?)"
                r"['\"]?\s*[:=]\s*"
                r")"
                + _RENDERED_SECRET_VALUE
            ),
            r"\1[REDACTED]",
        ),
        (
            re.compile(
                r"(?i)((?<!\w)['\"]?Authorization['\"]?\s*[:=]\s*)"
                r"(?:(?:Bearer|Basic)\s+)?"
                + _RENDERED_SECRET_VALUE
            ),
            r"\1[REDACTED]",
        ),
        (
            re.compile(r"(?i)(\bBearer\s+)" + _RENDERED_SECRET_VALUE),
            r"\1[REDACTED]",
        ),
    )

    @classmethod
    def redact(cls, text):
        """Redact secrets from a fully rendered log entry."""
        redacted_text = text
        for pattern, replacement in cls._patterns:
            redacted_text = pattern.sub(replacement, redacted_text)
        return redacted_text

    def filter(self, record):
        message = self.redact(record.getMessage())
        record.msg = message
        record.args = ()
        return True


class SensitiveDataFormatter(logging.Formatter):
    """Redact after formatting so exception tracebacks are covered as well."""

    def format(self, record):
        return SensitiveDataFilter.redact(super().format(record))


def setup_logging(log_directory, timestamp=None):
    if timestamp is None:
        timestamp = datetime.now().strftime(LOG_TIMESTAMP_FORMAT)

    os.makedirs(log_directory, exist_ok=True)
    debug_log_filepath, info_log_filepath = _reserve_log_filepaths(
        log_directory,
        timestamp,
    )

    # Set up the root logger. Remove only handlers previously installed by this
    # function so repeated setup in tests or embedded use remains idempotent.
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Set root level to DEBUG to allow all messages
    for existing_handler in list(logger.handlers):
        if getattr(existing_handler, AUTODIGISIGN_HANDLER_ATTRIBUTE, False):
            logger.removeHandler(existing_handler)
            existing_handler.close()

    # Keep application diagnostics while suppressing third-party wire logs that
    # may contain passwords, PINs, session tokens, or other request payloads.
    for noisy_logger in ('selenium', 'urllib3', 'PIL', 'pytesseract'):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)

    sensitive_data_filter = SensitiveDataFilter()

    # File handler to log everything at DEBUG level with UTF-8 encoding
    file_handler_debug = logging.FileHandler(
        debug_log_filepath,
        mode='a',
        encoding='utf-8',
    )
    file_handler_debug.setLevel(logging.DEBUG)  # Record all levels of logs
    file_formatter_debug = SensitiveDataFormatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    )
    file_handler_debug.setFormatter(file_formatter_debug)
    file_handler_debug.addFilter(sensitive_data_filter)
    setattr(file_handler_debug, AUTODIGISIGN_HANDLER_ATTRIBUTE, True)

    # File handler to log INFO level and above with UTF-8 encoding
    file_handler_info = logging.FileHandler(
        info_log_filepath,
        mode='a',
        encoding='utf-8',
    )
    file_handler_info.setLevel(logging.INFO)  # Record only INFO and above
    file_formatter_info = SensitiveDataFormatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    )
    file_handler_info.setFormatter(file_formatter_info)
    file_handler_info.addFilter(sensitive_data_filter)
    setattr(file_handler_info, AUTODIGISIGN_HANDLER_ATTRIBUTE, True)

    # Keep live terminal output without creating a separate console log file.
    terminal_handler = logging.StreamHandler()
    terminal_handler.setLevel(logging.DEBUG)
    terminal_formatter = SensitiveDataFormatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    )
    terminal_handler.setFormatter(terminal_formatter)
    terminal_handler.addFilter(sensitive_data_filter)
    setattr(terminal_handler, AUTODIGISIGN_HANDLER_ATTRIBUTE, True)

    # Add handlers to the logger
    logger.addHandler(file_handler_debug)
    logger.addHandler(file_handler_info)
    logger.addHandler(terminal_handler)

    # Return log file paths if needed
    return debug_log_filepath, info_log_filepath


def format_exception_summary(error):
    """Return one length-bounded physical line for an exception."""
    concise_message = next(
        (
            line.strip()
            for line in str(error).splitlines()
            if line.strip()
        ),
        '<no message>',
    )
    if len(concise_message) > MAX_INFO_EXCEPTION_MESSAGE_CHARACTERS:
        concise_message = (
            concise_message[: MAX_INFO_EXCEPTION_MESSAGE_CHARACTERS - 3]
            + '...'
        )
    return f"{type(error).__name__}: {concise_message}"


def log_exception(summary, error):
    """Write a concise error to INFO and the complete traceback to DEBUG."""
    logging.error(
        "%s: %s",
        summary,
        format_exception_summary(error),
    )
    logging.debug(
        "%s traceback",
        summary,
        exc_info=(type(error), error, error.__traceback__),
    )
