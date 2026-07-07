# Usage Guide

Open **http://localhost:3000** after `docker compose up --build`.

The app has three modes, selectable from the tabs at the top.

## 1. Tune by taste

Build the *vibe* you want through a simple card-based flow, then let the engine
find matching tracks. Results refresh automatically as you make selections.

1. **Step 1 — Mood:** tap one or more mood cards (Joy, Sadness, Love, Anger,
   Fear, Surprise).
2. **Step 2 — Genres:** pick any genres (Pop, Rock, Jazz, Filmi/Bollywood,
   Ghazal, Sufi, and more), or leave it open.
3. **Step 3 — Activity / Vibe:** match the music to what you are doing (Party,
   Work & Study, Exercise, Driving, ...).
4. **Step 4 — Language:** choose Hindi / Bollywood, English / International, or
   a Mix.

The engine filters tracks to your selections, builds a taste vector from the
average audio features of the matching tracks, and ranks by cosine similarity
with a small popularity blend. Each card shows a **match %** and a mini
equalizer of its features.

**Example:** Mood *Joy* + genre *Rock* + activity *Party* + language *English* →
upbeat, energetic English rock rises to the top.

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

This is the browse-by-popularity view.

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

- Combine mood, genre, activity, and language for the most targeted results.
- Match scores are relative within a result set, not absolute quality ratings.
- The API is open at **http://localhost:8010/docs** if you want to call it
  directly.
