"""
Unit tests for the recommendation engine.

These test the recommender in isolation against the CSV dataset, so they
run without a database. Run with:  pytest  (from the backend/ directory).
"""

import os

import pandas as pd
import pytest

from app.recommender import MusicRecommender

DATA = os.path.join(os.path.dirname(__file__), "..", "..", "data", "dataset.csv")


@pytest.fixture(scope="module")
def rec() -> MusicRecommender:
    df = pd.read_csv(DATA)
    return MusicRecommender(df)


def test_track_count_and_genres(rec):
    assert rec.track_count() > 0
    assert len(rec.genres()) >= 5


def test_search_finds_known_track(rec):
    hits = rec.search("Wildfire", limit=5)
    assert len(hits) >= 1
    assert all("wildfire" in h["track_name"].lower() for h in hits)


def test_similar_excludes_seed_and_returns_scores(rec):
    seed_id = rec.df.iloc[0]["track_id"]
    sims = rec.similar_to(seed_id, limit=5)
    assert len(sims) == 5
    # seed must not recommend itself
    assert all(s["track_id"] != seed_id for s in sims)
    # scores present and sorted descending
    scores = [s["match_score"] for s in sims]
    assert scores == sorted(scores, reverse=True)


def test_similar_unknown_id_raises(rec):
    with pytest.raises(KeyError):
        rec.similar_to("does-not-exist")


def test_preferences_respect_energy(rec):
    """High-energy preference should surface high-energy tracks on average."""
    high = rec.recommend_from_preferences(
        {"danceability": 0.5, "energy": 0.95, "valence": 0.5,
         "acousticness": 0.05, "instrumentalness": 0.2},
        genres=["metal", "electronic"], limit=10,
    )
    avg_energy = sum(t["energy"] for t in high) / len(high)
    assert avg_energy > 0.6


def test_genre_preference_filters(rec):
    recs = rec.recommend_from_preferences(
        {"danceability": 0.5, "energy": 0.5, "valence": 0.5,
         "acousticness": 0.5, "instrumentalness": 0.3},
        genres=["classical"], limit=8,
    )
    # classical should dominate the results given the strong genre signal
    classical = sum(1 for t in recs if t["genre"] == "classical")
    assert classical >= len(recs) // 2


def test_popular_is_sorted(rec):
    pop = rec.popular(limit=10)
    pops = [t["popularity"] for t in pop]
    assert pops == sorted(pops, reverse=True)
