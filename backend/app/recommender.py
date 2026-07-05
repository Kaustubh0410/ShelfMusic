"""
ShelfMusic recommendation engine (Kaggle 900K-Spotify edition).

Content-based recommender over real Spotify audio features, with faceted
filtering by mood (emotion), genre, artist, and activity.

Track vectors combine normalized numeric audio features with a TF-IDF
encoding of genre + emotion, so recommendations respect both how a track
sounds and its mood. Similarity is computed on demand against the current
candidate set (after filters), which keeps memory flat even for large
datasets -- we never materialize a full N x N matrix.
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

# Features the user steers with sliders (all 0..1).
STEERABLE = ["danceability", "energy", "valence", "acousticness", "instrumentalness"]

ACTIVITY_LABELS = {
    "party": "Party", "work_study": "Work/Study", "relaxation": "Relaxation",
    "exercise": "Exercise", "running": "Running", "yoga": "Yoga",
    "driving": "Driving", "social": "Social", "morning": "Morning",
}


class MusicRecommender:
    def __init__(self, df: pd.DataFrame):
        self.df = df.reset_index(drop=True).copy()

        # Scale numeric features to 0..1 (tempo/loudness need it; others already are).
        self._scaler = MinMaxScaler()
        self._numeric_scaled = self._scaler.fit_transform(self.df[NUMERIC_FEATURES])

        # TF-IDF over "genre emotion" so both contribute to similarity.
        self._tags = (self.df["genre"].fillna("") + " " + self.df["emotion"].fillna("")).str.strip()
        self._vectorizer = TfidfVectorizer()
        tag_matrix = self._vectorizer.fit_transform(self._tags).toarray()

        tag_weight = 1.5
        self._feature_matrix = np.hstack([self._numeric_scaled, tag_matrix * tag_weight])

        self._id_to_pos = {tid: i for i, tid in enumerate(self.df["track_id"])}

    # ------------------------------------------------------------------ #
    # Facet metadata for the UI dropdowns
    # ------------------------------------------------------------------ #
    def facets(self) -> dict:
        genres = sorted(g for g in self.df["genre"].dropna().unique() if g)
        moods = sorted(m for m in self.df["emotion"].dropna().unique() if m and m != "nan")
        top_artists = self.df["artist_name"].value_counts().head(300).index.tolist()
        activities = [{"key": k, "label": v} for k, v in ACTIVITY_LABELS.items()]
        return {
            "genres": genres,
            "moods": moods,
            "artists": sorted(top_artists),
            "activities": activities,
            "track_count": int(len(self.df)),
        }

    def track_count(self) -> int:
        return int(len(self.df))

    # ------------------------------------------------------------------ #
    # Record serialization
    # ------------------------------------------------------------------ #
    def _rows_to_records(self, idx: Iterable[int], scores: dict[int, float] | None = None) -> list[dict]:
        out = []
        for i in idx:
            row = self.df.iloc[i]
            acts = [a for a in str(row["activities"]).split(",") if a]
            rec = {
                "track_id": row["track_id"],
                "track_name": row["track_name"],
                "artist_name": row["artist_name"],
                "genre": row["genre"],
                "emotion": row["emotion"],
                "album": row["album"],
                "release_date": row["release_date"],
                "explicit": bool(row["explicit"]),
                "popularity": int(row["popularity"]),
                "duration_sec": int(row["duration_sec"]),
                "tempo": round(float(row["tempo"]), 1),
                "danceability": round(float(row["danceability"]), 3),
                "energy": round(float(row["energy"]), 3),
                "valence": round(float(row["valence"]), 3),
                "acousticness": round(float(row["acousticness"]), 3),
                "language": str(row["language"]) if "language" in row else "english",
                "activities": [ACTIVITY_LABELS.get(a, a) for a in acts],
                "similar_tracks": [row["similar_1"], row["similar_2"], row["similar_3"]],
            }
            if scores is not None:
                rec["match_score"] = round(float(scores.get(i, 0.0)), 4)
            out.append(rec)
        return out

    # ------------------------------------------------------------------ #
    # Faceted filtering -> candidate index positions
    def _apply_filters(self, genres, moods, artists, activities, language: str = "mix") -> np.ndarray:
        mask = np.ones(len(self.df), dtype=bool)
        if genres:
            mask &= self.df["genre"].isin([g.lower() for g in genres]).to_numpy()
        if moods:
            mask &= self.df["emotion"].isin([m.lower() for m in moods]).to_numpy()
        if artists:
            mask &= self.df["artist_name"].isin(artists).to_numpy()
        if activities:
            want = set(activities)
            has_activity = self.df["activities"].apply(
                lambda s: bool(want & set(str(s).split(",")))
            ).to_numpy()
            mask &= has_activity
        if language and language != "mix" and "language" in self.df.columns:
            mask &= (self.df["language"] == language.lower()).to_numpy()
        return np.where(mask)[0]

    # ------------------------------------------------------------------ #
    # Search
    # ------------------------------------------------------------------ #
    def search(self, query: str, limit: int = 10) -> list[dict]:
        q = query.strip().lower()
        if not q:
            return []
        mask = (
            self.df["track_name"].str.lower().str.contains(q, regex=False, na=False)
            | self.df["artist_name"].str.lower().str.contains(q, regex=False, na=False)
        )
        idx = self.df.index[mask][:limit].tolist()
        return self._rows_to_records(idx)

    # ------------------------------------------------------------------ #
    # Preference + filter recommendations (main flow)
    # ------------------------------------------------------------------ #
    def recommend(
        self,
        preferences: dict[str, float] | None = None,
        genres: list[str] | None = None,
        moods: list[str] | None = None,
        artists: list[str] | None = None,
        activities: list[str] | None = None,
        language: str = "mix",
        limit: int = 24,
        popularity_weight: float = 0.15,
    ) -> list[dict]:
        candidates = self._apply_filters(genres, moods, artists, activities, language)
        if len(candidates) == 0:
            # Fallback: Relax strict filters and search across the entire language set
            candidates = self._apply_filters(None, None, None, None, language)

        # Sliders are removed, so we construct target features dynamically from matched filters.
        # Find tracks matching current filters (genres or moods or activities).
        filter_mask = np.zeros(len(self.df), dtype=bool)
        has_any_filter = False
        if genres:
            filter_mask |= self.df["genre"].isin([g.lower() for g in genres]).to_numpy()
            has_any_filter = True
        if moods:
            filter_mask |= self.df["emotion"].isin([m.lower() for m in moods]).to_numpy()
            has_any_filter = True
        if activities:
            want = set(activities)
            has_activity = self.df["activities"].apply(
                lambda s: bool(want & set(str(s).split(",")))
            ).to_numpy()
            filter_mask |= has_activity
            has_any_filter = True

        matched_indices = np.where(filter_mask)[0]
        if has_any_filter and len(matched_indices) > 0:
            # Use mean features of matching tracks as taste baseline
            target = self.df.iloc[matched_indices][NUMERIC_FEATURES].mean().to_dict()
        else:
            # Fallback to dataset mean
            target = self.df[NUMERIC_FEATURES].mean().to_dict()

        target_vec = self._scaler.transform(pd.DataFrame([target])[NUMERIC_FEATURES])[0]

        tag_text = " ".join((genres or []) + (moods or [])) or " ".join(self._tags.unique()[:50])
        tag_vec = self._vectorizer.transform([tag_text.lower()]).toarray()[0] * 1.5
        taste = np.hstack([target_vec, tag_vec]).reshape(1, -1)

        cand_matrix = self._feature_matrix[candidates]
        sims = cosine_similarity(taste, cand_matrix)[0]

        pop = self.df.iloc[candidates]["popularity"].to_numpy() / 100.0
        blended = (1 - popularity_weight) * sims + popularity_weight * pop

        order = np.argsort(blended)[::-1][:limit]
        top_positions = candidates[order]
        scores = {int(candidates[o]): float(blended[o]) for o in order}
        return self._rows_to_records([int(p) for p in top_positions], scores)

    # ------------------------------------------------------------------ #
    # Item-item similar tracks
    # ------------------------------------------------------------------ #
    def similar_to(self, track_id: str, limit: int = 12) -> list[dict]:
        if track_id not in self._id_to_pos:
            raise KeyError(track_id)
        pos = self._id_to_pos[track_id]
        sims = cosine_similarity(
            self._feature_matrix[pos].reshape(1, -1), self._feature_matrix
        )[0]
        sims[pos] = -1.0
        top = np.argsort(sims)[::-1][:limit]
        scores = {int(i): float(sims[i]) for i in top}
        return self._rows_to_records([int(i) for i in top], scores)

    # ------------------------------------------------------------------ #
    # Popular fallback
    # ------------------------------------------------------------------ #
    def popular(self, limit: int = 12, genre: str | None = None) -> list[dict]:
        df = self.df
        if genre:
            df = df[df["genre"] == genre.lower()]
        idx = df.sort_values("popularity", ascending=False).head(limit).index.tolist()
        return self._rows_to_records(idx)
