// Type guards for external data + derived view helpers (camelCase allowed here only).
import { CONF_LOW, CONF_SHOW, STALE_MIN, VIBE_BANDS } from '../config/thresholds';
import { cleanVenueName } from '../lib/names';
import type * as T from './types';

type Obj = Record<string, unknown>;
const isObj = (v: unknown): v is Obj => typeof v === 'object' && v !== null && !Array.isArray(v);
const isStr = (v: unknown): v is string => typeof v === 'string';
const isNum = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);
const numOrNull = (v: unknown) => v === null || v === undefined || isNum(v);
const strOrNull = (v: unknown) => v === null || v === undefined || isStr(v);
const isStrArr = (v: unknown): v is string[] => Array.isArray(v) && v.every(isStr);

export function asErrorEnvelope(v: unknown): { code: string; message: string; details: unknown } | null {
  if (!isObj(v) || !isObj(v.error)) return null;
  const e = v.error;
  return { code: isStr(e.code) ? e.code : 'error', message: isStr(e.message) ? e.message : 'Something went wrong', details: e.details ?? null };
}

export function isHealth(v: unknown): v is T.Health {
  return isObj(v) && typeof v.ok === 'boolean';
}
export function isDemoLogin(v: unknown): v is T.DemoLoginResult {
  return isObj(v) && isStr(v.token);
}
export function isLiveState(v: unknown): v is T.LiveVenueState {
  return (
    isObj(v) && isStr(v.venue_id) &&
    numOrNull(v.crowd) && numOrNull(v.dancing) && numOrNull(v.line_minutes) && numOrNull(v.cover_usd) &&
    numOrNull(v.vibe_score) && numOrNull(v.confidence) && numOrNull(v.freshness_minutes) &&
    (v.music_genres === null || v.music_genres === undefined || isStrArr(v.music_genres))
  );
}
const crOk = (v: unknown) =>
  v === null || v === undefined || (isObj(v) && isStr(v.label) && (v.level === null || v.level === undefined || v.level === 'low' || v.level === 'medium' || v.level === 'high'));

export function isVenueCard(v: unknown): v is T.VenueCard {
  return (
        isObj(v) && isStr(v.venue_id) && isStr(v.name) && strOrNull(v.display_name) && crOk(v.complaint_risk) &&
    isNum(v.lat) && isNum(v.lon) && (v.genres === undefined || isStrArr(v.genres)) &&
    (v.state === null || v.state === undefined || isLiveState(v.state))
  );
}
export function isReport(v: unknown): v is T.ScoutReport {
  return isObj(v) && isStr(v.report_id) && isStr(v.ts) && isNum(v.crowd);
}
export function isVenueDetail(v: unknown): v is T.VenueDetail {
  return (
    isObj(v) && isVenueCard(v.venue) && (v.state === null || isLiveState(v.state)) &&
    Array.isArray(v.recent_reports) && v.recent_reports.every(isReport) && Array.isArray(v.offers)
  );
}
export function isRecommendation(v: unknown): v is T.Recommendation {
  return (
    isObj(v) && isStr(v.venue_id) && isNum(v.match_score) && numOrNull(v.vibe_score) && crOk(v.complaint_risk) &&
    numOrNull(v.confidence) && isStrArr(v.reasons) && isStrArr(v.missing) && typeof v.excluded === 'boolean'
  );
}
export function isPlanStop(v: unknown): v is T.PlanStop {
  return isObj(v) && isNum(v.order) && isStr(v.venue_id) && isStr(v.arrive_at) && isStr(v.leave_at);
}
export function isReportResult(v: unknown): v is T.ReportResult {
  return isObj(v) && isStr(v.report_id) && isStr(v.status) && isNum(v.points_pending);
}
export function isLeaderboardRow(v: unknown): v is T.LeaderboardRow {
  return isObj(v) && isNum(v.rank) && isStr(v.scout_id) && isStr(v.display_name) && isNum(v.points);
}
export function isBounty(v: unknown): v is T.Bounty {
  return isObj(v) && isStr(v.bounty_id) && isStr(v.venue_id) && isNum(v.points);
}
export function isOwnerDashboard(v: unknown): v is T.OwnerDashboard {
  return isObj(v) && isStr(v.venue_id) && isNum(v.views) && Array.isArray(v.demand_by_hour);
}
export function isHeatPoint(v: unknown): v is T.HeatPoint {
  return isObj(v) && isStr(v.venue_id) && isNum(v.lat) && isNum(v.lon) && numOrNull(v.vibe_score);
}

// ---------- view helpers ----------
export function isSynthetic(v: { is_synthetic?: T.Synthetic } | null | undefined): boolean {
  return !!v && (v.is_synthetic === true || v.is_synthetic === 1);
}

/** CONTRACTS §A display band. Prefer the backend's `display` when present. */
export function displayBand(
  s: { display?: T.Display; confidence: number | null; vibe_score: number | null } | null | undefined,
): T.Display {
  if (!s) return 'none';
  if (s.display) return s.display;
  if (s.vibe_score === null || s.confidence === null || s.confidence < CONF_LOW) return 'none';
  return s.confidence < CONF_SHOW ? 'low' : 'show';
}

export type VibeLabel = 'Chill' | 'Lively' | 'Packed';
/** CONTRACTS §J vibe label bands; null → no label. */
export function vibeLabel(vibe: number | null | undefined): VibeLabel | null {
  if (vibe === null || vibe === undefined) return null;
  const v = Math.round(vibe);
  for (const [lo, hi, label] of VIBE_BANDS) if (v >= lo && v <= hi) return label;
  return null;
}

export function isStale(freshness: number | null | undefined): boolean {
  return freshness !== null && freshness !== undefined && freshness > STALE_MIN;
}

export type ConfidenceLevel = 'Low' | 'Some' | 'Good' | 'High';
/** PRD §6: 4-bar meter 0–.25–.5–.75–1. */
export function confidenceBars(c: number | null | undefined): { bars: 0 | 1 | 2 | 3 | 4; label: ConfidenceLevel | null } {
  if (c === null || c === undefined) return { bars: 0, label: null };
  if (c >= 0.75) return { bars: 4, label: 'High' };
  if (c >= 0.5) return { bars: 3, label: 'Good' };
  if (c >= 0.25) return { bars: 2, label: 'Some' };
  return { bars: 1, label: 'Low' };
}

export function venueName(v: { display_name?: string | null; name: string }): string {
  return v.display_name && v.display_name.trim() ? v.display_name : cleanVenueName(v.name);
}

export const DANCING_LABEL = ['None', 'Some', 'Lots'] as const;
export function dancingLabel(d: number | null): string | null {
  if (d === null) return null;
  return DANCING_LABEL[Math.max(0, Math.min(2, Math.round(d)))] ?? null;
}

export function complaintLevelLabel(cr: T.ComplaintRisk | null | undefined): string | null {
  if (!cr || !cr.level) return null;
  return cr.level.charAt(0).toUpperCase() + cr.level.slice(1);
}
