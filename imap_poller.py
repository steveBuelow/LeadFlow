import imaplib
import logging
import os
import re
import threading
import time
from email import message_from_bytes
from email.policy import default as default_policy
from email.utils import parseaddr
from html import unescape

from models import create_lead

logger = logging.getLogger(__name__)


def _env_int(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        raise ValueError(f"{name} must be an integer (got {raw!r})")


def _env_bool(name: str, default: bool = False) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "y", "on"}

def _env_first(names: list[str], default: str = "") -> str:
    for name in names:
        val = (os.getenv(name) or "").strip()
        if val:
            return val
    return default


def _env_int_first(names: list[str], default: int) -> int:
    raw = _env_first(names, default="")
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        raise ValueError(f"{names[0]} must be an integer (got {raw!r})")


def _strip_html(html: str) -> str:
    # Minimal, stdlib-only "good enough" HTML -> text.
    # (Avoids external dependencies for a student project.)
    html = re.sub(r"(?is)<(script|style).*?>.*?</\1>", "", html)
    html = re.sub(r"(?is)<br\s*/?>", "\n", html)
    html = re.sub(r"(?is)</p\s*>", "\n\n", html)
    html = re.sub(r"(?is)<[^>]+>", "", html)
    html = unescape(html)
    # Collapse excessive whitespace.
    html = re.sub(r"[ \t\r]+", " ", html)
    html = re.sub(r"\n{3,}", "\n\n", html)
    return html.strip()


def _get_text_body(msg) -> str:
    if msg.is_multipart():
        text_plain = None
        text_html = None
        for part in msg.walk():
            if part.get_content_maintype() == "multipart":
                continue
            if part.get_content_disposition() == "attachment":
                continue
            ctype = part.get_content_type()
            if ctype not in {"text/plain", "text/html"}:
                continue

            try:
                content = (part.get_content() or "").strip()
            except Exception:
                payload = part.get_payload(decode=True)
                if payload is None:
                    payload = (part.get_payload() or "").encode("utf-8", errors="replace")
                charset = part.get_content_charset() or "utf-8"
                content = bytes(payload).decode(charset, errors="replace").strip()

            if ctype == "text/plain" and not text_plain:
                text_plain = content
            elif ctype == "text/html" and not text_html:
                text_html = content

        if text_plain:
            return text_plain
        if text_html:
            return _strip_html(text_html)
        return ""
    try:
        return (msg.get_content() or "").strip()
    except Exception:
        payload = msg.get_payload(decode=True)
        if payload is None:
            # Some messages are not encoded; get_payload() returns a str.
            return str(msg.get_payload() or "").strip()
        charset = msg.get_content_charset() or "utf-8"
        return bytes(payload).decode(charset, errors="replace").strip()


def _process_rfc822(rfc822_bytes: bytes, inbound_user_id: int) -> int | None:
    msg = message_from_bytes(rfc822_bytes, policy=default_policy)
    sender_name, sender_email = parseaddr(str(msg.get("From", "") or ""))
    sender_name = (sender_name or sender_email or "").strip()
    subject = str(msg.get("Subject", "") or "").strip()
    body = _get_text_body(msg)

    if not sender_name:
        logger.warning("Skipping email: could not parse sender")
        return None

    message = body
    if subject and body:
        message = f"Subject: {subject}\n\n{body}"
    elif subject:
        message = f"Subject: {subject}"

    if len(message) > 10_000:
        message = message[:10_000] + "\n\n[trimmed]"

    new_id = create_lead(
        name=sender_name,
        source=os.getenv("EMAIL_POLL_SOURCE", "Email"),
        message=message,
        status=os.getenv("EMAIL_POLL_STATUS", "New"),
        notes=f"Inbound email from {sender_email}".strip(),
        user_id=inbound_user_id,
    )
    return new_id


