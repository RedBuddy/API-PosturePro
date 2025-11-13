import os, smtplib, ssl
from email.message import EmailMessage

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")  # solo ENV
SMTP_PASS = os.getenv("SMTP_PASS")  # solo ENV
FRONTEND_URL = os.getenv("FRONTEND_URL")  # opcional

def build_reset_link(reset_token: str) -> str:
    try:
        from flask import request
        base = FRONTEND_URL or (request.headers.get('Origin') or request.host_url.rstrip('/'))
    except Exception:
        base = FRONTEND_URL or "http://localhost:5173"
    return f"{base}/reset-password?token={reset_token}"

def send_reset_email(to_email: str, reset_token: str):
    link = build_reset_link(reset_token)

    # Si no hay credenciales, solo loguea el enlace (dev)
    if not (SMTP_USER and SMTP_PASS):
        print(f"[MAIL][DEBUG] Reset link: {link} (configura SMTP_USER/SMTP_PASS)")
        return

    msg = EmailMessage()
    msg["Subject"] = "Recuperación de contraseña"
    msg["From"] = SMTP_USER
    msg["To"] = to_email
    msg.set_content(f"""
Hola,

Recibimos una solicitud para restablecer tu contraseña.
Enlace: {link}

Si no solicitaste esto, ignora el correo.
""".strip())

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as s:
            s.starttls(context=context)
            s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)
    except Exception as e:
        print(f"[MAIL][ERROR] {e}")