"""Who is calling? Identity always comes from the validated token, never from the client body."""
import re
import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User

bearer = HTTPBearer(auto_error=False)
_SESSION_ID = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


def _unauthorized(message: str = "Not authenticated.") -> HTTPException:
    return HTTPException(status_code=401, detail=message,
                         headers={"WWW-Authenticate": "Bearer"})


def get_optional_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User | None:
    """No token -> None. A bad or expired token -> 401 (never silently anonymous)."""
    if creds is None:
        return None
    try:
        data = decode_access_token(creds.credentials)
        user_id = uuid.UUID(data["sub"])
    except (jwt.PyJWTError, ValueError, KeyError):
        raise _unauthorized("Invalid or expired token.")
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _unauthorized("Invalid or expired token.")
    return user


def get_current_user(user: User | None = Depends(get_optional_user)) -> User:
    if user is None:
        raise _unauthorized()
    return user


def require_roles(*roles: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="You do not have permission to do this.")
        return user
    return checker


@dataclass
class Actor:
    user: User | None
    session_id: str | None


def get_actor(
    user: User | None = Depends(get_optional_user),
    x_session_id: str | None = Header(default=None),
) -> Actor:
    if x_session_id is not None and not _SESSION_ID.match(x_session_id):
        raise HTTPException(status_code=400, detail="X-Session-Id must be 8-64 letters, digits, - or _.")
    return Actor(user=user, session_id=x_session_id)


def require_actor(actor: Actor = Depends(get_actor)) -> Actor:
    if actor.user is None and actor.session_id is None:
        raise HTTPException(status_code=400,
                            detail="Send a bearer token or an X-Session-Id header.")
    return actor
