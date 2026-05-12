import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """
    Central place for application settings.

    Values are loaded from environment variables. During local development,
    python-dotenv also lets you place them in a .env file.
    """

    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/llm_qa_search",
    )
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key-for-development")
    JWT_ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")


settings = Settings()
