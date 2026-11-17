import { NavLink } from 'react-router-dom';

const TABS = [
  { to: '/tonight', label: 'Pick', icon: '★' },
  { to: '/browse', label: 'Browse', icon: '☰' },
  { to: '/map', label: 'Map', icon: '◎' },
  { to: '/scout', label: 'Scout', icon: '✎' },
  { to: '/more', label: 'More', icon: '…' },
];
export function TabBar() {
  return (
    <nav aria-label="Main" className="fixed inset-x-0 bottom-0 z-20 border-t border-line bg-bg/95 backdrop-blur">
      <ul className="mx-auto flex max-w-[560px] justify-around">
        {TABS.map((t) => (
          <li key={t.to} className="flex-1">
            <NavLink to={t.to} end={t.to === '/scout'}
              className={({ isActive }) => `flex min-h-[56px] flex-col items-center justify-center text-xs ${isActive ? 'text-accent' : 'text-muted hover:text-ink'}`}>
              <span aria-hidden className="text-lg leading-none">{t.icon}</span>
              {t.label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
