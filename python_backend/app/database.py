"""
Database module for CodeScan.

Handles database connection, session management, and schema migrations
using SQLAlchemy with MySQL.
"""

from typing import Optional, List, Tuple
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import QueuePool

from app.config import DBConfig
from app.models import Task, TaskStage, Base


# Global session factory
SessionLocal: Optional[sessionmaker] = None
engine = None


def build_connection_string(cfg: DBConfig, with_database: bool = True) -> str:
    """Build MySQL connection string."""
    db_name = cfg.dbname if with_database else ""
    return (
        f"mysql+pymysql://{cfg.user}:{cfg.password}@{cfg.host}:{cfg.port}/{db_name}"
        f"?charset=utf8mb4"
    )


def init_database(cfg: DBConfig) -> Session:
    """Initialize database connection and return a session."""
    global engine, SessionLocal
    
    # First connect without database to ensure it exists
    root_engine = create_engine(
        build_connection_string(cfg, with_database=False),
        poolclass=QueuePool,
        pool_size=10,
        max_overflow=20,
    )
    
    # Ensure database exists
    ensure_database(root_engine, cfg.dbname)
    root_engine.dispose()
    
    # Connect to the actual database
    engine = create_engine(
        build_connection_string(cfg, with_database=True),
        poolclass=QueuePool,
        pool_size=25,
        max_idle_conns=10,
        pool_recycle=300,  # 5 minutes
    )
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    return SessionLocal()


def ensure_database(root_engine, db_name: str) -> Tuple[bool, bool]:
    """Ensure database exists, create if not. Returns (existed, created)."""
    existed = False
    
    with root_engine.connect() as conn:
        # Check if database exists
        result = conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = :dbname"
            ),
            {"dbname": db_name}
        )
        count = result.scalar()
        existed = count > 0
        
        # Create database if not exists
        conn.execute(
            text(
                f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        )
        conn.commit()
    
    return existed, not existed


def ensure_schema(db_session: Session) -> List[str]:
    """Ensure database schema is up to date. Returns list of repairs applied."""
    repairs = []
    
    # Create all tables
    Base.metadata.create_all(bind=db_session.bind)
    
    # Check and repair column types
    required_columns = [
        ("tasks", "result", "LONGTEXT"),
        ("task_stages", "result", "LONGTEXT"),
    ]
    
    inspector = inspect(db_session.bind)
    
    for table_name, column_name, expected_type in required_columns:
        repaired = ensure_column_type(db_session, inspector, table_name, column_name, expected_type)
        if repaired:
            repairs.append(f"{table_name}.{column_name} -> {expected_type}")
    
    db_session.commit()
    return repairs


def ensure_column_type(
    db_session: Session, 
    inspector, 
    table_name: str, 
    column_name: str, 
    expected_type: str
) -> bool:
    """Ensure column has the correct type, repair if needed."""
    try:
        columns = inspector.get_columns(table_name)
        current_type = None
        
        for col in columns:
            if col['name'] == column_name:
                current_type = str(col['type']).upper()
                break
        
        if current_type is None:
            raise Exception(f"Column {table_name}.{column_name} not found after migration")
        
        if current_type == expected_type:
            return False
        
        # Repair column type
        db_session.execute(
            text(
                f"ALTER TABLE `{table_name}` MODIFY COLUMN `{column_name}` {expected_type}"
            )
        )
        return True
        
    except Exception as e:
        raise Exception(f"Error repairing {table_name}.{column_name}: {e}")


def get_db() -> Session:
    """Dependency for FastAPI to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
