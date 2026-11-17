// TanStack Query hooks. All API reads go through these (RULES §2).
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { REFRESH_MS } from '../config/thresholds';
import { useDemoClock } from '../state/demoClock';
import { api } from './client';
import type * as T from './types';

export function prefsHash(p: T.Preferences): string {
  return JSON.stringify(p);
}

export interface VenueFilters {
  q?: string;
  style?: string;
  genre?: string;
  lat?: number;
  lon?: number;
}

export function useVenues(f: VenueFilters) {
  const { now } = useDemoClock();
  return useQuery({
    queryKey: ['venues', f, now],
    queryFn: () => api.venues({ ...f, limit: 50 }),
    placeholderData: keepPreviousData,
  });
}
export function useVenue(id: string | undefined) {
  const { now } = useDemoClock();
  return useQuery({ queryKey: ['venue', id, now], queryFn: () => api.venue(id ?? ''), enabled: !!id });
}
export function useRecommend(prefs: T.Preferences) {
  const { now } = useDemoClock();
  return useQuery({
    queryKey: ['recommend', prefsHash(prefs), now],
    queryFn: () => api.recommend(prefs),
    refetchInterval: REFRESH_MS,
    refetchIntervalInBackground: false,
    placeholderData: keepPreviousData,
  });
}
export function useHeatmap(byHour: boolean) {
  const { now } = useDemoClock();
  return useQuery({
    queryKey: ['heatmap', now, byHour],
    queryFn: () => api.heatmap(byHour),
    refetchInterval: REFRESH_MS,
    placeholderData: keepPreviousData,
  });
}
export function useLeaderboard() {
  const { now } = useDemoClock();
  return useQuery({ queryKey: ['leaderboard', now], queryFn: () => api.leaderboard() });
}
export function useBounties() {
  const { now } = useDemoClock();
  return useQuery({ queryKey: ['bounties', now], queryFn: () => api.bounties() });
}
export function useOwnerDashboard(id: string | undefined) {
  const { now } = useDemoClock();
  return useQuery({ queryKey: ['owner', id, now], queryFn: () => api.ownerDashboard(id ?? ''), enabled: !!id });
}
export function usePlan(prefs: T.Preferences, n: number, enabled: boolean) {
  const { now } = useDemoClock();
  return useQuery({
    queryKey: ['plan', prefsHash(prefs), n, now],
    queryFn: () => api.planNight({ ...prefs, n_stops: n }),
    enabled,
    placeholderData: keepPreviousData,
  });
}

export function useSubmitReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (i: T.ReportInput) => api.report(i),
    onSuccess: () => {
      for (const k of ['venue', 'venues', 'recommend', 'heatmap', 'leaderboard', 'bounties']) {
        void qc.invalidateQueries({ queryKey: [k] });
      }
    },
  });
}
export function useOwnerUpdate(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (u: Omit<T.VenueUpdate, 'update_id' | 'ts' | 'venue_id'>) => api.ownerUpdate(id, u),
    onSuccess: () => {
      for (const k of ['venue', 'venues', 'owner', 'recommend']) void qc.invalidateQueries({ queryKey: [k] });
    },
  });
}
