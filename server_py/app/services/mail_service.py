import os
import smtplib
from email.message import EmailMessage
from html import escape

from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "1") == "1"
MAIL_FROM = os.getenv("MAIL_FROM", SMTP_USERNAME)
MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", "SeatSurfing")


def _smtp_send(msg: EmailMessage) -> None:
    if not SMTP_HOST:
        raise RuntimeError("SMTP_HOST non configurato")
    if not SMTP_USERNAME:
        raise RuntimeError("SMTP_USERNAME non configurato")
    if not SMTP_PASSWORD:
        raise RuntimeError("SMTP_PASSWORD non configurato")
    if not MAIL_FROM:
        raise RuntimeError("MAIL_FROM non configurato")

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
        if SMTP_USE_TLS:
            server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)


def build_booking_email_html(
    location_name: str,
    space_name: str,
    start_text: str,
    end_text: str,
    subject_text: str,
) -> str:
    return f"""
    <html>
      <body style="margin:0; padding:0; background:#f4f6f8; font-family:Arial, Helvetica, sans-serif;">
        <div style="max-width:620px; margin:24px auto; background:#ffffff; border-radius:18px; overflow:hidden; box-shadow:0 12px 32px rgba(0,0,0,0.12);">

          <div style="background:linear-gradient(135deg,#0d6efd,#3aa0ff); padding:28px 30px; color:#ffffff;">
            <h1 style="margin:0; font-size:26px; line-height:1.2;">Prenotazione confermata</h1>
            <p style="margin:8px 0 0; font-size:15px; opacity:0.92;">La tua postazione è stata registrata con successo.</p>
          </div>

          <div style="padding:28px 30px; color:#1f2937;">
            <p style="font-size:16px; margin:0 0 20px;">
              Ciao 👋<br>
              trovi qui sotto il riepilogo della tua prenotazione.
            </p>

            <div style="background:#f8fbff; border:1px solid #e2edff; border-radius:14px; padding:18px 20px;">
              <p style="margin:0 0 12px;"><strong>📍 Sede:</strong> {escape(location_name)}</p>
              <p style="margin:0 0 12px;"><strong>💺 Spazio:</strong> {escape(space_name)}</p>
              <p style="margin:0 0 12px;"><strong>🕒 Inizio:</strong> {escape(start_text)}</p>
              <p style="margin:0 0 12px;"><strong>🕕 Fine:</strong> {escape(end_text)}</p>
              <p style="margin:0;"><strong>📝 Oggetto:</strong> {escape(subject_text or "Prenotazione via SeatSurfing")}</p>
            </div>

            <p style="font-size:14px; color:#4b5563; margin:22px 0 0;">
              📅 In allegato trovi il file calendario <strong>.ics</strong> per aggiungere l’evento a Outlook o Google Calendar.
            </p>
          </div>

          <div style="padding:16px 30px; background:#f9fafb; color:#9ca3af; font-size:12px; text-align:center;">
            SeatSurfing • Smart Office Booking
          </div>

        </div>
      </body>
    </html>
    """


def send_email(to_email: str, subject: str, body: str, html_body: str | None = None) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{MAIL_FROM_NAME} <{MAIL_FROM}>"
    msg["To"] = to_email

    msg.set_content(body)

    if html_body:
        msg.add_alternative(html_body, subtype="html")

    _smtp_send(msg)


def send_calendar_invite(
    to_email: str,
    subject: str,
    body_text: str,
    ics_content: str,
    filename: str = "invite.ics",
    body_html: str | None = None,
) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{MAIL_FROM_NAME} <{MAIL_FROM}>"
    msg["To"] = to_email

    msg.set_content(body_text)

    if body_html:
        msg.add_alternative(body_html, subtype="html")

    msg.add_alternative(
        ics_content,
        subtype="calendar",
        params={"method": "REQUEST", "name": filename},
    )

    msg.add_attachment(
        ics_content.encode("utf-8"),
        maintype="text",
        subtype="calendar",
        filename=filename,
        params={"method": "REQUEST", "charset": "UTF-8"},
    )

    _smtp_send(msg)