import os


class Settings:
    """Application settings loaded from environment variables."""

    DRAGONFLY_URL: str = os.getenv("DRAGONFLY_URL", "redis://localhost:6379")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-me-orochi")
    NOVITA_API_KEY: str = os.getenv("NOVITA_API_KEY", "")
    NOVITA_URL: str = os.getenv(
        "NOVITA_URL", "https://api.novita.ai/v3/openai/chat/completions"
    )
    NOVITA_MODEL: str = os.getenv("NOVITA_MODEL", "moonshotai/kimi-k2-instruct")

    COOKIE_NAME: str = "orochi_session"
    COOKIE_MAX_AGE: int = 60 * 60 * 24 * 7  # 7 days

    # Scheduling — 45-minute booking slots within clinic hours
    CLINIC_OPEN: str = os.getenv("CLINIC_OPEN", "08:00")
    CLINIC_CLOSE: str = os.getenv("CLINIC_CLOSE", "18:00")
    SLOT_MINUTES: int = int(os.getenv("SLOT_MINUTES", "45"))
    SCHEDULE_HORIZON_DAYS: int = int(os.getenv("SCHEDULE_HORIZON_DAYS", "21"))

    CORS_ORIGINS = ["http://localhost:5173"]


settings = Settings()
