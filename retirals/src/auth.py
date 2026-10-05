"""Single-user, server-side session authentication for the retirement planner."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from dataclasses import dataclass
from threading import Lock

from fastapi import HTTPException, Request

SESSION_COOKIE = "retirement_session"
SESSION_TTL_SECONDS = 8 * 60 * 60
LOCKOUT_WINDOW_SECONDS = 15 * 60
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_SECONDS = 10 * 60


@dataclass
class Session:
    username: str
    expires_at: float


_sessions: dict[str, Session] = {}
_failures: dict[str, tuple[int, float]] = {}
_lock = Lock()


def _configured_credentials() -> tuple[str, str]:
    return os.getenv("APP_USERNAME", "").strip(), os.getenv("APP_PASSWORD", "")


def _cleanup(now: float) -> None:
    expired = [sid for sid, session in _sessions.items() if session.expires_at <= now]
    for sid in expired:
        _sessions.pop(sid, None)

    stale = [ip for ip, (_, timestamp) in _failures.items() if now - timestamp > LOCKOUT_WINDOW_SECONDS]
    for ip in stale:
        _failures.pop(ip, None)


def _client_ip(request: Request) -> str:
    return request.headers.get("cf-connecting-ip") or (request.client.host if request.client else "unknown")


def _same_origin(request: Request) -> bool:
    origin = request.headers.get("origin")
    if origin:
        expected = f"{request.url.scheme}://{request.headers.get('host', request.url.netloc)}"
        if origin != expected:
            forwarded_proto = request.headers.get("x-forwarded-proto", "").split(",")[0].strip()
            if forwarded_proto:
                expected = f"{forwarded_proto}://{request.headers.get('host', request.url.netloc)}"
        return origin == expected

    referer = request.headers.get("referer")
    if referer:
        return referer.startswith(f"{request.url.scheme}://{request.headers.get('host', request.url.netloc)}/")

    return False


def require_same_origin(request: Request) -> None:
    if not _same_origin(request):
        raise HTTPException(status_code=403, detail="Cross-origin request blocked")


def authenticate(username: str, password: str, request: Request) -> str:
    configured_username, configured_password = _configured_credentials()
    client_ip = _client_ip(request)
    now = time.time()

    with _lock:
        _cleanup(now)
        failures, last_failure = _failures.get(client_ip, (0, 0.0))
        if failures >= MAX_FAILED_ATTEMPTS and now - last_failure < LOCKOUT_SECONDS:
            raise HTTPException(status_code=429, detail="Too many login attempts. Please try again later.")

        valid = bool(configured_username and configured_password)
        valid &= hmac.compare_digest(username, configured_username)
        valid &= hmac.compare_digest(password, configured_password)

        if not valid:
            _failures[client_ip] = (failures + 1, now)
            raise HTTPException(status_code=401, detail="Invalid username or password")

        _failures.pop(client_ip, None)
        session_id = secrets.token_urlsafe(32)
        _sessions[session_id] = Session(username=configured_username, expires_at=now + SESSION_TTL_SECONDS)
        return session_id


def _session_id(request: Request) -> str | None:
    return request.cookies.get(SESSION_COOKIE)


def get_session(request: Request) -> Session | None:
    session_id = _session_id(request)
    if not session_id:
        return None

    now = time.time()
    with _lock:
        _cleanup(now)
        session = _sessions.get(session_id)
        if not session or session.expires_at <= now:
            _sessions.pop(session_id, None)
            return None
        return session


def require_auth(request: Request) -> Session:
    session = get_session(request)
    if not session:
        raise HTTPException(status_code=401, detail="Authentication required")
    return session


def logout(request: Request) -> None:
    session_id = _session_id(request)
    if session_id:
        with _lock:
            _sessions.pop(session_id, None)


def cookie_secure(request: Request) -> bool:
    forwarded_proto = request.headers.get("x-forwarded-proto", "").split(",")[0].strip().lower()
    return request.url.scheme == "https" or forwarded_proto == "https"


def set_session_cookie(response, request: Request, session_id: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=session_id,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=cookie_secure(request),
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")
