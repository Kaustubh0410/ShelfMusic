import type { Track } from "./api";
import { AlbumCover } from "./AlbumCover";

function fmtDuration(sec: number): string {
  return `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, "0")}`;
}

const FEATURES: { key: keyof Track; label: string }[] = [
  { key: "energy", label: "Energy" },
  { key: "danceability", label: "Danceability" },
  { key: "valence", label: "Positivity" },
  { key: "acousticness", label: "Acoustic" },
];

export function TrackModal({
  track,
  onClose,
  onFindSimilar,
}: {
  track: Track;
  onClose: () => void;
  onFindSimilar: (t: Track) => void;
}) {
  return (
    <div className="modal-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose} aria-label="Close">×</button>

        <div className="modal-head">
          <AlbumCover track={track} size={180} />
          <div className="modal-head-info">
            <div className="modal-genre">{track.genre}</div>
            <h2 className="modal-title">{track.track_name}</h2>
            <p className="modal-artist">{track.artist_name}</p>
            <div className="modal-badges">
              <span className="badge mood">{track.emotion}</span>
              {track.explicit && <span className="badge explicit">Explicit</span>}
              {track.match_score != null && (
                <span className="badge score">{Math.round(track.match_score * 100)}% match</span>
              )}
            </div>
          </div>
        </div>

        <div className="modal-meta">
          <div><span>Album</span>{track.album || "—"}</div>
          <div><span>Released</span>{track.release_date || "—"}</div>
          <div><span>Duration</span>{fmtDuration(track.duration_sec)}</div>
          <div><span>Tempo</span>{Math.round(track.tempo)} BPM</div>
          <div><span>Popularity</span>{track.popularity}/100</div>
        </div>

        <div className="modal-features">
          {FEATURES.map((f) => {
            const v = Number(track[f.key]) || 0;
            return (
              <div className="feat-bar-row" key={f.key}>
                <span className="feat-name">{f.label}</span>
                <div className="feat-track">
                  <div className="feat-fill" style={{ width: `${Math.round(v * 100)}%` }} />
                </div>
                <span className="feat-val">{Math.round(v * 100)}</span>
              </div>
            );
          })}
        </div>

        {track.activities.length > 0 && (
          <div className="modal-activities">
            <span className="section-label">Good for</span>
            <div className="chips">
              {track.activities.map((a) => (
                <span key={a} className="chip static">{a}</span>
              ))}
            </div>
          </div>
        )}

        {track.similar_tracks.some((s) => s && s !== "nan – nan") && (
          <div className="modal-similar">
            <span className="section-label">Listeners also like</span>
            <ul>
              {track.similar_tracks
                .filter((s) => s && s !== "nan – nan")
                .map((s, i) => <li key={i}>{s}</li>)}
            </ul>
          </div>
        )}

        <button className="btn full" onClick={() => onFindSimilar(track)}>
          Find similar tracks
        </button>
      </div>
    </div>
  );
}
