// Thin typed client for the ShelfMusic backend API.
// All calls go through the relative /api path, which nginx (prod) or the
// Vite dev proxy forwards to the backend container.

export interface Track {
  track_id: string;
  track_name: string;
  artist_name: string;
  genre: string;
  popularity: number;
  duration_ms: number;
  danceability: number;
  energy: number;
  valence: number;
  acousticness: number;
  tempo: number;
  match_score?: number | null;
}

export interface Preferences {
  danceability: number;
  energy: number;
  valence: number;
  acousticness: number;
  instrumentalness: number;
}

export interface RecommendResponse {
  strategy: string;
  count: number;
  results: Track[];
}

export interface Meta {
  track_count: number;
  genres: string[];
}

const BASE = "/api";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  meta: () => req<Meta>("/meta"),

  search: (q: string) =>
    req<Track[]>(`/search?q=${encodeURIComponent(q)}&limit=8`),

  similar: (trackId: string) =>
    req<RecommendResponse>(`/tracks/${encodeURIComponent(trackId)}/similar?limit=12`),

  recommend: (preferences: Preferences, genres: string[]) =>
    req<RecommendResponse>("/recommend", {
      method: "POST",
      body: JSON.stringify({ preferences, genres, limit: 12 }),
    }),

  popular: (genre?: string) =>
    req<RecommendResponse>(`/popular?limit=12${genre ? `&genre=${genre}` : ""}`),
};
