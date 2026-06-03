"""
LeadFlow — utils/mailer.py
Minimal SMTP mailer using stdlib only (no extra dependencies).

Required environment variables (all optional — if absent, emails are skipped):
  MAIL_SERVER    SMTP hostname (default: smtp.gmail.com)
  MAIL_PORT      SMTP port     (default: 587)
  MAIL_USE_TLS   "true" | "false"  (default: true)
  MAIL_USERNAME  SMTP login / sender address
  MAIL_PASSWORD  SMTP password or app-password
  MAIL_FROM      From address override (defaults to MAIL_USERNAME)

For Gmail: create an App Password at myaccount.google.com/apppasswords and set
MAIL_USERNAME=youraddress@gmail.com  MAIL_PASSWORD=<16-char app password>
"""
from __future__ import annotations

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import parseaddr

logger = logging.getLogger(__name__)


def _is_configured() -> bool:
    return bool(os.environ.get("MAIL_USERNAME"))


def send_password_reset_email(to_email: str, reset_url: str, display_name: str) -> bool:
    """
    Send a password-reset email.
    Returns True on success, False if mail is not configured or send fails.
    Never raises — callers must not expose errors to end-users.
    """
    if not _is_configured():
        logger.info("Mail not configured — skipping reset email (to=%s)", to_email)
        return False

    mail_user  = os.environ.get("MAIL_USERNAME", "")
    mail_pass  = os.environ.get("MAIL_PASSWORD", "")
    from_addr  = os.environ.get("MAIL_FROM") or mail_user   # e.g. "LeadFlow <user@gmail.com>"
    server     = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    port       = int(os.environ.get("MAIL_PORT", "587"))
    use_tls    = os.environ.get("MAIL_USE_TLS", "true").strip().lower() == "true"

    # smtp.sendmail() needs a bare address for the envelope sender;
    # parseaddr handles both "user@example.com" and "Name <user@example.com>"
    _, envelope_from = parseaddr(from_addr)
    if not envelope_from:
        envelope_from = mail_user

    subject = "Reset your LeadFlow password"

    text_body = (
        f"Hi {display_name},\n\n"
        "We received a request to reset your LeadFlow password.\n\n"
        f"Click the link below to set a new password (expires in 1 hour):\n{reset_url}\n\n"
        "If you didn't request this, you can safely ignore this email — "
        "your password will not change.\n\n"
        "— The LeadFlow team"
    )

    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:40px 20px;font-family:'Segoe UI',Arial,sans-serif;
             background:#08090f;color:#edf0f7;">
  <div style="max-width:480px;margin:0 auto;">
    <h2 style="color:#4070f4;margin-bottom:8px;">Reset your password</h2>
    <p style="color:#9aa0b8;">Hi {display_name},</p>
    <p style="color:#9aa0b8;line-height:1.6;">
      We received a request to reset your LeadFlow password.
      Click the button below to set a new one. This link expires in <strong style="color:#edf0f7;">1 hour</strong>.
    </p>
    <a href="{reset_url}"
       style="display:inline-block;margin:20px 0;padding:12px 24px;background:#4070f4;
              color:#fff;border-radius:999px;text-decoration:none;font-weight:600;">
      Reset password
    </a>
    <p style="color:#555d78;font-size:13px;line-height:1.5;">
      If you didn't request a password reset, you can ignore this email —
      your password won't be changed.
    </p>
    <hr style="border:none;border-top:1px solid rgba(255,255,255,0.07);margin:28px 0;">
    <p style="color:#555d78;font-size:12px;">LeadFlow &mdash; Secure CRM</p>
  </div>
</body>
</html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = from_addr
    msg["To"]      = to_email
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html",  "utf-8"))

    try:
        with smtplib.SMTP(server, port, timeout=10) as smtp:
            smtp.ehlo()
            if use_tls:
                smtp.starttls()
                smtp.ehlo()
            smtp.login(mail_user, mail_pass)
            smtp.sendmail(envelope_from, [to_email], msg.as_string())
        logger.info("Reset email sent (to=%s)", to_email)
        return True
    except Exception:
        logger.exception("Failed to send reset email (to=%s)", to_email)
        return False
