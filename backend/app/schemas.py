"""Pydantic request/response models for the API layer."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Track(BaseModel):
    """A single track returned to the frontend."""

    track_id: str
    track_name: str
    artist_name: str
    genre: str
    popularity: int
    duration_ms: int
    danceability: float
    energy: float
    valence: float
    acousticness: float
    tempo: float
    match_score: float | None = None


class Preferences(BaseModel):
    """User-supplied taste sliders (all 0..1) plus preferred genres."""

    danceability: float = Field(0.5, ge=0.0, le=1.0)
    energy: float = Field(0.5, ge=0.0, le=1.0)
    valence: float = Field(0.5, ge=0.0, le=1.0, description="Musical positivity / mood")
    acousticness: float = Field(0.5, ge=0.0, le=1.0)
    instrumentalness: float = Field(0.5, ge=0.0, le=1.0)


class RecommendRequest(BaseModel):
    """Payload for preference-based recommendations."""

    preferences: Preferences = Preferences()
    genres: list[str] = Field(default_factory=list)
    limit: int = Field(12, ge=1, le=50)


class RecommendResponse(BaseModel):
    strategy: str
    count: int
    results: list[Track]


class MetaResponse(BaseModel):
    track_count: int
    genres: list[str]
