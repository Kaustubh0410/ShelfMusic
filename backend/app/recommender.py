"""
Hybrid music recommendation engine.

Two complementary strategies are combined:

1. Content-based filtering
   Each track is represented by a feature vector built from:
     - Normalized numeric audio features (danceability, energy, valence,
       acousticness, instrumentalness, speechiness, liveness, tempo, loudness).
     - A TF-IDF encoding of the genre label, so genre similarity contributes
       to the vector space alongside the audio features.
   Similarity between tracks is cosine similarity over these vectors.

2. Preference-based scoring
   When a user supplies target preferences (mood/energy sliders + genres),
   we build a synthetic "taste vector" and rank all tracks against it,
   blending in popularity so well-known tracks surface for cold starts.

The engine is fit once at startup from a pandas DataFrame and then answers
queries in-memory.
"""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler

NUMERIC_FEATURES = [
    "danceability", "energy", "valence", "acousticness",
    "instrumentalness", "speechiness", "liveness", "tempo", "loudness",
]

# Features a user can steer directly via the UI (all on a 0..1 scale).
STEERABLE_FEATURES = [
    "danceability", "energy", "valence", "acousticness", "instrumentalness",
]


class MusicRecommender:
    def __init__(self, df: pd.DataFrame):
        self.df = df.reset_index(drop=True).copy()
        self._scaler = MinMaxScaler()
        self._numeric_scaled = self._scaler.fit_transform(self.df[NUMERIC_FEATURES])

        # TF-IDF over genre so genre overlap contributes to similarity.
        self._genre_vectorizer = TfidfVectorizer()
        genre_matrix = self._genre_vectorizer.fit_transform(self.df["genre"]).toarray()

        # Weight genre vs audio features. Genre is weighted so same-genre
        # tracks cluster, but audio features still differentiate within a genre.
        genre_weight = 1.5
        self._feature_matrix = np.hstack([
            self._numeric_scaled,
            genre_matrix * genre_weight,
        ])

        # Precompute the full track-track similarity matrix (small dataset).
        self._similarity = cosine_similarity(self._feature_matrix)

        # Index helpers
        self._id_to_pos = {tid: i for i, tid in enumerate(self.df["track_id"])}

    # ------------------------------------------------------------------ #
    # Metadata helpers
    # ------------------------------------------------------------------ #
    def genres(self) -> list[str]:
        return sorted(self.df["genre"].unique().tolist())

    def track_count(self) -> int:
        return int(len(self.df))

    def _rows_to_records(self, idx: Iterable[int], scores: dict[int, float] | None = None) -> list[dict]:
        out = []
        for i in idx:
            row = self.df.iloc[i]
            rec = {
                "track_id": row["track_id"],
                "track_name": row["track_name"],
                "artist_name": row["artist_name"],
                "genre": row["genre"],
                "popularity": int(row["popularity"]),
                "duration_ms": int(row["duration_ms"]),
                "danceability": round(float(row["danceability"]), 3),
                "energy": round(float(row["energy"]), 3),
                "valence": round(float(row["valence"]), 3),
                "acousticness": round(float(row["acousticness"]), 3),
                "tempo": round(float(row["tempo"]), 1),
            }
            if scores is not None:
                rec["match_score"] = round(float(scores.get(i, 0.0)), 4)
            out.append(rec)
        return out

    # ------------------------------------------------------------------ #
    # Search
    # ------------------------------------------------------------------ #
    def search(self, query: str, limit: int = 20) -> list[dict]:
        q = query.strip().lower()
        if not q:
            return []
        mask = (
            self.df["track_name"].str.lower().str.contains(q, regex=False)
            | self.df["artist_name"].str.lower().str.contains(q, regex=False)
        )
        idx = self.df.index[mask][:limit].tolist()
        return self._rows_to_records(idx)

    # ------------------------------------------------------------------ #
    # Similar-track recommendations (content-based, item-item)
    # ------------------------------------------------------------------ #
    def similar_to(self, track_id: str, limit: int = 10) -> list[dict]:
        if track_id not in self._id_to_pos:
            raise KeyError(track_id)
        pos = self._id_to_pos[track_id]
        sims = self._similarity[pos].copy()
        sims[pos] = -1.0  # exclude the seed track itself
        top = np.argsort(sims)[::-1][:limit]
        scores = {int(i): float(sims[i]) for i in top}
        return self._rows_to_records([int(i) for i in top], scores)

    # ------------------------------------------------------------------ #
    # Preference-based recommendations (taste vector)
    # ------------------------------------------------------------------ #
    def recommend_from_preferences(
        self,
        preferences: dict[str, float],
        genres: list[str] | None = None,
        limit: int = 12,
        popularity_weight: float = 0.15,
    ) -> list[dict]:
        """
        preferences: dict of steerable feature -> target value in [0,1].
        genres: optional list of preferred genres (soft filter / boost).
        """
        # Build a synthetic target row in the ORIGINAL feature space, then scale.
        target = self.df[NUMERIC_FEATURES].mean().to_dict()
        for feat, val in preferences.items():
            if feat in target:
                target[feat] = float(val)
        # tempo/loudness aren't on a 0..1 scale; leave them at dataset mean
        # unless explicitly steered (UI only steers 0..1 features).
        target_vec = self._scaler.transform(
            pd.DataFrame([target])[NUMERIC_FEATURES]
        )[0]

        # Genre component of the taste vector.
        if genres:
            genre_text = " ".join(genres)
        else:
            genre_text = " ".join(self.df["genre"].unique())
        genre_vec = self._genre_vectorizer.transform([genre_text]).toarray()[0] * 1.5

        taste_vector = np.hstack([target_vec, genre_vec]).reshape(1, -1)
        sims = cosine_similarity(taste_vector, self._feature_matrix)[0]

        # Blend in normalized popularity.
        pop = self.df["popularity"].to_numpy() / 100.0
        blended = (1 - popularity_weight) * sims + popularity_weight * pop

        # Hard genre preference boost (soft): add small bonus for matching genre.
        if genres:
            genre_set = set(genres)
            bonus = self.df["genre"].isin(genre_set).to_numpy().astype(float) * 0.05
            blended = blended + bonus

        top = np.argsort(blended)[::-1][:limit]
        scores = {int(i): float(blended[i]) for i in top}
        return self._rows_to_records([int(i) for i in top], scores)

    # ------------------------------------------------------------------ #
    # Popular fallback
    # ------------------------------------------------------------------ #
    def popular(self, limit: int = 12, genre: str | None = None) -> list[dict]:
        df = self.df
        if genre:
            df = df[df["genre"] == genre]
        idx = df.sort_values("popularity", ascending=False).head(limit).index.tolist()
        return self._rows_to_records(idx)
