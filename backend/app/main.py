"""
ShelfMusic backend — FastAPI application.

Exposes a REST API the React frontend consumes:

  GET  /api/health                  liveness probe
  GET  /api/meta                    dataset genres + track count
  GET  /api/search?q=...            search tracks by name/artist
  GET  /api/tracks/{id}/similar     item-item similar tracks
  POST /api/recommend               preference-based recommendations
  GET  /api/popular                 popularity fallback

At startup the app initializes the database (creates schema + seeds the
dataset), loads all tracks into a DataFrame, and fits the recommender.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app import database
from app.recommender import MusicRecommender
from app.schemas import (
    MetaResponse,
    RecommendRequest,
    RecommendResponse,
    Track,
)

# Populated on startup.
state: dict[str, MusicRecommender | None] = {"recommender": None}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB and fit the recommender before serving requests."""
    print("[startup] initializing database ...")
    database.init_db()
    print("[startup] loading tracks ...")
    df = database.load_tracks_dataframe()
    print(f"[startup] fitting recommender on {len(df)} tracks ...")
    state["recommender"] = MusicRecommender(df)
    print("[startup] ready.")
    yield
    state["recommender"] = None


app = FastAPI(
    title="ShelfMusic API",
    description="Hybrid music recommendation service (content-based + preference scoring).",
    version="1.0.0",
    lifespan=lifespan,
)

# The frontend runs on a separate origin (its own container / port),
# so CORS must allow it. Kept permissive for the training/demo context.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _engine() -> MusicRecommender:
    rec = state["recommender"]
    if rec is None:
        raise HTTPException(status_code=503, detail="Recommender not ready yet.")
    return rec


@app.get("/api/health")
def health() -> dict[str, str]:
    """Liveness probe used by Docker healthcheck and the frontend."""
    ready = state["recommender"] is not None
    return {"status": "ok" if ready else "starting"}


@app.get("/api/meta", response_model=MetaResponse)
def meta() -> MetaResponse:
    """Return available genres and total track count for UI controls."""
    rec = _engine()
    return MetaResponse(track_count=rec.track_count(), genres=rec.genres())


@app.get("/api/search", response_model=list[Track])
def search(
    q: str = Query(..., min_length=1, description="Track or artist name substring"),
    limit: int = Query(20, ge=1, le=50),
) -> list[Track]:
    """Search tracks by name or artist for the 'find similar' flow."""
    rec = _engine()
    return [Track(**r) for r in rec.search(q, limit=limit)]


@app.get("/api/tracks/{track_id}/similar", response_model=RecommendResponse)
def similar(track_id: str, limit: int = Query(10, ge=1, le=50)) -> RecommendResponse:
    """Return tracks similar to a seed track (content-based item-item)."""
    rec = _engine()
    try:
        results = rec.similar_to(track_id, limit=limit)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown track_id: {track_id}")
    return RecommendResponse(
        strategy="content_based_similarity",
        count=len(results),
        results=[Track(**r) for r in results],
    )


@app.post("/api/recommend", response_model=RecommendResponse)
def recommend(req: RecommendRequest) -> RecommendResponse:
    """Return recommendations from user taste sliders + preferred genres."""
    rec = _engine()
    results = rec.recommend_from_preferences(
        preferences=req.preferences.model_dump(),
        genres=req.genres,
        limit=req.limit,
    )
    return RecommendResponse(
        strategy="preference_taste_vector",
        count=len(results),
        results=[Track(**r) for r in results],
    )


@app.get("/api/popular", response_model=RecommendResponse)
def popular(
    limit: int = Query(12, ge=1, le=50),
    genre: str | None = Query(None),
) -> RecommendResponse:
    """Popularity-ranked fallback, optionally filtered by genre."""
    rec = _engine()
    results = rec.popular(limit=limit, genre=genre)
    return RecommendResponse(
        strategy="popularity",
        count=len(results),
        results=[Track(**r) for r in results],
    )
