from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import DATABASE_URL

# Create the engine, handling pooling and reconnect logic (essential for Supabase free tier connection persistence)
engine = create_engine(
    DATABASE_URL, 
    pool_size=10, 
    max_overflow=20, 
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """
    FastAPI Session Dependency Injector.
    Guarantees session cleanup after query completion.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
