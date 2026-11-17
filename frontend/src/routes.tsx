import { Navigate, Route, Routes } from 'react-router-dom';
import { Bounties } from './screens/Bounties';
import { Browse } from './screens/Browse';
import { Leaderboard } from './screens/Leaderboard';
import { MapScreen } from './screens/MapScreen';
import { More } from './screens/More';
import { NotFound } from './screens/NotFound';
import { Onboarding } from './screens/Onboarding';
import { OwnerDashboard } from './screens/OwnerDashboard';
import { Pick } from './screens/Pick';
import { RunMyNight } from './screens/RunMyNight';
import { VenueProfile } from './screens/VenueProfile';
import { VibeCheck } from './screens/VibeCheck';
import { usePersona } from './state/persona';
import { usePrefs } from './state/prefs';

function Home() {
  const { saved, fromUrl } = usePrefs();
  return <Navigate to={saved || fromUrl ? '/tonight' : '/onboarding'} replace />;
}
function OwnerHome() {
  const { ownerVenueId } = usePersona();
  return <Navigate to={`/owner/${ownerVenueId}`} replace />;
}

/** Deep links (PRD F7). */
export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/onboarding" element={<Onboarding />} />
      <Route path="/tonight" element={<Pick />} />
      <Route path="/browse" element={<Browse />} />
      <Route path="/map" element={<MapScreen />} />
      <Route path="/venue/:venueId" element={<VenueProfile />} />
      <Route path="/scout" element={<VibeCheck />} />
      <Route path="/scout/leaderboard" element={<Leaderboard />} />
      <Route path="/scout/bounties" element={<Bounties />} />
      <Route path="/plan" element={<RunMyNight />} />
      <Route path="/owner" element={<OwnerHome />} />
      <Route path="/owner/:venueId" element={<OwnerDashboard />} />
      <Route path="/more" element={<More />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
