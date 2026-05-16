import os
import dj_database_url
import psycopg2
import psycopg2.extras
from psycopg2.extras import RealDictCursor

psycopg2.extras.register_uuid()


def get_db_connection():
    db_config = dj_database_url.parse(
        os.environ["DATABASE_URL"]
    )

    return psycopg2.connect(
        dbname=db_config["NAME"],
        user=db_config["USER"],
        password=db_config["PASSWORD"],
        host=db_config["HOST"],
        port=db_config["PORT"],
        sslmode="require"
    )


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
