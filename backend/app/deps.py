from fastapi import Cookie, HTTPException, status

from . import db
from .config import settings
from .security import read_session


def current_user(orochi_session: str = Cookie(default=None)):
    """FastAPI dependency: resolve the session cookie into a user dict.
    Raises 401 if the cookie is missing, invalid, or the user is unknown."""
    email = read_session(orochi_session) if orochi_session else None
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    user = db.get_user(email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    return {"email": user["email"]}
