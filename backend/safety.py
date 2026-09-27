"""Code-level safety helpers: remove sensitive data before it goes anywhere.

scrub_message() runs on every shopper message before the agent, the chat
history table or the audit trail sees it. scrub_for_log() also hides contact
details, for the audit trail only.
"""

import re

# 13-19 digits, optionally split by spaces or dashes: payment card numbers.
CARD = re.compile(r"\b(?:\d[ -]?){12,18}\d\b")
SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
# "my password is hunter2", "password: hunter2", "pw = hunter2"
PASSWORD = re.compile(r"\b(pass(?:word|code)?|pwd|pw)\b(\s*(?:is|:|=)\s*)(\S+)", re.I)
EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
PHONE = re.compile(r"(?<!\d)(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]?\d{3}[ .-]?\d{4}(?!\d)")

# The store's own contact details are public and appear in replies.
STORE_CONTACTS = {"orderdept@campuscustoms.com", "(475) 301-4205", "475-301-4205"}


def _luhn_ok(digits: str) -> bool:
    total, alt = 0, False
    for ch in reversed(digits):
        n = int(ch)
        if alt:
            n = n * 2 - 9 if n > 4 else n * 2
        total += n
        alt = not alt
    return total % 10 == 0


def _card(match: re.Match) -> str:
    digits = re.sub(r"\D", "", match.group())
    return "[card number removed]" if 13 <= len(digits) <= 19 and _luhn_ok(digits) else match.group()


def scrub_message(text: str) -> tuple[str, list[str]]:
    """Remove card numbers, SSNs and typed passwords. Returns (clean text, what was removed)."""
    removed = []
    cleaned = CARD.sub(_card, text)
    if cleaned != text:
        removed.append("card number")
    before = cleaned
    cleaned = SSN.sub("[SSN removed]", cleaned)
    if cleaned != before:
        removed.append("SSN")
    before = cleaned
    cleaned = PASSWORD.sub(lambda m: f"{m.group(1)}{m.group(2)}[password removed]", cleaned)
    if cleaned != before:
        removed.append("password")
    return cleaned, removed


def scrub_for_log(text: str) -> str:
    """scrub_message() plus shoppers' emails and phone numbers, for the audit trail."""
    cleaned, _ = scrub_message(text)
    cleaned = EMAIL.sub(lambda m: m.group() if m.group().lower() in STORE_CONTACTS else "[email]", cleaned)
    return PHONE.sub(lambda m: m.group() if m.group() in STORE_CONTACTS else "[phone]", cleaned)
