import type { Track } from "./api";

// Renders a small equalizer where each bar is an audio feature.
// The height encodes the value; the color maps calm (cool) -> intense (warm).
const FEATURES: { key: keyof Track; label: string; color: string }[] = [
  { key: "danceability", label: "DNC", color: "var(--cool)" },
  { key: "energy", label: "NRG", color: "var(--warm)" },
  { key: "valence", label: "MOOD", color: "var(--warm-2)" },
  { key: "acousticness", label: "ACO", color: "var(--cool-2)" },
];

export function FeatureEqualizer({ track }: { track: Track }) {
  return (
    <div className="feat-eq" role="img" aria-label="audio feature levels">
      {FEATURES.map((f) => {
        const value = Number(track[f.key]) || 0;
        const pct = Math.max(6, Math.min(100, value * 100));
        return (
          <div className="feat-col" key={f.key}>
            <div
              className="bar"
              style={{ height: `${pct}%`, background: f.color }}
              title={`${f.label}: ${value.toFixed(2)}`}
            />
            <div className="bar-label">{f.label}</div>
          </div>
        );
      })}
    </div>
  );
}
