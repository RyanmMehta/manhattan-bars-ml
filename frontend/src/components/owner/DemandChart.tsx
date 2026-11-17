// Lazy chunk: Recharts is only loaded on the owner dashboard (RULES §2).
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

const hourLabel = (h: number) => (h === 0 ? '12a' : h < 12 ? `${h}a` : h === 12 ? '12p' : `${h - 12}p`);

export default function DemandChart({ data }: { data: { hour: number; value: number }[] }) {
  return (
    <div className="h-48 w-full" role="img" aria-label={`Demand by hour, peak ${Math.max(...data.map((d) => d.value))} at ${hourLabel(data.reduce((a, b) => (b.value > a.value ? b : a), data[0] ?? { hour: 0, value: 0 }).hour)}`}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data.map((d) => ({ ...d, label: hourLabel(d.hour) }))} margin={{ top: 8, right: 4, left: -24, bottom: 0 }}>
          <XAxis dataKey="label" tick={{ fill: 'var(--c-muted)', fontSize: 11 }} axisLine={{ stroke: 'var(--c-line)' }} tickLine={false} />
          <YAxis tick={{ fill: 'var(--c-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
          <Tooltip cursor={{ fill: 'var(--c-raised)' }} contentStyle={{ background: 'var(--c-raised)', border: '1px solid var(--c-line)', borderRadius: 12, color: 'var(--c-ink)' }} />
          <Bar dataKey="value" name="Demand" fill="var(--c-accent)" radius={[6, 6, 0, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
