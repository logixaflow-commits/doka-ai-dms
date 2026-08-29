"""
Office DMS - Database Module
SQLAlchemy engine, session management, and connection handling.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# =============================================================================
# Engine Configuration
# =============================================================================
if settings.DATABASE_URL.startswith("sqlite"):
    # SQLite configuration
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=settings.DEBUG and settings.ENVIRONMENT == "development",
    )
else:
    # PostgreSQL configuration
    engine = create_engine(
        settings.DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=settings.DEBUG and settings.ENVIRONMENT == "development",
    )

# =============================================================================
# Session Factory
# =============================================================================
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


# =============================================================================
# Event Listeners for Connection Pooling
# =============================================================================
@event.listens_for(engine, "connect")
def on_connect(dbapi_conn, connection_record):
    """Set SQLite pragmas on connection."""
    if settings.DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.execute("PRAGMA busy_timeout=5000;")
        cursor.close()
        logger.debug("SQLite connection configured with WAL mode")


@event.listens_for(engine, "checkout")
def on_checkout(dbapi_conn, connection_record, connection_proxy):
    """Verify connection is alive on checkout from pool."""
    if settings.DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_conn.cursor()
        try:
            cursor.execute("SELECT 1")
        except Exception:
            connection_record.connection = None
            raise
        finally:
            cursor.close()


# =============================================================================
# Dependency for FastAPI
# =============================================================================
def get_db() -> Session:
    """
    FastAPI dependency that provides a database session.
    Usage: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =============================================================================
# Database Initialization
# =============================================================================
def init_database():
    """Create all tables if they don't exist."""
    from app.models.database import Base

    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized.")


def get_db_status() -> dict:
    """Check database connectivity. Returns status dictionary."""
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return {
            "status": "connected",
            "type": (
                "sqlite" if settings.DATABASE_URL.startswith("sqlite") else "postgresql"
            ),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
