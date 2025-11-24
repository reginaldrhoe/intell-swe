from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data.db")

# For SQLite, echo=False by default; tune for production
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db():
    # Create tables (simple approach for MVP)
    Base.metadata.create_all(bind=engine)
