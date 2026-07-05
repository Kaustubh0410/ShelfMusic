"""
Prepare the ShelfMusic dataset from the Kaggle "900K Spotify" dataset.

Source (declared per project rules):
  devdope/900k-spotify  ->  spotify_dataset.csv
  https://www.kaggle.com/datasets/devdope/900k-spotify

The raw file is ~1.1 GB and ~900K rows, which is far too large to load
into an in-memory similarity model or to commit to Git. This script:

  1. Reads the raw CSV in chunks (memory-safe).
  2. Cleans the columns we use (parses "-6.85db" -> -6.85, "03:47" -> 227s,
     scales 0-100 audio features to 0-1, normalizes text fields).
  3. Samples a manageable subset (default 15,000) stratified by genre so
     every genre stays represented.
  4. Writes a compact data/dataset.csv that the backend seeds from.

Usage (run once, locally, after downloading the Kaggle file):

    python data/prepare_dataset.py \
        --input "C:/Users/Hp/.cache/kagglehub/datasets/devdope/900k-spotify/versions/3/spotify_dataset.csv" \
        --output data/dataset.csv \
        --sample 15000

If --input is omitted, the script looks for spotify_dataset.csv next to it.
"""

from __future__ import annotations

import argparse
import os
import re

import numpy as np
import pandas as pd

# Columns we read from the raw file (ignore the rest).
RAW_USE = [
    "Artist(s)", "song", "emotion", "Genre", "Album", "Release Date",
    "Tempo", "Loudness (db)", "Length", "Explicit", "Popularity",
    "Energy", "Danceability", "Positiveness", "Speechiness",
    "Liveness", "Acousticness", "Instrumentalness",
    "Good for Party", "Good for Work/Study", "Good for Relaxation/Meditation",
    "Good for Exercise", "Good for Running", "Good for Yoga/Stretching",
    "Good for Driving", "Good for Social Gatherings", "Good for Morning Routine",
    "Similar Artist 1", "Similar Song 1",
    "Similar Artist 2", "Similar Song 2",
    "Similar Artist 3", "Similar Song 3",
]

# The nine activity flags become one comma-joined "activities" string.
ACTIVITY_COLS = {
    "Good for Party": "party",
    "Good for Work/Study": "work_study",
    "Good for Relaxation/Meditation": "relaxation",
    "Good for Exercise": "exercise",
    "Good for Running": "running",
    "Good for Yoga/Stretching": "yoga",
    "Good for Driving": "driving",
    "Good for Social Gatherings": "social",
    "Good for Morning Routine": "morning",
}

INDIAN_ARTIST_KEYWORDS = [
    "arijit", "lata", "kishore", "pritam", "rahman", "alka", "udit", "shreya", "sonu", "asha",
    "mukesh", "burman", "sanu", "chauhan", "mohit", "badshah", "diljit", "honey", "trivedi",
    "jubin", "neha", "kakkar", "atif", "aslam", "darshan", "raval", "vishal", "shekhar",
    "sachin", "jigar", "tanishk", "bagchi", "rafi", "sukhwinder", "kher", "shaan", "kk",
    "mahadevan", "hariharan", "krishnamurthy", "sargam", "wadkar", "paudwal", "balasubrahmanyam",
    "chithra", "ehsaan", "loy", "dadlani", "ravjiani", "sajid", "wajid", "reshammiya", "malik",
    "jatin", "lalit", "fateh", "ali", "khan", "bhajan", "ghazal", "qawwali"
]

INDIAN_GENRES = [
    "filmi", "indipop", "sufi", "singles", "devotional", "ghazal", "garba", "bhajan",
    "bollywood", "desi", "punjabi", "indian", "bengali", "patriotic"
]

def get_language(artist: str, genre: str) -> str:
    artist_lower = str(artist).lower()
    genre_lower = str(genre).lower()
    if any(g in genre_lower for g in INDIAN_GENRES):
        return "hindi"
    if any(a in artist_lower for a in INDIAN_ARTIST_KEYWORDS):
        return "hindi"
    return "english"

def parse_loudness(val) -> float:
    """'-6.85db' -> -6.85 ; robust to NaN/odd formats."""
    if pd.isna(val):
        return -8.0
    m = re.search(r"-?\d+(\.\d+)?", str(val))
    return float(m.group()) if m else -8.0


def parse_length_to_seconds(val) -> int:
    """'03:47' -> 227 seconds."""
    if pd.isna(val):
        return 210
    s = str(val).strip()
    parts = s.split(":")
    try:
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except ValueError:
        pass
    return 210


def scale_0_100(series: pd.Series) -> pd.Series:
    """Audio features come 0-100; scale to 0-1 and clip."""
    return (pd.to_numeric(series, errors="coerce").fillna(50) / 100.0).clip(0, 1)


