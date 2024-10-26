# email_utils.py
import configparser
import logging
import os
import re
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Generate a customized email body
def generate_email_body(log_filepath_info):
    # Read the content of the INFO log file to use as email body
    email_body_lines = []
    with open(log_filepath_info, 'r', encoding='utf-8') as log_file:
        for line in log_file:
            # Optionally filter or modify lines
            # Keep all logs of WARNING or higher levels
            if "- WARNING -" in line or "- ERROR -" in line or "- CRITICAL -" in line:
                email_body_lines.append(line)
            # Simplify the customized AutoDigiSign messages
            elif "- INFO -" in line and "AutoDigiSign" in line:
                # Regular expression to extract "AutoDigiSign" lines
                pattern = r"AutoDigiSign (.*)"
                match = re.search(pattern, line)
                if match:
                    email_body_lines.append(f"{match.group(0)}\n")
            # Simplify the messages containing Employee ID
            elif "- INFO -" in line and "Employee ID" in line:
                # Regular expression to extract employee ID and message
                pattern = r"Employee ID: (\d+), Web message: (.*)"
                match = re.search(pattern, line)
                if match:
                    employee_id = match.group(1).strip()
                    message = match.group(2).strip()

                    # Remove '[CrossBrowser]' from the message if it exists
                    message = re.sub(r"\[CrossBrowser\]\s*", "", message)

                    email_body_lines.append(f"{employee_id}: {message}\n")
            # Ignore other INFO level logs
            elif "- INFO -" in line:
                continue
            # Keep other logs in case
            else:
                email_body_lines.append(line)

    # Add custom headers or modify content as needed
    email_body = "AutoDigiSign Log Summary:\n\n"  # Add a header
    email_body += "".join(email_body_lines)
    email_body += "\nNote: This is an automated log summary. Please check the log file for complete details."  # Add a note
    
    return email_body

# Send a email with attachment
def send_email_with_attachment(subject, body, log_filepath_info, log_filepath_debug, log_filepath_console):
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

    # Attach the INFO log file
    with open(log_filepath_info, "rb") as attachment:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(log_filepath_info)}')
    msg.attach(part)

    # Attach the DEBUG log file
    with open(log_filepath_debug, "rb") as attachment:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(log_filepath_debug)}')
    msg.attach(part)

    # Attach the Console log file
    with open(log_filepath_console, "rb") as attachment:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(log_filepath_console)}')
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
