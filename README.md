# 🎧 ShelfMusic — a hybrid music recommender

ShelfMusic recommends songs by **listening to the audio, not the hype**. You
either tune a set of sliders that describe how you want to feel (energy, mood,
danceability, acoustic-ness) or pick a track you already love, and the engine
finds the closest matches in audio-feature space.

It is a fully containerized, plug-and-play project: one command brings up a
React frontend, a FastAPI backend, and a PostgreSQL database, each in its own
container on a shared Docker network.

```bash
docker-compose up --build
```

Then open **http://localhost:3000**.

---

## Table of contents

- [Why this project](#why-this-project)
- [What makes it unique](#what-makes-it-unique)
- [Architecture](#architecture)
- [Tech stack](#tech-stack)
- [Data source](#data-source)
- [How to install](#how-to-install)
- [How to use](#how-to-use)
- [API reference](#api-reference)
- [How the recommender works](#how-the-recommender-works)
- [Project layout](#project-layout)
- [Running tests](#running-tests)
- [Implementation process](#implementation-process)

---

## Why this project

Most "recommendations" people see are driven by popularity and marketing. I
wanted to build something that recommends on the **intrinsic properties of the
music itself** — its tempo, energy, how acoustic or danceable it is — so the
suggestions reflect *how a song actually sounds* rather than how many streams it
already has. A music recommender is also a clean, self-contained way to
demonstrate the full stack the brief asks for: a data pipeline, a machine-
learning core, a separated API, a database, and a real UI.

## What makes it unique

- **Two complementary recommendation modes in one app.** A *content-based*
  item-to-item engine ("more like this track") **and** a *preference-driven*
  taste-vector engine ("build me something that feels like this"). Most demo
  recommenders ship only one.
- **Audio features are the interface.** The signature UI element is a live
  **equalizer**: every result card renders its danceability / energy / mood /
  acousticness as spectrum bars, so you can *see* why a track was matched.
- **Genre similarity is folded into the vector space via TF-IDF**, so
  recommendations balance "same genre" against "similar sound" instead of
  hard-filtering by genre.
- **Truly plug-and-play.** A synthesized, genre-consistent dataset ships in the
  repo, so `docker-compose up` works with zero external downloads or API keys.
  Swap in the real Kaggle CSV any time (see [Data source](#data-source)).

## Architecture

```
                         ┌─────────────────────────────────────────┐
   Browser  ──http──▶    │  frontend (nginx + React/TS SPA) :8080   │
                         │   • serves the built SPA                 │
                         │   • proxies /api ──▶ backend             │
                         └───────────────┬─────────────────────────┘
                                         │  /api (HTTP, Docker DNS)
                         ┌───────────────▼─────────────────────────┐
                         │  backend (FastAPI + uvicorn) :8000       │
                         │   • REST API                            │
                         │   • scikit-learn recommender (in-memory)│
                         └───────────────┬─────────────────────────┘
                                         │  SQL (psycopg2 / SQLAlchemy)
                         ┌───────────────▼─────────────────────────┐
                         │  db (PostgreSQL 16) :5432                │
                         │   • tracks table, seeded on first run   │
                         └─────────────────────────────────────────┘

        All three services share the custom bridge network `shelfnet`.
```

The frontend and backend are **logically separated** and communicate **only
through the REST API**. In production the browser talks to a single origin
(the nginx frontend), which reverse-proxies `/api` to the backend — clean CORS,
no hardcoded backend host.

## Tech stack

| Layer     | Technology                                             |
|-----------|--------------------------------------------------------|
| Frontend  | React 18 + **TypeScript**, Vite, nginx (static serving)|
| Backend   | **Python**, FastAPI, uvicorn, Pydantic                 |
| ML / data | scikit-learn (TF-IDF, cosine similarity), pandas, numpy|
| Database  | PostgreSQL 16                                          |
| Infra     | Docker, docker-compose, custom bridge network          |

## Data source

The project uses the **Kaggle "900K Spotify" dataset** by *devdope*:
https://www.kaggle.com/datasets/devdope/900k-spotify

Each track includes metadata (artist, song, album, genre, release date),
an **emotion/mood** label, nine **"good for" activity** flags (party,
work/study, exercise, driving, ...), and audio features (energy,
danceability, positiveness/valence, acousticness, tempo, loudness, etc.).

**Preparing the data (required once).** The raw file is ~1.1 GB / ~900K
rows — far too large to load into memory or commit to Git. `data/prepare_dataset.py`
cleans it (parsing `-6.85db` -> -6.85, `03:47` -> seconds, scaling 0-100
features to 0-1) and takes a **genre-stratified sample** (default 15,000
tracks) into a compact `data/dataset.csv` that the app seeds from:

```bash
pip install kagglehub pandas numpy
python -c "import kagglehub; print(kagglehub.dataset_download('devdope/900k-spotify'))"
# then point --input at the spotify_dataset.csv inside that path:
python data/prepare_dataset.py --input "<path>/spotify_dataset.csv" --output data/dataset.csv --sample 15000
```

The committed `data/dataset.csv` is the small sampled file; the raw
1.1 GB CSV and JSONs are git-ignored.

## How to install

See **[docs/INSTALL.md](docs/INSTALL.md)** for the full guide. The short version:

**Prerequisites:** Docker and Docker Compose.

```bash
git clone <your-public-repo-url> shelfmusic
cd shelfmusic
docker-compose up --build
```

That's it. On first boot the backend waits for PostgreSQL, creates the `tracks`
table, seeds it from `data/dataset.csv`, and fits the recommender.

Open **http://localhost:3000**.

## How to use

See **[docs/USAGE.md](docs/USAGE.md)** for a walkthrough with examples. Briefly:

1. **Tune by taste** — drag the sliders (energy, danceability, mood, acoustic,
   instrumental), optionally pick genres, and hit *Get recommendations*.
2. **Find similar** — search a track by name or artist, click it, and get its
   nearest neighbours in audio space.
3. **Popular** — browse the most popular tracks overall or by genre.

Every result card shows a mini equalizer of its audio features and (where
applicable) a match score.

## API reference

Base URL (inside the app): `/api` — proxied to the backend. Interactive docs are
available at **http://localhost:8000/docs** (FastAPI's auto-generated Swagger UI).

| Method | Path                          | Purpose                                   |
|--------|-------------------------------|-------------------------------------------|
| GET    | `/api/health`                 | Liveness probe                            |
| GET    | `/api/meta`                   | Track count + available genres            |
| GET    | `/api/search?q=`              | Search tracks by name/artist              |
| GET    | `/api/tracks/{id}/similar`    | Content-based similar tracks              |
| POST   | `/api/recommend`              | Preference/taste-vector recommendations   |
| GET    | `/api/popular?genre=`         | Popularity-ranked fallback                |

Example:

```bash
curl -X POST http://localhost:8000/api/recommend \
  -H "Content-Type: application/json" \
  -d '{"preferences":{"energy":0.9,"danceability":0.6,"valence":0.4,
       "acousticness":0.05,"instrumentalness":0.3},
       "genres":["metal","electronic"],"limit":5}'
```

## How the recommender works

See **[docs/TECHNICAL.md](docs/TECHNICAL.md)** for the deep dive. In summary:

Each track becomes a vector of **normalized audio features** concatenated with a
**TF-IDF encoding of its genre** (genre weighted so same-genre tracks cluster
without overwhelming the audio signal).

- **Similar tracks:** cosine similarity between the seed track's vector and every
  other track; return the top-N (excluding the seed).
- **Preference recommendations:** build a synthetic *taste vector* from the
  slider values + preferred genres, cosine-rank all tracks against it, and blend
  in normalized popularity so cold-start queries still surface known tracks.

## Project layout

```
shelfmusic/
├── docker-compose.yml         # orchestrates db + backend + frontend
├── README.md
├── .env.example
├── data/
│   ├── dataset.csv            # seed data (generated; Kaggle-compatible schema)
│   └── prepare_dataset.py    # regenerates dataset.csv
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py            # FastAPI app + routes
│   │   ├── recommender.py     # scikit-learn recommendation engine
│   │   ├── database.py        # PostgreSQL schema + seeding + load
│   │   └── schemas.py         # Pydantic models
│   └── tests/
│       └── test_recommender.py
├── frontend/
│   ├── Dockerfile             # multi-stage: vite build -> nginx
│   ├── nginx.conf             # serves SPA, proxies /api
│   ├── package.json
│   └── src/
│       ├── App.tsx            # UI + modes
│       ├── FeatureEqualizer.tsx
│       ├── api.ts             # typed API client
│       └── styles.css
└── docs/
    ├── INSTALL.md
    ├── USAGE.md
    └── TECHNICAL.md
```

## Running tests

The recommender has a unit-test suite that runs without a database:

```bash
cd backend
pip install -r requirements.txt pytest
pytest
```

## Implementation process

1. **Data** — defined a Kaggle-compatible schema and a generator that produces
   genre-consistent audio features, so the project is reproducible and needs no
   API keys.
2. **Recommender** — built and validated the content-based + preference engines
   in isolation with unit tests.
3. **Database** — added an idempotent PostgreSQL layer that seeds on first run.
4. **API** — wrapped the engine in FastAPI with typed request/response models
   and a startup lifespan that fits the model once.
5. **Frontend** — built a React/TypeScript SPA with the equalizer motif and the
   three recommendation modes, talking to the API through a typed client.
6. **Containers** — Dockerized each service and wired them together on a custom
   network with health checks and first-run seeding.

---

*ShelfMusic — training project. Data: Spotify-style audio features (see above).*
