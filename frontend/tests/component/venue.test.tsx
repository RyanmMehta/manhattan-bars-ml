// US-02/US-03/US-11 component tests: null, low-confidence, stale and synthetic cases.
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import type { LiveVenueState, Recommendation, VenueCard as Card } from '../../src/api/types';
import { DemoBadge } from '../../src/components/demo/DemoBadge';
import { ConfidenceMeter } from '../../src/components/venue/ConfidenceMeter';
import { FilterBar, type FilterValue } from '../../src/components/venue/FilterBar';
import { PickHero } from '../../src/components/venue/PickHero';
import { VenueCard } from '../../src/components/venue/VenueCard';
import { VibeBadge } from '../../src/components/venue/VibeBadge';
import { StateBlock } from '../../src/components/venue/StateBlock';
import { VenueCardCompact } from '../../src/components/venue/VenueCardCompact';

const state = (p: Partial<LiveVenueState> = {}): LiveVenueState => ({
  venue_id: 'v1', crowd: 3.8, dancing: 1.4, line_minutes: 10, cover_usd: 15, music_genres: ['hip-hop'],
  vibe_score: 78, confidence: 0.71, freshness_minutes: 12, n_reports: 4, trend: 'rising', sources: ['scout'], is_synthetic: true, ...p,
});
const card = (s: LiveVenueState | null, syn: 0 | 1 = 1): Card => ({
  venue_id: 'v1', name: 'APT 5 LLC', display_name: null, style: 'club', genres: ['hip-hop'], price_level: 2, typical_cover_usd: 10,
  lat: 40.7, lon: -73.9, distance_km: 0.4, opening_hours: null, is_claimed: 0, state: s, complaint_risk: 0.3, is_synthetic: syn,
});
const rec = (p: Partial<Recommendation> = {}): Recommendation => ({
  venue_id: 'v1', name: 'Subject', match_score: 91, vibe_score: 78, confidence: 0.71, distance_km: 0.3,
  reasons: ['Hip-hop playing', 'Line ~10 min'], missing: ['cover not reported tonight'], excluded: false, rank: 1,
  freshness_minutes: 12, n_reports: 4, is_synthetic: true, ...p,
});
const wrap = (ui: JSX.Element) => render(<MemoryRouter>{ui}</MemoryRouter>);

describe('VibeBadge', () => {
  it('shows number + label (colour never alone)', () => {
    render(<VibeBadge vibe={78} confidence={0.71} />);
    expect(screen.getByTestId('vibe-badge')).toHaveTextContent('78Packed');
  });
  it('low confidence is greyed and labelled', () => {
    render(<VibeBadge vibe={50} confidence={0.3} />);
    expect(screen.getByTestId('vibe-badge')).toHaveAttribute('data-band', 'low');
    expect(screen.getByText('low confidence')).toBeInTheDocument();
  });
  it('null / very low → No fresh reports', () => {
    const { rerender } = render(<VibeBadge vibe={null} confidence={0.9} />);
    expect(screen.getByText('No fresh reports')).toBeInTheDocument();
    rerender(<VibeBadge vibe={70} confidence={0.1} />);
    expect(screen.getByText('No fresh reports')).toBeInTheDocument();
  });
  it('honours backend display', () => {
    render(<VibeBadge vibe={70} confidence={0.9} display="none" />);
    expect(screen.getByTestId('vibe-badge')).toHaveAttribute('data-band', 'none');
  });
});

describe('ConfidenceMeter', () => {
  it('labels levels and unknown', () => {
    const { rerender } = render(<ConfidenceMeter confidence={0.8} />);
    expect(screen.getByRole('img')).toHaveAccessibleName('Confidence High (80%)');
    rerender(<ConfidenceMeter confidence={null} />);
    expect(screen.getByRole('img')).toHaveAccessibleName('Confidence unknown');
  });
});

describe('DemoBadge (US-11)', () => {
  it('renders only for synthetic data', () => {
    const { rerender } = render(<DemoBadge data={{ is_synthetic: 1 }} />);
    expect(screen.getByTestId('demo-badge')).toHaveTextContent('demo data');
    rerender(<DemoBadge data={{ is_synthetic: 0 }} />);
    expect(screen.queryByTestId('demo-badge')).toBeNull();
    rerender(<DemoBadge force />);
    expect(screen.getByTestId('demo-badge')).toBeInTheDocument();
  });
});

