"""Unit tests for the faceted recommendation engine (no DB required)."""
import os
import pandas as pd
import pytest
from app.recommender import MusicRecommender

DATA = os.path.join(os.path.dirname(__file__), "..", "..", "data", "dataset.csv")


@pytest.fixture(scope="module")
def rec() -> MusicRecommender:
    return MusicRecommender(pd.read_csv(DATA))


def test_facets(rec):
    f = rec.facets()
    assert f["track_count"] > 0
    assert len(f["genres"]) >= 3
    assert len(f["moods"]) >= 2
    assert len(f["activities"]) == 9


def test_search(rec):
    hits = rec.search(rec.df.iloc[0]["track_name"][:3], limit=5)
    assert isinstance(hits, list)


def test_recommend_respects_genre_filter(rec):
    # Genres are stored as comma-separated multi-tag strings (e.g.
    # "rock,pop,indie rock"), so we pick ONE clean tag that actually occurs
    # standalone in the data, and assert it's present among each result's
    # tags rather than requiring an exact full-string match (which would
    # only ever match tracks with that exact single tag and nothing else).
    single_tag_genres = rec.df["genre"][~rec.df["genre"].str.contains(",", na=False)]
    g = single_tag_genres.iloc[0]
    recs = rec.recommend(
        preferences=dict(danceability=0.5, energy=0.5, valence=0.5, acousticness=0.5, instrumentalness=0.2),
        genres=[g], limit=8)
    assert len(recs) > 0
    assert all(g in [t.strip() for t in rec_track["genre"].split(",")] for rec_track in recs)


def test_recommend_respects_mood_filter(rec):
    m = rec.df["emotion"].iloc[0]
    recs = rec.recommend(
        preferences=dict(danceability=0.5, energy=0.5, valence=0.5, acousticness=0.5, instrumentalness=0.2),
        moods=[m], limit=8)
    assert all(t["emotion"] == m for t in recs)


def test_similar_excludes_seed(rec):
    seed = rec.df.iloc[0]["track_id"]
    sims = rec.similar_to(seed, limit=5)
    assert all(s["track_id"] != seed for s in sims)
    scores = [s["match_score"] for s in sims]
    assert scores == sorted(scores, reverse=True)


def test_similar_unknown_raises(rec):
    with pytest.raises(KeyError):
        rec.similar_to("nope")


def test_popular_sorted(rec):
    pop = rec.popular(limit=10)
    pops = [t["popularity"] for t in pop]
    assert pops == sorted(pops, reverse=True)