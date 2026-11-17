// Route walk in jsdom against the MSW handlers: providers, query hooks, screens, badges (US-01..US-11).
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { setupServer } from 'msw/node';
import { MemoryRouter } from 'react-router-dom';
import { Providers, makeQueryClient } from '../../src/App';
import { configureClient, setToken } from '../../src/api/client';
import { AppShell } from '../../src/components/layout/AppShell';
import { createDb } from '../../src/mocks/db';
import { makeHandlers } from '../../src/mocks/handlers';
import { AppRoutes } from '../../src/routes';
import { DEFAULT_PREFS, PREFS_KEY } from '../../src/state/prefsReducer';

const BASE = 'http://localhost/api';
const NOW = '2026-11-14T23:30:00-05:00';
let server: ReturnType<typeof setupServer>;
const PREFS = { ...DEFAULT_PREFS, genres: ['hip-hop', 'r&b'], want_dancing: true, crowd_pref: 4, lat: 40.7203, lon: -73.9881 };

beforeAll(() => {
  configureClient({ base: BASE });
});
beforeEach(() => {
  server = setupServer(...makeHandlers(createDb(), BASE));
  server.listen({ onUnhandledRequest: 'bypass' });
  localStorage.clear();
  sessionStorage.clear();
  setToken(null);
});
afterEach(() => server.close());

