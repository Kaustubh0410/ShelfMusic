# Technical Documentation

## Overview

ShelfMusic is a hybrid recommender combining **content-based filtering** with a
**preference-driven taste vector**. All ML runs in-memory in the backend
process; it is fit once at startup from the `tracks` table.

## Data model

The `tracks` table (seeded from `data/dataset.csv`):

| Column             | Type    | Notes                                   |
|--------------------|---------|-----------------------------------------|
| track_id           | TEXT PK | stable id                               |
| track_name         | TEXT    |                                         |
| artist_name        | TEXT    |                                         |
| genre              | TEXT    | one of 12 genres                        |
| popularity         | INT     | 1–100                                   |
| duration_ms        | INT     |                                         |
| danceability       | FLOAT   | 0–1                                     |
| energy             | FLOAT   | 0–1                                     |
| valence            | FLOAT   | 0–1 (musical positivity)                |
| acousticness       | FLOAT   | 0–1                                     |
| instrumentalness   | FLOAT   | 0–1                                     |
| speechiness        | FLOAT   | 0–1                                     |
| liveness           | FLOAT   | 0–1                                     |
| tempo              | FLOAT   | BPM                                     |
| loudness           | FLOAT   | dB (negative)                           |

## Feature representation

For each track we build a vector by concatenating:

1. **Numeric audio features** — the 9 numeric columns above, scaled to `[0,1]`
   with `MinMaxScaler` so no single feature (e.g. tempo in BPM) dominates the
   distance metric.
2. **Genre component** — a `TfidfVectorizer` encoding of the genre string,
   multiplied by a `genre_weight` of **1.5**. This makes same-genre tracks
   cluster while still letting audio features differentiate within a genre.

```
feature_matrix = [ MinMaxScaled(numeric) | TFIDF(genre) * 1.5 ]
```

Because the dataset is small, the full **track×track cosine similarity matrix**
is precomputed once at fit time for instant item-item lookups.

## Recommendation strategies

### 1. Content-based item-item (`/api/tracks/{id}/similar`)

```
sims = cosine_similarity(feature_matrix)[seed]
sims[seed] = -1                # exclude the seed itself
top = argsort(sims)[::-1][:N]
```

Returns the N most similar tracks with their cosine scores as `match_score`.

### 2. Preference taste vector (`/api/recommend`)

The user's slider values overwrite the corresponding features of a synthetic
"mean track"; tempo/loudness stay at dataset means (the UI only steers 0–1
features). Preferred genres form the genre component:

```
target_vec  = scale(mean_track overwritten by slider values)
genre_vec   = TFIDF(" ".join(preferred_genres)) * 1.5
taste       = [ target_vec | genre_vec ]

sims        = cosine_similarity(taste, feature_matrix)
blended     = (1 - w) * sims + w * (popularity/100)   # w = 0.15
blended    += 0.05 for tracks whose genre is preferred # soft boost
```

Blending popularity handles cold-start / vague queries; the soft genre boost
nudges (rather than hard-filters) toward chosen genres.

### 3. Popularity fallback (`/api/popular`)

Simple `ORDER BY popularity DESC`, optionally filtered by genre.

## Backend structure

- `app/recommender.py` — `MusicRecommender` class: fit, search, `similar_to`,
  `recommend_from_preferences`, `popular`. Pure Python/scikit-learn, no web deps.
- `app/database.py` — connection with retry (waits for the DB container),
  schema creation, idempotent seeding, and DataFrame loading via SQLAlchemy.
- `app/schemas.py` — Pydantic request/response models with validation
  (e.g. slider values constrained to `[0,1]`).
- `app/main.py` — FastAPI routes + a `lifespan` handler that initializes the DB
  and fits the recommender before the app serves traffic.

## Frontend structure

- `src/api.ts` — typed `fetch` client; all calls hit the relative `/api` path.
- `src/App.tsx` — three modes (taste / similar / popular), state, debounced
  search.
- `src/FeatureEqualizer.tsx` — renders each track's audio features as bars.
- nginx (`nginx.conf`) serves the built SPA and reverse-proxies `/api` to the
  backend, so the browser uses a single origin (clean CORS).

## Container topology

Defined in `docker-compose.yml`:

- **db** — `postgres:16-alpine`, persistent named volume `db_data`, healthcheck
  via `pg_isready`.
- **backend** — built from `backend/Dockerfile`, `depends_on` db health, mounts
  `./data` read-only for seeding, healthcheck hits `/api/health`.
- **frontend** — multi-stage build (Vite → nginx), depends on backend.

All three join the custom bridge network **`shelfnet`**; services address each
other by name (`db`, `backend`) via Docker's internal DNS.

## Extending

- **Collaborative filtering:** add a `ratings` table and matrix factorization,
  then blend its scores into `recommend_from_preferences`.
- **Larger data:** for big datasets, replace the precomputed similarity matrix
  with an approximate-nearest-neighbour index (e.g. FAISS/Annoy).
- **Real audio features:** swap `data/dataset.csv` for the Kaggle export.
