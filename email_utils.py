# email_utils.py
import configparser
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

def send_email_with_attachment(subject, body, attachment_path=None):
    # Load email configuration from config file
    config = configparser.ConfigParser()
    config.read('email_config.ini')
    smtp_server = config['EMAIL']['smtp_server']
    smtp_port = int(config['EMAIL']['smtp_port'])
    sender_email = config['EMAIL']['sender_email']
    sender_password = config['EMAIL']['sender_password']
    recipient_email = config['EMAIL']['recipient_email']

    # Create the email content
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject

    # Attach the email body
    msg.attach(MIMEText(body, 'plain'))

    # Attach the file (if provided)
    if attachment_path:
        try:
            attachment = MIMEBase('application', 'octet-stream')
            with open(attachment_path, 'rb') as attachment_file:
                attachment.set_payload(attachment_file.read())
            encoders.encode_base64(attachment)
            attachment.add_header('Content-Disposition', f'attachment; filename={attachment_path.split("/")[-1]}')
            msg.attach(attachment)
        except Exception as e:
            print(f"Failed to attach file. Error: {e}")

    # Send the email
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()
    except Exception as e:
        print(f"Failed to send email. Error: {e}")
