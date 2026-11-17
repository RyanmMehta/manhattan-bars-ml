import type { Trend } from '../../api/types';
import { Unknown } from '../ui/Unknown';

const MAP = { rising: ['↑', 'Rising', 'text-cyan'], steady: ['→', 'Steady', 'text-muted'], falling: ['↓', 'Falling', 'text-warn'] } as const;
export function TrendArrow({ trend }: { trend: Trend }) {
  if (trend === null) return <Unknown />;
  const [a, l, c] = MAP[trend];
  return <span className={c}><span aria-hidden>{a}</span> {l}</span>;
}
