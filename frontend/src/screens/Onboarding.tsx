import { useReducer, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Chip } from '../components/ui/Chip';
import { Slider } from '../components/ui/Slider';
import { Toggle } from '../components/ui/Toggle';
import { GENRES, genreLabel } from '../config/genres';
import { COVER_OPTIONS, DISTANCE_OPTIONS, LES_CENTER, LINE_OPTIONS } from '../config/thresholds';
import { usePrefs } from '../state/prefs';
import { DEFAULT_PREFS, prefsReducer } from '../state/prefsReducer';

const CROWD = ['Chill', 'Relaxed', 'Buzzing', 'Busy', 'Packed'];

/** US-01: onboarding / preferences. */
export function Onboarding() {
  const { stored, save, saved } = usePrefs();
  const [p, dispatch] = useReducer(prefsReducer, stored);
  const [loc, setLoc] = useState<'pending' | 'gps' | 'center'>(
    stored.lat !== LES_CENTER.lat || stored.lon !== LES_CENTER.lon ? 'gps' : 'center',
  );
  const nav = useNavigate();

  const locate = () => {
    if (!('geolocation' in navigator)) {
      setLoc('center');
      return;
    }
    setLoc('pending');
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        dispatch({ type: 'set', patch: { lat: pos.coords.latitude, lon: pos.coords.longitude } });
        setLoc('gps');
      },
      () => {
        dispatch({ type: 'set', patch: { lat: LES_CENTER.lat, lon: LES_CENTER.lon } });
        setLoc('center');
      },
      { timeout: 4000, maximumAge: 600000 },
    );
  };

  const done = (prefs = p) => {
    save(prefs);
    nav('/tonight');
  };

  return (
    <div className="space-y-4">
      <div>
        <h1 className="font-display text-xl font-semibold">
          {saved ? 'Your group’s preferences' : 'What’s the plan tonight?'}
        </h1>
        <p className="text-sm text-muted">
          Set it once. We match it against live reports from the Lower East Side.
        </p>
      </div>
      {!saved && (
        <Button variant="secondary" className="w-full" onClick={() => done(DEFAULT_PREFS)}>
          Skip — use defaults
        </Button>
      )}
      <Card>
        <fieldset>
          <legend className="text-sm font-medium">
            Music <span className="text-muted">(pick any)</span>
          </legend>
          <div className="mt-2 flex flex-wrap gap-2">
            {GENRES.map((g) => (
              <Chip
                key={g}
                selected={p.genres.includes(g)}
                onClick={() => dispatch({ type: 'toggleGenre', genre: g })}
              >
                {genreLabel(g)}
              </Chip>
            ))}
          </div>
        </fieldset>
      </Card>
      <Card className="space-y-4">
        <Toggle
          label="We want to dance"
          checked={p.want_dancing}
          onChange={(v) => dispatch({ type: 'set', patch: { want_dancing: v } })}
        />
        <Slider
          label="Crowd"
          min={1}
          max={5}
          value={p.crowd_pref}
          valueText={`${p.crowd_pref} · ${CROWD[p.crowd_pref - 1] ?? ''}`}
          minLabel="chill"
          maxLabel="packed"
          onChange={(v) => dispatch({ type: 'set', patch: { crowd_pref: v } })}
        />
        <Slider
          label="Group size"
          min={1}
          max={12}
          value={p.group_size}
          valueText={`${p.group_size} people`}
          onChange={(v) => dispatch({ type: 'set', patch: { group_size: v } })}
        />
      </Card>
      <Card className="space-y-4">
        <fieldset>
          <legend className="text-sm font-medium">Max cover</legend>
          <div className="mt-2 flex flex-wrap gap-2">
            {COVER_OPTIONS.map((c) => (
              <Chip
                key={String(c)}
                selected={p.max_cover_usd === c}
                onClick={() => dispatch({ type: 'set', patch: { max_cover_usd: c } })}
              >
                {c === null ? 'Any' : c === 0 ? 'Free only' : `≤ $${c}`}
              </Chip>
            ))}
          </div>
        </fieldset>
        <fieldset>
          <legend className="text-sm font-medium">Max line</legend>
          <div className="mt-2 flex flex-wrap gap-2">
            {LINE_OPTIONS.map((c) => (
              <Chip
                key={String(c)}
                selected={p.max_line_minutes === c}
                onClick={() => dispatch({ type: 'set', patch: { max_line_minutes: c } })}
              >
                {c === null ? 'Any' : c === 0 ? 'No line' : `≤ ${c} min`}
              </Chip>
            ))}
          </div>
        </fieldset>
        <fieldset>
          <legend className="text-sm font-medium">How far will you walk?</legend>
          <div className="mt-2 flex flex-wrap gap-2">
            {DISTANCE_OPTIONS.map((d) => (
              <Chip
                key={d}
                selected={p.max_distance_km === d}
                onClick={() => dispatch({ type: 'set', patch: { max_distance_km: d } })}
              >
                {d} km
              </Chip>
            ))}
          </div>
        </fieldset>
        <div className="flex items-center justify-between gap-2">
          <p className="text-sm" data-testid="location-status">
            {loc === 'gps' ? 'Using your location' : loc === 'pending' ? 'Locating…' : 'Using LES center'}
          </p>
          <Button variant="secondary" onClick={locate}>
            Use my location
          </Button>
        </div>
      </Card>
      <Button className="w-full" onClick={() => done()}>
        Save & show tonight’s pick
      </Button>
    </div>
  );
}
