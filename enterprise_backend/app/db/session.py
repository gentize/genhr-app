from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# For development, we use SQLite. For production, switch to PostgreSQL.
SQLALCHEMY_DATABASE_URL = os.environ.get("DATABASE_URL") or "sqlite:///./enterprise_attendance.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    from app.models.attendance import Base
    Base.metadata.create_all(bind=engine)
