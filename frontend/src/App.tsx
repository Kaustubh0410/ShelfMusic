import { useEffect, useState } from "react";
import { api } from "./api";
import type { Facets, Track, RecommendPayload } from "./api";
import { AlbumCover } from "./AlbumCover";
import { TrackModal } from "./TrackModal";
import { FeatureEqualizer } from "./FeatureEqualizer";

const MOOD_CARDS: Record<string, { label: string; emoji: string; desc: string }> = {
  joy: { label: "Joy", emoji: "☀️", desc: "Upbeat, happy, and bright vibes" },
  sadness: { label: "Sadness", emoji: "🌧️", desc: "Melancholic, deep, and emotional" },
  love: { label: "Love", emoji: "💖", desc: "Romantic, warm, and sentimental" },
  anger: { label: "Anger", emoji: "🔥", desc: "Intense, aggressive, and powerful" },
  fear: { label: "Fear", emoji: "👻", desc: "Spooky, mysterious, and tense" },
  surprise: { label: "Surprise", emoji: "⚡", desc: "Energetic, dynamic, and unexpected" },
};

const POPULAR_GENRES = [
  { key: "pop", label: "Pop", emoji: "🎤" },
  { key: "rock", label: "Rock", emoji: "🎸" },
  { key: "hip hop", label: "Hip Hop", emoji: "🎧" },
  { key: "jazz", label: "Jazz", emoji: "🎷" },
  { key: "classical", label: "Classical", emoji: "🎻" },
  { key: "metal", label: "Metal", emoji: "💀" },
  { key: "country", label: "Country", emoji: "🤠" },
  { key: "r&b", label: "R&B", emoji: "🍷" },
  { key: "electronic", label: "Electronic", emoji: "🎹" },
  { key: "reggae", label: "Reggae", emoji: "🌴" },
  { key: "indie", label: "Indie", emoji: "🍀" },
  { key: "folk", label: "Folk", emoji: "🪕" },
  { key: "filmi", label: "Filmi / Bollywood", emoji: "🎬" },
  { key: "indipop", label: "Indipop", emoji: "📻" },
  { key: "sufi", label: "Sufi", emoji: "✨" },
  { key: "ghazal", label: "Ghazal", emoji: "🥀" },
];

const VIBE_CARDS: Record<string, { label: string; emoji: string }> = {
  party: { label: "Party", emoji: "🎉" },
  work_study: { label: "Work & Study", emoji: "📚" },
  relaxation: { label: "Relaxation", emoji: "🧘" },
  exercise: { label: "Exercise", emoji: "💪" },
  running: { label: "Running", emoji: "🏃" },
  yoga: { label: "Yoga & Stretch", emoji: "🧘‍♀️" },
  driving: { label: "Driving", emoji: "🚗" },
  social: { label: "Social", emoji: "👥" },
  morning: { label: "Morning", emoji: "🌅" },
};

