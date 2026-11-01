"""Process-local owner sessions, independent of durable financial state."""

from dataclasses import dataclass
import math
import secrets
import threading
import time

from .gateway import Principal
from .ledger import Rejection


SESSION_SECONDS = 30 * 60
COOKIE_NAME = "goalguard_owner_session"


@dataclass(frozen=True)
class OwnerSession:
    identifier: str
    csrf_token: str
    principal: Principal
    expires_at: float


class OwnerSessions:
    def __init__(self):
        self._sessions: dict[str, OwnerSession] = {}
        self._lock = threading.Lock()

    def create(self, principal: Principal) -> OwnerSession:
        if principal.role != "owner":
            raise Rejection("forbidden", "Only an owner can unlock a browser session.")
        with self._lock:
            now = time.monotonic()
            self._sessions = {key: session for key, session in self._sessions.items()
                              if session.expires_at > now}
            session = OwnerSession(secrets.token_urlsafe(32), secrets.token_urlsafe(32),
                                   principal, now + SESSION_SECONDS)
            self._sessions[session.identifier] = session
            return session

    def get(self, identifier: str) -> OwnerSession:
        with self._lock:
            session = self._sessions.get(identifier)
            if session is None or session.expires_at <= time.monotonic():
                self._sessions.pop(identifier, None)
                raise Rejection("unauthorized", "Unlock the owner interface again.")
            return session

    def revoke(self, identifier: str) -> None:
        with self._lock:
            self._sessions.pop(identifier, None)

    @staticmethod
    def describe(session: OwnerSession) -> dict:
        return {"csrf_token": session.csrf_token,
                "expires_in_seconds": max(0, math.ceil(session.expires_at - time.monotonic()))}

    @staticmethod
    def check_csrf(session: OwnerSession, provided: str) -> None:
        if not secrets.compare_digest(session.csrf_token.encode(), provided.encode()):
            raise Rejection("forbidden", "A session-bound CSRF token is required.")


def session_cookie(identifier: str, *, clear=False) -> str:
    lifetime = 0 if clear else SESSION_SECONDS
    return f"{COOKIE_NAME}={identifier}; HttpOnly; Max-Age={lifetime}; Path=/; SameSite=Strict"
