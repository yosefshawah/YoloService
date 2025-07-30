
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
load_dotenv()
DB_BACKEND = os.getenv("DB_BACKEND", "sqlite")

if DB_BACKEND == "postgres":
    DATABASE_URL = "postgresql://user:pass@localhost:5432/predictions"
else:
    DATABASE_URL = "sqlite:///./predictions.db"

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
    if DB_BACKEND == "postgres":
        print("Creating tables in Postgres...")
        Base.metadata.create_all(bind=engine)