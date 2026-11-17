import { dayLabel, clockLabel } from '../../lib/time';
import { useDataMode } from '../../state/dataMode';
import { useDemoClock } from '../../state/demoClock';

export function DemoBanner() {
  const { synthetic, mode } = useDataMode();
  const { now } = useDemoClock();
  if (!synthetic) return null;
  return (
    <div data-testid="demo-banner" role="note" className="border-b border-warn/40 bg-warn/10 px-4 py-1.5 text-center text-xs text-warn">
      Demo data: simulated {now ? `${dayLabel(now)}, ${clockLabel(now)}` : 'night'}
      {mode === 'mock' ? ' · offline mock API' : ''}
    </div>
  );
}
