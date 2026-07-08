# database.py — Database connection setup
# This file creates the connection to PostgreSQL
# and provides a session for each request

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# Build the database URL from environment variables
# Format: postgresql://user:password@host:port/dbname
DATABASE_URL = (
    f"postgresql://"
    f"{os.getenv('POSTGRES_USER', 'postgres')}:"
    f"{os.getenv('POSTGRES_PASSWORD', 'teleguard123')}@"
    f"{os.getenv('POSTGRES_HOST', 'postgres')}:"
    f"{os.getenv('POSTGRES_PORT', '5432')}/"
    f"{os.getenv('POSTGRES_DB', 'teleguard')}"
)

print(f"🗄️ Connecting to database: {DATABASE_URL}")

# Create engine — the actual connection to PostgreSQL
engine = create_engine(DATABASE_URL)

# SessionLocal — factory for database sessions
# Each request gets its own session
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base — all models inherit from this
Base = declarative_base()

# Dependency — used in FastAPI routes
# Automatically closes session after each request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()