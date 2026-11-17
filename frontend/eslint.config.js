import js from '@eslint/js';
import globals from 'globals';
import tseslint from 'typescript-eslint';
import reactHooks from 'eslint-plugin-react-hooks';
import jsxA11y from 'eslint-plugin-jsx-a11y';

export default tseslint.config(
  { ignores: ['dist', 'coverage', 'public/mockServiceWorker.js', 'node_modules', 'test-results'] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: { globals: { ...globals.browser } },
    plugins: { 'react-hooks': reactHooks, 'jsx-a11y': jsxA11y },
    rules: {
      ...reactHooks.configs.recommended.rules,
      ...jsxA11y.flatConfigs.recommended.rules,
      '@typescript-eslint/no-explicit-any': 'error',
      'no-restricted-syntax': [
        'error',
        { selector: 'Literal[value=/^#[0-9a-fA-F]{3,8}$/]', message: 'No hex colour literals; use tokens.' },
      ],
    },
  },
  {
    // Null means unknown: no `?? 0` on Live Venue State fields in venue components (RULES §3).
    files: ['src/components/venue/**/*.tsx'],
    rules: {
      'no-restricted-syntax': [
        'error',
        { selector: "LogicalExpression[operator='??'][right.value=0]", message: 'Null means unknown; render <Unknown/>.' },
        { selector: "LogicalExpression[operator='||'][right.value=0]", message: 'Null means unknown; render <Unknown/>.' },
        { selector: 'Literal[value=/^#[0-9a-fA-F]{3,8}$/]', message: 'No hex colour literals; use tokens.' },
      ],
    },
  },
  {
    files: ['tailwind.config.ts'],
    rules: { 'no-restricted-syntax': 'off' },
  },
  {
    files: ['scripts/**/*.mjs', '*.config.js'],
    languageOptions: { globals: { ...globals.node } },
  },
);