def clean_chunk(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Drop rows missing the essentials.
    df = df.dropna(subset=["song", "Artist(s)", "Genre"])

    # Normalize text fields.
    df["track_name"] = df["song"].astype(str).str.strip()
    df["artist_name"] = df["Artist(s)"].astype(str).str.strip()
    df["genre"] = df["Genre"].astype(str).str.strip().str.lower()
    df["emotion"] = df["emotion"].astype(str).str.strip().str.lower().fillna("unknown")
    df["album"] = df["Album"].astype(str).str.strip()
    df["release_date"] = df["Release Date"].astype(str).str.strip()
    df["explicit"] = df["Explicit"].astype(str).str.strip().str.lower().map(
        {"yes": True, "no": False}
    ).fillna(False)

    # Numeric metadata.
    df["popularity"] = pd.to_numeric(df["Popularity"], errors="coerce").fillna(30).astype(int).clip(0, 100)
    df["tempo"] = pd.to_numeric(df["Tempo"], errors="coerce").fillna(120).clip(40, 240)
    df["loudness"] = df["Loudness (db)"].apply(parse_loudness)
    df["duration_sec"] = df["Length"].apply(parse_length_to_seconds)

    # Audio features (0-100 -> 0-1).
    df["energy"] = scale_0_100(df["Energy"])
    df["danceability"] = scale_0_100(df["Danceability"])
    df["valence"] = scale_0_100(df["Positiveness"])       # Positiveness == valence
    df["speechiness"] = scale_0_100(df["Speechiness"])
    df["liveness"] = scale_0_100(df["Liveness"])
    df["acousticness"] = scale_0_100(df["Acousticness"])
    df["instrumentalness"] = scale_0_100(df["Instrumentalness"])

    # Activities: comma-joined list of the flags that are set.
    def activities_for_row(row) -> str:
        active = [short for col, short in ACTIVITY_COLS.items()
                  if str(row.get(col, "0")).strip() in ("1", "1.0", "True", "true")]
        return ",".join(active)

    df["activities"] = df.apply(activities_for_row, axis=1)

    # Language classification.
    df["language"] = df.apply(lambda r: get_language(r["artist_name"], r["genre"]), axis=1)

    # Dataset's own precomputed similar songs (kept for a bonus UI feature).
    df["similar_1"] = (df["Similar Artist 1"].astype(str) + " \u2013 " + df["Similar Song 1"].astype(str)).str.strip()
    df["similar_2"] = (df["Similar Artist 2"].astype(str) + " \u2013 " + df["Similar Song 2"].astype(str)).str.strip()
    df["similar_3"] = (df["Similar Artist 3"].astype(str) + " \u2013 " + df["Similar Song 3"].astype(str)).str.strip()

    keep = [
        "track_name", "artist_name", "genre", "emotion", "album", "release_date",
        "explicit", "popularity", "tempo", "loudness", "duration_sec",
        "energy", "danceability", "valence", "speechiness", "liveness",
        "acousticness", "instrumentalness", "activities", "language",
        "similar_1", "similar_2", "similar_3",
    ]
    return df[keep]


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=os.path.join(here, "spotify_dataset.csv"),
                    help="Path to the raw Kaggle spotify_dataset.csv")
    ap.add_argument("--output", default=os.path.join(here, "dataset.csv"),
                    help="Where to write the compact dataset")
    ap.add_argument("--sample", type=int, default=15000,
                    help="Number of tracks to keep (stratified by genre)")
    args = ap.parse_args()

    if not os.path.exists(args.input):
        raise SystemExit(
            f"Raw file not found: {args.input}\n"
            "Download it from Kaggle (devdope/900k-spotify) and pass --input."
        )

    print(f"[prep] reading {args.input} in chunks ...")
    cleaned = []
    reader = pd.read_csv(args.input, usecols=lambda c: c in RAW_USE,
                         chunksize=100_000, on_bad_lines="skip", low_memory=False)
    for i, chunk in enumerate(reader, 1):
        cleaned.append(clean_chunk(chunk))
        print(f"[prep]   processed chunk {i} ({i*100_000:,} rows seen)")

    df = pd.concat(cleaned, ignore_index=True)
    print(f"[prep] cleaned rows: {len(df):,}")

    # Drop exact duplicate songs (same title + artist).
    df = df.drop_duplicates(subset=["track_name", "artist_name"]).reset_index(drop=True)
    print(f"[prep] after de-dup: {len(df):,}")
    # Stratified sample of English tracks, while keeping ALL Hindi/Indian tracks
    df_hindi = df[df["language"] == "hindi"]
    df_english = df[df["language"] == "english"]
    print(f"[prep] split: {len(df_hindi):,} Hindi tracks, {len(df_english):,} English tracks")

    sample_english_size = args.sample
    if len(df_english) > sample_english_size:
        frac = sample_english_size / len(df_english)
        df_english_sampled = (df_english.groupby("genre", group_keys=False)
                              .apply(lambda g: g.sample(max(1, int(len(g) * frac)), random_state=42)))
    else:
        df_english_sampled = df_english

    df = pd.concat([df_hindi, df_english_sampled], ignore_index=True)
    df = df.sample(frac=1.0, random_state=42).reset_index(drop=True)
    print(f"[prep] final blended dataset: {len(df):,} rows ({len(df_hindi):,} Hindi + {len(df_english_sampled):,} English) across {df['genre'].nunique()} genres")    # Stable track_id.
    df.insert(0, "track_id", [f"trk_{i:06d}" for i in range(1, len(df) + 1)])

    df.to_csv(args.output, index=False)
    print(f"[prep] wrote {args.output} ({os.path.getsize(args.output)/1e6:.1f} MB)")


if __name__ == "__main__":
    main()
