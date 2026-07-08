from . import db
from .scheduling import WEEKDAYS, slot_times
from .security import hash_password

ADMIN_EMAIL = "admin@orochi.local"
ADMIN_PASSWORD = "orochi123"

# Default weekly template: Mon–Fri fully open, weekends closed.
DEFAULT_OPEN_DAYS = WEEKDAYS[:5]


def seed():
    """Seed the default admin user and a default availability template."""
    if not db.user_exists(ADMIN_EMAIL):
        db.create_user(ADMIN_EMAIL, hash_password(ADMIN_PASSWORD))

    if db.availability_is_empty():
        for weekday in DEFAULT_OPEN_DAYS:
            for time in slot_times():
                db.set_slot_availability(weekday, time, True)
