import '@testing-library/jest-dom/vitest';
// jsdom lacks ResizeObserver (Recharts ResponsiveContainer).
class RO {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver ??= RO as unknown as typeof ResizeObserver;
