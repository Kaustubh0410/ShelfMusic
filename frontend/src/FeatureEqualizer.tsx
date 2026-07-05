import type { Track } from "./api";

interface FeatureEqualizerProps {
  track: Track;
}

export function FeatureEqualizer({ track }: FeatureEqualizerProps) {
  const features = [
    { key: "danceability" as const, label: "DNC", color: "var(--cool)" },
    { key: "energy" as const, label: "NRG", color: "var(--warm)" },
    { key: "valence" as const, label: "MOOD", color: "var(--warm-2)" },
    { key: "acousticness" as const, label: "ACO", color: "var(--cool-2)" },
  ];

  return (
    <div className="feat-eq">
      {features.map((f) => {
        const val = track[f.key] ?? 0;
        const pct = Math.round(val * 100);
        return (
          <div className="feat-col" key={f.key}>
            <div
              className="bar"
              style={{
                height: `${Math.max(2, pct)}%`,
                backgroundColor: f.color,
              }}
              title={`${f.label}: ${pct}%`}
            />
            <span className="bar-label">{f.label}</span>
          </div>
        );
      })}
    </div>
  );
}
