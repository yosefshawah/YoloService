
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
load_dotenv()

# Choose backend via env; default to sqlite
DB_BACKEND = os.getenv("DB_BACKEND", "sqlite")

# Allow overriding full URL via env; otherwise pick sensible default per backend
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://user:pass@localhost:5432/predictions"
    if DB_BACKEND == "postgres"
    else "sqlite:///./predictions.db",
)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
def init_db():
    print(f"Creating tables for {DB_BACKEND}...")
    Base.metadata.create_all(bind=engine)