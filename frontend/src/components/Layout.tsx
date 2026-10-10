import { NavLink, Link, Outlet } from 'react-router-dom';

const navItems = [
  { to: '/', label: 'Start', icon: '⌂' },
  { to: '/kosten', label: 'Kosten', icon: '€' },
  { to: '/vergleich', label: 'Vergleich', icon: '◫' },
  { to: '/tarife', label: 'Tarife', icon: '§' },
  { to: '/einstellungen', label: 'Einstellungen', icon: '✦' },
];

export function Layout() {
  return (
    <>
      <header className="app-header">
        <Link to="/" className="app-title">
          Verbrauchstracker
        </Link>
        <nav className="desktop-nav" aria-label="Hauptnavigation">
          {navItems.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.to === '/'}>
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
      <nav className="app-nav" aria-label="Hauptnavigation (mobil)">
        {navItems.map((item) => (
          <NavLink key={item.to} to={item.to} end={item.to === '/'}>
            <span className="nav-icon" aria-hidden="true">
              {item.icon}
            </span>
            {item.label}
          </NavLink>
        ))}
      </nav>
    </>
  );
}
