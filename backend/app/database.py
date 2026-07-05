"""
PostgreSQL access layer (Kaggle 900K-Spotify schema).

Responsibilities:
- Wait for the database container to be reachable.
- Create the `tracks` table if it does not exist.
- Seed the table from the prepared CSV on first startup (idempotent).
- Load all tracks into a pandas DataFrame for the recommender to fit on.

Connection settings come from environment variables so the app is
configurable via docker-compose.
"""

from __future__ import annotations

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
    "track_id", "track_name", "artist_name", "genre", "emotion", "album",
    "release_date", "explicit", "popularity", "tempo", "loudness",
    "duration_sec", "energy", "danceability", "valence", "speechiness",
    "liveness", "acousticness", "instrumentalness", "activities", "language",
    "similar_1", "similar_2", "similar_3",
]

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS tracks (
    track_id         TEXT PRIMARY KEY,
    track_name       TEXT NOT NULL,
    artist_name      TEXT NOT NULL,
    genre            TEXT NOT NULL,
    emotion          TEXT,
    album            TEXT,
    release_date     TEXT,
    explicit         BOOLEAN,
    popularity       INTEGER,
    tempo            DOUBLE PRECISION,
    loudness         DOUBLE PRECISION,
    duration_sec     INTEGER,
    energy           DOUBLE PRECISION,
    danceability     DOUBLE PRECISION,
    valence          DOUBLE PRECISION,
    speechiness      DOUBLE PRECISION,
    liveness         DOUBLE PRECISION,
    acousticness     DOUBLE PRECISION,
    instrumentalness DOUBLE PRECISION,
    activities       TEXT,
    language         TEXT,
    similar_1        TEXT,
    similar_2        TEXT,
    similar_3        TEXT
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
        except psycopg2.OperationalError as err:
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
                "Run data/prepare_dataset.py to build it from the Kaggle file."
            )

        df = pd.read_csv(DATASET_PATH)
        # Ensure all expected columns exist.
        for col in TABLE_COLUMNS:
            if col not in df.columns:
                df[col] = None
        df = df[TABLE_COLUMNS]
        df = df.where(pd.notna(df), None)
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
