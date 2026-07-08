from typing import Optional

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from passlib.context import CryptContext

from .config import settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_serializer = URLSafeTimedSerializer(settings.SECRET_KEY, salt="orochi-session")


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _pwd_context.verify(password, password_hash)
    except Exception:
        return False


def make_session(email: str) -> str:
    """Create a signed session token carrying the user's email."""
    return _serializer.dumps({"email": email})


def read_session(token: str, max_age: Optional[int] = None) -> Optional[str]:
    """Read a session token, returning the email or None if invalid/expired."""
    if not token:
        return None
    if max_age is None:
        max_age = settings.COOKIE_MAX_AGE
    try:
        data = _serializer.loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired, Exception):
        return None
    if not isinstance(data, dict):
        return None
    return data.get("email")