describe('VenueCard (US-03)', () => {
  it('renders fields, cleaned name and badge', () => {
    wrap(<VenueCard venue={card(state())} />);
    expect(screen.getByRole('link', { name: 'Apt 5' })).toHaveAttribute('href', '/venue/v1');
    expect(screen.getByText('~10 min')).toBeInTheDocument();
    expect(screen.getByText('$15')).toBeInTheDocument();
    expect(screen.getByTestId('demo-badge')).toBeInTheDocument();
  });
  it('null fields render "not reported", never 0', () => {
    wrap(<VenueCard venue={card(state({ line_minutes: null, cover_usd: null }), 0)} />);
    expect(screen.getAllByText('not reported')).toHaveLength(2);
    expect(screen.queryByText('$0')).toBeNull();
    expect(screen.queryByTestId('demo-badge')).toBeNull();
  });
  it('null state', () => {
    wrap(<VenueCard venue={card(null)} />);
    expect(screen.getByText('No fresh reports')).toBeInTheDocument();
    expect(screen.getByText('no recent reports')).toBeInTheDocument();
  });
  it('stale tag over 60 min', () => {
    wrap(<VenueCard venue={card(state({ freshness_minutes: 75 }))} />);
    expect(screen.getByTestId('stale-tag')).toBeInTheDocument();
  });
});

describe('StateBlock (US-04)', () => {
  it('unknowns stay unknown', () => {
    render(<StateBlock s={state({ crowd: null, dancing: null, trend: null, music_genres: [] })} />);
    expect(screen.getAllByText('not reported').length).toBeGreaterThanOrEqual(4);
  });
});

describe('PickHero (US-02)', () => {
  it('shows scores, reasons, missing, freshness', () => {
    wrap(<PickHero rec={rec()} />);
    expect(screen.getByRole('heading', { name: 'Subject' })).toBeInTheDocument();
    expect(screen.getByText('91')).toBeInTheDocument();
    expect(screen.getByText('Hip-hop playing')).toBeInTheDocument();
    expect(screen.getByText('cover not reported tonight')).toBeInTheDocument();
    expect(screen.getByText(/updated 12 min ago/)).toBeInTheDocument();
    expect(screen.queryByText('Be the Scout')).toBeNull();
  });
  it('no fresh reports → Be the Scout', () => {
    wrap(<PickHero rec={rec({ confidence: 0.1 })} />);
    expect(screen.getByRole('link', { name: 'Be the Scout' })).toHaveAttribute('href', '/scout?venue=v1');
  });
  it('low confidence and stale', () => {
    wrap(<PickHero rec={rec({ confidence: 0.3, freshness_minutes: 90 })} />);
    expect(screen.getByText('low confidence')).toBeInTheDocument();
    expect(screen.getByTestId('stale-tag')).toBeInTheDocument();
  });
  it('excluded compact card shows the reason', () => {
    wrap(<ul><VenueCardCompact rec={rec({ excluded: true, excluded_reason: 'Line ~30 min, over your 15-min limit' })} excluded /></ul>);
    expect(screen.getByText(/Excluded: Line ~30 min/)).toBeInTheDocument();
  });
});

describe('FilterBar (US-03)', () => {
  it('emits search, style, genre, sort', async () => {
    const u = userEvent.setup();
    const v: FilterValue = { q: '', style: '', genre: '', sort: 'vibe' };
    const on = vi.fn();
    render(<FilterBar value={v} onChange={on} />);
    await u.type(screen.getByLabelText('Search venues'), 'a');
    expect(on).toHaveBeenLastCalledWith({ ...v, q: 'a' });
    await u.selectOptions(screen.getByLabelText('Style'), 'club');
    expect(on).toHaveBeenLastCalledWith({ ...v, style: 'club' });
    await u.selectOptions(screen.getByLabelText('Genre'), 'r&b');
    expect(on).toHaveBeenLastCalledWith({ ...v, genre: 'r&b' });
    await u.selectOptions(screen.getByLabelText('Sort'), 'distance');
    expect(on).toHaveBeenLastCalledWith({ ...v, sort: 'distance' });
  });
});
