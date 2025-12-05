import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os


def send_email(subject: str, body: str):
    """
    Send an email using Gmail SMTP.
    
    Args:
        subject: Email subject line
        body: Email body text
        
    Raises:
        ValueError: If required environment variables are missing
        smtplib.SMTPException: If email sending fails
        
    Environment variables required:
        EMAIL_SENDER: Gmail address to send from
        EMAIL_APP_PASSWORD: Gmail app-specific password
    """
    sender = os.getenv("EMAIL_SENDER")
    app_password = os.getenv("EMAIL_APP_PASSWORD")

    if not sender or not app_password:
        raise ValueError(
            "Missing EMAIL_SENDER or EMAIL_APP_PASSWORD environment variables. "
            "Please set these before running the script."
        )

    # Build email message
    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = "hassaan.vzpg@gmail.com"
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    # Send email
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(sender, app_password)
            smtp.send_message(msg)
            
    except smtplib.SMTPAuthenticationError as e:
        raise Exception(
            f"SMTP authentication failed. Check your EMAIL_SENDER and EMAIL_APP_PASSWORD. "
            f"Error: {str(e)}"
        )
    except smtplib.SMTPException as e:
        raise Exception(f"SMTP error occurred: {str(e)}")
    except Exception as e:
        raise Exception(f"Failed to send email: {str(e)}")