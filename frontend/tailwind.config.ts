import type { Config } from 'tailwindcss';

// Design tokens (PRD §6). Hex literals live only here and in src/styles/tokens.css.
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: 'var(--c-bg)',
        surface: 'var(--c-surface)',
        raised: 'var(--c-raised)',
        line: 'var(--c-line)',
        ink: 'var(--c-ink)',
        muted: 'var(--c-muted)',
        accent: 'var(--c-accent)',
        cyan: 'var(--c-cyan)',
        warn: 'var(--c-warn)',
        danger: 'var(--c-danger)',
        chill: 'var(--c-chill)',
        lively: 'var(--c-lively)',
        packed: 'var(--c-packed)',
        none: 'var(--c-none)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['"Space Grotesk"', 'Inter', 'system-ui', 'sans-serif'],
      },
      fontSize: { xs: '12px', sm: '14px', base: '16px', lg: '20px', xl: '28px', '2xl': '40px' },
      borderRadius: { md: '12px', lg: '20px' },
      transitionDuration: { DEFAULT: '150ms' },
    },
  },
  plugins: [],
} satisfies Config;