function renderAt(path: string, prefs: typeof PREFS | null = PREFS) {
  if (prefs) localStorage.setItem(PREFS_KEY, JSON.stringify(prefs));
  const sep = path.includes('?') ? '&' : '?';
  return render(
    <MemoryRouter initialEntries={[`${path}${sep}now=${encodeURIComponent(NOW)}`]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Providers mode="mock" health={{ ok: true, data: 'synthetic', demo_now: NOW }} client={makeQueryClient()}>
        <AppShell>
          <AppRoutes />
        </AppShell>
      </Providers>
    </MemoryRouter>,
  );
}

describe('route walk (mock mode)', () => {
  it('/ without prefs → onboarding; skip uses defaults (US-01 AC4)', async () => {
    const u = userEvent.setup();
    renderAt('/', null);
    await u.click(await screen.findByRole('button', { name: /Skip/ }));
    expect(await screen.findByTestId('pick-hero')).toBeInTheDocument();
    expect(JSON.parse(localStorage.getItem(PREFS_KEY)!)).toEqual(DEFAULT_PREFS);
  });
  it('onboarding saves chosen prefs', async () => {
    const u = userEvent.setup();
    renderAt('/onboarding', null);
    await u.click(await screen.findByRole('button', { name: 'Hip-hop' }));
    await u.click(screen.getByRole('switch', { name: /dance/ }));
    await u.click(screen.getByRole('button', { name: '≤ 10 min' }));
    expect(screen.getByTestId('location-status')).toHaveTextContent('Using LES center');
    await u.click(screen.getByRole('button', { name: /Save/ }));
    const saved = JSON.parse(localStorage.getItem(PREFS_KEY)!);
    expect(saved.genres).toEqual(['hip-hop']);
    expect(saved.want_dancing).toBe(true);
    expect(saved.max_line_minutes).toBe(10);
  });
  it('/tonight shows hero, alternatives, excluded toggle, banner (US-02)', async () => {
    const u = userEvent.setup();
    renderAt('/tonight');
    const hero = await screen.findByTestId('pick-hero');
    expect(within(hero).getByText('Subject')).toBeInTheDocument();
    expect(within(hero).getByText('91')).toBeInTheDocument();
    expect(screen.getAllByTestId('alt-card')).toHaveLength(4);
    await u.click(screen.getByRole('button', { name: 'Show 3 excluded' }));
    expect(screen.getAllByTestId('excluded-card')).toHaveLength(3);
    expect(screen.getByTestId('demo-banner')).toHaveTextContent('Demo data: simulated Sat, Nov 14');
    await u.click(screen.getByRole('button', { name: 'Share pick' }));
    expect(await screen.findByText(/Link copied/)).toBeInTheDocument();
  });
  it('/browse filters and clears (US-03)', async () => {
    const u = userEvent.setup();
    renderAt('/browse');
    await waitFor(() => expect(screen.getAllByTestId('venue-card')).toHaveLength(35));
    await u.type(screen.getByLabelText('Search venues'), 'zzzz');
    expect(await screen.findByText('No venues match', {}, { timeout: 3000 })).toBeInTheDocument();
    await u.click(screen.getByRole('button', { name: 'Clear filters' }));
    await waitFor(() => expect(screen.getAllByTestId('venue-card')).toHaveLength(35));
    await u.selectOptions(screen.getByLabelText('Sort'), 'name');
    await u.selectOptions(screen.getByLabelText('Style'), 'club');
    await waitFor(() => expect(screen.getAllByTestId('venue-card').length).toBeLessThan(35));
  });
  it('/venue/:id profile (US-04)', async () => {
    renderAt('/venue/0370-21-116653');
    expect(await screen.findByRole('heading', { name: 'Subject' })).toBeInTheDocument();
    expect(screen.getByTestId('directions')).toHaveAttribute('href', expect.stringContaining('40.7'));
    expect(screen.getByText('311 noise-complaint risk')).toBeInTheDocument();
    expect(screen.getAllByTestId('demo-badge').length).toBeGreaterThan(0);
    await userEvent.setup().click(screen.getByRole('button', { name: 'Rate 4 of 5' }));
    expect(await screen.findByText(/Thanks/)).toBeInTheDocument();
  });
  it('/scout vibe check submits and pays points (US-06)', async () => {
    const u = userEvent.setup();
    renderAt('/scout?venue=0370-23-131873');
    await u.click(await screen.findByRole('button', { name: 'Crowd 3: Buzzing' }));
    await u.click(screen.getByRole('button', { name: 'Some' }));
    await u.click(screen.getByRole('button', { name: '5' }));
    expect(screen.getByTestId('presence-hint')).toBeInTheDocument();
    await u.click(screen.getByRole('button', { name: 'Send vibe check' }));
    expect(await screen.findByText(/\+60 pts pending/)).toBeInTheDocument();
  });
  it('/scout/leaderboard and bounties (US-07)', async () => {
    const u = userEvent.setup();
    renderAt('/scout/leaderboard');
    expect(await screen.findByTestId('me-row')).toHaveTextContent('Demo Scout');
    await u.click(screen.getByRole('tab', { name: 'All time' }));
    expect(screen.getAllByTestId('lb-row').length).toBeGreaterThan(5);
  });
  it('/scout/bounties', async () => {
    renderAt('/scout/bounties');
    const b = await screen.findAllByTestId('bounty');
    expect(b[0]).toHaveTextContent('50');
    expect(b[0]).toHaveAttribute('href', '/scout?venue=0370-23-131873');
  });
  it('/plan with swap (US-08)', async () => {
    const u = userEvent.setup();
    renderAt('/plan');
    const stops = await screen.findAllByTestId('plan-stop');
    expect(stops).toHaveLength(3);
    const first = within(stops[0]!).getByRole('link').textContent;
    await u.click(within(stops[0]!).getByRole('button', { name: 'Swap stop' }));
    await waitFor(() => expect(within(screen.getAllByTestId('plan-stop')[0]!).getByRole('link').textContent).not.toBe(first));
  });
  it('/owner posts an update with preview (US-09)', async () => {
    const u = userEvent.setup();
    renderAt('/owner');
    expect(await screen.findByTestId('kpis')).toBeInTheDocument();
    await u.type(screen.getByLabelText('Offer'), '$10 cover before midnight');
    await u.type(screen.getByLabelText('DJ'), 'Balkan Beat');
    expect(screen.getByTestId('offer-card')).toHaveTextContent('$10 cover before midnight');
    await u.click(screen.getByRole('button', { name: 'Post update' }));
    expect(await screen.findByText(/Update posted/)).toBeInTheDocument();
  });
  it('/more, 404, demo panel (US-10)', async () => {
    const u = userEvent.setup();
    renderAt('/nope?demo=1');
    expect(screen.getByText('Nothing here')).toBeInTheDocument();
    const panel = screen.getByTestId('demo-panel');
    await u.click(within(panel).getByRole('button', { name: '−1 h' }));
    await u.click(within(panel).getByRole('button', { name: 'Scout' }));
    expect(await screen.findByText('Logged in as demo scout')).toBeInTheDocument();
    await u.click(within(panel).getByRole('switch', { name: /synthetic outline/ }));
    expect(document.documentElement.classList.contains('syn-outline')).toBe(true);
    await u.click(screen.getByRole('link', { name: /More/ }));
    expect(await screen.findByText('Owner dashboard')).toBeInTheDocument();
  });
});
