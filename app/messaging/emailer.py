import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os



def send_email(subject: str, body: str):
    sender = os.getenv("EMAIL_SENDER")
    app_password = os.getenv("EMAIL_APP_PASSWORD")

    if not sender or not app_password:
        raise ValueError("Missing EMAIL_SENDER or EMAIL_APP_PASSWORD environment variables.")

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = "hassaan.vzpg@gmail.com"
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(sender, app_password)
        smtp.send_message(msg)
