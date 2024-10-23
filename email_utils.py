# email_utils.py
import configparser
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# Email configuration
def send_email_with_attachment(subject, body, debug_log_path, info_log_path):
    # Load email configuration from config file (can be from INI, JSON, or YAML)
    config = configparser.ConfigParser()
    config.read('email_config.ini')

    # Email setup
    smtp_server = config['email']['smtp_server']
    smtp_port = int(config['email']['smtp_port'])
    sender_email = config['email']['sender_email']
    sender_password = config['email']['sender_password']

    # Get the recipients as a list
    try:
        recipients = [email.strip() for email in config.get('email', 'recipients').split(',')]
    except configparser.NoSectionError:
        logging.error("Error: Section [email] not found in the configuration file.")

    # Create the email
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = ", ".join(recipients)  # Comma-separated string of recipients
    msg['Subject'] = subject

    # Email body
    msg.attach(MIMEText(body, 'plain'))

    # Attach the DEBUG log file
    with open(debug_log_path, "rb") as attachment:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(debug_log_path)}')
    msg.attach(part)

    # Attach the INFO log file
    with open(info_log_path, "rb") as attachment:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(info_log_path)}')
    msg.attach(part)

    # Send the email
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Upgrade the connection to secure
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipients, msg.as_string())
        server.quit()
        logger = logging.getLogger()  # Get the logger instance
        logger.info("Logs sent successfully via email.")

    except Exception as e:
        logger = logging.getLogger()  # Get the logger instance
        logger.error(f"Failed to send email. Error: {e}")
