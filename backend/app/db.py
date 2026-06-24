from contextlib import contextmanager
import psycopg
from psycopg_pool import ConnectionPool
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Initialize connection pool
try:
    pool = ConnectionPool(settings.database_url, min_size=2, max_size=10)
    logger.info("Database connection pool initialized.")
except Exception as e:
    logger.error(f"Failed to initialize database pool: {e}")
    pool = None

@contextmanager
def get_connection():
    if not pool:
        conn = psycopg.connect(settings.database_url)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return

    with pool.connection() as conn:
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

def run_migrations():
    """Safe startup migration to add sessions support without deleting data."""
    migration_sql = """
    -- 1. Create sessions table
    CREATE TABLE IF NOT EXISTS sessions (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- 2. Modify chat_logs to support session-based messaging
    ALTER TABLE chat_logs ADD COLUMN IF NOT EXISTS session_id INTEGER REFERENCES sessions(id) ON DELETE CASCADE;
    ALTER TABLE chat_logs ADD COLUMN IF NOT EXISTS role TEXT;
    ALTER TABLE chat_logs ADD COLUMN IF NOT EXISTS content TEXT;
    ALTER TABLE chat_logs ADD COLUMN IF NOT EXISTS sources JSONB;
    
    -- Relax old constraints to allow new message format to coexist without breaking old records
    -- ALTER TABLE chat_logs ALTER COLUMN question DROP NOT NULL;
    -- ALTER TABLE chat_logs ALTER COLUMN answer DROP NOT NULL;

    -- 3. Multi-modal support
    ALTER TABLE chunks ADD COLUMN IF NOT EXISTS image_path TEXT;

    -- 4. Mode-specific knowledge base
    ALTER TABLE papers ADD COLUMN IF NOT EXISTS ai_mode TEXT DEFAULT 'local';
    """
    
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(migration_sql)
        logger.info("Database migrations ran successfully.")
    except Exception as e:
        logger.error(f"Failed to run database migrations: {e}")
        # Don't block app startup if this fails, we can catch DB errors at endpoint level

