import type { Track } from "./api";

// The dataset has no album images, so we generate a deterministic cover
// from the track's genre + mood. Same track always yields the same art.
// This keeps the app fully self-contained (no image hosting, no API keys).

const GENRE_HUE: Record<string, number> = {
  "hip hop": 275, pop: 330, rock: 5, jazz: 40, classical: 220, metal: 260,
  country: 30, "r&b": 300, electronic: 190, reggae: 130, indie: 160, folk: 90,
};

const MOOD_ACCENT: Record<string, string> = {
  joy: "#ffd23f", sadness: "#5b8cff", love: "#ff6b9d", anger: "#ff5252",
  fear: "#9b59b6", surprise: "#4dd0e1",
};

function hueFor(genre: string): number {
  return GENRE_HUE[genre?.toLowerCase()] ?? 210;
}

function initials(track: Track): string {
  const a = track.track_name?.trim()?.[0] ?? "?";
  const b = track.artist_name?.trim()?.[0] ?? "";
  return (a + b).toUpperCase();
}

export function AlbumCover({ track, size = 200 }: { track: Track; size?: number }) {
  const hue = hueFor(track.genre);
  const accent = MOOD_ACCENT[track.emotion?.toLowerCase()] ?? "#ffffff";
  const bg1 = `hsl(${hue}, 55%, 32%)`;
  const bg2 = `hsl(${(hue + 40) % 360}, 60%, 18%)`;

  // A few concentric "vinyl" rings + a mood-colored accent arc.
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 200 200"
      role="img"
      aria-label={`Generated cover for ${track.track_name}`}
      style={{ display: "block", borderRadius: 10 }}
    >
      <defs>
        <linearGradient id={`g-${track.track_id}`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor={bg1} />
          <stop offset="100%" stopColor={bg2} />
        </linearGradient>
      </defs>
      <rect width="200" height="200" fill={`url(#g-${track.track_id})`} />
      <circle cx="100" cy="100" r="70" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="1" />
      <circle cx="100" cy="100" r="52" fill="none" stroke="rgba(255,255,255,0.10)" strokeWidth="1" />
      <circle cx="100" cy="100" r="34" fill="none" stroke="rgba(255,255,255,0.12)" strokeWidth="1" />
      <path
        d="M 100 30 A 70 70 0 0 1 170 100"
        fill="none"
        stroke={accent}
        strokeWidth="4"
        strokeLinecap="round"
        opacity="0.9"
      />
      <circle cx="100" cy="100" r="16" fill={accent} opacity="0.85" />
      <text
        x="100"
        y="100"
        textAnchor="middle"
        dominantBaseline="central"
        fontFamily="'Space Grotesk', sans-serif"
        fontSize="14"
        fontWeight="700"
        fill="#0b0d14"
      >
        {initials(track)}
      </text>
    </svg>
  );
}
