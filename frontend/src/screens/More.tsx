import { Link } from 'react-router-dom';
import { env } from '../config/env';
import { usePersona } from '../state/persona';
import { DemoBadge } from '../components/demo/DemoBadge';

export function More() {
  const { ownerVenueId } = usePersona();
  const links = [
    { to: '/onboarding', label: 'Group preferences', hint: 'Music, crowd, cover, line, distance' },
    ...(env.featureRouting ? [{ to: '/plan', label: 'Run my night', hint: 'A 2–4 stop plan with walk times' }] : []),
    { to: '/scout/leaderboard', label: 'Scout leaderboard', hint: 'Points this week and all time' },
    { to: '/scout/bounties', label: 'Open bounties', hint: 'Venues that need a fresh report' },
    { to: `/owner/${ownerVenueId}`, label: 'Owner dashboard', hint: 'Post cover, DJ and offers; see demand' },
    { to: '/tonight?demo=1', label: 'Demo panel', hint: 'Persona, time travel, API mode' },
  ];
  return (
    <div className="space-y-3">
      <h1 className="font-display text-xl font-semibold">More</h1>
      <ul className="space-y-2">
        {links.map((l) => (
          <li key={l.to}>
            <Link to={l.to} className="block min-h-[44px] rounded-lg border border-line bg-surface p-3 hover:border-accent">
              <span className="block font-medium">{l.label}</span>
              <span className="block text-xs text-muted">{l.hint}</span>
            </Link>
          </li>
        ))}
      </ul>
      <p className="text-xs text-muted">
        Everything marked <DemoBadge force /> is simulated. See docs/synthetic/frontend.md for each dataset and how to
        swap it for real data.
      </p>
    </div>
  );
}
