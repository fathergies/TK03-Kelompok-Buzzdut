import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from pathlib import Path
import psycopg2.extras
psycopg2.extras.register_uuid()

# Load environment variables explicitly from project root
BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / '.env'
load_dotenv(dotenv_path=env_path)

def get_db_connection():
    """
    Establish and return a connection to the PostgreSQL database.
    Sets the search_path to the configured SCHEMA.
    """
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        port=os.getenv('DB_PORT', 5432)
    )
    
    # Automatically set the schema search path for this connection
    schema = os.getenv('SCHEMA', 'public')
    with conn.cursor() as cur:
        cur.execute(f"SET search_path TO {schema}, public;")
    
    return conn

def fetch_all(query, params=None):
    """
    Execute a SELECT query and return all rows as dictionaries.
    """
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchall()

def fetch_one(query, params=None):
    """
    Execute a SELECT query and return a single row as a dictionary.
    """
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchone()

def execute_query(query, params=None):
    """
    Execute an INSERT, UPDATE, or DELETE query and commit the changes.
    Returns the number of rows affected.
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            conn.commit()
            return cur.rowcount
