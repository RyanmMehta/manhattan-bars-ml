import { useId } from 'react';

export function Slider({ label, min, max, step = 1, value, onChange, valueText, minLabel, maxLabel }: {
  label: string; min: number; max: number; step?: number; value: number; onChange: (v: number) => void;
  valueText?: string; minLabel?: string; maxLabel?: string;
}) {
  const id = useId();
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <label htmlFor={id} className="text-sm font-medium">{label}</label>
        <span className="font-display text-sm text-cyan">{valueText ?? value}</span>
      </div>
      <input
        id={id} type="range" min={min} max={max} step={step} value={value}
        aria-valuetext={valueText}
        onChange={(e) => onChange(Number(e.target.value))}
        className="mt-2 h-11 w-full accent-[var(--c-accent)]"
      />
      {(minLabel || maxLabel) && (
        <div className="flex justify-between text-xs text-muted"><span>{minLabel}</span><span>{maxLabel}</span></div>
      )}
    </div>
  );
}
