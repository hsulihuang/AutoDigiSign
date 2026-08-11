import configparser
import logging
import os
import re
import smtplib
import ssl
from dataclasses import dataclass
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path


SMTP_TIMEOUT_SECONDS = 30


class EmailConfigurationError(ValueError):
    """Raised when email_config.ini is present but invalid."""


@dataclass(frozen=True)
class EmailSettings:
    smtp_server: str
    smtp_port: int
    sender_email: str
    sender_password: str
    recipients: tuple


def load_email_settings(email_config_filepath):
    """Load and validate all email settings before the signing workflow starts."""
    config_path = Path(email_config_filepath)
    if not config_path.is_file():
        raise FileNotFoundError(
            f"Email configuration file was not found: {config_path}"
        )

    config = configparser.ConfigParser()
    try:
        loaded_files = config.read(config_path, encoding='utf-8-sig')
    except (configparser.Error, OSError) as error:
        raise EmailConfigurationError(
            f"Could not read email configuration {config_path}: {error}"
        ) from error
    if not loaded_files or not config.has_section('email'):
        raise EmailConfigurationError(
            f"Missing [email] section in {config_path}."
        )

    required_options = (
        'smtp_server',
        'smtp_port',
        'sender_email',
        'sender_password',
        'recipients',
    )
    values = {}
    for option in required_options:
        if not config.has_option('email', option):
            raise EmailConfigurationError(
                f"Missing email.{option} in {config_path}."
            )
        value = config.get('email', option)
        if not value.strip():
            raise EmailConfigurationError(
                f"Configuration value email.{option} is empty in {config_path}."
            )
        values[option] = value

    try:
        smtp_port = int(values['smtp_port'].strip())
    except ValueError as error:
        raise EmailConfigurationError(
            f"email.smtp_port must be an integer in {config_path}."
        ) from error
    if not 1 <= smtp_port <= 65535:
        raise EmailConfigurationError(
            f"email.smtp_port must be between 1 and 65535 in {config_path}."
        )

    recipients = tuple(
        recipient.strip()
        for recipient in values['recipients'].split(',')
        if recipient.strip()
    )
    if not recipients:
        raise EmailConfigurationError(
            f"email.recipients must contain at least one address in {config_path}."
        )

    return EmailSettings(
        smtp_server=values['smtp_server'].strip(),
        smtp_port=smtp_port,
        sender_email=values['sender_email'].strip(),
        sender_password=values['sender_password'],
        recipients=recipients,
    )


def generate_email_subject(info_log_filepath, timestamp):
    with open(info_log_filepath, 'r', encoding='utf-8') as log_file:
        for line in log_file:
            if re.search(r' - (?:WARNING|ERROR|CRITICAL) - ', line):
                return f"{timestamp} [Alert] AutoDigiSign Finished"
    return f"{timestamp} AutoDigiSign Finished Successfully"


def generate_email_body(info_log_filepath):
    email_body_lines = []
    with open(info_log_filepath, 'r', encoding='utf-8') as log_file:
        for line in log_file:
            if re.search(r' - (?:WARNING|ERROR|CRITICAL) - ', line):
                email_body_lines.append(line)
            elif '- INFO -' in line and 'AutoDigiSign' in line:
                match = re.search(r'AutoDigiSign (.*)', line)
                if match:
                    email_body_lines.append(f"{match.group(0)}\n")
            elif '- INFO -' in line and 'Employee ID' in line:
                match = re.search(
                    r'Employee ID: (\d+), Name: (.*), Web message: (.*)',
                    line,
                )
                if match:
                    employee_id = match.group(1).strip()
                    employee_name = match.group(2).strip()
                    message = re.sub(
                        r"\[CrossBrowser\]\s*",
                        "",
                        match.group(3).strip(),
                    )
                    if re.search('查無待簽章電子病歷資料', message):
                        message = '無待簽章'
                    email_body_lines.append(
                        f"{employee_name}({employee_id}){message}\n"
                    )
            elif '- INFO -' not in line:
                email_body_lines.append(line)

    return (
        "AutoDigiSign Log Summary:\n\n"
        + "".join(email_body_lines)
        + "\nNote: This is an automated log summary. Please check the log file "
        "for complete details."
    )


def _attach_file(message, file_path):
    with open(file_path, 'rb') as attachment:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
    encoders.encode_base64(part)
    part.add_header(
        'Content-Disposition',
        f'attachment; filename={os.path.basename(file_path)}',
    )
    message.attach(part)


def send_email_with_attachment(
    email_config_filepath,
    subject,
    body,
    info_log_filepath,
    debug_log_filepath,
    settings=None,
):
    """Send INFO and DEBUG logs using validated SMTP settings."""
    settings = settings or load_email_settings(email_config_filepath)

    message = MIMEMultipart()
    message['From'] = settings.sender_email
    message['To'] = ', '.join(settings.recipients)
    message['Subject'] = subject
    message.attach(MIMEText(body, 'plain', 'utf-8'))
    _attach_file(message, info_log_filepath)
    _attach_file(message, debug_log_filepath)

    tls_context = ssl.create_default_context()
    server = smtplib.SMTP(
        settings.smtp_server,
        settings.smtp_port,
        timeout=SMTP_TIMEOUT_SECONDS,
    )
    try:
        server.starttls(context=tls_context)
        server.login(settings.sender_email, settings.sender_password)
        server.sendmail(
            settings.sender_email,
            list(settings.recipients),
            message.as_string(),
        )
        try:
            server.quit()
        except smtplib.SMTPException:
            # Delivery has already completed. Do not replace that result with a
            # secondary protocol error raised only while closing the session.
            logging.debug("SMTP QUIT failed after log delivery.", exc_info=True)
    finally:
        try:
            server.close()
        except Exception:
            # Closing must never hide the original connection, TLS, login, or
            # delivery exception.
            logging.debug("SMTP connection close failed.", exc_info=True)

    logging.info("Logs sent successfully via email.")
