import type { HeatPoint } from '../../api/types';
import { dotRadius, isHollow, vibeColorVar } from './mapColors';

/** PRD R5 fallback: an SVG dot plot when WebGL or the tile host is unavailable. */
export function SvgDotMap({
  points,
  names,
  heat,
  onSelect,
  selected,
}: {
  points: HeatPoint[];
  names: Record<string, string>;
  heat: boolean;
  onSelect: (id: string) => void;
  selected: string | null;
}) {
  if (!points.length) return null;
  const lats = points.map((p) => p.lat);
  const lons = points.map((p) => p.lon);
  const pad = 0.002;
  const [minLat, maxLat] = [Math.min(...lats) - pad, Math.max(...lats) + pad];
  const [minLon, maxLon] = [Math.min(...lons) - pad, Math.max(...lons) + pad];
  const W = 400;
  const H = 520;
  const x = (lon: number) => ((lon - minLon) / (maxLon - minLon)) * W;
  const y = (lat: number) => H - ((lat - minLat) / (maxLat - minLat)) * H;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-full w-full" role="group" aria-label="Venue map (simplified)" data-testid="svg-map">
      <defs>
        <radialGradient id="heat">
          <stop offset="0%" stopColor="var(--c-accent)" stopOpacity="0.55" />
          <stop offset="100%" stopColor="var(--c-accent)" stopOpacity="0" />
        </radialGradient>
        <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
          <path d="M 40 0 L 0 0 0 40" fill="none" stroke="var(--c-line)" strokeWidth="1" />
        </pattern>
      </defs>
      <rect width={W} height={H} fill="var(--c-surface)" />
      <rect width={W} height={H} fill="url(#grid)" />
      {heat &&
        points.map((p) =>
          p.vibe_score === null || p.confidence === null ? null : (
            <circle key={`h-${p.venue_id}`} cx={x(p.lon)} cy={y(p.lat)} r={20 + (p.vibe_score / 100) * p.confidence * 70} fill="url(#heat)" />
          ),
        )}
      {points.map((p) => {
        const c = vibeColorVar(p.vibe_score);
        const hollow = isHollow(p.confidence);
        const label = `${names[p.venue_id] ?? p.venue_id}: ${p.vibe_score === null ? 'no fresh reports' : `vibe ${p.vibe_score}`}`;
        return (
          <g key={p.venue_id}>
            <circle
              cx={x(p.lon)}
              cy={y(p.lat)}
              r={dotRadius(p.confidence)}
              fill={hollow ? 'transparent' : c}
              stroke={c}
              strokeWidth={hollow ? 2.5 : 1.5}
              className="cursor-pointer"
              role="button"
              tabIndex={0}
              aria-label={label}
              aria-pressed={selected === p.venue_id}
              onClick={() => onSelect(p.venue_id)}
              onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && onSelect(p.venue_id)}
            />
            {selected === p.venue_id && (
              <circle cx={x(p.lon)} cy={y(p.lat)} r={dotRadius(p.confidence) + 5} fill="none" stroke="var(--c-cyan)" strokeWidth={2} />
            )}
          </g>
        );
      })}
    </svg>
  );
}
