import { useState, type ReactNode } from 'react';
import { useLocation, useSearchParams } from 'react-router-dom';
import { DemoBanner } from '../demo/DemoBanner';
import { DemoPanel } from '../demo/DemoPanel';
import { Header } from './Header';
import { TabBar } from './TabBar';

export function AppShell({ children, notice }: { children: ReactNode; notice?: ReactNode }) {
  const [params] = useSearchParams();
  const { pathname } = useLocation();
  const wide = pathname.startsWith('/owner') || pathname.startsWith('/map');
  const [panel, setPanel] = useState(params.get('demo') === '1');
  return (
    <div className="min-h-screen pb-20">
      <a href="#main" className="sr-only focus:not-sr-only">
        Skip to content
      </a>
      <Header onSecret={() => setPanel(true)} />
      <DemoBanner />
      {notice}
      {panel && <DemoPanel onClose={() => setPanel(false)} />}
      <main id="main" className={`mx-auto px-4 pt-4 ${wide ? 'max-w-6xl' : 'max-w-[560px]'}`}>
        {children}
      </main>
      <TabBar />
    </div>
  );
}
