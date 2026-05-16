import os
import dj_database_url
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from pathlib import Path
from psycopg2.extras import RealDictCursor
from urllib.parse import quote

psycopg2.extras.register_uuid()

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def get_database_url():
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        return database_url

    if os.environ.get("DB_HOST"):
        db_user = quote(os.environ.get("DB_USER", ""), safe="")
        db_password = quote(os.environ.get("DB_PASSWORD", ""), safe="")
        db_host = os.environ.get("DB_HOST")
        db_port = os.environ.get("DB_PORT", "5432")
        db_name = os.environ.get("DB_NAME", "postgres")
        return f"postgres://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    return None

def get_db_connection():
    database_url = get_database_url()
    if not database_url:
        raise RuntimeError("DATABASE_URL or DB_* environment variables are required")

    db_config = dj_database_url.parse(
        database_url,
        conn_max_age=600,
        ssl_require=True
    )

    conn = psycopg2.connect(
        dbname=db_config['NAME'],
        user=db_config['USER'],
        password=db_config['PASSWORD'],
        host=db_config['HOST'],
        port=db_config['PORT'],
        sslmode='require'
    )

    schema = os.environ.get("SCHEMA")
    if schema:
        with conn.cursor() as cur:
            cur.execute(f"SET search_path TO {schema}, public;")

    return conn


def fetch_all(query, params=None):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchall()


def fetch_one(query, params=None):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchone()


def execute_query(query, params=None):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            conn.commit()
            return cur.rowcount


def get_database_error_message(error):
    diag = getattr(error, "diag", None)
    message = getattr(diag, "message_primary", None) or str(error)
    return message.strip().splitlines()[0]
