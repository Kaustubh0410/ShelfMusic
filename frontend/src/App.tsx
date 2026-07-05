import { useEffect, useMemo, useState } from "react";
import { api } from "./api";
import type { Facets, Preferences, Track, RecommendPayload } from "./api";
import { MultiSelect } from "./MultiSelect";
import { AlbumCover } from "./AlbumCover";
import { TrackModal } from "./TrackModal";
import { FeatureEqualizer } from "./FeatureEqualizer";

const DEFAULT_PREFS: Preferences = {
  danceability: 0.6,
  energy: 0.6,
  valence: 0.5,
  acousticness: 0.3,
  instrumentalness: 0.2,
};

const SLIDERS: { key: keyof Preferences; label: string }[] = [
  { key: "energy", label: "Energy" },
  { key: "danceability", label: "Danceability" },
  { key: "valence", label: "Mood / positivity" },
  { key: "acousticness", label: "Acoustic feel" },
  { key: "instrumentalness", label: "Instrumental" },
];

function Spinner() {
  return (
    <span className="spinner-eq" aria-label="loading">
      <span />
      <span />
      <span />
      <span />
    </span>
  );
}

function fmtDuration(sec: number): string {
  return `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, "0")}`;
}

type Mode = "taste" | "similar" | "popular";

export default function App() {
  const [mode, setMode] = useState<Mode>("taste");
  const [facets, setFacets] = useState<Facets | null>(null);
  const [prefs, setPrefs] = useState<Preferences>(DEFAULT_PREFS);

  const [genres, setGenres] = useState<string[]>([]);
  const [moods, setMoods] = useState<string[]>([]);
  const [artists, setArtists] = useState<string[]>([]);
  const [activities, setActivities] = useState<string[]>([]);

  // Find similar states
  const [searchQuery, setSearchQuery] = useState("");
  const [suggestions, setSuggestions] = useState<Track[]>([]);

  // Popular states
  const [selectedPopularGenre, setSelectedPopularGenre] = useState<string | null>(null);

  const [results, setResults] = useState<Track[]>([]);
  const [strategy, setStrategy] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Track | null>(null);
  const [heading, setHeading] = useState("Tuned to your taste");

  useEffect(() => {
    api.facets().then(setFacets).catch((e) => setError(e.message));
  }, []);

  // Debounced search for similar track mode
  useEffect(() => {
    if (searchQuery.trim().length < 2) {
      setSuggestions([]);
      return;
    }
    const delayDebounce = setTimeout(async () => {
      try {
        const hits = await api.search(searchQuery);
        setSuggestions(hits);
      } catch (e) {
        console.error(e);
      }
    }, 250);

    return () => clearTimeout(delayDebounce);
  }, [searchQuery]);

  // Load popular tracks when switching to popular tab or changing popular genre
  useEffect(() => {
    if (mode === "popular") {
      runPopular(selectedPopularGenre || undefined);
    }
  }, [mode, selectedPopularGenre]);

  async function runRecommend() {
    setLoading(true);
    setError(null);
    setHeading("Tuned to your taste");
    try {
      const payload: RecommendPayload = {
        preferences: prefs,
        genres,
        moods,
        artists,
        activities,
        limit: 12,
      };
      const r = await api.recommend(payload);
      setResults(r.results);
      setStrategy(r.strategy);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function runSimilar(track: Track) {
    setSelected(null);
    setLoading(true);
    setError(null);
    setHeading(`More like “${track.track_name}”`);
    setMode("similar");
    try {
      const r = await api.similar(track.track_id);
      setResults(r.results);
      setStrategy(r.strategy);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function runPopular(genre?: string) {
    setLoading(true);
    setError(null);
    setHeading(genre ? `Popular in ${genre}` : "Popular overall");
    try {
      const r = await api.popular(genre);
      setResults(r.results);
      setStrategy(r.strategy);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  const activityOptions = useMemo(
    () => (facets?.activities ?? []).map((a) => a.label),
    [facets]
  );
  
  // Map activity label back to key for the API.
  const labelToKey = useMemo(() => {
    const m: Record<string, string> = {};
    (facets?.activities ?? []).forEach((a) => (m[a.label] = a.key));
    return m;
  }, [facets]);

  function setActivityLabels(labels: string[]) {
    setActivities(labels.map((l) => labelToKey[l] ?? l));
  }
  
  const selectedActivityLabels = useMemo(() => {
    const keyToLabel: Record<string, string> = {};
    (facets?.activities ?? []).forEach((a) => (keyToLabel[a.key] = a.label));
    return activities.map((k) => keyToLabel[k] ?? k);
  }, [activities, facets]);

  const handleTabChange = (newMode: Mode) => {
    setMode(newMode);
    setResults([]);
    setStrategy("");
    setError(null);
  };

  return (
    <div className="wrap">
      <header className="masthead">
        <div className="brand">
          <div className="eq" aria-hidden="true">
            <span />
            <span />
            <span />
            <span />
          </div>
          <div>
            <h1>Shelf<span>Music</span></h1>
            <p className="tagline">Filter by mood, genre, artist and vibe — matched on how the music actually sounds.</p>
          </div>
        </div>
        <div className="stat">
          {facets ? (
            <>
              <div><b>{facets.track_count.toLocaleString()}</b> tracks</div>
              <div><b>{facets.genres.length}</b> genres · <b>{facets.moods.length}</b> moods</div>
            </>
          ) : <div>connecting…</div>}
        </div>
      </header>

      {error && <div className="error">Something went wrong: {error}</div>}

      <div className="tabs">
        <button
          className="tab"
          aria-selected={mode === "taste"}
          onClick={() => handleTabChange("taste")}
        >
          Tune by taste
        </button>
        <button
          className="tab"
          aria-selected={mode === "similar"}
          onClick={() => handleTabChange("similar")}
        >
          Find similar
        </button>
        <button
          className="tab"
          aria-selected={mode === "popular"}
          onClick={() => handleTabChange("popular")}
        >
          Popular
        </button>
      </div>

      {mode === "taste" && (
        <section className="panel">
          <h2>Find your next listen</h2>
          <p className="hint">Pick any filters (all optional), shape the sound with the sliders, then get matches.</p>

          {facets && (
            <div className="filters">
              <MultiSelect label="Mood" options={facets.moods} selected={moods} onChange={setMoods} />
              <MultiSelect label="Genre" options={facets.genres} selected={genres} onChange={setGenres} searchable />
              <MultiSelect label="Artist" options={facets.artists} selected={artists} onChange={setArtists} searchable />
              <MultiSelect label="Good for" options={activityOptions} selected={selectedActivityLabels} onChange={setActivityLabels} />
            </div>
          )}

          <div className="sliders">
            {SLIDERS.map(({ key, label }) => (
              <div className="slider-row" key={key}>
                <label htmlFor={key}>{label}</label>
                <input
                  id={key} type="range" min={0} max={1} step={0.01}
                  value={prefs[key]}
                  onChange={(e) => setPrefs((p) => ({ ...p, [key]: parseFloat(e.target.value) }))}
                />
                <span className="val">{prefs[key].toFixed(2)}</span>
              </div>
            ))}
          </div>

          <div className="btn-row">
            <button className="btn" onClick={runRecommend} disabled={loading}>
              {loading ? "Mixing…" : "Get recommendations"}
            </button>
            {loading && <Spinner />}
          </div>
        </section>
      )}

      {mode === "similar" && (
        <section className="panel">
          <h2>Search for a track</h2>
          <p className="hint">Type a track name or artist to find its closest audio matches.</p>
          <div className="search-box">
            <input
              type="text"
              placeholder="Search track by title or artist..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          {suggestions.length > 0 && (
            <div className="search-results">
              {suggestions.map((t) => (
                <div
                  key={t.track_id}
                  className="search-item"
                  onClick={() => {
                    setSearchQuery("");
                    setSuggestions([]);
                    runSimilar(t);
                  }}
                >
                  <div>
                    <strong>{t.track_name}</strong> by {t.artist_name}
                  </div>
                  <div className="meta">
                    {t.genre} · pop {t.popularity}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {mode === "popular" && (
        <section className="panel">
          <h2>Popular tracks</h2>
          <p className="hint">Explore the most popular tracks overall or by genre.</p>
          {facets && (
            <div className="chips">
              <button
                className="chip"
                aria-pressed={selectedPopularGenre === null}
                onClick={() => setSelectedPopularGenre(null)}
              >
                All
              </button>
              {facets.genres.map((g) => (
                <button
                  key={g}
                  className="chip"
                  aria-pressed={selectedPopularGenre === g}
                  onClick={() => setSelectedPopularGenre(g)}
                >
                  {g}
                </button>
              ))}
            </div>
          )}
        </section>
      )}

      {(results.length > 0 || loading) && (
        <>
          <div className="results-head">
            <h2>{heading}</h2>
            {strategy && <span className="strategy">strategy: {strategy}</span>}
          </div>

          {loading && results.length === 0 ? (
            <div className="state">
              <Spinner />
              <div style={{ marginTop: 12 }}>Reading the waveform…</div>
            </div>
          ) : results.length === 0 ? (
            <div className="state">
              <div className="big">No tracks match those filters.</div>
              Try removing a filter or widening the sliders.
            </div>
          ) : (
            <div className="grid">
              {results.map((t) => (
                <div
                  className="card"
                  key={t.track_id}
                  onClick={() => setSelected(t)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      setSelected(t);
                    }
                  }}
                >
                  <AlbumCover track={t} size={200} />
                  <div className="card-body">
                    <div className="row">
                      <span className="genre-tag">{t.genre}</span>
                      {t.match_score != null && (
                        <span className="score">{Math.round(t.match_score * 100)}%</span>
                      )}
                    </div>
                    <div className="title">{t.track_name}</div>
                    <div className="artist">{t.artist_name}</div>
                    <div className="card-mood">{t.emotion}</div>
                    
                    <FeatureEqualizer track={t} />

                    <div className="footer">
                      <span>{fmtDuration(t.duration_sec)} · pop {t.popularity}</span>
                      <button
                        className="link-btn"
                        onClick={(e) => {
                          e.stopPropagation();
                          runSimilar(t);
                        }}
                      >
                        more like this →
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {!loading && results.length === 0 && (
        <div className="state">
          {mode === "taste" && (
            <>
              <div className="big">Ready when you are.</div>
              Set filters and hit “Get recommendations”.
            </>
          )}
          {mode === "similar" && (
            <>
              <div className="big">Search for a song.</div>
              Find a track to see similar recommendations.
            </>
          )}
          {mode === "popular" && (
            <>
              <div className="big">Loading popular tracks…</div>
            </>
          )}
        </div>
      )}

      {selected && (
        <TrackModal track={selected} onClose={() => setSelected(null)} onFindSimilar={runSimilar} />
      )}

      <footer className="foot">
        <span>ShelfMusic · faceted content-based recommender</span>
        <span>data: Kaggle 900K-Spotify (sampled)</span>
      </footer>
    </div>
  );
}
