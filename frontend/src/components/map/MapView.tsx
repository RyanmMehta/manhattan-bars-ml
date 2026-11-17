// Lazy chunk: MapLibre GL is only loaded on the Map screen (PRD N2).
import { useEffect, useRef, useState } from 'react';
import maplibregl, { type GeoJSONSource, type Map as MLMap } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import type { HeatPoint } from '../../api/types';
import { CONF_SHOW } from '../../config/thresholds';
import { SvgDotMap } from './SvgDotMap';
import { token } from './mapColors';

// CONTRACTS §J: free, no-key styles. OpenFreeMap first, CARTO dark-matter second.
const STYLES = [
  'https://tiles.openfreemap.org/styles/dark',
  'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
];

interface Props {
  points: HeatPoint[];
  names: Record<string, string>;
  heat: boolean;
  selected: string | null;
  onSelect: (id: string) => void;
}

function toGeo(points: HeatPoint[]): GeoJSON.FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: points.map((p) => ({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [p.lon, p.lat] },
      properties: {
        venue_id: p.venue_id,
        vibe: p.vibe_score === null ? -1 : p.vibe_score,
        conf: p.confidence === null ? 0 : p.confidence,
        weight: p.vibe_score === null || p.confidence === null ? 0 : (p.vibe_score / 100) * p.confidence,
      },
    })),
  };
}

function webglOk(): boolean {
  try {
    const c = document.createElement('canvas');
    return !!(c.getContext('webgl2') || c.getContext('webgl'));
  } catch {
    return false;
  }
}

export default function MapView(props: Props) {
  const { points, heat, onSelect } = props;
  const el = useRef<HTMLDivElement>(null);
  const map = useRef<MLMap | null>(null);
  const [failed, setFailed] = useState(() => new URLSearchParams(window.location.search).get('map') === 'svg' || !webglOk());
  const [ready, setReady] = useState(false);
  const styleIdx = useRef(0);
  const selectRef = useRef(onSelect);
  selectRef.current = onSelect;

  useEffect(() => {
    if (failed || !el.current) return;
    let m: MLMap;
    try {
      m = new maplibregl.Map({
        container: el.current,
        style: STYLES[0]!,
        center: [-73.9893, 40.7178],
        zoom: 14.6,
        attributionControl: { compact: true },
      });
    } catch {
      setFailed(true);
      return;
    }
    map.current = m;
    m.on('error', (e) => {
      // Style or tile host failure → try the next style, then the SVG fallback.
      if (!m.isStyleLoaded() && (e.error?.message ?? '').match(/style|fetch|Failed/i)) {
        styleIdx.current += 1;
        const next = STYLES[styleIdx.current];
        if (next) m.setStyle(next);
        else setFailed(true);
      }
    });
    m.on('load', () => {
      const vibeColor: maplibregl.ExpressionSpecification = [
        'case',
        ['<', ['get', 'vibe'], 0], token('--c-none'),
        ['<', ['get', 'vibe'], 35], token('--c-chill'),
        ['<', ['get', 'vibe'], 65], token('--c-lively'),
        token('--c-packed'),
      ];
      m.addSource('venues', { type: 'geojson', data: toGeo([]) });
      m.addLayer({
        id: 'heat',
        type: 'heatmap',
        source: 'venues',
        layout: { visibility: 'none' },
        paint: {
          'heatmap-weight': ['get', 'weight'],
          'heatmap-radius': 45,
          'heatmap-intensity': 1.4,
          'heatmap-opacity': 0.75,
          'heatmap-color': [
            'interpolate', ['linear'], ['heatmap-density'],
            0, 'rgba(0,0,0,0)',
            0.3, token('--c-chill'),
            0.6, token('--c-lively'),
            1, token('--c-packed'),
          ],
        },
      });
      m.addLayer({
        id: 'dots',
        type: 'circle',
        source: 'venues',
        paint: {
          'circle-radius': ['+', 5, ['*', 9, ['get', 'conf']]],
          'circle-color': vibeColor,
          'circle-opacity': ['case', ['<', ['get', 'conf'], CONF_SHOW], 0, 0.95],
          'circle-stroke-color': vibeColor,
          'circle-stroke-width': ['case', ['<', ['get', 'conf'], CONF_SHOW], 2.5, 1],
        },
      });
      m.on('click', 'dots', (e) => {
        const id = e.features?.[0]?.properties?.venue_id;
        if (typeof id === 'string') selectRef.current(id);
      });
      m.on('mouseenter', 'dots', () => (m.getCanvas().style.cursor = 'pointer'));
      m.on('mouseleave', 'dots', () => (m.getCanvas().style.cursor = ''));
      setReady(true);
    });
    const timer = setTimeout(() => {
      if (!m.isStyleLoaded()) setFailed(true);
    }, 12000);
    return () => {
      clearTimeout(timer);
      m.remove();
      map.current = null;
    };
  }, [failed]);

  useEffect(() => {
    const m = map.current;
    if (!ready || !m) return;
    (m.getSource('venues') as GeoJSONSource | undefined)?.setData(toGeo(points));
  }, [points, ready]);
  useEffect(() => {
    const m = map.current;
    if (!ready || !m) return;
    m.setLayoutProperty('heat', 'visibility', heat ? 'visible' : 'none');
  }, [heat, ready]);

  if (failed) return <SvgDotMap {...props} />;
  return (
    <div ref={el} className="h-full w-full" data-testid="maplibre-map" data-ready={ready ? '1' : '0'} role="region" aria-label="Map of venues; tap a dot for details" />
  );
}
