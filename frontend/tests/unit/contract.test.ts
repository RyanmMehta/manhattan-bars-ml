// Contract test: TS type guards accept the CONTRACTS.md example per endpoint.
import * as g from '../../src/api/adapters';
import live from '../../src/mocks/fixtures/contract-samples/live_state.json';
import recs from '../../src/mocks/fixtures/contract-samples/recommendation.json';
import cards from '../../src/mocks/fixtures/contract-samples/venue_card.json';
import detail from '../../src/mocks/fixtures/contract-samples/venue_detail.json';
import report from '../../src/mocks/fixtures/contract-samples/report_result.json';
import board from '../../src/mocks/fixtures/contract-samples/leaderboard.json';
import bounties from '../../src/mocks/fixtures/contract-samples/bounties.json';
import owner from '../../src/mocks/fixtures/contract-samples/owner_dashboard.json';
import heat from '../../src/mocks/fixtures/contract-samples/heatmap.json';
import plan from '../../src/mocks/fixtures/contract-samples/plan_night.json';
import health from '../../src/mocks/fixtures/contract-samples/health.json';
import errorEnv from '../../src/mocks/fixtures/contract-samples/error.json';

describe('contract samples satisfy type guards', () => {
  it.each([
    ['live state', live, g.isLiveState],
    ['venue detail', detail, g.isVenueDetail],
    ['report result', report, g.isReportResult],
    ['owner dashboard', owner, g.isOwnerDashboard],
    ['health', health, g.isHealth],
  ] as const)('%s', (_n, v, guard) => expect(guard(v)).toBe(true));
  it.each([
    ['recommendation', recs, g.isRecommendation],
    ['venue card', cards, g.isVenueCard],
    ['leaderboard', board, g.isLeaderboardRow],
    ['bounty', bounties, g.isBounty],
    ['heatmap', heat, g.isHeatPoint],
    ['plan stop', plan, g.isPlanStop],
  ] as const)('%s list', (_n, v, guard) => expect((v as unknown[]).every((x) => guard(x))).toBe(true));
  it('error envelope', () => {
    expect(g.asErrorEnvelope(errorEnv)).toEqual({ code: 'validation_error', message: 'crowd must be 1-5', details: { field: 'crowd' } });
  });
  it('rejects a wrong shape', () => {
    expect(g.isLiveState({ venue_id: 'x', crowd: 'lots' })).toBe(false);
    expect(g.isRecommendation({ venue_id: 'x' })).toBe(false);
  });
});
