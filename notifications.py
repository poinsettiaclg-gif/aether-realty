"""
Notification system for qualified leads.
Supports SendGrid (recommended) with SMTP fallback.
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# ─── Configuration ────────────────────────────────────────────────────────────
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")

REALTOR_EMAIL = os.environ.get("REALTOR_EMAIL", "")
REALTOR_NAME = os.environ.get("REALTOR_NAME", "Realtor")
FROM_EMAIL = os.environ.get("FROM_EMAIL", "leads@aether-realty.com")


def send_qualified_lead_notification(lead_data: dict, transcript: str) -> bool:
    """
    Send an email notification when a lead is fully qualified.
    Returns True if sent successfully.
    """
    if not REALTOR_EMAIL:
        print("⚠️  No REALTOR_EMAIL set — skipping notification.")
        return False

    intent = lead_data.get("intent", "unknown")
    timeline = lead_data.get("timeline", "unknown")
    budget = lead_data.get("budget", "unknown")
    contact = lead_data.get("contact", "unknown")
    session_id = lead_data.get("session_id", "unknown")

    subject = f"🔥 New Qualified Lead — {intent.title()}, {budget}, {timeline}"

    html_body = f"""
    <div style="font-family: 'Inter', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #0a0a0c; color: #ffffff; padding: 30px; border-radius: 16px;">
        <h1 style="color: #648cff; margin-bottom: 5px;">New Qualified Lead</h1>
        <p style="color: #a0a0b0; margin-top: 0;">Captured by your AETHER AI Agent • {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>

        <div style="background: #121216; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 20px; margin: 20px 0;">
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="color: #a0a0b0; padding: 8px 0; font-size: 12px; text-transform: uppercase; letter-spacing: 1px;">Intent</td>
                    <td style="color: #ffffff; padding: 8px 0; font-weight: 600;">{intent.title()}</td>
                </tr>
                <tr>
                    <td style="color: #a0a0b0; padding: 8px 0; font-size: 12px; text-transform: uppercase; letter-spacing: 1px;">Timeline</td>
                    <td style="color: #ffffff; padding: 8px 0; font-weight: 600;">{timeline}</td>
                </tr>
                <tr>
                    <td style="color: #a0a0b0; padding: 8px 0; font-size: 12px; text-transform: uppercase; letter-spacing: 1px;">Budget</td>
                    <td style="color: #ffffff; padding: 8px 0; font-weight: 600;">{budget}</td>
                </tr>
                <tr>
                    <td style="color: #a0a0b0; padding: 8px 0; font-size: 12px; text-transform: uppercase; letter-spacing: 1px;">Contact</td>
                    <td style="color: #648cff; padding: 8px 0; font-weight: 600;">{contact}</td>
                </tr>
            </table>
        </div>

        <div style="background: #121216; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 20px; margin: 20px 0;">
            <h3 style="color: #a0a0b0; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; margin-top: 0;">Conversation Transcript</h3>
            <pre style="color: #d0d0d0; font-size: 13px; line-height: 1.6; white-space: pre-wrap; word-wrap: break-word;">{transcript}</pre>
        </div>

        <p style="color: #a0a0b0; font-size: 12px; text-align: center; margin-top: 30px;">
            Powered by AETHER Logic Engine • <a href="https://aether-realty.com" style="color: #648cff;">aether-realty.com</a>
        </p>
    </div>
    """

    plain_body = f"""
NEW QUALIFIED LEAD — {datetime.now().strftime('%B %d, %Y at %I:%M %p')}

Intent: {intent.title()}
Timeline: {timeline}
Budget: {budget}
Contact: {contact}

--- CONVERSATION TRANSCRIPT ---
{transcript}

Powered by AETHER Logic Engine
"""

    # Try SendGrid first, then SMTP fallback
    if SENDGRID_API_KEY:
        return _send_via_sendgrid(subject, html_body, plain_body)
    elif SMTP_HOST:
        return _send_via_smtp(subject, html_body, plain_body)
    else:
        print("⚠️  No email service configured (set SENDGRID_API_KEY or SMTP_HOST).")
        print(f"📋 QUALIFIED LEAD (logged to console):\n{plain_body}")
        return False


def _send_via_sendgrid(subject: str, html_body: str, plain_body: str) -> bool:
    """Send email using SendGrid API."""
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail, Email, To, Content

        message = Mail(
            from_email=Email(FROM_EMAIL, "AETHER Realty Agent"),
            to_emails=To(REALTOR_EMAIL, REALTOR_NAME),
            subject=subject,
        )
        message.add_content(Content("text/plain", plain_body))
        message.add_content(Content("text/html", html_body))

        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)

        if response.status_code in (200, 201, 202):
            print(f"✅ Lead notification sent to {REALTOR_EMAIL} via SendGrid")
            return True
        else:
            print(f"⚠️  SendGrid returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"⚠️  SendGrid error: {e}")
        return False


def _send_via_smtp(subject: str, html_body: str, plain_body: str) -> bool:
    """Send email using SMTP (Gmail, Outlook, etc.)."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = FROM_EMAIL
        msg["To"] = REALTOR_EMAIL

        msg.attach(MIMEText(plain_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)

        print(f"✅ Lead notification sent to {REALTOR_EMAIL} via SMTP")
        return True
    except Exception as e:
        print(f"⚠️  SMTP error: {e}")
        return False
