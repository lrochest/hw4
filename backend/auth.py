"""Account routes: sign up, log in, log out, and "who am I".

Sessions live in an HttpOnly cookie, so page JavaScript (or an injected
script) can't read the token.
"""

import os
import re
import sqlite3
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, field_validator

import security
from db import connect

router = APIRouter(prefix="/api/auth", tags=["auth"])

COOKIE_NAME = "cc_session"
SESSION_DAYS = 7
# Set COOKIE_SECURE=1 when serving over HTTPS so the cookie is never sent in plain text.
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "0") == "1"

MIN_PASSWORD = 8
MAX_PASSWORD = 128  # caps hashing cost so huge inputs can't be used to slow the server
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Brute-force guard: at most MAX_FAILURES wrong logins per email + IP per window.
MAX_FAILURES = 5
FAILURE_WINDOW_SECONDS = 15 * 60
_failures: dict[str, deque[float]] = defaultdict(deque)


# --- Request / response models --------------------------------------------

def _clean_email(value: str) -> str:
    value = value.strip().lower()
    if not EMAIL_RE.match(value) or len(value) > 254:
        raise ValueError("Enter a valid email address.")
    return value


class SignupRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=60)
    last_name: str = Field(min_length=1, max_length=60)
    email: str
    password: str = Field(min_length=MIN_PASSWORD, max_length=MAX_PASSWORD)

    @field_validator("first_name", "last_name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("is required")
        return v

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        return _clean_email(v)


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=MAX_PASSWORD)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class User(BaseModel):
    """What the frontend is allowed to see. Never includes password_hash."""

    id: int
    first_name: str
    last_name: str
    email: str


def _to_user(row: sqlite3.Row) -> User:
    # Seed users may lack first/last name columns; fall back to splitting name.
    first, _, last = (row["name"] or "").partition(" ")
    return User(
        id=row["id"],
        first_name=row["first_name"] or first,
        last_name=row["last_name"] or last,
        email=row["email"],
    )


# --- Sessions ---------------------------------------------------------------

def _start_session(conn: sqlite3.Connection, response: Response, user_id: int) -> None:
    token = security.new_session_token()
    expires = datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)
    conn.execute(
        "INSERT INTO sessions (user_id, token_hash, expires_at) VALUES (?, ?, ?)",
        (user_id, security.hash_token(token), expires.strftime("%Y-%m-%d %H:%M:%S")),
    )
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=SESSION_DAYS * 24 * 3600,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/",
    )


def user_from_token(token: str | None) -> User | None:
    """Look up the logged-in user for a session cookie. Used by other routes too."""
    if not token:
        return None
    with connect() as conn:
        row = conn.execute(
            """
            SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = ? AND s.expires_at > datetime('now')
            """,
            (security.hash_token(token),),
        ).fetchone()
    return _to_user(row) if row else None


# --- Brute-force guard ------------------------------------------------------

def _limit_key(request: Request, email: str) -> str:
    ip = request.client.host if request.client else "unknown"
    return f"{ip}|{email}"


def _recent_failures(key: str) -> deque[float]:
    attempts = _failures[key]
    cutoff = time.monotonic() - FAILURE_WINDOW_SECONDS
    while attempts and attempts[0] < cutoff:
        attempts.popleft()
    return attempts


# --- Routes -----------------------------------------------------------------

@router.post("/signup", response_model=User, status_code=status.HTTP_201_CREATED)
def signup(body: SignupRequest, response: Response) -> User:
    password_hash = security.hash_password(body.password)
    with connect() as conn:
        try:
            cur = conn.execute(
                """
                INSERT INTO users (name, email, password_hash, first_name, last_name)
                VALUES (?, ?, ?, ?, ?)
                """,
                (f"{body.first_name} {body.last_name}", body.email, password_hash,
                 body.first_name, body.last_name),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(status.HTTP_409_CONFLICT, "An account with that email already exists.")
        _start_session(conn, response, cur.lastrowid)
        row = conn.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _to_user(row)


@router.post("/login", response_model=User)
def login(body: LoginRequest, request: Request, response: Response) -> User:
    key = _limit_key(request, body.email)
    if len(_recent_failures(key)) >= MAX_FAILURES:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Too many failed attempts. Please wait a few minutes and try again.",
        )

    with connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE lower(email) = ?", (body.email,)).fetchone()
        # Always run a hash check, even for unknown emails, so both cases take the same time.
        ok = security.verify_password(body.password, row["password_hash"] if row else security.DUMMY_HASH)
        if not row or not ok:
            _failures[key].append(time.monotonic())
            # Same message either way: don't reveal whether the email is registered.
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password.")

        _failures.pop(key, None)
        if security.needs_rehash(row["password_hash"]):
            # Upgrade older, weaker hashes (the seed users) now that we know the password.
            conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (security.hash_password(body.password), row["id"]),
            )
        _start_session(conn, response, row["id"])
    return _to_user(row)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, cc_session: str | None = Cookie(default=None)) -> None:
    if cc_session:
        with connect() as conn:
            conn.execute("DELETE FROM sessions WHERE token_hash = ?", (security.hash_token(cc_session),))
    response.delete_cookie(COOKIE_NAME, path="/")


@router.get("/me", response_model=User)
def me(cc_session: str | None = Cookie(default=None)) -> User:
    user = user_from_token(cc_session)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not logged in.")
    return user
