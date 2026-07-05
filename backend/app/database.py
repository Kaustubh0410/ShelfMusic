"""
PostgreSQL access layer.

Responsibilities:
- Wait for the database container to be reachable.
- Create the `tracks` table if it does not exist.
- Seed the table from the CSV dataset on first startup (idempotent).
- Load all tracks into a pandas DataFrame for the recommender to fit on.

Connection settings come from environment variables so the app is
configurable via docker-compose. See README for the full list.
"""

from __future__ import annotations

import io
import os
import time

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from sqlalchemy import create_engine

DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "db"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "dbname": os.getenv("POSTGRES_DB", "shelfmusic"),
    "user": os.getenv("POSTGRES_USER", "shelfmusic"),
    "password": os.getenv("POSTGRES_PASSWORD", "shelfmusic"),
}

DATASET_PATH = os.getenv("DATASET_PATH", "/data/dataset.csv")


def _sqlalchemy_url() -> str:
    c = DB_CONFIG
    return (
        f"postgresql+psycopg2://{c['user']}:{c['password']}"
        f"@{c['host']}:{c['port']}/{c['dbname']}"
    )

TABLE_COLUMNS = [
    "track_id", "track_name", "artist_name", "genre", "popularity",
    "duration_ms", "danceability", "energy", "valence", "acousticness",
    "instrumentalness", "speechiness", "liveness", "tempo", "loudness",
]

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS tracks (
    track_id         TEXT PRIMARY KEY,
    track_name       TEXT NOT NULL,
    artist_name      TEXT NOT NULL,
    genre            TEXT NOT NULL,
    popularity       INTEGER NOT NULL,
    duration_ms      INTEGER NOT NULL,
    danceability     DOUBLE PRECISION NOT NULL,
    energy           DOUBLE PRECISION NOT NULL,
    valence          DOUBLE PRECISION NOT NULL,
    acousticness     DOUBLE PRECISION NOT NULL,
    instrumentalness DOUBLE PRECISION NOT NULL,
    speechiness      DOUBLE PRECISION NOT NULL,
    liveness         DOUBLE PRECISION NOT NULL,
    tempo            DOUBLE PRECISION NOT NULL,
    loudness         DOUBLE PRECISION NOT NULL
);
"""


def _connect(retries: int = 30, delay: float = 2.0) -> psycopg2.extensions.connection:
    """Connect to PostgreSQL, retrying while the DB container starts up."""
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            conn.autocommit = True
            return conn
        except psycopg2.OperationalError as err:  # DB not ready yet
            last_err = err
            print(f"[database] DB not ready (attempt {attempt}/{retries}): {err}")
            time.sleep(delay)
    raise RuntimeError(f"Could not connect to PostgreSQL: {last_err}")


def _seed_if_empty(conn: psycopg2.extensions.connection) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM tracks;")
        count = cur.fetchone()[0]
        if count > 0:
            print(f"[database] tracks table already seeded ({count} rows).")
            return

        if not os.path.exists(DATASET_PATH):
            raise FileNotFoundError(
                f"Dataset not found at {DATASET_PATH}. "
                "Run data/generate_dataset.py or mount the dataset volume."
            )

        df = pd.read_csv(DATASET_PATH)
        df = df[TABLE_COLUMNS]
        rows = list(df.itertuples(index=False, name=None))
        execute_values(
            cur,
            f"INSERT INTO tracks ({', '.join(TABLE_COLUMNS)}) VALUES %s "
            "ON CONFLICT (track_id) DO NOTHING;",
            rows,
        )
        print(f"[database] seeded tracks table with {len(rows)} rows.")


def init_db() -> None:
    """Create schema and seed data. Safe to call repeatedly."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(CREATE_TABLE_SQL)
        _seed_if_empty(conn)
    finally:
        conn.close()


def load_tracks_dataframe() -> pd.DataFrame:
    """Read the full tracks table into a DataFrame for the recommender."""
    engine = create_engine(_sqlalchemy_url())
    try:
        df = pd.read_sql(f"SELECT {', '.join(TABLE_COLUMNS)} FROM tracks;", engine)
    finally:
        engine.dispose()
    return df
