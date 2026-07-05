import { useState, useEffect } from "react";
import type { Track } from "./api";

// The dataset has no album images, so we fetch them dynamically from the free iTunes Search API.
// We cache requests in-memory to avoid duplicates when rendering lists and modals.
const artCache: Record<string, string> = {};

const GENRE_HUE: Record<string, number> = {
  "hip hop": 275, pop: 330, rock: 5, jazz: 40, classical: 220, metal: 260,
  country: 30, "r&b": 300, electronic: 190, reggae: 130, indie: 160, folk: 90,
  filmi: 340, indipop: 320, sufi: 45, singles: 200, devotional: 60, ghazal: 15,
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
  const [imgUrl, setImgUrl] = useState<string | null>(() => {
    const cacheKey = `${track.artist_name} - ${track.track_name}`;
    return artCache[cacheKey] || null;
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const cacheKey = `${track.artist_name} - ${track.track_name}`;
    if (artCache[cacheKey]) {
      setImgUrl(artCache[cacheKey]);
      return;
    }

    setLoading(true);
    // Sanitize search query: use first artist and clean track name of parentheticals
    const cleanArtist = track.artist_name.split(',')[0].trim();
    const cleanSong = track.track_name.replace(/\(.*\)/g, '').trim();
    const term = `${cleanArtist} ${cleanSong}`;
    const url = `https://itunes.apple.com/search?term=${encodeURIComponent(term)}&entity=song&limit=1`;

    let active = true;

    fetch(url)
      .then((res) => res.json())
      .then((data) => {
        if (!active) return;
        if (data.results && data.results.length > 0) {
          const rawUrl = data.results[0].artworkUrl100;
          // Modify URL to get a higher resolution (e.g. size x size)
          const highResUrl = rawUrl.replace("100x100bb.jpg", `${size}x${size}bb.jpg`);
          artCache[cacheKey] = highResUrl;
          setImgUrl(highResUrl);
        }
      })
      .catch((err) => {
        console.error("Failed to fetch artwork from iTunes", err);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [track.track_name, track.artist_name, size]);

  const hue = hueFor(track.genre);
  const accent = MOOD_ACCENT[track.emotion?.toLowerCase()] ?? "#ffffff";
  const bg1 = `hsl(${hue}, 55%, 32%)`;
  const bg2 = `hsl(${(hue + 40) % 360}, 60%, 18%)`;

  const fallbackSvg = (
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

  if (imgUrl) {
    return (
      <img
        src={imgUrl}
        alt={`Cover for ${track.track_name}`}
        width={size}
        height={size}
        style={{
          display: "block",
          borderRadius: 10,
          objectFit: "cover",
          transition: "opacity 0.3s ease",
          opacity: loading ? 0.6 : 1,
        }}
        onError={() => setImgUrl(null)} // fallback to SVG if image loading fails
      />
    );
  }

  return fallbackSvg;
}
