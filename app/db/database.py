from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

# The engine manages the connection pool to the database.
engine = create_engine(settings.DATABASE_URL)

# SessionLocal creates database sessions.
# Each API request will get its own session and close it when finished.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base is the parent class for all SQLAlchemy models.
# Any model that inherits from Base can be converted into a database table.
Base = declarative_base()


def get_db():
    """
    FastAPI dependency that provides a database session.

    The yield gives the session to the route. The finally block closes the
    session after the request is complete, even if an error happens.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()