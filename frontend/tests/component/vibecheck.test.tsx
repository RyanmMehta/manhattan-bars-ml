// US-06: VibeCheckForm submits the right body.
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { VibeCheckForm } from '../../src/components/venue/VibeCheckForm';

describe('VibeCheckForm (US-06)', () => {
  it('is disabled until venue, crowd, dancing and line are set', async () => {
    const u = userEvent.setup();
    const on = vi.fn();
    render(<VibeCheckForm venueId="v1" location={null} onSubmit={on} />);
    const send = screen.getByRole('button', { name: 'Send vibe check' });
    expect(send).toBeDisabled();
    await u.click(screen.getByRole('button', { name: 'Crowd 4: Busy' }));
    await u.click(screen.getByRole('button', { name: 'Lots' }));
    await u.click(screen.getByRole('button', { name: '10' }));
    expect(send).toBeEnabled();
    await u.click(send);
    expect(on).toHaveBeenCalledWith({ venue_id: 'v1', crowd: 4, dancing: 2, line_minutes: 10 });
  });
  it('adds optional cover, genre and location', async () => {
    const u = userEvent.setup();
    const on = vi.fn();
    render(<VibeCheckForm venueId="v1" location={{ lat: 40.7, lon: -73.9 }} onSubmit={on} />);
    await u.click(screen.getByRole('button', { name: 'Crowd 2: Quiet' }));
    await u.click(screen.getByRole('button', { name: 'None' }));
    await u.click(screen.getByRole('button', { name: '30+' }));
    await u.click(screen.getByRole('button', { name: /cover & music/ }));
    await u.type(screen.getByLabelText('Cover ($)'), '20');
    await u.selectOptions(screen.getByLabelText('Music'), 'house');
    await u.click(screen.getByRole('button', { name: 'Send vibe check' }));
    expect(on).toHaveBeenCalledWith({ venue_id: 'v1', crowd: 2, dancing: 0, line_minutes: 30, cover_usd: 20, music_genre: 'house', lat: 40.7, lon: -73.9 });
  });
  it('no venue → cannot submit', () => {
    render(<VibeCheckForm venueId={null} location={null} onSubmit={vi.fn()} />);
    expect(screen.getByRole('button', { name: 'Send vibe check' })).toBeDisabled();
  });
});
