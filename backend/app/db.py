from __future__ import annotations

import snowflake.connector
from .config import settings


def get_connection():
    # Allow disabling OCSP/SSL checks for hackathon scenarios behind strict firewalls or broken cert chains
    # Only enable when SNOWFLAKE_INSECURE=true
    ocsp_fail_open = settings.snowflake_insecure
    insecure_mode = settings.snowflake_insecure

    return snowflake.connector.connect(
        account=settings.snowflake_account,
        user=settings.snowflake_user,
        password=settings.snowflake_password,
        warehouse=settings.snowflake_warehouse,
        database=settings.snowflake_database,
        schema=settings.snowflake_schema,
        ocsp_fail_open=ocsp_fail_open,
        insecure_mode=insecure_mode,
    )


def fetch_one(query: str, params: tuple | None = None):
    with get_connection() as conn:
        with conn.cursor(snowflake.connector.DictCursor) as cur:
            cur.execute(query, params or ())
            return cur.fetchone()


def execute(query: str, params: tuple | None = None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            conn.commit()


def execute_many(query: str, seq_of_params: list[tuple] | list[dict]):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(query, seq_of_params)
            conn.commit()


def fetch_all(query: str, params: tuple | dict | None = None):
    with get_connection() as conn:
        with conn.cursor(snowflake.connector.DictCursor) as cur:  # type: ignore
            cur.execute(query, params or ())
            return cur.fetchall()


