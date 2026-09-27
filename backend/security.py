"""Password hashing and session tokens.

Passwords are never stored. We store a salted, slow PBKDF2-SHA256 hash:

    new hashes:     pbkdf2_sha256$<iterations>$<salt>$<hex digest>
    seed database:  pbkdf2_sha256$<salt>$<hex digest>   (120,000 iterations)

Session tokens are random and only their SHA-256 hash is stored, so a copy of
the database can't be used to log in as anyone.
"""

import hashlib
import hmac
import secrets

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 600_000          # OWASP 2023+ recommendation for PBKDF2-SHA256
LEGACY_ITERATIONS = 120_000   # what the seed database's 3-part hashes use
SALT_BYTES = 16


def _pbkdf2(password: str, salt: str, iterations: int) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations).hex()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(SALT_BYTES)
    return f"{ALGORITHM}${ITERATIONS}${salt}${_pbkdf2(password, salt, ITERATIONS)}"


def _parse(stored: str) -> tuple[int, str, str] | None:
    parts = stored.split("$")
    if parts[0] != ALGORITHM:
        return None
    if len(parts) == 4 and parts[1].isdigit():
        return int(parts[1]), parts[2], parts[3]
    if len(parts) == 3:
        return LEGACY_ITERATIONS, parts[1], parts[2]
    return None


def verify_password(password: str, stored: str) -> bool:
    parsed = _parse(stored)
    if parsed is None:
        return False
    iterations, salt, expected = parsed
    # compare_digest takes the same time whether the first or last character
    # differs, so response timing leaks nothing about the hash.
    return hmac.compare_digest(_pbkdf2(password, salt, iterations), expected)


def needs_rehash(stored: str) -> bool:
    """True for hashes weaker than today's settings (e.g. the seed users)."""
    parsed = _parse(stored)
    return parsed is None or parsed[0] < ITERATIONS


# Used when an email isn't registered, so "no such user" takes as long as
# "wrong password" and attackers can't probe which emails have accounts.
DUMMY_HASH = hash_password(secrets.token_hex(16))


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
