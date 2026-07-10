from . import db
from . import store_catalog
from .security import hash_password
from .seed_transcripts import seed_transcripts

ADMIN_EMAIL = "admin@orochi.local"
ADMIN_PASSWORD = "orochi123"


def seed():
    """Seed the admin user, the provider/procedure catalog, and each provider's
    default weekly availability (Mon–Fri, all slots)."""
    if not db.user_exists(ADMIN_EMAIL):
        db.create_user(ADMIN_EMAIL, hash_password(ADMIN_PASSWORD))

    # Providers + procedure types (no-op if already seeded).
    store_catalog.ensure_seeded()
    # Per-provider availability template (Mon–Fri) for any provider with none.
    db.ensure_provider_availability_seeded()

    # Synthetic call transcripts + precomputed judgments for the Transcripts demo.
    seed_transcripts()
