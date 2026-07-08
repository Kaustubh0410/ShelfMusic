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
| genre              | TEXT    | comma-separated tags, e.g. "rock,pop"; ~3,100 distinct strings, ~47% of rows have more than one tag |
| language           | TEXT    | "hindi" or "english" (see classification below) |
| popularity         | INT     | 0–98                                    |
| duration_sec       | INT     |                                         |
| danceability       | FLOAT   | 0–1                                     |
| energy             | FLOAT   | 0–1                                     |
| valence             | FLOAT   | 0–1 (musical positivity)                |
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

Similarity is **not** precomputed as a full track×track matrix — for 16,000+
tracks that would be a large, mostly-wasted matrix, since most requests only
need one row of it. Instead, `similar_to()` computes cosine similarity
on-demand between a single seed track's vector and every other track
(`cosine_similarity(seed_vector, feature_matrix)`), which keeps memory flat
and is still fast enough for interactive use at this dataset size.

## Recommendation strategies

### 1. Content-based item-item (`/api/tracks/{id}/similar`)

```
sims = cosine_similarity(feature_matrix)[seed]
sims[seed] = -1                # exclude the seed itself
top = argsort(sims)[::-1][:N]
```

Returns the N most similar tracks with their cosine scores as `match_score`.

### 2. Faceted taste vector (`/api/recommend`)

The user's card selections (moods, genres, activities, language) first **filter**
the catalogue to the matching tracks. Instead of reading slider values, the
taste vector is built **dynamically** from the average audio features of those
matching tracks, combined with a TF-IDF tag vector of the chosen genres/moods:

```
candidates  = filter(tracks, moods, genres, activities, language)
target_vec  = scale(mean audio features of candidates)
tag_vec     = TFIDF(" ".join(selected genres + moods)) * 1.5
taste       = [ target_vec | tag_vec ]

sims        = cosine_similarity(taste, candidate_matrix)
blended     = (1 - w) * sims + w * (popularity/100)   # w = 0.15
```

If a filter combination matches nothing, the engine relaxes the mood/genre/
activity filters (keeping language) so the user still gets sensible results
rather than an empty screen.

The backend still accepts an optional `preferences` object (from an earlier
slider-based UI) for backward compatibility, but the current card UI drives the
dynamic path above.

### Search ranking (`/api/search`)

Search matches on substring in either the track name or artist name, then
ranks hits by relevance rather than dataset order: title-starts-with (3) >
title-contains (2) > artist-starts-with (1.5) > artist-contains (1), with
popularity as a tiebreaker. This keeps a query like "sabrina" surfacing
Sabrina Carpenter first instead of an unrelated track that happens to contain
the substring somewhere in a long collaboration credit.

### Genre matching

Genres are stored as comma-separated multi-tag strings (e.g. `"rock,pop,indie
rock"`) rather than a single clean label — about 47% of rows have more than
one tag. Filtering therefore checks whether a selected genre appears as **any**
one of a track's comma-separated tags, not whether the whole genre field
equals the selection exactly. An exact-match approach would silently miss the
majority of multi-tagged tracks (e.g. only ~100 of the ~2,600 tracks genuinely
tagged "rock" have *just* "rock" as their only tag).

### Shuffle

The taste tab's Shuffle button re-requests `/api/recommend` with `shuffle=true`.
Instead of deterministically returning the top-N by blended score, the engine
takes a wider pool of strong matches (top `3×limit`) and randomly samples
`limit` tracks from it — so results stay relevant to the current filters but
vary between presses. Non-shuffle requests (e.g. the auto-refresh on filter
change) remain fully deterministic.

### Language classification (data prep)

The Kaggle dataset has no language field, so `data/prepare_dataset.py` classifies
each track as **hindi** or **english** using two signals: (1) genuine Indian
genre tags (filmi, ghazal, sufi, indipop, ...), and (2) a set of known Indian
artist names matched on the **full** name (matching full names rather than bare
surnames avoids false positives such as "Luke Sital-Singh"). This is a heuristic:
the dataset is predominantly Western, so the honest Hindi count is small, and the
classifier is tuned to avoid false positives rather than maximise recall.

### 3. Top Charts (`/api/popular`)

The Top Charts tab renders this as a ranked leaderboard: results are sorted by
`popularity DESC` and displayed with a rank badge (#1, #2, #3…). No genre
filtering — that's already covered by the taste tab, so Top Charts stays a
single, simple "what's popular overall" view rather than duplicating it.

## Backend structure

- `app/recommender.py` — `MusicRecommender` class: fit, search, `similar_to`,
  `recommend`, `popular`. Pure Python/scikit-learn, no web deps.
- `app/database.py` — connection with retry (waits for the DB container),
  schema creation, idempotent seeding, and DataFrame loading via SQLAlchemy.
- `app/schemas.py` — Pydantic request/response models with validation
  (e.g. `language` and `limit` bounds on the recommend request).
- `app/main.py` — FastAPI routes + a `lifespan` handler that initializes the DB
  and fits the recommender before the app serves traffic.

## Frontend structure

- `src/api.ts` — typed `fetch` client; all calls hit the relative `/api` path.
- `src/App.tsx` — three modes (taste / similar / popular), state, debounced
  search.
- `src/FeatureEqualizer.tsx` — renders each track's audio features as bars.
- `src/AlbumCover.tsx` — fetches album art from the iTunes Search API at display
  time, with a generated SVG fallback when a track has no match.
- `src/TrackModal.tsx` — the track detail modal.
- `src/MultiSelect.tsx` — a multi-select dropdown built during an earlier
  design iteration; superseded by the card grids in `App.tsx` and not
  currently imported. Kept in the tree rather than deleted.
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
  then blend its scores into `recommend`.
- **Larger data:** for big datasets, replace the precomputed similarity matrix
  with an approximate-nearest-neighbour index (e.g. FAISS/Annoy).
- **Real audio features:** swap `data/dataset.csv` for the Kaggle export.