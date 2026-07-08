from . import db
from .security import hash_password

ADMIN_EMAIL = "admin@orochi.local"
ADMIN_PASSWORD = "orochi123"


def seed():
    """Seed the default admin user if it does not yet exist."""
    if not db.user_exists(ADMIN_EMAIL):
        db.create_user(ADMIN_EMAIL, hash_password(ADMIN_PASSWORD))
