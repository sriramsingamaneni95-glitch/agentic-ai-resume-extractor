"""
PII protection + secure file handling.

- mask_pii(): redacts emails/phone numbers before they ever hit a log line
- secure_delete(): overwrites and removes an uploaded file after processing
- sanitize_filename(): prevents path traversal on user-supplied filenames
"""
import os
import re
import secrets

EMAIL_RE = re.compile(r"[\w\.\+\-]+@[\w\-]+(\.[\w\-]+)*\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}")


def mask_pii(text: str) -> str:
    """Redact emails and phone-number-shaped strings before logging."""
    if not text:
        return text
    text = EMAIL_RE.sub(lambda m: _mask_email(m.group(0)), text)
    text = PHONE_RE.sub("[REDACTED_PHONE]", text)
    return text


def _mask_email(email: str) -> str:
    try:
        user, domain = email.split("@", 1)
    except ValueError:
        return "[REDACTED_EMAIL]"
    visible = user[:2] if len(user) > 2 else user[:1]
    return f"{visible}***@{domain}"


def sanitize_filename(filename: str) -> str:
    """Strip path components / traversal sequences from a user-supplied filename."""
    filename = os.path.basename(filename)
    filename = filename.replace("..", "")
    return filename or f"upload_{secrets.token_hex(4)}"


def secure_delete(path: str) -> None:
    """
    Best-effort secure delete: overwrite the file's bytes before unlinking,
    so a resume containing PII doesn't linger recoverable on disk after
    processing. Not a substitute for full-disk encryption, but reduces the
    window an uploaded resume's raw bytes are sitting around.
    """
    if not path or not os.path.exists(path):
        return
    try:
        length = os.path.getsize(path)
        with open(path, "r+b") as f:
            f.write(secrets.token_bytes(length))
        os.remove(path)
    except OSError:
        # Fail soft - never let cleanup crash the main pipeline
        pass
