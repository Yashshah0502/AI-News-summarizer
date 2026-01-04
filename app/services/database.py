# app/services/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base

def _db_url() -> str:
    user = os.getenv("POSTGRES_USER", "news")
    pwd = os.getenv("POSTGRES_PASSWORD", "news_password")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5433")
    db = os.getenv("POSTGRES_DB", "newsdb")
    return f"postgresql+psycopg://{user}:{pwd}@{host}:{port}/{db}"


engine = create_engine(_db_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
