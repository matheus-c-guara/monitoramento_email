import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

# Configurações de email
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL = os.getenv("EMAIL")
EMAIL_TO = os.getenv("EMAIL_TO")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

def send_email(subject, message):
    msg = MIMEMultipart()
    msg["From"] = EMAIL
    msg["To"] = EMAIL
    msg["Subject"] = subject

    msg.attach(MIMEText(message, "plain"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL, EMAIL_PASSWORD)
            server.send_message(msg)
            print(f"E-mail enviado com sucesso: {subject}")
    except Exception as e:
        print("Erro ao enviar e-mail:", e)

subject = "Alerta: CPQ acima do limite no Meta Ads"
message = f"Os anúncios: tiveram uma performance abaixo do esperado, mostrando um CPQ > R$100."
send_email(subject, message)