const LANGUAGE_CARDS = [
  { key: "mix", label: "Mix Vibes", emoji: "🌎", desc: "Blended Hindi & English" },
  { key: "hindi", label: "Hindi / Bollywood", emoji: "🇮🇳", desc: "Desi hits, ghazals, and sufi" },
  { key: "english", label: "English / International", emoji: "🇬🇧", desc: "Pop, Rock, Hip Hop, and Metal" },
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

  const [genres, setGenres] = useState<string[]>([]);
  const [moods, setMoods] = useState<string[]>([]);
  const artists: string[] = [];
  const [activities, setActivities] = useState<string[]>([]);
  const [language, setLanguage] = useState<string>("mix");

  // Find similar states
  const [searchQuery, setSearchQuery] = useState("");
  const [suggestions, setSuggestions] = useState<Track[]>([]);

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

  // Load the Top Charts when switching to the popular tab
  useEffect(() => {
    if (mode === "popular") {
      runPopular();
    }
  }, [mode]);

  // Auto-run recommendations when taste filters change
  useEffect(() => {
    if (mode === "taste") {
      runRecommend();
    }
  }, [moods, genres, activities, language, mode]);

  async function runRecommend() {
    setLoading(true);
    setError(null);
    setHeading("Tuned to your taste");
    try {
      const payload: RecommendPayload = {
        genres,
        moods,
        artists,
        activities,
        language,
        limit: 24,
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

  async function runPopular() {
    setLoading(true);
    setError(null);
    setHeading("Top Charts");
    try {
      const r = await api.popular();
      setResults(r.results);
      setStrategy(r.strategy);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

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
          Top Charts
        </button>
      </div>

      {mode === "taste" && (
        <section className="panel">
          <div className="step-header">
            <span className="step-num">Step 1</span>
            <h2>Select your Moods</h2>
          </div>
          <p className="hint">Choose how you want to feel. Tap multiple moods to combine vibes.</p>
          <div className="card-grid">
            {Object.entries(MOOD_CARDS).map(([key, item]) => {
              const isSelected = moods.includes(key);
              return (
                <button
                  key={key}
                  className={`choice-card ${isSelected ? 'selected' : ''}`}
                  onClick={() => {
                    setMoods(prev => prev.includes(key) ? prev.filter(m => m !== key) : [...prev, key]);
                  }}
                  aria-pressed={isSelected}
                >
                  <div className="choice-emoji">{item.emoji}</div>
                  <div className="choice-label">{item.label}</div>
                  <div className="choice-desc">{item.desc}</div>
                </button>
              );
            })}
          </div>

          <div className="step-header" style={{ marginTop: 32 }}>
            <span className="step-num">Step 2</span>
            <h2>Select Genres</h2>
          </div>
          <p className="hint">Pick genres (keep it formal, or select a mix).</p>
          <div className="card-grid genre-grid">
            {POPULAR_GENRES.map((item) => {
              const isSelected = genres.includes(item.key);
              return (
                <button
                  key={item.key}
                  className={`choice-card compact ${isSelected ? 'selected' : ''}`}
                  onClick={() => {
                    setGenres(prev => prev.includes(item.key) ? prev.filter(g => g !== item.key) : [...prev, item.key]);
                  }}
                  aria-pressed={isSelected}
                >
                  <span className="choice-emoji">{item.emoji}</span>
                  <span className="choice-label">{item.label}</span>
                </button>
              );
            })}
          </div>

          <div className="step-header" style={{ marginTop: 32 }}>
            <span className="step-num">Step 3</span>
            <h2>Vibe / Activities</h2>
          </div>
          <p className="hint">Match music to what you are doing right now.</p>
          <div className="card-grid activity-grid">
            {Object.entries(VIBE_CARDS).map(([key, item]) => {
              const isSelected = activities.includes(key);
              return (
                <button
                  key={key}
                  className={`choice-card compact ${isSelected ? 'selected' : ''}`}
                  onClick={() => {
                    setActivities(prev => prev.includes(key) ? prev.filter(a => a !== key) : [...prev, key]);
                  }}
                  aria-pressed={isSelected}
                >
                  <span className="choice-emoji">{item.emoji}</span>
                  <span className="choice-label">{item.label}</span>
                </button>
              );
            })}
          </div>

          <div className="step-header" style={{ marginTop: 32 }}>
            <span className="step-num">Step 4</span>
            <h2>Select Language Mix</h2>
          </div>
          <p className="hint">Blended Hindi & English results matching your vibe.</p>
          <div className="card-grid language-grid">
            {LANGUAGE_CARDS.map((item) => {
              const isSelected = language === item.key;
              return (
                <button
                  key={item.key}
                  className={`choice-card lang-card ${isSelected ? 'selected' : ''}`}
                  onClick={() => setLanguage(item.key)}
                  aria-pressed={isSelected}
                >
                  <div className="choice-emoji">{item.emoji}</div>
                  <div className="choice-label">{item.label}</div>
                  <div className="choice-desc">{item.desc}</div>
                </button>
              );
            })}
          </div>

          <div className="btn-row" style={{ marginTop: 32 }}>
            <button className="btn" onClick={runRecommend} disabled={loading}>
              {loading ? "Mixing…" : "Refresh recommendations"}
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
        <section className="panel charts-intro">
          <h2>🔥 Top Charts</h2>
          <p className="hint">The most popular tracks across the whole collection, ranked by popularity.</p>
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
              Try changing your steps or selections.
            </div>
          ) : (
            <div className={mode === "popular" ? "grid chart-grid" : "grid"}>
              {results.map((t, i) => (
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
                  {mode === "popular" && <span className="chart-rank">#{i + 1}</span>}
                  <AlbumCover track={t} size={240} />
                  <div className="card-body">
                    <div className="row">
                      <span className="genre-tag">{t.genre}</span>
                      {t.match_score != null && (
                        <span className="score">{Math.round(t.match_score * 100)}%</span>
                      )}
                    </div>
                    <div className="title">{t.track_name}</div>
                    <div className="artist">{t.artist_name}</div>
                    <div className="card-mood">
                      <span className="language-badge">{t.language === "hindi" ? "🇮🇳 Hindi" : "🇬🇧 English"}</span>
                      {t.emotion}
                    </div>
                    
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
              Tap your moods or language above to see results.
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
        <span>ShelfMusic · card-based hybrid music recommender</span>
        <span>data: Kaggle 900K-Spotify (Hindi/English mix sampled)</span>
      </footer>
    </div>
  );
}
