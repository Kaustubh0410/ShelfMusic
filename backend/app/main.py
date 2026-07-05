"""
ShelfMusic backend - FastAPI application (Kaggle 900K-Spotify edition).

Endpoints:
  GET  /api/health                  liveness probe
  GET  /api/facets                  genres, moods, artists, activities for UI
  GET  /api/search?q=...            search tracks by name/artist
  POST /api/recommend               faceted preference recommendations
  GET  /api/tracks/{id}/similar     item-item similar tracks
  GET  /api/popular                 popularity fallback

At startup the app initializes the database (schema + seed), loads all
tracks into a DataFrame, and fits the recommender.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app import database
from app.recommender import MusicRecommender
from app.schemas import (
    FacetsResponse,
    RecommendRequest,
    RecommendResponse,
    Track,
)

state: dict[str, MusicRecommender | None] = {"recommender": None}


@asynccontextmanager
async def lifespan(app: FastAPI):
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
    description="Faceted music recommender over the Kaggle 900K-Spotify dataset.",
    version="2.0.0",
    lifespan=lifespan,
)

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
    return {"status": "ok" if state["recommender"] is not None else "starting"}


@app.get("/api/facets", response_model=FacetsResponse)
def facets() -> FacetsResponse:
    return FacetsResponse(**_engine().facets())


@app.get("/api/search", response_model=list[Track])
def search(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
) -> list[Track]:
    return [Track(**r) for r in _engine().search(q, limit=limit)]


@app.post("/api/recommend", response_model=RecommendResponse)
def recommend(req: RecommendRequest) -> RecommendResponse:
    rec = _engine()
    results = rec.recommend(
        preferences=req.preferences.model_dump() if req.preferences else None,
        genres=req.genres,
        moods=req.moods,
        artists=req.artists,
        activities=req.activities,
        language=req.language,
        limit=req.limit,
    )
    return RecommendResponse(
        strategy="faceted_taste_vector",
        count=len(results),
        results=[Track(**r) for r in results],
    )



@app.get("/api/tracks/{track_id}/similar", response_model=RecommendResponse)
def similar(track_id: str, limit: int = Query(12, ge=1, le=50)) -> RecommendResponse:
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


@app.get("/api/popular", response_model=RecommendResponse)
def popular(
    limit: int = Query(12, ge=1, le=50),
    genre: str | None = Query(None),
) -> RecommendResponse:
    rec = _engine()
    results = rec.popular(limit=limit, genre=genre)
    return RecommendResponse(
        strategy="popularity",
        count=len(results),
        results=[Track(**r) for r in results],
    )