def poll_gmail_forever(stop_event: threading.Event) -> None:
    """
    Poll Gmail over IMAP for unseen messages and create leads.

    Required env vars:
    
    """
    enabled = _env_bool("ENABLE_EMAIL_POLLER", default=False)
    if not enabled:
        logger.info("Email poller disabled (set ENABLE_EMAIL_POLLER=1 to enable).")
        return

    # Support two naming conventions:
    # - "GMAIL_IMAP_*" / "EMAIL_POLL_*" (this repo's .env.example)
    # - "EMAIL_USER/EMAIL_PASS/IMAP_*" / "INBOUND_USER_ID" (common student snippets)
    user = _env_first(["GMAIL_IMAP_USER", "EMAIL_USER"], default="")
    password = _env_first(["GMAIL_IMAP_APP_PASSWORD", "EMAIL_PASS"], default="")
    mailbox = _env_first(["EMAIL_POLL_MAILBOX", "IMAP_MAILBOX"], default="INBOX") or "INBOX"
    interval = _env_int_first(["EMAIL_POLL_INTERVAL_SECONDS", "POLL_INTERVAL"], 60)
    inbound_user_id = _env_int_first(["EMAIL_POLL_USER_ID", "INBOUND_USER_ID"], 0)

    if not user or not password or not inbound_user_id:
        logger.warning(
            "Email poller not configured. Need user+password and an integer user id.\n"
            "Set either:\n"
            "  GMAIL_IMAP_USER + GMAIL_IMAP_APP_PASSWORD + EMAIL_POLL_USER_ID\n"
            "or:\n"
            "  EMAIL_USER + EMAIL_PASS + INBOUND_USER_ID"
        )
        return

    host = _env_first(["EMAIL_POLL_IMAP_HOST", "IMAP_HOST"], default="imap.gmail.com").strip()
    port = _env_int_first(["EMAIL_POLL_IMAP_PORT", "IMAP_PORT"], 993)

    # Common typo: "imap.google.com" is not Gmail IMAP.
    if host.lower() == "imap.gmail.com":
        logger.warning("IMAP_HOST=imap.google.com is likely wrong for Gmail. Try imap.gmail.com.")

    logger.info("Email poller starting (host=%s port=%s mailbox=%s interval=%ss)", host, port, mailbox, interval)

    while not stop_event.is_set():
        imap = None
        try:
            imap = imaplib.IMAP4_SSL(host, port)
            imap.login(user, password)
            imap.select(mailbox)

            status, data = imap.search(None, "UNSEEN")
            if status != "OK":
                raise RuntimeError(f"IMAP search failed: {status}")

            msg_ids = [x for x in (data[0] or b"").split() if x]
            for msg_id in msg_ids:
                if stop_event.is_set():
                    break
                fetch_status, parts = imap.fetch(msg_id, "(RFC822)")
                if fetch_status != "OK" or not parts:
                    logger.warning("IMAP fetch failed for msg_id=%r status=%s", msg_id, fetch_status)
                    continue

                rfc822 = None
                for item in parts:
                    if isinstance(item, tuple) and item and isinstance(item[1], (bytes, bytearray)):
                        rfc822 = bytes(item[1])
                        break
                if not rfc822:
                    logger.warning("IMAP fetch returned no RFC822 bytes for msg_id=%r", msg_id)
                    continue

                try:
                    lead_id = _process_rfc822(rfc822, inbound_user_id)
                except Exception:
                    logger.exception("Failed to process msg_id=%r (leaving it unseen for retry)", msg_id)
                    continue

                # Mark as seen only after successful processing.
                imap.store(msg_id, "+FLAGS", "\\Seen")
                if lead_id:
                    logger.info("Email -> lead #%s (msg_id=%s)", lead_id, msg_id.decode(errors="ignore"))

        except Exception:
            logger.exception("Email poller loop error (will retry)")
        finally:
            try:
                if imap is not None:
                    imap.logout()
            except Exception:
                pass

        stop_event.wait(interval)


def start_email_poller_thread() -> threading.Event | None:
    """
    Start a background daemon thread. Returns the stop_event, or None if not started.
    """
    enabled = _env_bool("ENABLE_EMAIL_POLLER", default=False)
    if not enabled:
        return None

    # In debug, Werkzeug reloader starts the app twice; avoid double pollers.
    if os.getenv("FLASK_ENV") != "production" and os.getenv("WERKZEUG_RUN_MAIN") != "true":
        return None

    stop_event = threading.Event()
    t = threading.Thread(
        target=poll_gmail_forever,
        args=(stop_event,),
        name="email-poller",
        daemon=True,
    )
    t.start()
    return stop_event
