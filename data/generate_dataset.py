"""
Generate a Spotify-style tracks dataset.

This mirrors the schema of the public Kaggle dataset
"Spotify Tracks Dataset" (maharshipandya/spotify-tracks-dataset):
audio features (danceability, energy, valence, tempo, etc.) plus
track/artist/genre metadata. We synthesize genre-consistent audio
features so the content-based recommender produces meaningful results
in a plug-and-play setup without a large external download.

If you prefer the real Kaggle data, drop `dataset.csv` (same columns)
into this folder and it will be used instead. See README for details.
"""

import numpy as np
import pandas as pd

RNG = np.random.default_rng(42)

# Genre "centers" in audio-feature space. Values are means; we add noise.
# Features roughly follow Spotify's 0..1 scales (tempo/loudness handled separately).
GENRE_PROFILES = {
    "pop":         dict(danceability=0.70, energy=0.72, valence=0.62, acousticness=0.18, instrumentalness=0.02, speechiness=0.07, liveness=0.16, tempo=118, loudness=-5.5),
    "rock":        dict(danceability=0.52, energy=0.82, valence=0.55, acousticness=0.10, instrumentalness=0.05, speechiness=0.06, liveness=0.22, tempo=128, loudness=-5.0),
    "hip-hop":     dict(danceability=0.78, energy=0.66, valence=0.55, acousticness=0.14, instrumentalness=0.01, speechiness=0.24, liveness=0.18, tempo=95,  loudness=-6.0),
    "electronic":  dict(danceability=0.74, energy=0.80, valence=0.50, acousticness=0.06, instrumentalness=0.45, speechiness=0.06, liveness=0.19, tempo=126, loudness=-6.5),
    "classical":   dict(danceability=0.28, energy=0.30, valence=0.40, acousticness=0.90, instrumentalness=0.85, speechiness=0.04, liveness=0.14, tempo=100, loudness=-14.0),
    "jazz":        dict(danceability=0.55, energy=0.45, valence=0.55, acousticness=0.62, instrumentalness=0.35, speechiness=0.06, liveness=0.25, tempo=110, loudness=-11.0),
    "r-n-b":       dict(danceability=0.68, energy=0.55, valence=0.52, acousticness=0.28, instrumentalness=0.03, speechiness=0.10, liveness=0.15, tempo=104, loudness=-7.0),
    "country":     dict(danceability=0.56, energy=0.62, valence=0.58, acousticness=0.35, instrumentalness=0.02, speechiness=0.05, liveness=0.20, tempo=120, loudness=-6.5),
    "metal":       dict(danceability=0.44, energy=0.94, valence=0.38, acousticness=0.03, instrumentalness=0.10, speechiness=0.09, liveness=0.24, tempo=140, loudness=-4.0),
    "acoustic":    dict(danceability=0.50, energy=0.35, valence=0.50, acousticness=0.82, instrumentalness=0.06, speechiness=0.05, liveness=0.18, tempo=108, loudness=-10.0),
    "indie":       dict(danceability=0.58, energy=0.58, valence=0.52, acousticness=0.40, instrumentalness=0.08, speechiness=0.06, liveness=0.19, tempo=116, loudness=-7.5),
    "reggae":      dict(danceability=0.72, energy=0.60, valence=0.68, acousticness=0.30, instrumentalness=0.05, speechiness=0.12, liveness=0.20, tempo=98,  loudness=-7.0),
}

# Word pools to synthesize plausible track + artist names per genre.
ARTIST_FIRST = ["Neon", "Silver", "Midnight", "Golden", "Crimson", "Electric", "Velvet",
                "Cosmic", "Wild", "Lunar", "Echo", "Paper", "Iron", "Glass", "Coral",
                "Amber", "Shadow", "River", "Ember", "Frost"]
ARTIST_LAST = ["Foxes", "Avenue", "Collective", "Theory", "Brothers", "Rebellion",
               "Skyline", "Order", "Machine", "Parade", "District", "Union", "Society",
               "Empire", "Kids", "Sisters", "Club", "Project", "Waves", "Rivals"]
TITLE_WORDS = ["Runaway", "Gravity", "Golden Hour", "Neon Lights", "Wildfire", "Silhouette",
               "Paper Planes", "Midnight Drive", "Ocean Eyes", "Afterglow", "Heartlines",
               "Electric Feel", "Slow Burn", "Daydream", "Northern Sky", "Velvet Rope",
               "Ghost Town", "Higher Ground", "Little Secrets", "Weightless", "Cold War",
               "Sun Chaser", "Static", "Free Fall", "Undertow", "Wanderlust", "Halcyon",
               "Skyfall", "Renegade", "Kaleidoscope", "Mirage", "Nightcall", "Bloom",
               "Aurora", "Landslide", "Fever Dream", "Solstice", "Echoes", "Vertigo"]


def _clip01(x):
    return float(np.clip(x, 0.0, 1.0))


def build(n_per_genre: int = 40) -> pd.DataFrame:
    rows = []
    tid = 0
    for genre, prof in GENRE_PROFILES.items():
        for _ in range(n_per_genre):
            tid += 1
            artist = f"{RNG.choice(ARTIST_FIRST)} {RNG.choice(ARTIST_LAST)}"
            title = f"{RNG.choice(TITLE_WORDS)}"
            rows.append({
                "track_id": f"trk_{tid:05d}",
                "track_name": title,
                "artist_name": artist,
                "genre": genre,
                "popularity": int(np.clip(RNG.normal(55, 22), 1, 100)),
                "duration_ms": int(np.clip(RNG.normal(210000, 45000), 90000, 400000)),
                "danceability": _clip01(RNG.normal(prof["danceability"], 0.08)),
                "energy": _clip01(RNG.normal(prof["energy"], 0.08)),
                "valence": _clip01(RNG.normal(prof["valence"], 0.10)),
                "acousticness": _clip01(RNG.normal(prof["acousticness"], 0.10)),
                "instrumentalness": _clip01(RNG.normal(prof["instrumentalness"], 0.10)),
                "speechiness": _clip01(RNG.normal(prof["speechiness"], 0.04)),
                "liveness": _clip01(RNG.normal(prof["liveness"], 0.06)),
                "tempo": round(float(np.clip(RNG.normal(prof["tempo"], 8), 50, 210)), 2),
                "loudness": round(float(np.clip(RNG.normal(prof["loudness"], 1.5), -30, 0)), 2),
            })
    df = pd.DataFrame(rows)
    # De-duplicate identical (title, artist) pairs by suffixing.
    dup = df.duplicated(subset=["track_name", "artist_name"], keep=False)
    df.loc[dup, "track_name"] = df.loc[dup, "track_name"] + " (" + (df.loc[dup].groupby(["track_name", "artist_name"]).cumcount() + 1).astype(str) + ")"
    return df


if __name__ == "__main__":
    df = build()
    df.to_csv("dataset.csv", index=False)
    print(f"Wrote dataset.csv with {len(df)} tracks across {df['genre'].nunique()} genres.")
