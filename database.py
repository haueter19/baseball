import hashlib
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

engine = create_engine(
    'sqlite:///local_baseball.db',
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=20,
    pool_recycle=3600  # Recycle connections after 1 hour
)


# Create session local for each database
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

meta = MetaData()


# Dependency to get the main DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()