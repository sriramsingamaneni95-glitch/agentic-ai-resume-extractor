
import os
import re
import secrets

EMAIL_RE = re.compile(r"[\w\.\+\-]+@[\w\-]+(\.[\w\-]+)*\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}")


def mask_pii(text: str) -> str:
   
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
   
    filename = os.path.basename(filename)
    filename = filename.replace("..", "")
    return filename or f"upload_{secrets.token_hex(4)}"


def secure_delete(path: str) -> None:
   
    if not path or not os.path.exists(path):
        return
    try:
        length = os.path.getsize(path)
        with open(path, "r+b") as f:
            f.write(secrets.token_bytes(length))
        os.remove(path)
    except OSError:
      
        pass
