import { useEffect, useMemo, useState } from "react";
import { api } from "./api";
import type { Meta, Preferences, Track } from "./api";
import { FeatureEqualizer } from "./FeatureEqualizer";

type Mode = "taste" | "similar" | "popular";

const DEFAULT_PREFS: Preferences = {
  danceability: 0.6,
  energy: 0.6,
  valence: 0.5,
  acousticness: 0.3,
  instrumentalness: 0.2,
};

const SLIDER_META: { key: keyof Preferences; label: string }[] = [
  { key: "energy", label: "Energy" },
  { key: "danceability", label: "Danceability" },
  { key: "valence", label: "Mood / positivity" },
  { key: "acousticness", label: "Acoustic feel" },
  { key: "instrumentalness", label: "Instrumental" },
];

function formatDuration(ms: number): string {
  const s = Math.round(ms / 1000);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

function Spinner() {
  return (
    <span className="spinner-eq" aria-label="loading">
      <span /><span /><span /><span />
    </span>
  );
}

export default function App() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [mode, setMode] = useState<Mode>("taste");

  // taste mode
  const [prefs, setPrefs] = useState<Preferences>(DEFAULT_PREFS);
  const [selectedGenres, setSelectedGenres] = useState<string[]>([]);

  // similar mode
  const [query, setQuery] = useState("");
  const [searchHits, setSearchHits] = useState<Track[]>([]);
  const [seed, setSeed] = useState<Track | null>(null);

  // shared results
  const [results, setResults] = useState<Track[]>([]);
  const [strategy, setStrategy] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.meta().then(setMeta).catch((e) => setError(String(e.message)));
  }, []);

  // Debounced track search for the "similar" flow.
  useEffect(() => {
    if (mode !== "similar" || query.trim().length < 2) {
      setSearchHits([]);
      return;
    }
    const t = setTimeout(() => {
      api.search(query).then(setSearchHits).catch(() => setSearchHits([]));
    }, 250);
    return () => clearTimeout(t);
  }, [query, mode]);

  async function runTaste() {
    setLoading(true);
    setError(null);
    try {
      const r = await api.recommend(prefs, selectedGenres);
      setResults(r.results);
      setStrategy(r.strategy);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function runSimilar(track: Track) {
    setSeed(track);
    setSearchHits([]);
    setQuery(`${track.track_name} — ${track.artist_name}`);
    setLoading(true);
    setError(null);
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

  function toggleGenre(g: string) {
    setSelectedGenres((prev) =>
      prev.includes(g) ? prev.filter((x) => x !== g) : [...prev, g]
    );
  }

  function switchMode(m: Mode) {
    setMode(m);
    setResults([]);
    setStrategy("");
    setError(null);
    setSeed(null);
    setQuery("");
    if (m === "popular") runPopular();
  }

  const resultsTitle = useMemo(() => {
    if (mode === "taste") return "Tuned to your taste";
    if (mode === "similar") return seed ? `More like “${seed.track_name}”` : "Find similar tracks";
    return "Popular right now";
  }, [mode, seed]);

  return (
    <div className="wrap">
      <header className="masthead">
        <div className="brand">
          <div className="eq" aria-hidden="true">
            <span /><span /><span /><span />
          </div>
          <div>
            <h1>Shelf<span>Music</span></h1>
            <p className="tagline">
              Tell it how you want to feel — it reads the audio, not the hype.
            </p>
          </div>
        </div>
        <div className="stat">
          {meta ? (
            <>
              <div><b>{meta.track_count}</b> tracks indexed</div>
              <div><b>{meta.genres.length}</b> genres</div>
            </>
          ) : (
            <div>connecting…</div>
          )}
        </div>
      </header>

      <nav className="tabs" role="tablist" aria-label="recommendation modes">
        <button className="tab" role="tab" aria-selected={mode === "taste"} onClick={() => switchMode("taste")}>
          Tune by taste
        </button>
        <button className="tab" role="tab" aria-selected={mode === "similar"} onClick={() => switchMode("similar")}>
          Find similar
        </button>
        <button className="tab" role="tab" aria-selected={mode === "popular"} onClick={() => switchMode("popular")}>
          Popular
        </button>
      </nav>

      {error && <div className="error">Something went wrong: {error}</div>}

      {mode === "taste" && (
        <section className="panel">
          <h2>Set the mood</h2>
          <p className="hint">Slide to shape the sound. Pick genres to narrow it down (optional).</p>
          <div className="sliders">
            {SLIDER_META.map(({ key, label }) => (
              <div className="slider-row" key={key}>
                <label htmlFor={key}>{label}</label>
                <input
                  id={key}
                  type="range"
                  min={0}
                  max={1}
                  step={0.01}
                  value={prefs[key]}
                  onChange={(e) =>
                    setPrefs((p) => ({ ...p, [key]: parseFloat(e.target.value) }))
                  }
                />
                <span className="val">{prefs[key].toFixed(2)}</span>
              </div>
            ))}
          </div>

          {meta && (
            <div className="chips">
              {meta.genres.map((g) => (
                <button
                  key={g}
                  className="chip"
                  aria-pressed={selectedGenres.includes(g)}
                  onClick={() => toggleGenre(g)}
                >
                  {g}
                </button>
              ))}
            </div>
          )}

          <div className="btn-row">
            <button className="btn" onClick={runTaste} disabled={loading}>
              {loading ? "Mixing…" : "Get recommendations"}
            </button>
            {loading && <Spinner />}
          </div>
        </section>
      )}

      {mode === "similar" && (
        <section className="panel">
          <h2>Start from a track you like</h2>
          <p className="hint">Search by song or artist, then pick one to find neighbours in audio space.</p>
          <div className="search-box">
            <input
              type="text"
              placeholder="e.g. Wildfire, or Silver Sisters"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          {searchHits.length > 0 && (
            <div className="search-results">
              {searchHits.map((t) => (
                <div key={t.track_id} className="search-item" onClick={() => runSimilar(t)}>
                  <div>
                    <strong>{t.track_name}</strong>
                    <span className="meta"> · {t.artist_name}</span>
                  </div>
                  <span className="meta">{t.genre}</span>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {mode === "popular" && meta && (
        <section className="panel">
          <h2>Browse by genre</h2>
          <p className="hint">Or see what's popular across everything.</p>
          <div className="chips">
            <button className="chip" onClick={() => runPopular()}>all</button>
            {meta.genres.map((g) => (
              <button key={g} className="chip" onClick={() => runPopular(g)}>{g}</button>
            ))}
          </div>
        </section>
      )}

      {(results.length > 0 || loading) && (
        <>
          <div className="results-head">
            <h2>{resultsTitle}</h2>
            {strategy && <span className="strategy">strategy: {strategy}</span>}
          </div>

          {loading && results.length === 0 ? (
            <div className="state"><Spinner /><div style={{ marginTop: 12 }}>Reading the waveform…</div></div>
          ) : (
            <div className="grid">
              {results.map((t) => (
                <article className="card" key={t.track_id}>
                  <div>
                    <div className="row">
                      <span className="genre-tag">{t.genre}</span>
                      {t.match_score != null && (
                        <span className="score">{Math.round(t.match_score * 100)}%</span>
                      )}
                    </div>
                    <div className="title" style={{ marginTop: 10 }}>{t.track_name}</div>
                    <div className="artist">{t.artist_name}</div>
                  </div>

                  <FeatureEqualizer track={t} />

                  <div className="footer">
                    <span>{formatDuration(t.duration_ms)} · pop {t.popularity}</span>
                    <button className="link-btn" onClick={() => { switchMode("similar"); runSimilar(t); }}>
                      more like this →
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </>
      )}

      {!loading && results.length === 0 && mode === "taste" && (
        <div className="state">
          <div className="big">Ready when you are.</div>
          Set the sliders and hit “Get recommendations”.
        </div>
      )}

      <footer className="foot">
        <span>ShelfMusic · content-based + preference recommender</span>
        <span>data: Spotify-style audio features (see README)</span>
      </footer>
    </div>
  );
}
