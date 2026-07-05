// Typed client for the ShelfMusic backend API.
// All calls go through the relative /api path (nginx proxies to backend).
export interface Track {
  track_id: string;
  track_name: string;
  artist_name: string;
  genre: string;
  emotion: string;
  album: string;
  release_date: string;
  explicit: boolean;
  popularity: number;
  duration_sec: number;
  tempo: number;
  danceability: number;
  energy: number;
  valence: number;
  acousticness: number;
  language: string;
  activities: string[];
  similar_tracks: string[];
  match_score?: number | null;
}

export interface Preferences {
  danceability: number;
  energy: number;
  valence: number;
  acousticness: number;
  instrumentalness: number;
}

export interface Activity {
  key: string;
  label: string;
}

export interface Facets {
  track_count: number;
  genres: string[];
  moods: string[];
  artists: string[];
  activities: Activity[];
}

export interface RecommendResponse {
  strategy: string;
  count: number;
  results: Track[];
}

export interface RecommendPayload {
  preferences?: Preferences;
  genres: string[];
  moods: string[];
  artists: string[];
  activities: string[];
  language: string;
  limit: number;
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
  facets: () => req<Facets>("/facets"),

  search: (q: string) =>
    req<Track[]>(`/search?q=${encodeURIComponent(q)}&limit=8`),

  recommend: (payload: RecommendPayload) =>
    req<RecommendResponse>("/recommend", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  similar: (trackId: string) =>
    req<RecommendResponse>(`/tracks/${encodeURIComponent(trackId)}/similar?limit=12`),

  popular: (genre?: string) =>
    req<RecommendResponse>(`/popular?limit=12${genre ? `&genre=${encodeURIComponent(genre)}` : ""}`),
};
