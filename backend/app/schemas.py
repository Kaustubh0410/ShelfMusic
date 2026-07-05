"""Pydantic request/response models for the API layer."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Track(BaseModel):
    """A single track returned to the frontend."""

    track_id: str
    track_name: str
    artist_name: str
    genre: str
    emotion: str
    album: str
    release_date: str
    explicit: bool
    popularity: int
    duration_sec: int
    tempo: float
    danceability: float
    energy: float
    valence: float
    acousticness: float
    activities: list[str] = Field(default_factory=list)
    similar_tracks: list[str] = Field(default_factory=list)
    match_score: float | None = None


class Preferences(BaseModel):
    """User-supplied taste sliders (all 0..1)."""

    danceability: float = Field(0.5, ge=0.0, le=1.0)
    energy: float = Field(0.5, ge=0.0, le=1.0)
    valence: float = Field(0.5, ge=0.0, le=1.0, description="Musical positivity / mood")
    acousticness: float = Field(0.5, ge=0.0, le=1.0)
    instrumentalness: float = Field(0.5, ge=0.0, le=1.0)


class RecommendRequest(BaseModel):
    """Payload for faceted preference-based recommendations."""

    preferences: Preferences = Preferences()
    genres: list[str] = Field(default_factory=list)
    moods: list[str] = Field(default_factory=list)
    artists: list[str] = Field(default_factory=list)
    activities: list[str] = Field(default_factory=list)
    limit: int = Field(12, ge=1, le=50)


class RecommendResponse(BaseModel):
    strategy: str
    count: int
    results: list[Track]


class Activity(BaseModel):
    key: str
    label: str


class FacetsResponse(BaseModel):
    track_count: int
    genres: list[str]
    moods: list[str]
    artists: list[str]
    activities: list[Activity]
