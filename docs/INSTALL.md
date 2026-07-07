# Installation Guide

## Prerequisites

- **Docker** (20.10+) and **Docker Compose** (v2 `docker compose` or v1 `docker-compose`).
- ~1 GB free disk for images.
- Ports **3000**, **8010**, and **5432** free on your host.

Verify Docker:

```bash
docker --version
docker compose version   # or: docker-compose --version
```

## 1. Get the code

```bash
git clone <your-public-repo-url> shelfmusic
cd shelfmusic
```

## 2. (Optional) configure

Defaults work out of the box. To override credentials or ports, copy the
example env file and edit it — Docker Compose picks it up automatically:

```bash
cp .env.example .env
```

| Variable            | Default      | Meaning                          |
|---------------------|--------------|----------------------------------|
| `POSTGRES_DB`       | `shelfmusic` | Database name                    |
| `POSTGRES_USER`     | `shelfmusic` | Database user                    |
| `POSTGRES_PASSWORD` | `shelfmusic` | Database password                |
| `POSTGRES_HOST`     | `db`         | DB host (the compose service)    |
| `POSTGRES_PORT`     | `5432`       | DB port                          |
| `DATASET_PATH`      | `/data/dataset.csv` | Seed CSV path (in container) |

## 3. Build and run

```bash
docker-compose up --build
```

What happens on first boot:

1. **db** starts and becomes healthy (`pg_isready`).
2. **backend** waits for the DB, creates the `tracks` table, seeds it from
   `data/dataset.csv` (~16,000 tracks), and fits the recommender.
3. **frontend** serves the built SPA and proxies `/api` to the backend.

When you see `Application startup complete`, open:

- App: **http://localhost:3000**
- API docs (Swagger): **http://localhost:8010/docs**

## 4. Stop / reset

```bash
# Stop (Ctrl-C if running in foreground), then:
docker-compose down

# Wipe the seeded database volume too (fresh reseed next time):
docker-compose down -v
```

## Regenerating the dataset (optional)

```bash
cd data
python prepare_dataset.py     # requires: pip install pandas numpy
```

## Using the real Kaggle dataset (optional)

Download the *Spotify Tracks Dataset* from Kaggle, ensure it has the same
columns as `data/dataset.csv`, save it as `data/dataset.csv`, then:

```bash
docker-compose down -v && docker-compose up --build
```

## Troubleshooting

- **Port already in use** — edit the `ports:` mappings in `docker-compose.yml`
  (e.g. change `3000:80` to `3000:80`).
- **Backend can't reach the DB** — the backend retries for ~60s on startup;
  if it still fails, run `docker-compose down -v` and try again.
- **Stale data after swapping the CSV** — the table only seeds when empty, so
  run `docker-compose down -v` to force a reseed.
