from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text
from app.api.auth_routes import router as auth_router
from app.api.dashboard_routes import router as dashboard_router
from app.api.document_routes import router as document_router
from app.api.search_routes import router as search_router
from app.db.database import Base, engine

# Import models before create_all so SQLAlchemy knows tables.
from app.models import document, search_history, user  # noqa: F401


def add_user_id_column_if_missing():
    """
    Add user_id for older local databases before using migrations.
    """
    inspector = inspect(engine)

    if not inspector.has_table("documents"):
        return

    column_names = [column["name"] for column in inspector.get_columns("documents")]

    if "user_id" not in column_names:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE documents ADD COLUMN user_id INTEGER"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_documents_user_id ON documents (user_id)"))


def allow_google_users_without_password():
    """
    Allow Google-created users to have no local password hash.
    """
    inspector = inspect(engine)

    if not inspector.has_table("users"):
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE users ALTER COLUMN hashed_password DROP NOT NULL"))


def add_search_time_column_if_missing():
    """
    Add search_time_ms for older local databases before using migrations.
    """
    inspector = inspect(engine)

    if not inspector.has_table("search_history"):
        return

    column_names = [column["name"] for column in inspector.get_columns("search_history")]

    if "search_time_ms" not in column_names:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE search_history ADD COLUMN search_time_ms FLOAT"))


@asynccontextmanager
async def lifespan(app: FastAPI):

    """
    Create database tables when the API starts.
    This keeps local setup simple. A production project would usually use
    Alembic migrations instead.
    """    
    Base.metadata.create_all(bind=engine)
    add_user_id_column_if_missing()
    add_search_time_column_if_missing()
    allow_google_users_without_password()
    yield

app = FastAPI(
    title="LLM-Powered Q&A Search Engine",
    description="Backend for document storage, semantic search, and question answering.",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    """
    Confirm that the API process is running.
    """
    return {
        "status": "ok",
        "message": "LLM Q&A Search Engine backend is running",
    }

app.include_router(document_router)
app.include_router(search_router)
app.include_router(auth_router)
app.include_router(dashboard_router)