# Usage Guide

Open **http://localhost:8080** after `docker-compose up --build`.

The app has three modes, selectable from the tabs at the top.

## 1. Tune by taste

Shape the *sound* you want, then let the engine find matching tracks.

1. Drag the sliders (each is 0–1):
   - **Energy** — intensity and power.
   - **Danceability** — how suited to dancing (steady rhythm, strong beat).
   - **Mood / positivity** — musical *valence* (happy/bright vs. dark/sad).
   - **Acoustic feel** — acoustic vs. produced/electric.
   - **Instrumental** — likelihood the track has no vocals.
2. (Optional) Tap **genre chips** to bias toward those genres.
3. Click **Get recommendations**.

Results are ranked by how closely each track's audio matches your taste vector,
with a small popularity blend. Each card shows a **match %** and a mini
equalizer of its features.

**Example:** Energy `0.90`, Acoustic `0.05`, genres *metal* + *electronic* →
high-intensity, produced tracks rise to the top.

## 2. Find similar

Start from a track you already like.

1. Type a song or artist name in the search box (min. 2 characters).
2. Pick a result from the dropdown.
3. The grid fills with its **nearest neighbours in audio space** (content-based
   similarity), each with a similarity score.

You can also hit **"more like this →"** on any result card to pivot to that
track's neighbours.

## 3. Popular

Browse without any input.

- Tap **all** for the most popular tracks overall, or
- Tap a **genre** chip for the most popular tracks in that genre.

This is the cold-start / fallback view.

## Reading a result card

```
┌─────────────────────────────┐
│ [GENRE]              92%     │  ← genre tag + match score
│ Track Name                  │
│ Artist Name                 │
│ ▁▃▅▂  (DNC NRG MOOD ACO)    │  ← audio-feature equalizer
│ 3:24 · pop 71   more like → │  ← duration · popularity · pivot
└─────────────────────────────┘
```

## Tips

- Combine sliders **and** genres for the most targeted results.
- Match scores are relative within a result set, not absolute quality ratings.
- The API is open at **http://localhost:8000/docs** if you want to call it
  directly.
