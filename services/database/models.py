"""Local SQLite metadata, separate from legacy deployment tables."""

from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from utils.paths import session_data_root
from services.local_context import LOCAL_USER_ID

DB_DIR = session_data_root().parent
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "researchmind.db"
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Session(Base):
    __tablename__ = "local_sessions"

    id = Column(Integer, primary_key=True)
    session_id = Column(String(100), unique=True, nullable=False)
    user_id = Column(String(100), default=LOCAL_USER_ID, nullable=False)
    title = Column(String(200), default="新对话")
    agent_id = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
