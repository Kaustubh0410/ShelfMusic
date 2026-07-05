# Project Changes Summary

This document summarizes all modifications made to the **ShelfMusic** recommendation stack. The changes remove the audio feature sliders, introduce a step-by-step card selection UI, integrate a large blended Hindi/English dataset, and fetch real track cover banners via the iTunes Search API.

---

## 📊 Summary of Modified Files

| Component | File Path | Type | Key Changes |
| :--- | :--- | :--- | :--- |
| **Data** | [data/prepare_dataset.py](file:///d:/shelfmusic-v2/shelfmusic/data/prepare_dataset.py) | `MODIFY` | Classify tracks as Hindi/English; sample all Hindi tracks + 18k English tracks. |
| **Data** | [data/dataset.csv](file:///d:/shelfmusic-v2/shelfmusic/data/dataset.csv) | `MODIFY` | Re-generated dataset containing **28,961 tracks** (10,291 Hindi + 18,670 English). |
| **Backend** | [backend/app/database.py](file:///d:/shelfmusic-v2/shelfmusic/backend/app/database.py) | `MODIFY` | Added `language` column to PostgreSQL schema and seeding scripts. |
| **Backend** | [backend/app/schemas.py](file:///d:/shelfmusic-v2/shelfmusic/backend/app/schemas.py) | `MODIFY` | Added `language` to Pydantic models; increased recommendation limit to 24. |
| **Backend** | [backend/app/recommender.py](file:///d:/shelfmusic-v2/shelfmusic/backend/app/recommender.py) | `MODIFY` | Added language filtering; calculates taste vectors dynamically from selected cards. |
| **Backend** | [backend/app/main.py](file:///d:/shelfmusic-v2/shelfmusic/backend/app/main.py) | `MODIFY` | Passed language request parameter from FastAPI route to recommender. |
| **Frontend** | [frontend/src/api.ts](file:///d:/shelfmusic-v2/shelfmusic/frontend/src/api.ts) | `MODIFY` | Added `language` fields to TypeScript interfaces and payload models. |
| **Frontend** | [frontend/src/AlbumCover.tsx](file:///d:/shelfmusic-v2/shelfmusic/frontend/src/AlbumCover.tsx) | `MODIFY` | Integrated iTunes Search API to fetch live track banners with cache and SVG fallback. |
| **Frontend** | [frontend/src/App.tsx](file:///d:/shelfmusic-v2/shelfmusic/frontend/src/App.tsx) | `MODIFY` | Removed sliders; created a 4-step card selection panel with auto-fetching. |
| **Frontend** | [frontend/src/styles.css](file:///d:/shelfmusic-v2/shelfmusic/frontend/src/styles.css) | `MODIFY` | Appended styles for step headers, compact grids, choice card highlights, and images. |

---

## 🛠️ Detailed Breakdown of Implementation

### 1. Data Pipeline & Blended Dataset
- **Classification Rules**: Checks if `Artist(s)` matches popular Indian artists (e.g. Arijit Singh, Lata Mangeshkar, Kishore Kumar, A.R. Rahman, Pritam, Shreya Ghoshal) or if the genre matches Indian/Hindi tags (`filmi`, `sufi`, `indipop`, `ghazal`, etc.) to mark them as `language = 'hindi'`, setting others to `'english'`.
- **Stratified Sampling**: Keeps all **10,291 Hindi tracks** and samples **18,670 English tracks** to form a balanced mix of **28,961 tracks** (replaced the original 180 mock tracks).

### 2. Backend & Similarity Logic
- **Database updates**: Modified schema `language TEXT` to store the classification.
- **Dynamic Taste Vector**: Replaced the static taste vector from sliders. Now:
  - If filters are selected, it queries the average numeric features of matching tracks (e.g. mean danceability, energy, acousticness) to construct a baseline taste profile.
  - Concatenates with the text TF-IDF vector of selected moods and genres.
  - Scores candidates using **Cosine Similarity**, then blends in popularity (15%).

### 3. Frontend Interactive Cards
- **Album Cover Banner**: Calls `https://itunes.apple.com/search?term={Artist}+{Song}&entity=song&limit=1` on component mount. Automatically caches URLs in a global map (`artCache`) to avoid duplicate lookups.
- **Step-by-Step UI Panels**:
  - **Step 1: Moods** (Cards directly on screen for Joy, Sadness, Love, Anger, Fear, Surprise).
  - **Step 2: Curated Genres** (Formal, clean title-cased cards like Pop, Rock, Hip Hop, Jazz, Classical, Filmi, Sufi, Ghazal).
  - **Step 3: Activities** (Party, Work/Study, Relaxation, Exercise, Running, Yoga, Driving, Social, Morning).
  - **Step 4: Language** (Mix Vibes, Hindi/Bollywood, English/International).
- **Auto-Fetch**: Triggered inside a React `useEffect` whenever any selections are updated.

---

## 🔍 Code Changes & Diffs

Here are the key structural updates across the codebase:

```diff
# database.py: Add language field to columns list and PostgreSQL schema
 TABLE_COLUMNS = [
     "track_id", "track_name", "artist_name", "genre", "emotion", "album",
     "release_date", "explicit", "popularity", "tempo", "loudness",
     "duration_sec", "energy", "danceability", "valence", "speechiness",
-    "liveness", "acousticness", "instrumentalness", "activities",
+    "liveness", "acousticness", "instrumentalness", "activities", "language",
     "similar_1", "similar_2", "similar_3",
 ]
```

```diff
# recommender.py: Filter by language and calculate taste features dynamically
     def recommend(
         self,
-        preferences: dict[str, float],
+        preferences: dict[str, float] | None = None,
         genres: list[str] | None = None,
         moods: list[str] | None = None,
         artists: list[str] | None = None,
         activities: list[str] | None = None,
+        language: str = "mix",
-        limit: int = 12,
+        limit: int = 24,
         popularity_weight: float = 0.15,
     ) -> list[dict]:
-        candidates = self._apply_filters(genres, moods, artists, activities)
+        candidates = self._apply_filters(genres, moods, artists, activities, language)
...
+        # Find tracks matching current filters to construct taste baseline
+        matched_indices = np.where(filter_mask)[0]
+        if has_any_filter and len(matched_indices) > 0:
+            target = self.df.iloc[matched_indices][NUMERIC_FEATURES].mean().to_dict()
+        else:
+            target = self.df[NUMERIC_FEATURES].mean().to_dict()
```

```diff
# AlbumCover.tsx: Retrieve track cover artwork from iTunes Search API on mount
+    fetch(`https://itunes.apple.com/search?term=${encodeURIComponent(term)}&entity=song&limit=1`)
+      .then((res) => res.json())
+      .then((data) => {
+        if (data.results && data.results.length > 0) {
+          const rawUrl = data.results[0].artworkUrl100;
+          const highResUrl = rawUrl.replace("100x100bb.jpg", `${size}x${size}bb.jpg`);
+          artCache[cacheKey] = highResUrl;
+          setImgUrl(highResUrl);
+        }
+      })
```
